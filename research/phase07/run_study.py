"""Freeze before opening new holdout, run and exactly reproduce deterministic outputs."""
import argparse
import gzip
import hashlib
import json
import platform
from pathlib import Path
from datetime import datetime, timezone
from time import perf_counter

import baseline
import cached
import development
import study

HERE = Path(__file__).resolve().parent
CORE = ("baseline.py", "cached.py", "development.py", "study.py", "audit.py", "run_study.py", "PROTOCOL.md", "THEORY.md")
DETERMINISTIC = ("audit.json", "holdout_results.json", "holdout_rows.json.gz", "regression_results.json", "regression_rows.json.gz")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def freeze():
    if (HERE/"freeze.json").exists():
        raise RuntimeError("Freeze already exists")
    baseline.verify_sources()
    save(HERE/"data/development.json", development.build())
    names = (*CORE, "data/development.json", "holdout_builder.py", "data/holdout.json", "HOLDOUT_AUTHOR.md")
    save(HERE/"freeze.json", {"created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "13d166dc106fa3ab33128ad0626679fafdce5019", "seed": 2026102207,
        "boundary": "Local freeze before root reads new holdout; same-model author/shared design; not external preregistration",
        "hashes": {name: sha(HERE/name) for name in names},
        "baseline_hashes": {str(p.relative_to(baseline.ROOT)): sha(p) for p in (baseline.P6DIR/"scoped.py", baseline.P6DIR/"evaluate.py", baseline.ROOT/"research/phase05/revision02/engine.py")}})

def verify():
    frozen = json.loads((HERE/"freeze.json").read_text())
    for name, digest in frozen["hashes"].items():
        assert sha(HERE/name) == digest, name
    for name, digest in frozen["baseline_hashes"].items():
        assert sha(baseline.ROOT/name) == digest, name
    baseline.verify_sources()
    return frozen

def save_result(output, name, result):
    rows = result.pop("rows")
    row_name = name.replace("_results.json", "_rows.json.gz")
    raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    with (output/row_name).open("wb") as file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=file, mtime=0) as zipper:
            zipper.write(raw)
    result["raw_rows"] = {"file": row_name, "count": len(rows), "uncompressed_bytes": len(raw), "sha256": sha(output/row_name)}
    result["hypothesis_decisions"] = {
        "H7_S": "passed_observed_parity_and_gold_checks" if not result["failures"] else "failed",
        "H7_P": "exercised" if result["comparisons"]["lru"]["parser_executions_after"] < result["comparisons"]["lru"]["parser_executions_before"] else "not_exercised",
        "H7_C": "lower_proxy_in_this_dataset" if result["comparisons"]["lru"]["after_proxy"] < result["comparisons"]["lru"]["before_proxy"] else "no_total_proxy_gain",
        "real_LLM_cost_tokens_quality": "not_measured"}
    save(output/name, result)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    for name in ("dev", "freeze", "run"):
        mode.add_argument("--"+name, action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", type=Path)
    args=parser.parse_args()
    if args.freeze:
        freeze()
        print("Frozen before new holdout evaluation")
        return
    if args.output is None:
        parser.error("New --output directory required")
    args.output.mkdir(parents=True, exist_ok=False)
    started=perf_counter()
    import audit
    if args.dev:
        result=study.evaluate(development.build())
        save(args.output/"audit.json", audit.run())
        save_result(args.output,"development_results.json",result)
        print(json.dumps({"failures":result["failures"],"lru":result["comparisons"]["lru"]},ensure_ascii=False))
        if result["failures"]:
            raise SystemExit(1)
        return
    verify()
    streams=json.loads((HERE/"data/holdout.json").read_text())
    checks=audit.run()
    save(args.output/"audit.json",checks)
    result=study.evaluate(streams)
    regression=study.evaluate(study.regressions())
    failures=len(result["failures"])+len(regression["failures"])
    save_result(args.output,"holdout_results.json",result)
    save_result(args.output,"regression_results.json",regression)
    timing=study.benchmark(streams)
    meds=timing["groups"]["all"]["methods"]
    timing["H7_T"]={"comparison":"lru vs frozen fresh, all streams from cold start",
        "median_change_percent":100*(meds["lru"]["median_seconds"]/meds["fresh"]["median_seconds"]-1),
        "statistical_significance_tested":False}
    save(args.output/"timing.json",timing)
    compared=[]
    if args.compare:
        for name in DETERMINISTIC:
            same=(args.output/name).read_bytes()==(args.compare/name).read_bytes()
            compared.append({"file":name,"byte_identical":same})
            assert same,name
    receipt={"created_at_utc":datetime.now(timezone.utc).isoformat(),"python":platform.python_version(),
        "platform":platform.platform(),"freeze_sha256":sha(HERE/"freeze.json"),"elapsed_seconds":perf_counter()-started,
        "failures":failures,"status":"passed" if not failures else "failed","compared":compared,
        "artifact_sha256":{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}}
    save(args.output/"receipt.json",receipt)
    print(json.dumps({"receipt":receipt,"holdout_comparison":result["comparisons"]["lru"],"H7_T":timing["H7_T"]},ensure_ascii=False))
    if failures:
        raise SystemExit(1)

if __name__=="__main__":
    main()
