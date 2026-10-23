"""Freeze, verify, audit, time, and reproduce one bounded Phase09 study."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import traceback

from bindings import ROOT, BASE_COMMIT, E8, verify_sources
import derive_off

HERE = Path(__file__).resolve().parent
CORE = ("bindings.py", "derive_off.py", "runtime_off.py", "ERASURE_MAP.json", "benchmark.py",
        "audit_equivalence.py", "counterexamples.py", "run_study.py", "recount_results.py",
        "PROTOCOL.md", "THEORY.md", "MATH_REVIEW.md", "EVALUATOR_REVIEW.md")
DATA = ("holdout_builder.py", "HOLDOUT_AUTHOR.md", "data/holdout.json.gz", "data/holdout_manifest.json")
BASE_FILES = ("research/phase05/revision02/engine.py", "research/phase06/scoped.py", "research/phase06/evaluate.py",
              "research/phase07/baseline.py", "research/phase07/cached.py", "research/phase07/study.py",
              "research/phase08/frozen.py", "research/phase08/runtime.py", "research/phase08/evaluation.py",
              "research/phase08/data/holdout.json", "research/phase07/data/holdout.json",
              "research/phase06/data/holdout.json", "research/phase05/corpus.json")
DETERMINISTIC = ("audit_mutants.json", "counterexamples.json", "holdout_results.json", "holdout_rows.json.gz",
                 "regression_results.json", "regression_rows.json.gz")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def freeze():
    if (HERE / "freeze.json").exists():
        raise FileExistsError("The original freeze must not be replaced")
    verify_sources()
    generated, mapping = derive_off.generate()
    assert (HERE / "runtime_off.py").read_text() == generated
    assert (HERE / "ERASURE_MAP.json").read_text() == mapping
    for name in (*CORE, *DATA):
        tracked = subprocess.check_output(["git", "show", "HEAD:research/phase09/" + name], cwd=ROOT)
        assert tracked == (HERE / name).read_bytes(), "Commit exact pre-evaluation artifact: " + name
    save(HERE / "freeze.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "baseline_commit": BASE_COMMIT,
        "checkpoint_commit": git("rev-parse", "HEAD"), "checkpoint_tree": git("rev-parse", "HEAD^{tree}"),
        "boundary": "Root and reviewers have not opened new raw/gold/builder; same-model author with shared public design; local freeze, not external preregistration",
        "primary": "Median of 24 paired whole-workload selective_off/fresh_off ratios; cold-inclusive, 3 cycles; practical threshold 0.95 with conditional block interval and half-session consistency",
        "hashes": {name: sha(HERE / name) for name in (*CORE, *DATA)},
        "baseline_hashes": {name: sha(ROOT / name) for name in BASE_FILES},
    })


def verify():
    snapshot = json.loads((HERE / "freeze.json").read_text())
    for name, digest in snapshot["hashes"].items():
        assert sha(HERE / name) == digest, name
    for name, digest in snapshot["baseline_hashes"].items():
        assert sha(ROOT / name) == digest, name
    generated, mapping = derive_off.generate()
    assert (HERE / "runtime_off.py").read_text() == generated
    assert (HERE / "ERASURE_MAP.json").read_text() == mapping
    verify_sources()
    return snapshot


def regressions():
    p8 = json.loads((ROOT / "research/phase08/data/holdout.json").read_text())
    for stream in p8:
        stream["id"] = "phase08-" + stream["id"]
        stream["family"] = "phase08_known_development"
        stream["split"] = "known_development_regression"
    return p8 + E8.regressions()


def save_result(output, name, result):
    rows = result.pop("rows")
    row_name = name.replace("_results.json", "_rows.json.gz")
    raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    with (output / row_name).open("wb") as fh:
        with gzip.GzipFile(filename="", fileobj=fh, mode="wb", mtime=0) as zipped:
            zipped.write(raw)
    result["raw_rows"] = {"file": row_name, "count": len(rows), "uncompressed_bytes": len(raw),
                          "sha256": sha(output / row_name)}
    save(output / name, result)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    modes = ap.add_mutually_exclusive_group(required=True)
    for mode in ("freeze", "verify", "run"):
        modes.add_argument("--" + mode, action="store_true")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--compare", type=Path)
    args = ap.parse_args()
    if args.freeze:
        freeze()
        print("Local freeze saved; new input content not opened.")
        return
    if args.verify:
        verify()
        print("Frozen source/data/baseline hashes and generated erasure verified.")
        return
    if args.output is None:
        ap.error("A new --output directory is required")
    args.output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    try:
        verify()
        import audit_equivalence as audit
        import counterexamples
        import benchmark
        streams = json.loads(gzip.decompress((HERE / "data/holdout.json.gz").read_bytes()))
        save(args.output / "audit_mutants.json", {"state_mutants": audit.mutation_audit(),
                                                "restoration": audit.restoration_audit()})
        save(args.output / "counterexamples.json", counterexamples.run())
        result = audit.evaluate(streams)
        regression = audit.evaluate(regressions())
        failure_count = len(result["failures"]) + len(regression["failures"])
        save_result(args.output, "holdout_results.json", result)
        save_result(args.output, "regression_results.json", regression)
        if failure_count:
            raise RuntimeError(f"Erasure/gold audit failed: {failure_count}; timing forbidden")
        # No audit context or trace hook is active in benchmark.run.
        timing = benchmark.run(streams)
        save(args.output / "timing.json", timing)
        compared = []
        if args.compare:
            for name in DETERMINISTIC:
                equal = (args.output / name).read_bytes() == (args.compare / name).read_bytes()
                compared.append({"file": name, "byte_identical": equal})
                assert equal, name
        receipt = {"started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                   "python": platform.python_version(), "implementation": platform.python_implementation(),
                   "platform": platform.platform(), "freeze_sha256": sha(HERE / "freeze.json"),
                   "status": "passed", "correctness_failures": failure_count,
                   "H9": timing["summary"]["comparisons"]["primary_off_vs_off"]["decision"],
                   "compared": compared, "artifact_sha256": {p.name: sha(p) for p in sorted(args.output.iterdir()) if p.is_file()}}
        save(args.output / "receipt.json", receipt)
        print(json.dumps({"receipt": receipt, "primary": timing["summary"]["comparisons"]["primary_off_vs_off"]}, ensure_ascii=False))
    except Exception:
        save(args.output / "failure_receipt.json", {"started_at_utc": started,
             "failed_at_utc": datetime.now(timezone.utc).isoformat(), "traceback": traceback.format_exc(),
             "boundary": "Original partial outputs preserved; no advantageous rerun selected."})
        raise


if __name__ == "__main__":
    main()
