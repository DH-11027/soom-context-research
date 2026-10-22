"""Postfreeze aggregation of frozen predictions and exactly two timing sessions.

No fitting, feature change, new timing, selection, or additional resampling.
"""
import argparse
from collections import Counter
from pathlib import Path
from bridge import HERE, load, save, sha
from scoring import score, joint


def report():
    original = HERE / "results"
    predictions = load(original / "predictions.json")
    primary_time = load(original / "timing.json")
    reproduction_time = load(HERE / "reproduction_timing.json")
    receipts = [load(original / "receipt.json"), load(HERE / "reproduction_receipt.json")]
    assert all(r["status"] == "passed" and r["preservation_failures"] == 0 for r in receipts)
    assert len(receipts[1]["compared"]) == 8 and all(r["byte_identical"] for r in receipts[1]["compared"])
    primary = score(predictions, primary_time)
    reproduction = score(predictions, reproduction_time)
    assert primary == load(original / "scores.json")
    assert reproduction == load(HERE / "reproduction_scores.json")
    combined = joint(predictions, primary, reproduction)
    checked = load(original / "holdout_results.json")
    assert not checked["failures"]
    assert checked["exact_policy_state_mismatches"] == checked["exact_policy_trace_mismatches"] == 0
    summaries = checked["summary"]
    totals = {}
    for method, summary in summaries.items():
        actual = summary["separate_audit_actual_work"]
        totals[method] = {
            "parser_calls": sum(actual[s + "_calls"] for s in ("cheap", "contract", "detail")),
            "parser_source_bytes": sum(actual[s + "_source_bytes"] for s in ("cheap", "contract", "detail")),
            "snapshot_serialized_bytes": actual["snapshot_serialized_bytes"],
            "output_bytes": summary["output_bytes"],
            "p8_instrumented_only": summary["instrumented_cost"]["phase08_work_score"] if summary["instrumented_cost"] else None,
        }
    bounds = load(HERE / "calibration/model.json")["training_feature_bounds"]
    features = {r["stream_id"]:r for r in load(original / "holdout_features.json")["records"]}
    times = {"primary":primary_time, "reproduction":reproduction_time}
    scores = {"primary":primary, "reproduction":reproduction}
    extrapolation = {sid: [name for name, value in row["features"].items()
                         if not bounds[name]["min"] <= value <= bounds[name]["max"]]
                     for sid,row in features.items()}
    return {
        "joint_hypothesis": combined,
        "numerical_errors": {name:s["mean_normalized_absolute_error"] for name,s in scores.items()},
        "model_error_divided_by_best_baseline": {name:s["model_error_divided_by_best_baseline"] for name,s in scores.items()},
        "material_label_counts": {name:dict(Counter(r["summary"]["material_label"] for r in t["streams"])) for name,t in times.items()},
        "whole_workload": {name:t["whole_workload"]["summary"] for name,t in times.items()},
        "whole_workload_rounds": {name:len(t["whole_workload"]["rounds"]) for name,t in times.items()},
        "preservation": {k:checked[k] for k in ("prefixes","exact_observation_comparisons","exact_on_off_execution_trace_comparisons","exact_policy_state_mismatches","exact_policy_trace_mismatches","failures")},
        "method_summaries": summaries,
        "separate_audit_totals": totals,
        "extrapolation_outside_training_coordinate_ranges": extrapolation,
        "extrapolation_stream_count": sum(bool(x) for x in extrapolation.values()),
        "deterministic_artifact_comparisons": receipts[1]["compared"],
        "source_sha256": {"predictions.json":sha(original / "predictions.json"),
                          "primary_timing.json":sha(original / "timing.json"),
                          "reproduction_timing.json":sha(HERE / "reproduction_timing.json"),
                          "model.json":sha(HERE / "calibration/model.json"),
                          "freeze.json":sha(HERE / "freeze.json")},
        "boundary":"Postfreeze deterministic aggregation. No policy/model/data changes, no new timing or resampling. Error is equal-weight over fixed 48 streams; sign subset measurement-selected; no population, online-gate, or causal-cost conclusion. Coordinate-range extrapolation is descriptive, not a joint support guarantee.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = report()
    save(args.output, result)
    print(__import__("json").dumps({"conclusion":result["joint_hypothesis"]["conclusion"],
                                  "errors":result["numerical_errors"],
                                  "common_classes":result["joint_hypothesis"]["common_resolved_counts"]}))
