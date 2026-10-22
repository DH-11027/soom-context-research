"""Post-freeze audit from raw rows, without calling evaluator summary functions.

All summaries/comparisons are recomputed here with standard-library arithmetic.
A separate replay checks the declared directory ablation's complete resident
state. It uses the frozen runtime, no gold interpreter and no timing claims.
Existing artifacts are read-only; --output must be a new JSON path.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
METHODS = ("fresh", "lru", "selective", "no_directory")
STAGES = ("cheap", "contract", "detail")
OVERHEAD = ("key_build_bytes", "key_probe_bytes", "value_encode_bytes",
            "cache_read_payload_bytes", "cache_write_bytes")
OBSERVATIONS = ("status", "prediction", "selected", "output_bytes",
                "remaining_input_facts", "scope_trace", "reason", "rendered_sha256")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze():
    frozen = json.loads((HERE / "freeze.json").read_text())
    for name, expected in frozen["hashes"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in frozen["baseline_hashes"].items():
        assert sha(ROOT / name) == expected, name


def compare_direct(rows, candidate, reference, weight=8):
    pairs = defaultdict(dict)
    for row in rows:
        if row["method"] in (candidate, reference):
            pairs[(row["stream_id"], row["step_index"])][row["method"]] = row
    before = after = cb = ca = fewer = lower = equal = 0
    stream_deltas = defaultdict(list)
    for (stream, index), pair in sorted(pairs.items()):
        assert set(pair) == {candidate, reference}
        b, a = pair[reference]["cost"], pair[candidate]["cost"]
        score_b = b["phase07_work_proxy"] + weight * b["control_actions"]
        score_a = a["phase07_work_proxy"] + weight * a["control_actions"]
        call_b = sum(b[s + "_calls"] for s in STAGES)
        call_a = sum(a[s + "_calls"] for s in STAGES)
        before += score_b
        after += score_a
        cb += call_b
        ca += call_a
        fewer += call_a < call_b
        lower += score_a < score_b
        equal += score_a == score_b
        stream_deltas[stream].append((index, score_a - score_b))
    streams = []
    for stream, values in sorted(stream_deltas.items()):
        cumulative = []
        total = 0
        for _, value in values:
            total += value
            cumulative.append(total)
        negative = [i + 1 for i, value in enumerate(cumulative) if value < 0]
        nonnegative = [i + 1 for i, value in enumerate(cumulative) if value >= 0]
        stable = None if not cumulative or cumulative[-1] >= 0 else ((max(nonnegative) + 1) if nonnegative else 1)
        streams.append({"stream_id": stream, "cumulative_delta": cumulative,
                        "first_strict_break_even_step": min(negative) if negative else None,
                        "sustained_break_even_step": stable, "total_delta": total})
    return {"candidate": candidate, "reference": reference, "control_action_weight": weight,
            "paired_queries": len(pairs), "before_score": before, "after_score": after,
            "score_change_percent": 100 * (after / before - 1) if before else None,
            "parser_executions_before": cb, "parser_executions_after": ca,
            "parser_execution_reduction_percent": 100 * (1 - ca / cb) if cb else None,
            "queries_with_fewer_parser_executions": fewer,
            "queries_with_lower_score": lower, "queries_with_equal_score": equal,
            "streams": streams}


def recount(name):
    summary_path = HERE / "results" / (name + "_results.json")
    row_path = HERE / "results" / (name + "_rows.json.gz")
    stored = json.loads(summary_path.read_text())
    raw = gzip.decompress(row_path.read_bytes())
    rows = json.loads(raw)
    assert stored["raw_rows"]["sha256"] == sha(row_path)
    assert stored["raw_rows"]["count"] == len(rows)
    assert stored["raw_rows"]["uncompressed_bytes"] == len(raw)
    pairs = defaultdict(dict)
    for row in rows:
        pairs[(row["stream_id"], row["step_index"])][row["method"]] = row
        c = row["cost"]
        for stage in STAGES:
            assert c[stage + "_requests"] == c[stage + "_calls"] + c[stage + "_reused"]
        assert c["cache_lookups"] == c["cache_entry_hits"] + c["cache_entry_misses"]
        assert c["cache_overhead_bytes"] == sum(c[k] for k in OVERHEAD)
        parser_bytes = sum(c[s + "_source_bytes"] for s in STAGES) + c["reparse_source_bytes"]
        assert c["source_work_bytes"] == c["hash_serialized_bytes"] + parser_bytes
        assert c["output_plus_source_work_proxy"] == row["output_bytes"] + c["source_work_bytes"]
        assert c["phase07_work_proxy"] == row["output_bytes"] + c["source_work_bytes"] + c["cache_overhead_bytes"]
        assert c["control_actions"] == sum(c["control_events"].values())
        assert c["phase08_work_score"] == c["phase07_work_proxy"] + 8 * c["control_actions"]
        assert c["cache_retained_bytes"] <= c["cache_peak_bytes"] <= 65536
        assert c["cache_entries"] <= c["cache_peak_entries"] <= 64
        if not row["valid_snapshot"] or not row["supported"]:
            assert c["cache_lookups"] == c["control_actions"] == 0
    for key, pair in pairs.items():
        assert set(pair) == set(METHODS), key
        baseline = pair["fresh"]
        for method, row in pair.items():
            assert not row["parity_failures"]
            for field in OBSERVATIONS:
                assert row.get(field) == baseline.get(field), (key, method, field)
            for stage in STAGES:
                assert row["cost"][stage + "_requests"] == baseline["cost"][stage + "_calls"]
            assert row["cost"]["hash_serialized_bytes"] == baseline["cost"]["hash_serialized_bytes"]
            assert row["cost"]["hash_calls"] == baseline["cost"]["hash_calls"]

    summaries = {}
    first_step = {}
    for method in METHODS:
        rs = [r for r in rows if r["method"] == method]
        gold = [r for r in rs if r["gold_evaluated"]]
        cert = [r for r in gold if r["status"] == "certified_model"]
        events = Counter()
        for row in rs:
            events.update(row["cost"]["control_events"])
        counted = {
            "queries": len(rs), "streams": len({r["stream_id"] for r in rs}),
            "status_counts": dict(Counter(r["status"] for r in rs)),
            "valid_snapshots": sum(r["valid_snapshot"] for r in rs),
            "valid_supported": sum(r["valid_snapshot"] and r["supported"] for r in rs),
            "gold_evaluated": len(gold), "gold_excluded": len(rs) - len(gold),
            "gold_exclusion_reasons": dict(Counter(r["gold_exclusion_reason"] for r in rs if not r["gold_evaluated"])),
            "certified_gold_evaluated": len(cert),
            "false_certifications": sum(r["false_certification"] for r in cert),
            "containment_evaluated": sum(r["containment_violation"] is not None for r in gold),
            "containment_violations": sum(r["containment_violation"] is True for r in gold),
            "gold_projection_evaluated": sum(r["selected_gold_projection_equal"] is not None for r in gold),
            "gold_projection_failures": sum(r["selected_gold_projection_equal"] is False for r in gold),
            "parity_failures": sum(bool(r["parity_failures"]) for r in rs),
            "structural_errors": sum(r["structural_error"] or r["schema_error"] for r in rs),
            "actual_full_history": sum(r["actual_full_history"] for r in rs),
            "output_bytes": sum(r["output_bytes"] for r in rs),
            "cost": {k: sum(r["cost"][k] for r in rs) for k in stored["summary"][method]["cost"]},
            "control_events": dict(events),
            "max_retained_bytes": max(r["cost"]["cache_peak_bytes"] for r in rs),
            "max_entries": max(r["cost"]["cache_peak_entries"] for r in rs),
        }
        assert counted == stored["summary"][method], (name, method, "summary")
        summaries[method] = counted
        cold_rows = [r for r in rs if r["step_index"] == 0]
        first_step[method] = {"count": len(cold_rows),
                              "work_score": sum(r["cost"]["phase08_work_score"] for r in cold_rows),
                              "cache_overhead_bytes": sum(r["cost"]["cache_overhead_bytes"] for r in cold_rows),
                              "control_actions": sum(r["cost"]["control_actions"] for r in cold_rows),
                              "writes": sum(r["cost"]["cache_writes"] for r in cold_rows)}
    comparisons = {m: compare_direct(rows, m, "fresh") for m in METHODS if m != "fresh"}
    assert comparisons == stored["comparisons"], (name, "comparisons")
    cross = compare_direct(rows, "selective", "lru")
    ablation = compare_direct(rows, "selective", "no_directory")
    assert cross == stored["selective_vs_lru"]
    assert ablation == stored["directory_ablation"]
    sensitivity = {str(w): compare_direct(rows, "selective", "fresh", w) for w in (0, 8, 32, 128)}
    assert sensitivity == stored["sensitivity"]
    families = {}
    for family in sorted({r["family"] for r in rows}):
        rs = [r for r in rows if r["family"] == family]
        families[family] = {m: compare_direct(rs, m, "fresh") for m in METHODS if m != "fresh"}
    assert families == stored["families"]
    actual_failures = sum(bool(r["parity_failures"]) or r["structural_error"] or r["schema_error"] or r["false_certification"] or bool(r["containment_violation"]) or r["selected_gold_projection_equal"] is False for r in rows)
    assert actual_failures == len(stored["failures"]) == 0
    c = comparisons["selective"]
    supported = actual_failures == 0 and c["after_score"] < c["before_score"] and c["parser_executions_after"] < c["parser_executions_before"]
    assert stored["hypothesis_decisions"]["H8_supported_in_this_dataset"] == supported
    stream_counts = {
        "final_benefit": sum(s["total_delta"] < 0 for s in c["streams"]),
        "final_equal": sum(s["total_delta"] == 0 for s in c["streams"]),
        "final_loss": sum(s["total_delta"] > 0 for s in c["streams"]),
        "ever_strict_break_even": sum(s["first_strict_break_even_step"] is not None for s in c["streams"]),
        "sustained_break_even": sum(s["sustained_break_even_step"] is not None for s in c["streams"]),
    }
    return {"dataset": name, "rows": len(rows), "paired_steps": len(pairs),
            "mismatches": 0, "summary": summaries, "comparisons": comparisons,
            "selective_vs_lru": cross, "directory_ablation": ablation,
            "sensitivity": sensitivity, "families": families, "first_step": first_step,
            "selective_stream_counts": stream_counts,
            "families_with_aggregate_gain": [f for f, x in families.items() if x["selective"]["after_score"] < x["selective"]["before_score"]],
            "H8_supported_in_this_dataset": supported,
            "original_summary_sha256": sha(summary_path), "original_rows_sha256": sha(row_path)}, rows


def ablation_replay(rows):
    # This validates the ablation's state claim, not an independent parser.
    import runtime
    streams = json.loads((HERE / "data/holdout.json").read_text())
    originals = {(r["stream_id"], r["step_index"], r["method"]): r for r in rows}
    checked = 0
    normalized = lambda value: json.loads(json.dumps(value, ensure_ascii=False))
    for stream in streams:
        left = runtime.SelectiveCache(directory=True)
        right = runtime.SelectiveCache(directory=False)
        for i, step in enumerate(stream["steps"]):
            for method, cache in (("selective", left), ("no_directory", right)):
                public = {k: deepcopy(step["public"][k]) for k in ("records", "entities", "snapshot", "query")}
                observed = runtime.run(public, cache, namespace=step["parser_namespace"])
                saved = originals[(stream["id"], i, method)]
                for key, value in observed.items():
                    if key == "cost":
                        for field, amount in value.items():
                            if field != "local_seconds":
                                assert normalized(amount) == saved["cost"][field], (stream["id"], i, method, field)
                    else:
                        assert normalized(value) == saved[key], (stream["id"], i, method, key)
            assert list(left.entries) == list(right.entries), (stream["id"], i, "keys/order")
            assert left.entries == right.entries, (stream["id"], i, "all resident metadata and values")
            assert left.lengths == right.lengths
            assert (left.retained_bytes, left.peak_bytes, left.peak_entries, left.next_order) == (right.retained_bytes, right.peak_bytes, right.peak_entries, right.next_order)
            checked += 1
    return {"streams": len(streams), "checked_after_every_step": checked,
            "complete_resident_state_mismatches": 0,
            "result_and_non_time_ledger_rows_matched_original": 2 * checked,
            "boundary": "Replay of frozen runtime, not an independently implemented cache or semantic parser; not timed."}


def timing_comparison():
    original = json.loads((HERE / "results/timing.json").read_text())
    reproduction = json.loads((HERE / "reproduction_timing.json").read_text())
    groups = {}
    for group in original["groups"]:
        observations = {}
        for label, timing in (("original", original), ("reproduction", reproduction)):
            methods = timing["groups"][group]["methods"]
            a, b = methods["fresh"]["median_seconds"], methods["selective"]["median_seconds"]
            observations[label] = {"fresh_median_ms": a * 1000, "selective_median_ms": b * 1000,
                                   "change_percent": 100 * (b / a - 1)}
        observations["direction_agrees"] = (observations["original"]["change_percent"] < 0) == (observations["reproduction"]["change_percent"] < 0)
        groups[group] = observations
    return {"groups": groups, "statistical_significance_tested": False,
            "timing_in_byte_identity_comparison": False}


def run():
    verify_freeze()
    main, rows = recount("holdout")
    historical, _ = recount("regression")
    ablation = ablation_replay(rows)
    return {"postfreeze_audit": True, "freeze_sha256": sha(HERE / "freeze.json"),
            "main": main, "historical_regression": historical,
            "ablation_state_replay": ablation, "timing_comparison": timing_comparison(),
            "boundary": "Same-model separate reviewer; summary functions were not imported or called. Source semantics were not externally relabeled. Historical rows remain regressions."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("new output path required")
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"main_rows": result["main"]["rows"],
                      "regression_rows": result["historical_regression"]["rows"],
                      "mismatches": 0, "stream_counts": result["main"]["selective_stream_counts"],
                      "families_with_gain": result["main"]["families_with_aggregate_gain"],
                      "ablation_state_replay": result["ablation_state_replay"]}, ensure_ascii=False))
