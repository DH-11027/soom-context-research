"""Run the historical experiments in a NEW copy and compare semantic JSON results.

No freeze commands. No production access. Original archive remains unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from verify_archive import ROOT, verify

# Each phase runs in a separate interpreter; local modules cannot leak across phases.
PHASES = {
    "01": [
        ("", "experiment.py", [], ["results.json"]),
    ],
    "02": [
        ("phase02", "study.py", [], ["fixtures.json", "results.json"]),
        ("phase02", "diagnose_links.py", [], ["link_diagnostic.json"]),
    ],
    "03": [
        ("phase03", "evaluate.py", ["--dev"], ["development.json"]),
        ("phase03", "evaluate.py", ["--test"], ["evaluation_fixtures.json", "results.json"]),
        ("phase03", "audit_labels.py", [], ["label_audit.json"]),
    ],
    "04": [
        ("phase04", "study.py", ["--run"], ["results.json"]),
        ("phase04", "audit.py", [], ["audit.json"]),
    ],
    "05": [
        ("phase05", "study.py", ["--run"], ["results.json"]),
        ("phase05", "audit.py", [], ["audit.json"]),
        ("phase05", "reduction_study.py", ["--run"], ["reduction_results.json"]),
    ],
    "05r2": [
        ("phase05/revision02", "reduction_study.py", ["--run"], ["reduction_results.json"]),
    ],
}

REPORTS = {"01": ("", "make_note.py"), "02": ("phase02", "make_report.py"),
           "03": ("phase03", "make_report.py"), "04": ("phase04", "make_report.py"),
           "05": ("phase05", "make_report.py"), "05r2": ("phase05", "make_report.py")}

# Exact JSON paths, not a wildcard that might hide a metric named 'time'.
ENVIRONMENT_FIELDS = {
    "results.json": {("elapsed_seconds",), ("python",)},
    "phase02/results.json": {("elapsed_seconds",), ("python",)},
    "phase03/results.json": {("elapsed_seconds",), ("python",)},
    "phase04/audit.json": {("results_sha256",)},
}


def canonical(value, relative, path=()):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            current = path + (key,)
            ignored = current in ENVIRONMENT_FIELDS.get(relative, set())
            ignored |= (relative == "phase05/results.json" and len(current) == 3
                        and current[0] == "scaling" and current[-1] == "seconds_one_local_run")
            if not ignored:
                result[key] = canonical(item, relative, current)
        return result
    if isinstance(value, list):
        return [canonical(item, relative, path + (i,)) for i, item in enumerate(value)]
    return value


def first_difference(a, b, path="$"):
    if type(a) is not type(b):
        return f"{path}: type differs"
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return f"{path}: keys differ"
        for key in a:
            if a[key] != b[key]:
                return first_difference(a[key], b[key], f"{path}.{key}")
    elif isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: list length differs"
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return first_difference(x, y, f"{path}[{i}]")
    return f"{path}: values differ"


def compare(original: Path, generated: Path, relative: str):
    before = json.loads(original.read_text(encoding="utf-8"))
    after = json.loads(generated.read_text(encoding="utf-8"))
    if relative == "phase04/audit.json":
        digest = hashlib.sha256((generated.parent / "results.json").read_bytes()).hexdigest()
        if after["results_sha256"] != digest:
            raise RuntimeError("Regenerated audit is not bound to regenerated results")
    left, right = canonical(before, relative), canonical(after, relative)
    if left != right:
        raise RuntimeError(f"Result differs: {relative}: {first_difference(left, right)}")
    return {"path": relative, "semantic_json_equal": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["all", *PHASES], default="all")
    parser.add_argument("--output", type=Path, help="New output directory; must not already exist")
    parser.add_argument("--reports", action="store_true", help="Also regenerate HTML/notebooks in the copy")
    args = parser.parse_args()
    initial_check = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = args.output or ROOT / ".reproductions" / stamp
    output = output.resolve()
    if output == ROOT or (ROOT / "research") == output or (ROOT / "research") in output.parents:
        raise SystemExit("Output must be separate from the preserved archive")
    output.mkdir(parents=True, exist_ok=False)
    working = output / "research"
    shutil.copytree(ROOT / "research", working, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    phases = list(PHASES) if args.phase == "all" else [args.phase]
    environment = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    receipt = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
               "python": platform.python_version(), "platform": platform.system(), "phases": phases,
               "initial_archive_check": initial_check, "steps": [], "status": "running"}

    def run(folder, script, arguments, expected_files):
        number = len(receipt["steps"]) + 1
        label = str(Path(folder) / script)
        print(f"[{number}] {label} {' '.join(arguments)}", flush=True)
        start = time.perf_counter()
        target = working / folder / script
        command = [sys.executable, str(target), *arguments]
        log_name = f"{number:02d}-{Path(script).stem}.log"
        with (output / log_name).open("w", encoding="utf-8") as log:
            completed = subprocess.run(command, cwd=target.parent, env=environment,
                                       stdout=log, stderr=subprocess.STDOUT)
        step = {"script": label, "arguments": arguments, "exit_code": completed.returncode,
                "seconds": time.perf_counter() - start, "log": log_name, "comparisons": []}
        receipt["steps"].append(step)
        if completed.returncode:
            raise RuntimeError(f"{label} failed; see {output / log_name}")
        for name in expected_files:
            relative = (Path(folder) / name).as_posix()
            step["comparisons"].append(compare(ROOT / "research" / relative, working / relative, relative))

    try:
        for phase in phases:
            for folder, script, arguments, files in PHASES[phase]:
                run(folder, script, arguments, files)
        if "05r2" in phases:
            # This helper only reads the copied artifacts and does not rewrite receipts.
            from check_revision import check
            receipt["revision_regression"] = check(working)
        if args.reports:
            done = set()
            for phase in phases:
                report = REPORTS[phase]
                if report not in done:
                    run(*report, [], [])
                    done.add(report)
        receipt["final_archive_check"] = verify()
        receipt["status"] = "passed"
    except Exception as error:
        receipt["status"] = "failed"
        receipt["error"] = str(error)
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Receipt: {output / 'receipt.json'}", flush=True)
    print(f"PASS: {sum(len(s['comparisons']) for s in receipt['steps'])} JSON artifacts matched; original archive unchanged.", flush=True)


if __name__ == "__main__":
    main()
