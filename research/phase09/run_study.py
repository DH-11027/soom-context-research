"""Freeze, verify, evaluate, separately time, preserve, and reproduce Phase09."""
import argparse
from datetime import datetime, timezone, timedelta
import gzip
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from bindings import HERE, ROOT, BASE_COMMIT, P8E, sha, verify_sources
import erase
import data_profile

CORE = ("bindings.py", "erase.py", "erasure_manifest.json", "off_fresh.py", "off_selective.py",
        "execution.py", "evaluator.py", "audit.py", "counterexamples.py", "counterexample_results.json", "benchmark.py", "data_profile.py", "run_study.py",
        "PROTOCOL.md", "THEORY.md", "MATH_REVIEW.md", "EVALUATOR_REVIEW.md")
DATA = ("holdout_builder.py", "HOLDOUT_AUTHOR.md", "data/holdout.json.gz", "data/holdout_manifest.json")
BASE_FILES = ("research/phase05/revision02/engine.py", "research/phase06/scoped.py", "research/phase06/evaluate.py",
              "research/phase07/baseline.py", "research/phase07/cached.py", "research/phase07/study.py",
              "research/phase08/frozen.py", "research/phase08/runtime.py", "research/phase08/evaluation.py",
              "research/phase08/data/holdout.json", "research/phase08/data/development.json",
              "research/phase07/data/holdout.json", "research/phase06/data/holdout.json", "research/phase05/corpus.json")
DETERMINISTIC = ("audit.json", "holdout_results.json", "holdout_rows.json.gz", "holdout_states.json.gz",
                 "regression_results.json", "regression_rows.json.gz", "regression_states.json.gz", "data_profile.json")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_gzip(path, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", fileobj=handle, mode="wb", mtime=0, compresslevel=9) as target:
            target.write(raw)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def regressions():
    result = []
    for label, name in (("phase08_development", "development.json"), ("phase08_former_holdout", "holdout.json")):
        data = load(ROOT / "research/phase08/data" / name)
        for s in data:
            s["id"] = label + "-" + s["id"]
            s["split"] = "known_development_regression"
        result.extend(data)
    return result + P8E.regressions()


def freeze():
    assert not (HERE / "freeze.json").exists(), "Never replace a freeze"
    verify_sources()
    for name, content in erase.build().items():
        assert (HERE / name).read_bytes() == content, name
    for name in (*CORE, *DATA):
        disk = (HERE / name).read_bytes()
        tracked = subprocess.check_output(["git", "show", "HEAD:research/phase09/" + name], cwd=ROOT)
        assert tracked == disk, "Commit current source before freeze: " + name
    now = datetime.now(timezone.utc)
    save(HERE / "freeze.json", {"created_at_utc": now.isoformat(),
        "created_at_kst": now.astimezone(timezone(timedelta(hours=9))).isoformat(),
        "baseline_commit": BASE_COMMIT, "checkpoint_commit": git("rev-parse", "HEAD"),
        "checkpoint_tree": git("rev-parse", "HEAD^{tree}"),
        "boundary": "local freeze before root/math/evaluator opens new raw/labels/builder; same-model shared-design synthetic holdout; not external preregistration",
        "primary": "40 paired rounds, 3 cold-stream whole-workload replays each; median log-ratio selective_off/fresh_off; 3pct margin; original and one reproduction",
        "hashes": {name: sha(HERE / name) for name in (*CORE, *DATA)},
        "baseline_hashes": {name: sha(ROOT / name) for name in BASE_FILES}})


def verify():
    saved = load(HERE / "freeze.json")
    for name, value in saved["hashes"].items():
        assert sha(HERE / name) == value, name
    for name, value in saved["baseline_hashes"].items():
        assert sha(ROOT / name) == value, name
    for name, content in erase.build().items():
        assert (HERE / name).read_bytes() == content, name
    verify_sources()
    return saved


def save_evaluation(output, label, value):
    rows = value.pop("rows")
    states = value.pop("state_rows")
    save_gzip(output / (label + "_rows.json.gz"), rows)
    save_gzip(output / (label + "_states.json.gz"), states)
    value["raw_artifacts"] = {"rows": {"file": label + "_rows.json.gz", "count": len(rows), "sha256": sha(output / (label + "_rows.json.gz"))},
                              "states": {"file": label + "_states.json.gz", "count": len(states), "sha256": sha(output / (label + "_states.json.gz"))}}
    save(output / (label + "_results.json"), value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    for name in ("dev", "freeze", "verify", "run"):
        mode.add_argument("--" + name, action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--session", choices=("primary", "reproduction"), default="primary")
    args = parser.parse_args()
    if args.freeze:
        freeze()
        print("Local freeze created. New corpus contents were not printed/opened to the implementer.")
        return
    if args.verify:
        verify()
        print("Frozen source/data, base sources and exact AST erasure verified.")
        return
    if args.output is None:
        parser.error("A new --output directory is required")
    args.output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    import audit
    import evaluator
    verify_sources()
    save(args.output / "audit.json", audit.run())
    regression = evaluator.evaluate(regressions())
    save_evaluation(args.output, "regression", regression)
    if args.dev:
        save(args.output / "receipt.json", {"started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
             "status": "passed" if not regression["failures"] else "failed", "new_holdout_opened": False})
        print(json.dumps({"regression_summary": regression["summary"], "failures": regression["failures"]}, ensure_ascii=False))
        if regression["failures"]:
            raise SystemExit(1)
        return
    verify()
    streams = load(HERE / "data/holdout.json.gz")
    result = evaluator.evaluate(streams)
    save_evaluation(args.output, "holdout", result)
    save(args.output / "data_profile.json", data_profile.profile(streams))
    failures = len(result["failures"]) + len(regression["failures"])
    compared = []
    if args.compare:
        for name in DETERMINISTIC:
            equal = (args.output / name).read_bytes() == (args.compare / name).read_bytes()
            compared.append({"file": name, "byte_identical": equal})
            assert equal, name
    # A single discrepancy blocks all performance claims and main timing.
    if failures:
        save(args.output / "receipt.json", {"started_at_utc": started, "status": "erasure_contract_failed", "failures": failures,
             "timing_executed": False, "compared": compared})
        raise SystemExit("Contract failed; timing not run.")
    env = dict(os.environ, PYTHONHASHSEED="0")
    command = [sys.executable, str(HERE / "benchmark.py"), "--data", str(HERE / "data/holdout.json.gz"),
               "--output", str(args.output / "timing.json"), "--session", args.session]
    process = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    (args.output / "timing_stdout.txt").write_text(process.stdout)
    (args.output / "timing_stderr.txt").write_text(process.stderr)
    if process.returncode:
        save(args.output / "receipt.json", {"started_at_utc": started, "status": "timing_failed", "returncode": process.returncode,
              "compared": compared, "failures": failures})
        raise SystemExit(process.returncode)
    timing = load(args.output / "timing.json")
    save(args.output / "receipt.json", {"started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed", "failures": failures, "timing_separate_process": True, "session": args.session,
        "python": platform.python_version(), "platform": platform.platform(),
        "freeze_sha256": sha(HERE / "freeze.json"), "compared": compared,
        "artifact_sha256": {p.name: sha(p) for p in sorted(args.output.iterdir()) if p.is_file()}})
    print(json.dumps({"failures": failures, "compared": compared, "primary": timing["comparisons"]["primary"],
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

