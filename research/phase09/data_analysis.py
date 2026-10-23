"""Postfreeze descriptive data/timing recount; no selector or summary imports.

Written after the primary and one reproduction completed. It opens saved input,
audit rows and raw timing blocks, never executes parser/cache/timing code.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
METHODS = ("fresh_instrumented", "fresh_uninstrumented",
           "selective_instrumented", "selective_uninstrumented")
LONG_FAMILIES = ("cold_terminal", "long_cheap_repeated", "deep_finite_horizons",
                 "same_length_churn", "working_set_fit", "working_set_pressure", "phase_shift")


def load(path):
    payload = path.read_bytes()
    return json.loads(gzip.decompress(payload) if path.suffix == ".gz" else payload)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def duplicate_counts(steps):
    return {
        "steps": len(steps),
        "exact_records": len({canonical(q["public"]["records"]) for q in steps}),
        "records_and_expected_snapshot": len({canonical([q["public"]["records"], q["public"]["snapshot"]]) for q in steps}),
        "ordered_raw_histories": len({canonical([r["text"] for r in q["public"]["records"]]) for q in steps}),
        "ordered_raw_histories_and_entities": len({canonical([[r["text"] for r in q["public"]["records"]], q["public"]["entities"]]) for q in steps}),
        "public_and_namespace": len({canonical([q["public"], q["parser_namespace"]]) for q in steps}),
        "distinct_raw_strings": len({r["text"] for q in steps for r in q["public"]["records"]}),
        "exact_typed_event_arrays": len({canonical(q["gold"]) for q in steps}),
        "exact_typed_event_arrays_without_noops": len({canonical([e for e in q["gold"] if e["kind"] != "noop"]) for q in steps}),
    }


def proportion(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "percent": 100 * numerator / denominator}


def timing_description(path, corpus):
    saved = load(path)
    methods = {}
    for method in METHODS:
        times = [b["measurements"][method]["elapsed_ns"] / b["measurements"][method]["cycles"] / 1e9
                 for b in saved["blocks"]]
        med = statistics.median(times)
        assert math.isclose(med, saved["summary"]["methods"][method]["median_seconds"], rel_tol=1e-14)
        methods[method] = {"median_seconds": med, "min_seconds": min(times), "max_seconds": max(times)}
    comparisons = {}
    for label, candidate, reference in (
        ("primary_off_vs_off", "selective_uninstrumented", "fresh_uninstrumented"),
        ("instrumented_selective_vs_fresh", "selective_instrumented", "fresh_instrumented"),
        ("fresh_erasure", "fresh_uninstrumented", "fresh_instrumented"),
        ("selective_erasure", "selective_uninstrumented", "selective_instrumented"),
    ):
        ratios = [(b["measurements"][candidate]["elapsed_ns"] / b["measurements"][candidate]["cycles"])
                  / (b["measurements"][reference]["elapsed_ns"] / b["measurements"][reference]["cycles"])
                  for b in saved["blocks"]]
        median = statistics.median(ratios)
        expected = saved["summary"]["comparisons"][label]
        assert math.isclose(median, expected["median_paired_ratio"], rel_tol=1e-14)
        comparisons[label] = {"median_paired_ratio": median, "change_percent": (median - 1) * 100,
                              "faster_blocks": sum(r < 1 for r in ratios), "blocks": len(ratios),
                              "ratio_min_max": [min(ratios), max(ratios)],
                              "first_second_half_medians": [statistics.median(ratios[:12]), statistics.median(ratios[12:])],
                              "saved_conditional_bootstrap_95_interval": expected["conditional_bootstrap_95_interval"],
                              "interval_note": "read from frozen-run output; this script independently recomputes medians, not bootstrap"}
    supplementary = {}
    for key, group in saved["supplementary"].items():
        times = {m: [b["measurements"][m]["elapsed_ns"] / b["measurements"][m]["cycles"] / 1e9
                     for b in group["blocks"]] for m in ("fresh_uninstrumented", "selective_uninstrumented")}
        ratios = [s / f for s, f in zip(times["selective_uninstrumented"], times["fresh_uninstrumented"])]
        median = statistics.median(ratios)
        assert math.isclose(median, group["median_paired_ratio"], rel_tol=1e-14)
        supplementary[key] = {"family": group["family"], "queries": group["queries"],
                              "median_paired_ratio": median, "change_percent": (median - 1) * 100,
                              "faster_blocks": sum(r < 1 for r in ratios), "blocks": len(ratios),
                              "median_seconds": {m: statistics.median(v) for m, v in times.items()}}
    streams = {s["id"]: supplementary[s["id"]] for s in corpus}
    totals = {m: sum(v["median_seconds"][m] for v in streams.values())
              for m in ("fresh_uninstrumented", "selective_uninstrumented")}
    long_times = sum(v["median_seconds"]["fresh_uninstrumented"] for v in streams.values() if v["family"] in LONG_FAMILIES)
    families = {}
    for family in sorted({s["family"] for s in corpus}):
        values = [v for v in streams.values() if v["family"] == family]
        sums = {m: sum(v["median_seconds"][m] for v in values) for m in totals}
        families[family] = {"sum_standalone_stream_medians_seconds": sums,
                            "ratio_of_sums_change_percent": (sums["selective_uninstrumented"] / sums["fresh_uninstrumented"] - 1) * 100,
                            "faster_stream_median_ratios": sum(v["median_paired_ratio"] < 1 for v in values)}
    return {"methods": methods, "comparisons": comparisons,
            "all_first_steps": supplementary["all_first_steps"], "streams": streams, "families": families,
            "stream_speedup_counts": {"strictly_faster": sum(v["median_paired_ratio"] < 1 for v in streams.values()),
                                      "at_least_5_percent_faster": sum(v["median_paired_ratio"] < .95 for v in streams.values()),
                                      "equal": sum(v["median_paired_ratio"] == 1 for v in streams.values()),
                                      "slower": sum(v["median_paired_ratio"] > 1 for v in streams.values())},
            "long_family_share_of_sum_standalone_fresh_stream_medians": proportion(long_times, totals["fresh_uninstrumented"]),
            "standalone_sum_note": "sum of separately measured stream medians; not a decomposition or replacement of main whole-workload timing"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=HERE / "data_analysis.json")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    corpus_path, rows_path = HERE / "data/holdout.json.gz", HERE / "results/holdout_rows.json.gz"
    corpus, rows = load(corpus_path), load(rows_path)
    summary = load(HERE / "results/holdout_results.json")
    steps = {(s["id"], i): q for s in corpus for i, q in enumerate(s["steps"])}
    assert len(rows) == len(steps) * 4 == len({(r["stream_id"], r["step_index"], r["method"]) for r in rows})
    assert len(corpus) == 36 and len(steps) == 622
    valid = [q for q in steps.values() if q["expected_integrity"] == "valid"]
    gold = [q for q in steps.values() if q["gold_applicable"]]
    supported_valid_keys = {key for key, q in steps.items() if q["expected_integrity"] == "valid" and q["question_contract"]["supported"]}
    gold_keys = {key for key, q in steps.items() if q["gold_applicable"]}
    inputs, raw_occurrences = {}, []
    for stream in corpus:
        texts = [r["text"] for q in stream["steps"] for r in q["public"]["records"]]
        raw_occurrences.extend(texts)
        inputs[stream["id"]] = {"family": stream["family"], "steps": len(stream["steps"]),
                                "record_occurrences": len(texts), "distinct_raw_records": len(set(texts)),
                                "raw_utf8_bytes": sum(len(x.encode("utf-8")) for x in texts),
                                "max_record_utf8_bytes": max(len(x.encode("utf-8")) for x in texts),
                                "max_record_characters": max(map(len, texts)),
                                "duplication": duplicate_counts(stream["steps"])}
    raw_total = sum(len(x.encode("utf-8")) for x in raw_occurrences)
    lengths = {
        "raw_record_occurrences": len(raw_occurrences), "raw_utf8_total": raw_total,
        "raw_utf8_min_max": [min(len(x.encode("utf-8")) for x in raw_occurrences), max(len(x.encode("utf-8")) for x in raw_occurrences)],
        "raw_unicode_codepoints_min_max": [min(map(len, raw_occurrences)), max(map(len, raw_occurrences))],
        "at_least_256_codepoints": {"records": sum(len(x) >= 256 for x in raw_occurrences),
                                     "bytes_share": proportion(sum(len(x.encode("utf-8")) for x in raw_occurrences if len(x) >= 256), raw_total)},
        "at_least_4096_utf8_bytes_posthoc_description": {"records": sum(len(x.encode("utf-8")) >= 4096 for x in raw_occurrences),
                                                        "bytes_share": proportion(sum(len(x.encode("utf-8")) for x in raw_occurrences if len(x.encode("utf-8")) >= 4096), raw_total)},
    }
    aggregates = {}
    by_key = {(r["stream_id"], r["step_index"], r["method"]): r for r in rows}
    for method in METHODS:
        rr = [r for r in rows if r["method"] == method]
        for r in rr:
            q = steps[r["stream_id"], r["step_index"]]
            assert r["valid_snapshot"] == (q["expected_integrity"] == "valid")
            assert r["supported"] == q["question_contract"]["supported"]
            assert r["gold_evaluated"] == q["gold_applicable"]
            assert not r["structural_error"] and not r["schema_error"]
            assert not r["policy_errors"] and not r["parity_errors"]
        v = {"steps": len(rr), "status": dict(sorted(Counter(r["status"] for r in rr).items())),
             "actual_parser_calls": sum(sum(r["actual_parser_calls"].values()) for r in rr),
             "actual_parser_source_bytes": sum(sum(r["actual_parser_source_bytes"].values()) for r in rr),
             "actual_hash_calls": sum(r["actual_hash_calls"] for r in rr),
             "actual_hash_bytes": sum(r["actual_hash_bytes"] for r in rr),
             "output_bytes": sum(r["output_bytes"] for r in rr),
             "full_history_output": sum(r["status"] != "integrity_failure" and r["selected"] == list(range(len(steps[r["stream_id"], r["step_index"]]["public"]["records"]))) for r in rr),
             "false_certification": {"errors": sum(r["false_certification"] is True for r in rr), "evaluated": sum(r["gold_evaluated"] and r["status"] == "certified_model" for r in rr)},
             "containment": {"errors": sum(r["containment_violation"] is True for r in rr), "evaluated": sum(r["containment_violation"] is not None for r in rr)},
             "selected_projection": {"errors": sum(r["selected_gold_projection_equal"] is False for r in rr), "evaluated": sum(r["selected_gold_projection_equal"] is not None for r in rr)}}
        assert v["actual_parser_calls"] == sum(summary["summary"][method]["actual_parser_calls"].values())
        for f in ("steps", "actual_parser_source_bytes", "actual_hash_calls", "actual_hash_bytes", "output_bytes"):
            assert v[f] == summary["summary"][method][f]
        if "cost" in rr[0]:
            fields = ("phase07_work_proxy", "phase08_work_score", "control_actions", "cache_entry_hits", "cache_writes",
                      "cache_evictions", "admission_attempts", "admission_reject_gain", "admission_reject_capacity")
            v["instrumented_cost_sum"] = {f: sum(r["cost"][f] for r in rr) for f in fields}
        aggregates[method] = v
    family_descriptions = {}
    for family in sorted({s["family"] for s in corpus}):
        frows = [r for r in rows if r["family"] == family and r["method"] == "fresh_instrumented"]
        srows = [r for r in rows if r["family"] == family and r["method"] == "selective_instrumented"]
        fscore = sum(r["cost"]["phase08_work_score"] for r in frows)
        sscore = sum(r["cost"]["phase08_work_score"] for r in srows)
        fsteps = [q for stream in corpus if stream["family"] == family for q in stream["steps"]]
        family_descriptions[family] = {"steps": len(fsteps),
                                       "raw_utf8_bytes": sum(x["raw_utf8_bytes"] for x in inputs.values() if x["family"] == family),
                                       "valid_unique_raw_histories": duplicate_counts([q for q in fsteps if q["expected_integrity"] == "valid"])["ordered_raw_histories"],
                                       "gold_unique_typed_event_arrays": duplicate_counts([q for q in fsteps if q["gold_applicable"]])["exact_typed_event_arrays"],
                                       "fresh_p8": fscore, "selective_p8": sscore,
                                       "p8_change_percent": (sscore / fscore - 1) * 100}
    ftotal = aggregates["fresh_instrumented"]["instrumented_cost_sum"]["phase08_work_score"]
    long = {"families": LONG_FAMILIES,
            "steps": sum(v["steps"] for k, v in family_descriptions.items() if k in LONG_FAMILIES),
            "raw_share": proportion(sum(v["raw_utf8_bytes"] for k, v in family_descriptions.items() if k in LONG_FAMILIES), raw_total),
            "fresh_p8_family_share": proportion(sum(v["fresh_p8"] for k, v in family_descriptions.items() if k in LONG_FAMILIES), ftotal)}
    changes = []
    stream_scores = []
    for stream in corpus:
        delta = 0
        for i, q in enumerate(stream["steps"]):
            f = by_key[stream["id"], i, "fresh_instrumented"]["cost"]["phase08_work_score"]
            s = by_key[stream["id"], i, "selective_instrumented"]["cost"]["phase08_work_score"]
            changes.append(s-f); delta += s-f
        stream_scores.append({"id": stream["id"], "p8_delta": delta})
    original = timing_description(HERE / "results/timing.json", corpus)
    reproduction = timing_description(HERE / "reproduction_timing.json", corpus)
    sign_changes = [sid for sid in inputs if (original["streams"][sid]["median_paired_ratio"] < 1) != (reproduction["streams"][sid]["median_paired_ratio"] < 1)]
    result = {"phase": "postfreeze_description", "runtime_executed": False,
              "freeze_commit": "b4a844efcaca73483f2c0d8b8339a1e352872745",
              "source_hashes": {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                (corpus_path, rows_path, HERE / "results/timing.json", HERE / "reproduction_timing.json")},
              "counts": {"streams": len(corpus), "steps": len(steps), "raw_rows": len(rows),
                         "valid": len(valid), "gold": len(gold), "valid_supported": len(supported_valid_keys),
                         "gold_and_valid_supported": len(gold_keys & supported_valid_keys),
                         "gold_not_valid_supported": len(gold_keys - supported_valid_keys),
                         "valid_supported_not_gold": len(supported_valid_keys - gold_keys)},
              "duplicates": {"all_steps": duplicate_counts(list(steps.values())), "valid_steps": duplicate_counts(valid), "gold_steps": duplicate_counts(gold)},
              "length_distribution": lengths, "input_streams": inputs, "family_descriptions": family_descriptions,
              "large_family_dominance": long, "audit_aggregates": aggregates,
              "p8_descriptive_signs": {"steps_improved": sum(x < 0 for x in changes), "steps_equal": sum(x == 0 for x in changes), "steps_worse": sum(x > 0 for x in changes),
                                       "streams_improved": sum(x["p8_delta"] < 0 for x in stream_scores), "streams_worse": sum(x["p8_delta"] > 0 for x in stream_scores)},
              "stream_p8_deltas": stream_scores,
              "original_timing": original, "reproduction_timing": reproduction,
              "stream_timing_sign_reversals": sign_changes,
              "boundary": "same-model descriptive audit, no external semantic validation; raw rows are separate untimed audits, not main timing instrumentation"}
    payload = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check or args.output.exists():
        assert args.output.read_bytes() == payload
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    print(json.dumps({"counts": result["counts"], "output": str(args.output), "sha256": hashlib.sha256(payload).hexdigest()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
