"""Freeze before holdout; reproduce deterministic artifacts into a new folder."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from time import perf_counter

import audit
import development
import evaluate
import scoped

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE_COMMIT = "780891f6c147cfd3c1a3b0d065792776aaa525f3"
CORE = ("scoped.py", "evaluate.py", "audit.py", "development.py", "run_study.py", "PROTOCOL.md", "THEORY.md")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_result(output, name, result):
    rows_name = name.replace("_results.json", "_rows.json.gz")
    encoded = json.dumps(result["rows"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # Empty filename and zero mtime make the compressed bytes reproducible.
    with (output / rows_name).open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as zipped:
            zipped.write(encoded)
    summary = {k: v for k, v in result.items() if k != "rows"}
    summary["raw_rows"] = {"file": rows_name, "count": len(result["rows"]),
                           "sha256": sha(output / rows_name), "uncompressed_bytes": len(encoded)}
    save(output / name, summary)


def decisions(result):
    answers = {}
    for split, summary in result["summary"].items():
        new = summary["text_scoped"]
        comparison = result["comparisons"][split]["text_scoped"]
        valid = not (new["false_certifications"] or new["containment_violations"] or new["schema_errors"]
                     or new["selected_gold_projection_failures"])
        valid &= not any(failure["split"] == split for failure in result["failures"])
        exercised = new["proper_scope_events"] > 0 and comparison["strict_record_reductions"] > 0 and comparison["new_certifications"] > 0
        answers[split] = {"H6_S": "refuted_by_failure" if not valid else "supported_in_this_synthetic_split" if exercised else "not_supported_no_effect",
                          "nonvacuous_scope_reduction_and_new_certification": exercised,
                          "H6_C_equal_byte_work_proxy": "not_interpretable_validation_failed" if not valid else "supported_in_this_split" if comparison["work_proxy_reduction_percent"] > 0 else "not_supported_no_cost_reduction",
                          "H6_C_real_LLM_total_cost": "not_measured"}
    return answers


def corpus_run(cases):
    rows = []
    for case in cases:
        assert len(case["gold"]) == len(case["public"]["records"])
        assert all(value is not None for s in evaluate.exact_states(case["gold"], case["public"]["entities"]) for value in s)
        for query in case["queries"]:
            outcomes = {method: evaluate.evaluate_case(case, query, method) for method in scoped.METHODS}
            for method, row in outcomes.items():
                # Keep results before diagnosing failures; final status below,
                # rather than aborting and concealing the failing case.
                rows.append(row)
            for other, reference in (("global_control", "frozen_lazy"), ("text_scoped_eager", "text_scoped")):
                left, right = outcomes[other], outcomes[reference]
                for key in ("status", "prediction", "selected", "output_bytes"):
                    if left[key] != right[key]:
                        left.setdefault("parity_failures", []).append({"reference": reference, "key": key})
    summaries, comparisons, families = {}, {}, {}
    for split in sorted({r["split"] for r in rows}):
        split_rows = [r for r in rows if r["split"] == split]
        summaries[split] = {m: evaluate.summarize([r for r in split_rows if r["method"] == m]) for m in scoped.METHODS}
        comparisons[split] = {m: evaluate.compare(split_rows, m) for m in ("text_scoped", "oracle_scoped", "global_control")}
        families[split] = {family: evaluate.compare([r for r in split_rows if r["family"] == family])
                           for family in sorted({r["family"] for r in split_rows})}
    failures = [{"case_id": r["case_id"], "split": r["split"], "query": r["query"], "method": r["method"],
                 "schema_error": r["schema_error"], "false_certification": r["false_certification"],
                 "containment_violation": r["containment_violation"],
                 "selected_gold_projection_equal": r["selected_gold_projection_equal"],
                 "parity_failures": r.get("parity_failures", [])}
                for r in rows if r["schema_error"] or r["false_certification"] or r["containment_violation"]
                or not r["selected_gold_projection_equal"] or r.get("parity_failures")]
    return {"summary": summaries, "comparisons": comparisons, "families": families,
            "failures": failures, "rows": evaluate.strip_timing(rows)}


def benchmark(cases, repeats=5):
    # Wall-clock path excludes offline gold interpreter and annotation creation.
    methods = ("full_history", "frozen_lazy", "global_control", "text_scoped", "text_scoped_eager")
    publics = [{k: case["public"][k] for k in ("records", "entities", "snapshot")} | {"query": query}
               for case in cases for query in case["queries"]]
    samples = {m: [] for m in methods}
    for method in methods:  # warm-up, excluded
        for public in publics:
            scoped.run(public, method)
    for repeat in range(repeats):
        order = methods[repeat % len(methods):] + methods[:repeat % len(methods)]
        for method in order:
            start = perf_counter()
            for public in publics:
                scoped.run(public, method)
            samples[method].append(perf_counter() - start)
    return {"repeats": repeats, "query_count": len(publics), "rotation": list(methods),
            "scope": "Instrumented local Python path including hashing, parsing, inference, rendering; no LLM, retrieval service or gold evaluation",
            "methods": {m: {"seconds": values, "median_seconds": median(values),
                             "min_seconds": min(values), "max_seconds": max(values)} for m, values in samples.items()}}


def freeze():
    path = HERE / "freeze.json"
    if path.exists():
        raise SystemExit("Existing freeze must not be overwritten")
    dev = development.build()
    save(HERE / "data/development.json", dev)
    names = (*CORE, "data/development.json", "holdout_builder.py", "data/holdout.json", "HOLDOUT_AUTHOR.md")
    save(path, {"created_at_utc": datetime.now(timezone.utc).isoformat(), "baseline_commit": BASELINE_COMMIT,
                "scope": "Code chosen on development only; root has not read holdout examples or outcomes",
                "holdout_provenance": "Same-model separate agent; shared public grammar and hypothesis, no selector source/results; not external blind evaluation",
                "hashes": {name: sha(HERE / name) for name in names},
                "baseline_hashes": {str(p.relative_to(ROOT)): sha(p) for p in (
                    ROOT / "research/phase05/revision02/engine.py", ROOT / "research/phase05/corpus.json")}})
    print(f"Frozen: {path}")


def verify_freeze():
    record = json.loads((HERE / "freeze.json").read_text(encoding="utf-8"))
    for name, expected in record["hashes"].items():
        if sha(HERE / name) != expected:
            raise RuntimeError(f"Frozen source/data changed: {name}")
    for name, expected in record["baseline_hashes"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Baseline changed: {name}")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    if sum((args.dev, args.freeze, args.run)) != 1:
        parser.error("Choose exactly one of --dev, --freeze, --run")
    if args.freeze:
        freeze()
        return
    if args.output is None:
        parser.error("Use --output with a NEW directory")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    start = perf_counter()
    if args.dev:
        result = corpus_run(development.build())
        checks = audit.run()
        save(output / "development_results.json", result)
        save(output / "audit.json", checks)
        print(json.dumps({"failures": len(result["failures"]), "comparison": result["comparisons"],
                          "model": checks["model"]}, ensure_ascii=False, indent=2))
        if result["failures"]:
            raise SystemExit(1)
        return
    frozen = verify_freeze()
    cases = json.loads((HERE / "data/holdout.json").read_text(encoding="utf-8"))
    regression = json.loads((ROOT / "research/phase05/corpus.json").read_text(encoding="utf-8"))
    checks = audit.run()
    results = corpus_run(cases)
    regressions = corpus_run(regression)
    save(output / "audit.json", checks)
    results["hypothesis_decisions"] = decisions(results)
    regressions["hypothesis_decisions"] = decisions(regressions)
    save_result(output, "holdout_results.json", results)
    save_result(output, "regression_results.json", regressions)
    measurements = {split: benchmark([case for case in cases if case["split"] == split])
                    for split in sorted({case["split"] for case in cases})}
    measurements["legacy_regression"] = benchmark(regression)
    save(output / "timing.json", measurements)
    matched = []
    if args.compare:
        for name in ("audit.json", "holdout_results.json", "regression_results.json", "holdout_rows.json.gz", "regression_rows.json.gz"):
            if name.endswith(".gz"):
                same = (args.compare / name).read_bytes() == (output / name).read_bytes()
            else:
                same = json.loads((args.compare / name).read_text(encoding="utf-8")) == json.loads((output / name).read_text(encoding="utf-8"))
            matched.append({"file": name, "exact_json_equal": same})
            if not same:
                raise RuntimeError(f"Reproduction differs: {name}")
    failures = len(results["failures"]) + len(regressions["failures"])
    receipt = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "baseline_commit": BASELINE_COMMIT,
               "freeze_sha256": sha(HERE / "freeze.json"), "python": platform.python_version(),
               "platform": platform.platform(), "processor": platform.processor(),
               "elapsed_seconds": perf_counter() - start,
               "status": "passed" if failures == 0 else "failed", "failures": failures,
               "compared_artifacts": matched,
               "artifact_sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()}}
    save(output / "receipt.json", receipt)
    print(json.dumps({"receipt": receipt, "holdout_comparisons": results["comparisons"],
                      "regression_comparisons": regressions["comparisons"]}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
