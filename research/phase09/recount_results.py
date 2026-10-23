"""Recount frozen Phase09 raw results without importing runtime/evaluator/timer.

This checks arithmetic and reported denominators; it does not independently
validate natural-language gold or replace direct runtime state comparisons.
"""
import argparse
from collections import Counter
import gzip
import hashlib
from itertools import permutations
import json
import math
from pathlib import Path
import random
from statistics import median

HERE = Path(__file__).resolve().parent
METHODS = ("fresh_instrumented", "fresh_uninstrumented", "selective_instrumented", "selective_uninstrumented")
STAGES = ("cheap", "contract", "detail")
ASSERTIONS = 0


def check(condition, label):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(label)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(folder, name):
    report = json.loads((folder / (name + "_results.json")).read_text())
    path = folder / (name + "_rows.json.gz")
    raw = gzip.decompress(path.read_bytes())
    rows = json.loads(raw)
    metadata = report["raw_rows"]
    check(metadata["file"] == path.name, name + " raw file")
    check(metadata["count"] == len(rows), name + " row count")
    check(metadata["sha256"] == sha(path), name + " raw sha")
    if "uncompressed_bytes" in metadata:
        check(metadata["uncompressed_bytes"] == len(raw), name + " raw bytes")
    return report, rows


def recount_rows(report, rows, label):
    keys = [(r["stream_id"], r["step_index"], r["method"]) for r in rows]
    check(len(keys) == len(set(keys)), label + " unique row keys")
    check(set(r["method"] for r in rows) == set(METHODS), label + " four methods")
    pairs = {}
    for row in rows:
        pairs.setdefault((row["stream_id"], row["step_index"]), {})[row["method"]] = row
    for key, group in pairs.items():
        check(set(group) == set(METHODS), (label, key, "four rows per prefix"))
        reference = group["fresh_instrumented"]
        for method, row in group.items():
            for field in ("status", "reason", "prediction", "selected", "output_bytes",
                          "remaining_input_facts", "scope_trace", "rendered_sha256",
                          "observation_sha256",
                          "valid_snapshot", "supported", "gold_evaluated"):
                check((field in row) == (field in reference), (label, key, method, field, "presence"))
                check(row.get(field) == reference.get(field), (label, key, method, field))
            check(not row["policy_errors"] and not row["parity_errors"], (label, key, method, "parity"))
            if method.endswith("_uninstrumented"):
                on = group[method.replace("_uninstrumented", "_instrumented")]
                for field in ("policy_state_sha256", "actual_call_sequence_sha256", "actual_hash_inputs_sha256",
                              "actual_parser_calls", "actual_parser_source_bytes", "actual_hash_calls", "actual_hash_bytes"):
                    check(row[field] == on[field], (label, key, method, field))
                check("cost" not in row, (label, key, method, "no off ledger"))
            else:
                for stage in STAGES:
                    check(row["actual_parser_calls"][stage] == row["cost"][stage + "_calls"], (label, key, method, stage))
                check(row["actual_hash_calls"] == row["cost"]["hash_calls"], (label, key, method, "hash calls"))
                check(row["actual_hash_bytes"] == row["cost"]["hash_serialized_bytes"], (label, key, method, "hash bytes"))
    independent = {}
    for method in METHODS:
        rr = [r for r in rows if r["method"] == method]
        counts = Counter(r["status"] for r in rr)
        parsed = Counter()
        for row in rr:
            parsed.update(row["actual_parser_calls"])
        metrics = {
            "steps": len(rr), "streams": len({r["stream_id"] for r in rr}),
            "status_counts": dict(sorted(counts.items())),
            "valid_snapshots": sum(r["valid_snapshot"] for r in rr),
            "valid_supported": sum(r["valid_snapshot"] and r["supported"] for r in rr),
            "gold_evaluated": sum(r["gold_evaluated"] for r in rr),
            "certified_gold": sum(r["gold_evaluated"] and r["status"] == "certified_model" for r in rr),
            "false_certifications": sum(r["false_certification"] for r in rr),
            "containment_evaluated": sum(r["containment_violation"] is not None for r in rr),
            "containment_violations": sum(r["containment_violation"] is True for r in rr),
            "projection_evaluated": sum(r["selected_gold_projection_equal"] is not None for r in rr),
            "projection_failures": sum(r["selected_gold_projection_equal"] is False for r in rr),
            "observation_failures": sum("exact_observation" in r["parity_errors"] for r in rr),
            "state_failures": sum("exact_policy_state" in r["parity_errors"] for r in rr),
            "call_trace_failures": sum("exact_parser_hash_trace" in r["parity_errors"] for r in rr),
            "structural_errors": sum(r["structural_error"] or r["schema_error"] for r in rr),
            "policy_errors": sum(bool(r["policy_errors"]) for r in rr),
            "actual_parser_calls": {stage: parsed[stage] for stage in STAGES},
            "actual_parser_source_bytes": sum(sum(r["actual_parser_source_bytes"].values()) for r in rr),
            "actual_hash_calls": sum(r["actual_hash_calls"] for r in rr),
            "actual_hash_bytes": sum(r["actual_hash_bytes"] for r in rr),
            "output_bytes": sum(r["output_bytes"] for r in rr),
        }
        check(metrics == report["summary"][method], (label, method, "independent aggregate"))
        independent[method] = metrics
    flagged = [r for r in rows if r["policy_errors"] or r["parity_errors"] or r["structural_error"] or r["schema_error"]
               or r["false_certification"] or r["containment_violation"] or r["selected_gold_projection_equal"] is False]
    check(len(flagged) == len(report["failures"]), label + " failures length")
    check(len(flagged) == 0, label + " no correctness failures")
    return {"rows": len(rows), "prefixes": len(pairs), "summary": independent,
            "boundary": "Recorded exact-state/trace digests recounted; direct objects were compared by the separate replay auditor."}


def quantile(values, p):
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    low = math.floor(position)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (position - low)


def independent_comparison(blocks, candidate, reference):
    ratios = [b["measurements"][candidate]["elapsed_ns"] / b["measurements"][reference]["elapsed_ns"] for b in blocks]
    rng = random.Random(2026102310)
    samples = [median(rng.choices(ratios, k=len(ratios))) for _ in range(10000)]
    interval = [quantile(samples, p) for p in (.025, .975)]
    halves = [median(ratios[:len(ratios)//2]), median(ratios[len(ratios)//2:])]
    supported = interval[1] < .95 and all(r < .95 for r in halves)
    return {"paired_ratios": ratios, "median_paired_ratio": median(ratios),
            "change_percent": 100 * (median(ratios) - 1),
            "conditional_bootstrap_95_interval": interval,
            "first_and_second_half_median_ratios": halves,
            "decision": "supports_practical_speedup" if supported else "rejects_practical_speedup_here" if interval[0] > .95 else "inconclusive",
            "faster_blocks": sum(r < 1 for r in ratios), "blocks": len(ratios)}


def recount_timing(timing):
    blocks = timing["blocks"]
    check(len(blocks) == timing["repeats"] == 24, "24 blocks")
    check({tuple(b["order"]) for b in blocks} == set(permutations(METHODS)), "all method permutations")
    check(timing["outliers_removed"] == 0, "no timing exclusions")
    check(timing["environment"]["hashseed"] == "0" and timing["environment"]["gc_enabled"], "timing environment")
    for block in blocks:
        check(set(block["measurements"]) == set(METHODS), "full timing block")
        for method in METHODS:
            raw = block["measurements"][method]
            check(raw["elapsed_ns"] > 0 and raw["cycles"] == 3, "positive interval and cycles")
            check(raw["seconds_per_workload"] == raw["elapsed_ns"] / 3 / 1e9, "normalized interval")
    for method in METHODS:
        values = [b["measurements"][method]["seconds_per_workload"] for b in blocks]
        expected = {"samples_seconds": values, "median_seconds": median(values), "min_seconds": min(values),
                    "max_seconds": max(values), "q25_seconds": quantile(values, .25), "q75_seconds": quantile(values, .75)}
        check(expected == timing["summary"]["methods"][method], (method, "timing method summary"))
    specs = {"primary_off_vs_off": (METHODS[3], METHODS[1]),
             "instrumented_selective_vs_fresh": (METHODS[2], METHODS[0]),
             "fresh_erasure": (METHODS[1], METHODS[0]), "selective_erasure": (METHODS[3], METHODS[2])}
    comparisons = {}
    for label, (candidate, reference) in specs.items():
        result = independent_comparison(blocks, candidate, reference)
        for key, value in result.items():
            check(value == timing["summary"]["comparisons"][label][key], (label, key))
        comparisons[label] = result
    differences = []
    for block in blocks:
        t = {method: block["measurements"][method]["seconds_per_workload"] for method in METHODS}
        differences.append((t[METHODS[2]] - t[METHODS[3]]) - (t[METHODS[0]] - t[METHODS[1]]))
    check(differences == timing["summary"]["erasure_difference_in_differences_seconds"], "descriptive interaction")
    stream_signs = Counter()
    for label, group in timing["supplementary"].items():
        rows = group["blocks"]
        check(len(rows) == 8, (label, "supplementary repeats"))
        pair = (METHODS[1], METHODS[3])
        ratios = [r["measurements"][pair[1]]["elapsed_ns"] / r["measurements"][pair[0]]["elapsed_ns"] for r in rows]
        check(median(ratios) == group["median_paired_ratio"], (label, "supplementary ratio"))
        check(100 * (median(ratios) - 1) == group["change_percent"], (label, "supplementary percent"))
        for method in pair:
            values = [r["measurements"][method]["seconds_per_workload"] for r in rows]
            check(median(values) == group["methods"][method]["median_seconds"], (label, method, "supplementary median"))
        if label != "all_first_steps":
            stream_signs["faster" if median(ratios) < 1 else "slower" if median(ratios) > 1 else "equal"] += 1
    return {"comparisons": comparisons, "supplementary_stream_signs": dict(stream_signs),
            "cold_first_steps_change_percent": timing["supplementary"]["all_first_steps"]["change_percent"],
            "uncertainty_boundary": "Complete timing blocks are the resampling unit; fixed synthetic corpus, same local session, not independent dialogues."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "results")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    output = {}
    for name in ("holdout", "regression"):
        report, rows = read_rows(args.results, name)
        output[name] = recount_rows(report, rows, name)
    timing = json.loads((args.results / "timing.json").read_text())
    check(timing["steps"] == output["holdout"]["prefixes"], "timing/evaluation workload count")
    output["timing"] = recount_timing(timing)
    output["assertions_passed"] = ASSERTIONS
    output["mismatches"] = 0
    output["source_hashes"] = {p.name: sha(p) for p in sorted(args.results.iterdir()) if p.is_file()}
    output["boundary"] = "Independent recount code, same model. No runtime execution, no original summary helpers, no new timing."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"holdout_rows": output["holdout"]["rows"], "regression_rows": output["regression"]["rows"],
                      "assertions_passed": ASSERTIONS, "mismatches": 0,
                      "primary": output["timing"]["comparisons"]["primary_off_vs_off"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
