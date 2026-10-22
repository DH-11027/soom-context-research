"""Freeze before opening new evaluation; preserve outputs and reproduce exactly."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from time import perf_counter

import development
import evaluation
import frozen

HERE = Path(__file__).resolve().parent
CORE = ("frozen.py", "runtime.py", "evaluation.py", "development.py", "audit.py", "run_study.py",
        "PROTOCOL.md", "THEORY.md", "MATH_REVIEW.md", "EVALUATOR_REVIEW.md")
DATA = ("data/development.json", "holdout_builder.py", "data/holdout.json",
        "data/holdout_manifest.json", "HOLDOUT_AUTHOR.md")
BASE_FILES = ("research/phase05/revision02/engine.py", "research/phase06/scoped.py",
              "research/phase06/evaluate.py", "research/phase07/baseline.py", "research/phase07/cached.py",
              "research/phase07/study.py", "research/phase07/data/holdout.json",
              "research/phase06/data/holdout.json", "research/phase05/corpus.json")
DETERMINISTIC = ("audit.json", "holdout_results.json", "holdout_rows.json.gz",
                 "regression_results.json", "regression_rows.json.gz")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=frozen.ROOT, text=True).strip()


def freeze():
    if (HERE / "freeze.json").exists():
        raise RuntimeError("Existing freeze must not be overwritten")
    frozen.verify_sources()
    development_bytes = (json.dumps(development.build(), ensure_ascii=False, indent=2) + "\n").encode()
    assert (HERE / "data/development.json").read_bytes() == development_bytes, "Commit generated development data first"
    for name in (*CORE, *DATA):
        assert (HERE / name).is_file(), name
        # Every frozen artifact must already belong to the pre-evaluation
        # checkpoint commit, not just an untracked working-tree file.
        tracked = subprocess.check_output(["git", "show", "HEAD:research/phase08/" + name], cwd=frozen.ROOT)
        assert tracked == (HERE / name).read_bytes(), "Commit current artifact first: " + name
    save(HERE / "freeze.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": frozen.BASE_COMMIT,
        "checkpoint_commit": git("rev-parse", "HEAD"),
        "checkpoint_tree": git("rev-parse", "HEAD^{tree}"),
        "seed": 2026102208,
        "boundary": "Local freeze before root opens new Phase08 raw data/labels/builder; same model with shared public design; not external preregistration",
        "primary_metric": "P8=P7+8*control_actions; aggregate cold-start selective versus frozen fresh",
        "hashes": {name: sha(HERE / name) for name in (*CORE, *DATA)},
        "baseline_hashes": {name: sha(frozen.ROOT / name) for name in BASE_FILES},
    })


def verify():
    snapshot = json.loads((HERE / "freeze.json").read_text())
    for name, expected in snapshot["hashes"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in snapshot["baseline_hashes"].items():
        assert sha(frozen.ROOT / name) == expected, name
    frozen.verify_sources()
    return snapshot


def save_result(output, name, result):
    rows = result.pop("rows")
    row_name = name.replace("_results.json", "_rows.json.gz")
    raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    with (output / row_name).open("wb") as handle:
        with gzip.GzipFile(filename="", fileobj=handle, mode="wb", mtime=0) as zipped:
            zipped.write(raw)
    result["raw_rows"] = {"file": row_name, "count": len(rows), "uncompressed_bytes": len(raw), "sha256": sha(output / row_name)}
    comparison = result["comparisons"]["selective"]
    preserved = not result["failures"]
    reduced = comparison["parser_executions_after"] < comparison["parser_executions_before"]
    cheaper = comparison["after_score"] < comparison["before_score"]
    result["hypothesis_decisions"] = {
        "observed_preservation_checks_passed": preserved,
        "actual_parser_execution_reduction": reduced,
        "lower_primary_work_score": cheaper,
        "H8_supported_in_this_dataset": preserved and reduced and cheaper,
        "universal_cost_dominance": "refuted_by_predeclared_finite_stream_counterexamples",
        "external_natural_language_accuracy": "not_evaluated",
        "real_LLM_tokens_cost_quality": "not_measured",
    }
    save(output / name, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    for name in ("dev", "freeze", "verify", "run"):
        mode.add_argument("--" + name, action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
        print("Local freeze written without exposing holdout content to the root researcher.")
        return
    if args.verify:
        verify()
        print("All frozen Phase08 and baseline hashes verified.")
        return
    if args.output is None:
        parser.error("A new --output directory is required")
    args.output.mkdir(parents=True, exist_ok=False)
    started_utc, started = datetime.now(timezone.utc).isoformat(), perf_counter()
    import audit
    frozen.verify_sources()
    if args.dev:
        save(args.output / "audit.json", audit.run())
        result = evaluation.evaluate(development.build())
        save_result(args.output, "development_results.json", result)
        print(json.dumps({"failures": result["failures"], "primary": result["comparisons"]["selective"],
                          "hypothesis_decisions": result["hypothesis_decisions"]}, ensure_ascii=False))
        if result["failures"]:
            raise SystemExit(1)
        return
    verify()
    streams = json.loads((HERE / "data/holdout.json").read_text())
    save(args.output / "audit.json", audit.run())
    result = evaluation.evaluate(streams)
    regression = evaluation.evaluate(evaluation.regressions())
    failure_count = len(result["failures"]) + len(regression["failures"])
    save_result(args.output, "holdout_results.json", result)
    save_result(args.output, "regression_results.json", regression)
    timing = evaluation.benchmark(streams)
    save(args.output / "timing.json", timing)
    compared = []
    if args.compare:
        for name in DETERMINISTIC:
            equal = (args.output / name).read_bytes() == (args.compare / name).read_bytes()
            compared.append({"file": name, "byte_identical": equal})
            assert equal, name
    receipt = {
        "started_at_utc": started_utc, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "implementation": platform.python_implementation(),
        "platform": platform.platform(), "machine": platform.machine(), "libc": platform.libc_ver(),
        "freeze_sha256": sha(HERE / "freeze.json"), "elapsed_seconds": perf_counter() - started,
        "failures": failure_count, "status": "passed" if not failure_count else "failed",
        "compared": compared, "artifact_sha256": {p.name: sha(p) for p in sorted(args.output.iterdir()) if p.is_file()},
    }
    save(args.output / "receipt.json", receipt)
    print(json.dumps({"receipt": receipt, "H8": result["hypothesis_decisions"],
                      "primary": {k: v for k, v in result["comparisons"]["selective"].items() if k != "streams"},
                      "time_change_percent": timing["selective_vs_fresh_percent"]}, ensure_ascii=False))
    if failure_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
