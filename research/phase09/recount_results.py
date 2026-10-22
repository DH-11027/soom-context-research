"""Independent post-freeze result recount; imports no research implementation.

Only Python's standard library is used. This is a deterministic raw-artifact
audit, not a new benchmark. It does not rerun the policy, parser, or timing.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import median

HERE = Path(__file__).resolve().parent
METHODS = ("fresh_instrumented", "fresh_uninstrumented", "selective_instrumented", "selective_uninstrumented")
PAIRS = (("fresh_instrumented", "fresh_uninstrumented"),
         ("selective_instrumented", "selective_uninstrumented"))
OBS = ("status", "reason", "prediction", "selected", "output_bytes", "remaining_input_facts", "scope_trace", "rendered_sha256")
STATE_COST = {"cache_retained_bytes", "cache_entries", "cache_peak_bytes", "cache_peak_entries", "directory_entries"}
ORDER_SET = {(0, 1, 3, 2), (1, 2, 0, 3), (2, 3, 1, 0), (3, 0, 2, 1)}


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unexact(value):
    """Decode the stored type-tagged policy stage representation."""
    kind, body = value
    if kind == "mapping":
        return {unexact(k): unexact(v) for k, v in body}
    if kind == "tuple":
        return tuple(unexact(x) for x in body)
    if kind == "list":
        return [unexact(x) for x in body]
    if kind == "frozenset":
        return frozenset(unexact(x) for x in body)
    if kind == "set":
        return set(unexact(x) for x in body)
    if kind == "bytes":
        return bytes.fromhex(body["exact_bytes_hex"])
    assert kind in ("str", "int", "bool", "NoneType", "float"), kind
    return body


def check_state(state):
    assert state["max_entries"] == 64 and state["max_bytes"] == 65536 and state["directory"] is True
    entries = state["entries"]
    assert len(entries) <= 64
    keys, sizes, lengths = [], [], []
    for entry in entries:
        key, stages, size, characters, surplus, hits, order = entry
        context, raw = (bytes.fromhex(x["exact_bytes_hex"]) for x in key)
        keys.append((context, raw))
        decoded = unexact(stages)
        assert tuple(decoded) == ("cheap", "contract", "detail")
        assert decoded["cheap"][0]["kind"] == "havoc"
        assert decoded["contract"][0][0] is None
        payload = sum(slot[1] for slot in decoded.values())
        assert size == len(context) + len(raw) + payload + 80
        assert surplus == len(raw) - len(context) - payload - 64 and surplus > 0
        assert len(raw.decode("utf-8")) == characters
        assert 0 <= hits <= 255 and 0 <= order < state["next_order"]
        sizes.append(size)
        lengths.append(characters)
    assert len(set(keys)) == len(keys)
    assert sum(sizes) == state["retained_bytes"] <= 65536
    assert sorted(Counter(lengths).items()) == [tuple(x) for x in state["lengths"]]


def recount_dataset(directory, label):
    rows_path = directory / f"{label}_rows.json.gz"
    states_path = directory / f"{label}_states.json.gz"
    summary_path = directory / f"{label}_results.json"
    rows, states, stored = load(rows_path), load(states_path), load(summary_path)
    pairs = {}
    for r in rows:
        key = (r["stream_id"], r["step_index"])
        assert r["method"] not in pairs.setdefault(key, {}), ("duplicate row", key)
        pairs[key][r["method"]] = r
        assert not r["parity_failures"] and not r["structural_error"] and not r["schema_error"]
        assert not r["false_certification"] and not r["containment_violation"]
        assert r["selected_gold_projection_equal"] is not False
        is_on = r["method"] in ("fresh_instrumented", "selective_instrumented")
        assert ("cost" in r) == is_on
        if is_on:
            cost, audit = r["cost"], r["audit"]
            for stage in ("cheap", "contract", "detail"):
                assert cost[stage + "_calls"] == audit[stage + "_calls"]
                assert cost[stage + "_source_bytes"] == audit[stage + "_source_bytes"]
                assert cost[stage + "_requests"] == cost[stage + "_calls"] + cost[stage + "_reused"]
            assert cost["hash_calls"] == audit["snapshot_calls"]
            assert cost["hash_serialized_bytes"] == audit["snapshot_serialized_bytes"]
            assert cost["control_actions"] == sum(cost["control_events"].values())
            byte_fields = ("key_build_bytes", "key_probe_bytes", "value_encode_bytes", "cache_read_payload_bytes", "cache_write_bytes")
            assert cost["cache_overhead_bytes"] == sum(cost[k] for k in byte_fields)
            assert cost["phase07_work_proxy"] == cost["output_plus_source_work_proxy"] + cost["cache_overhead_bytes"]
            assert cost["phase08_work_score"] == cost["phase07_work_proxy"] + 8 * cost["control_actions"]
            if r["method"] == "selective_instrumented":
                assert cost["cache_lookups"] == audit["policy_get_calls"]
                assert cost["admission_attempts"] == audit["policy_admit_calls"]
                assert cost["cache_writes"] == audit["policy_insertions"]
                assert cost["cache_evictions"] == audit["policy_evictions"]
        assert r["output_bytes"] == r["audit"]["rendered_bytes"]
        if not r["valid_snapshot"] or not r["supported"]:
            assert not any(r["audit"][k] for k in ("cheap_calls", "contract_calls", "detail_calls", "policy_possible_calls", "policy_get_calls", "policy_admit_calls"))
    for key, pair in pairs.items():
        assert set(pair) == set(METHODS), key
        reference = pair[METHODS[0]]
        for row in pair.values():
            # Distinguish absence from a present field with None.
            assert {k: row[k] for k in OBS if k in row} == {k: reference[k] for k in OBS if k in reference}
        for on, off in PAIRS:
            for field in ("audit", "audit_trace_sha256", "audit_trace_events", "policy_trace_sha256", "policy_trace_events", "policy_retained_bytes", "policy_entries"):
                assert pair[on][field] == pair[off][field], (key, field)
    assert len(pairs) == stored["prefixes"] == len(states)
    state_keys = [(s["stream_id"], s["step_index"]) for s in states]
    assert len(set(state_keys)) == len(states) and set(state_keys) == set(pairs)
    assert len(rows) == 4 * len(pairs)
    assert stored["exact_observation_comparisons"] == 3 * len(pairs)
    assert stored["exact_on_off_execution_trace_comparisons"] == 2 * len(pairs)
    assert not stored["failures"] and not stored["exact_policy_state_mismatches"] and not stored["exact_policy_trace_mismatches"]
    previous = {}
    for row in states:
        key = (row["stream_id"], row["step_index"])
        assert row["exact_policy_state_equal"] and row["exact_policy_trace_equal"]
        assert "uninstrumented_state" not in row
        state = row["instrumented_state"]
        check_state(state)
        record = pairs[key]["selective_uninstrumented"]
        assert record["policy_retained_bytes"] == state["retained_bytes"]
        assert record["policy_entries"] == len(state["entries"])
        if row["stream_id"] in previous and (not record["valid_snapshot"] or not record["supported"]):
            assert state == previous[row["stream_id"]], key
        previous[row["stream_id"]] = state
    summaries = {}
    for method in METHODS:
        rr = [r for r in rows if r["method"] == method]
        gold = [r for r in rr if r["gold_evaluated"]]
        cert = [r for r in gold if r["status"] == "certified_model"]
        costs = [r["cost"] for r in rr if "cost" in r]
        cost_keys = {k for c in costs for k, v in c.items() if type(v) is int and k not in STATE_COST}
        fresh = {
            "queries": len(rr), "streams": len({r["stream_id"] for r in rr}),
            "status_counts": dict(Counter(r["status"] for r in rr)),
            "valid_snapshots": sum(r["valid_snapshot"] for r in rr),
            "valid_supported": sum(r["valid_snapshot"] and r["supported"] for r in rr),
            "gold_evaluated": len(gold), "gold_excluded": len(rr) - len(gold),
            "gold_exclusion_reasons": dict(Counter(r["gold_exclusion_reason"] for r in rr if not r["gold_evaluated"])),
            "certified_gold_evaluated": len(cert),
            "false_certifications": sum(r["false_certification"] for r in cert),
            "containment_evaluated": sum(r["containment_violation"] is not None for r in gold),
            "containment_violations": sum(r["containment_violation"] is True for r in gold),
            "gold_projection_evaluated": sum(r["selected_gold_projection_equal"] is not None for r in gold),
            "gold_projection_failures": sum(r["selected_gold_projection_equal"] is False for r in gold),
            "structural_errors": sum(r["structural_error"] or r["schema_error"] for r in rr),
            "parity_failure_rows": sum(bool(r["parity_failures"]) for r in rr),
            "actual_full_history": sum(r["actual_full_history"] for r in rr),
            "output_bytes": sum(r["output_bytes"] for r in rr),
            "max_retained_bytes_at_step_end": max((r["policy_retained_bytes"] for r in rr), default=0),
            "max_entries_at_step_end": max((r["policy_entries"] for r in rr), default=0),
            "instrumented_peak_retained_bytes": max((c["cache_peak_bytes"] for c in costs), default=None),
            "instrumented_peak_entries": max((c["cache_peak_entries"] for c in costs), default=None),
            "separate_audit_actual_work": {k: sum(r["audit"][k] for r in rr) for k in rr[0]["audit"]},
            "instrumented_cost": ({k: sum(c.get(k, 0) for c in costs) for k in sorted(cost_keys)} if costs else None),
            "instrumented_control_events": (dict(sum((Counter(c.get("control_events", {})) for c in costs), Counter())) if costs else None),
        }
        for field, value in fresh.items():
            assert value == stored["summary"][method][field], (method, field)
        summaries[method] = fresh
    return {"rows": len(rows), "prefixes": len(pairs), "summary": summaries,
            "state_records_checked": len(states), "mismatches": 0,
            "source_sha256": {p.name: sha(p) for p in (rows_path, states_path, summary_path)},
            "boundary": "Raw persisted trace hashes rechecked here; exact traces and two live policy states were compared in the separate execution audit, not reconstructed from a lone digest."}


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14), (a, b)


def independently_pair(rounds, candidate, reference):
    # Subtraction of logs is deliberately separate from benchmark's log(s/f).
    logs = [math.log(r["seconds"][candidate]) - math.log(r["seconds"][reference]) for r in rounds]
    observed = math.exp(median(logs))
    blocks = [logs[i:i + 4] for i in range(0, len(logs), 4)]
    rng = random.Random(902026)
    estimates = []
    for _ in range(20000):
        picked = []
        for _ in range(len(blocks)):
            picked.extend(blocks[rng.randrange(len(blocks))])
        estimates.append(math.exp(median(picked)))
    low, high = quantile(estimates, .025), quantile(estimates, .975)
    decision = ("material_speedup_observed" if high < .97 else
                "material_slowdown_observed" if low > 1.03 else
                "within_practical_margin" if low >= .97 and high <= 1.03 else
                "inconclusive_under_frozen_local_rule")
    return {"paired_median_ratio": observed, "change_percent": 100 * (observed - 1),
            "measurement_bootstrap_95pct_ratio": [low, high], "decision": decision}


def recount_timing(path):
    saved = load(path)
    rounds = saved["rounds"]
    assert len(rounds) == saved["rounds_count"] == 40
    assert saved["replays_per_interval"] == 3 and len(saved["warmups"]) == 2
    position_counts = {m: [0] * 4 for m in METHODS}
    for start in range(0, 40, 4):
        block = rounds[start:start + 4]
        assert {tuple(METHODS.index(m) for m in r["order"]) for r in block} == ORDER_SET
        for r in block:
            assert set(r["seconds"]) == set(METHODS)
            assert all(x > 0 for x in r["seconds"].values())
            for position, method in enumerate(r["order"]):
                position_counts[method][position] += 1
    assert all(x == [10, 10, 10, 10] for x in position_counts.values())
    medians = {}
    for method in METHODS:
        samples = [r["seconds"][method] for r in rounds]
        computed = {"median_seconds": median(samples), "min_seconds": min(samples), "max_seconds": max(samples),
                    "q25_seconds": quantile(samples, .25), "q75_seconds": quantile(samples, .75)}
        for field, value in computed.items():
            close(value, saved["methods"][method][field])
        medians[method] = computed
    comparisons = {}
    expected = {"primary": ("selective_uninstrumented", "fresh_uninstrumented"),
                "instrumented": ("selective_instrumented", "fresh_instrumented"),
                "fresh_erasure": ("fresh_uninstrumented", "fresh_instrumented"),
                "selective_erasure": ("selective_uninstrumented", "selective_instrumented")}
    for name, (candidate, reference) in expected.items():
        fresh = independently_pair(rounds, candidate, reference)
        old = saved["comparisons"][name]
        close(fresh["paired_median_ratio"], old["paired_median_ratio"])
        close(fresh["change_percent"], old["change_percent"])
        for a, b in zip(fresh["measurement_bootstrap_95pct_ratio"], old["measurement_bootstrap_95pct_ratio"]):
            close(a, b)
        assert fresh["decision"] == old["decision"]
        comparisons[name] = fresh
    diagnostic_rows, families = [], {}
    cold_before, cold_after = 0.0, 0.0
    for stream, data in saved["diagnostics"].items():
        for label in ("whole_stream", "first_step_cold"):
            for method in METHODS:
                samples = data[label]["samples_seconds"][method]
                assert len(samples) == 8 and all(x > 0 for x in samples)
                computed = {"median_seconds": median(samples), "min_seconds": min(samples), "max_seconds": max(samples),
                            "q25_seconds": quantile(samples, .25), "q75_seconds": quantile(samples, .75)}
                for field, value in computed.items():
                    close(value, data[label]["methods"][method][field])
        before = median(data["whole_stream"]["samples_seconds"]["fresh_uninstrumented"])
        after = median(data["whole_stream"]["samples_seconds"]["selective_uninstrumented"])
        cb = median(data["first_step_cold"]["samples_seconds"]["fresh_uninstrumented"])
        ca = median(data["first_step_cold"]["samples_seconds"]["selective_uninstrumented"])
        cold_before += cb
        cold_after += ca
        family = families.setdefault(data["family"], {"fresh_sum_stream_medians_seconds": 0., "selective_sum_stream_medians_seconds": 0., "streams": 0})
        family["fresh_sum_stream_medians_seconds"] += before
        family["selective_sum_stream_medians_seconds"] += after
        family["streams"] += 1
        diagnostic_rows.append({"stream": stream, "family": data["family"], "fresh_median_seconds": before,
                                "selective_median_seconds": after, "change_percent": 100 * (after / before - 1),
                                "cold_change_percent": 100 * (ca / cb - 1)})
    for family in families.values():
        family["change_percent"] = 100 * (family["selective_sum_stream_medians_seconds"] / family["fresh_sum_stream_medians_seconds"] - 1)
    return {"source_sha256": sha(path), "methods": medians, "comparisons": comparisons,
            "order_position_counts": position_counts, "diagnostic_streams": diagnostic_rows, "diagnostic_families": families,
            "diagnostic_streams_faster": sum(x["change_percent"] < 0 for x in diagnostic_rows),
            "diagnostic_streams_slower": sum(x["change_percent"] > 0 for x in diagnostic_rows),
            "first_step_cold_sum_of_medians": {"fresh_seconds": cold_before, "selective_seconds": cold_after,
                                               "change_percent": 100 * (cold_after / cold_before - 1)},
            "boundary": "Stream/cold numbers are separate descriptive sessions, not a decomposition of whole-workload main timing or independent conversation samples."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "results")
    parser.add_argument("--reproduction", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Do not overwrite an audit result"
    result = {"holdout": recount_dataset(args.results, "holdout"),
              "regression": recount_dataset(args.results, "regression"),
              "primary_timing": recount_timing(args.results / "timing.json"),
              "implementation_functions_imported": False}
    if args.reproduction:
        result["reproduction_timing"] = recount_timing(args.reproduction / "timing.json")
        primary = load(args.results / "timing.json")
        repeated = load(args.reproduction / "timing.json")
        assert primary["input_sha256"] == repeated["input_sha256"]
        decisions = [result[x]["comparisons"]["primary"]["decision"] for x in ("primary_timing", "reproduction_timing")]
        result["two_session_H9_speedup_rule_satisfied"] = all(d == "material_speedup_observed" for d in decisions)
        result["two_session_slowdown_rule_satisfied"] = all(d == "material_slowdown_observed" for d in decisions)
        result["deterministic_reproduction"] = {}
        for name in ("audit.json", "holdout_results.json", "holdout_rows.json.gz", "holdout_states.json.gz", "regression_results.json", "regression_rows.json.gz", "regression_states.json.gz", "data_profile.json"):
            identical = (args.results / name).read_bytes() == (args.reproduction / name).read_bytes()
            assert identical, name
            result["deterministic_reproduction"][name] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"holdout_rows": result["holdout"]["rows"], "regression_rows": result["regression"]["rows"],
                      "mismatches": 0, "primary": result["primary_timing"]["comparisons"]["primary"],
                      "reproduction": result.get("reproduction_timing", {}).get("comparisons", {}).get("primary")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
