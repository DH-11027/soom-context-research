"""Read-only independent recount of frozen Phase07 row-level accounting.

This does not import phase07.study or any selector. It recomputes the stored
summary from rows and verifies the post-hoc diagnostic against its original.
Run from repository root with --output pointing to a new JSON path.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
P7 = ROOT / "research/phase07"
STAGES = ("cheap", "contract", "detail")
OVERHEAD = ("key_build_bytes", "key_probe_bytes", "value_encode_bytes",
            "cache_read_payload_bytes", "cache_write_bytes")


def run():
    rows = json.loads(gzip.decompress((P7 / "results/holdout_rows.json.gz").read_bytes()))
    stored = json.loads((P7 / "results/holdout_results.json").read_text())
    checks = 0
    for row in rows:
        c = row["cost"]
        for stage in STAGES:
            assert c[stage + "_requests"] == c[stage + "_calls"] + c[stage + "_reused"]
            checks += 1
        assert c["cache_overhead_bytes"] == sum(c[k] for k in OVERHEAD)
        assert c["phase07_work_proxy"] == row["output_bytes"] + c["hash_serialized_bytes"] + sum(c[s + "_source_bytes"] for s in STAGES) + c["reparse_source_bytes"] + c["cache_overhead_bytes"]
        assert c["cache_retained_bytes"] <= 65536 and c["cache_entries"] <= 64
        checks += 3
    out = {}
    for method, expected in stored["summary"].items():
        rs = [r for r in rows if r["method"] == method]
        gold = [r for r in rs if r["gold_evaluated"]]
        cert = [r for r in gold if r["status"] == "certified_model"]
        summary = {
            "queries": len(rs), "streams": len({r["stream_id"] for r in rs}),
            "status_counts": dict(Counter(r["status"] for r in rs)),
            "valid_snapshots": sum(r["valid_snapshot"] for r in rs),
            "gold_evaluated": len(gold), "gold_excluded": len(rs) - len(gold),
            "certified_gold_evaluated": len(cert),
            "false_certifications": sum(r["false_certification"] for r in cert),
            "containment_evaluated": sum(r["containment_violation"] is not None for r in gold),
            "containment_violations": sum(r["containment_violation"] is True for r in gold),
            "structural_errors": sum(r["structural_error"] or r["schema_error"] for r in rs),
            "gold_projection_failures": sum(r["selected_gold_projection_equal"] is False for r in gold),
            "parity_failures": sum(bool(r["parity_failures"]) for r in rs),
            "actual_full_history": sum(r["actual_full_history"] for r in rs),
            "output_bytes": sum(r["output_bytes"] for r in rs),
            "cost": {k: sum(r["cost"][k] for r in rs) for k in expected["cost"]},
            "max_retained_bytes": max(r["cost"]["cache_peak_bytes"] for r in rs),
            "max_entries": max(r["cost"]["cache_peak_entries"] for r in rs),
        }
        assert summary == expected, method
        checks += len(summary)
        summary["parser_executions"] = sum(summary["cost"][s + "_calls"] for s in STAGES)
        out[method] = summary
    pairs = {}
    for r in rows:
        if r["method"] in ("fresh", "lru"):
            pairs.setdefault((r["stream_id"], r["step_index"]), {})[r["method"]] = r
    proxy_diffs = [p["lru"]["cost"]["phase07_work_proxy"] - p["fresh"]["cost"]["phase07_work_proxy"] for p in pairs.values()]
    parser_reductions = sum(sum(p["lru"]["cost"][s + "_calls"] for s in STAGES) < sum(p["fresh"]["cost"][s + "_calls"] for s in STAGES) for p in pairs.values())
    return {
        "baseline_commit": "6da051c0132811184ecf39975d7ff647a1f47842",
        "row_count": len(rows), "paired_steps": len(pairs), "methods": out,
        "row_and_aggregate_assertions": checks, "mismatches": 0,
        "queries_with_fewer_parser_executions": parser_reductions,
        "proxy_smaller_equal_larger": [sum(x < 0 for x in proxy_diffs), sum(x == 0 for x in proxy_diffs), sum(x > 0 for x in proxy_diffs)],
        "phase07_rows_sha256": hashlib.sha256((P7 / "results/holdout_rows.json.gz").read_bytes()).hexdigest(),
        "boundary": "Independent aggregation implementation by same-model agent; does not relabel source semantics or establish external independence.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must not already exist")
    value = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in value.items() if k != "methods"}, ensure_ascii=False))
