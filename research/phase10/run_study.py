"""Bounded calibration, freeze, sealed predictions, held-out timing and replay."""
import argparse
from datetime import datetime, timezone, timedelta
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from time import perf_counter
from bridge import HERE, ROOT, P9, BASE_COMMIT, load, save, save_gzip, sha, verify_base

CORE = ("bridge.py","development.py","features.py","time_model.py","time_worker.py","scoring.py","run_study.py",
        "audit.py","development_audit.json","counterexamples.py","counterexample_results.json",
        "PROTOCOL.md","THEORY.md","MATH_REVIEW.md","EVALUATOR_REVIEW.md","DEVELOPMENT_AUDIT.md","calibration_plan.json")
UNSEEN = ("holdout_builder.py","docs/HOLDOUT_AUTHOR.md","data/holdout.json.gz","data/holdout_manifest.json")
DETERMINISTIC = ("audit.json","model_refit.json","holdout_features.json","predictions.json",
                 "holdout_results.json","holdout_rows.json.gz","holdout_states.json.gz","data_profile.json")
STAGE = "initialization"

def stage(name):
    global STAGE
    STAGE = name

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()

def save_evaluation(output,label,result):
    rows,states = result.pop("rows"),result.pop("state_rows")
    save_gzip(output/(label+"_rows.json.gz"),rows)
    save_gzip(output/(label+"_states.json.gz"),states)
    result["raw_artifacts"] = {"rows":{"file":label+"_rows.json.gz","count":len(rows),"sha256":sha(output/(label+"_rows.json.gz"))},
                               "states":{"file":label+"_states.json.gz","count":len(states),"sha256":sha(output/(label+"_states.json.gz"))}}
    save(output/(label+"_results.json"),result)

def worker(data,output,session):
    env = dict(os.environ,PYTHONHASHSEED="0")
    command = [sys.executable,str(HERE/"time_worker.py"),"--data",str(data.resolve()),"--output",str(output/"timing.json"),"--session",session]
    try:
        process = subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,timeout=900)
    except subprocess.TimeoutExpired as error:
        for label,value in (("stdout",error.stdout),("stderr",error.stderr)):
            value = value.decode("utf-8",errors="replace") if isinstance(value,bytes) else value or ""
            (output/("timing_"+label+".txt")).write_text(value)
        save(output/"worker_failure.json",{"status":"timeout","seconds":900,
             "progress_exists":(output/"timing.progress.json").exists(),"partial_output_preserved":True})
        raise RuntimeError("Fixed session timed out; do not silently rerun") from error
    (output/"timing_stdout.txt").write_text(process.stdout)
    (output/"timing_stderr.txt").write_text(process.stderr)
    if process.returncode:
        save(output/"worker_failure.json",{"status":"worker_failed","returncode":process.returncode,
             "progress_exists":(output/"timing.progress.json").exists()})
        raise RuntimeError("Timing worker failed: "+process.stderr)
    return load(output/"timing.json")

def fitted_model(directory):
    from time_model import fit
    model = fit(load(directory/"calibration_features.json")["records"],load(directory/"timing.json"))
    model["calibration_sha256"] = {name:sha(directory/name) for name in ("calibration_data.json.gz","calibration_features.json","timing.json")}
    return model

def calibrate(output):
    import audit
    from development import build
    from features import extract
    from time_model import predict,grouped_cv
    from scoring import score
    started = datetime.now(timezone.utc).isoformat()
    stage("calibration_known_data_audit_and_features")
    verify_base()
    save(output/"audit.json",audit.run())
    streams = build()
    save_gzip(output/"calibration_data.json.gz",streams)
    features,checked = extract(streams)
    save(output/"calibration_features.json",features)
    save_evaluation(output,"calibration",checked)
    # Only this one predetermined calibration measurement; no holdout access.
    stage("calibration_timing")
    timing = worker(output/"calibration_data.json.gz",output,"calibration")
    stage("calibration_fixed_fit_and_grouped_cv")
    model = fitted_model(output)
    save(output/"model.json",model)
    predictions = predict(model,features["records"])
    save(output/"calibration_predictions.json",predictions)
    save(output/"calibration_scores.json",score(predictions,timing))
    cv = grouped_cv(features["records"],timing)
    all_predictions = {"predictions":[row for fold in cv["folds"] for row in fold["predictions"]]}
    cv["scores"] = score(all_predictions,timing)
    save(output/"grouped_cv.json",cv)
    save(output/"receipt.json",{"started_at_utc":started,"finished_at_utc":datetime.now(timezone.utc).isoformat(),
         "status":"passed","new_holdout_opened":False,"calibration_sessions":1,"hyperparameter_search":False,
         "files":{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}})
    print(json.dumps({"calibration_streams":len(streams),"prefixes":checked["prefixes"],
                      "train_errors":load(output/"calibration_scores.json")["mean_normalized_absolute_error"],
                      "grouped_cv_errors":cv["scores"]["mean_normalized_absolute_error"]}))

def freeze():
    verify_base()
    assert not (HERE/"freeze.json").exists()
    names = list(CORE)+list(UNSEEN)+[str(p.relative_to(HERE)) for p in sorted((HERE/"calibration").iterdir()) if p.is_file()]
    assert fitted_model(HERE/"calibration") == load(HERE/"calibration/model.json")
    for name in names:
        disk = (HERE/name).read_bytes()
        committed = subprocess.check_output(["git","show","HEAD:research/phase10/"+name],cwd=ROOT)
        assert disk==committed,"Commit before freeze: "+name
    now = datetime.now(timezone.utc)
    save(HERE/"freeze.json",{"created_at_utc":now.isoformat(),"created_at_kst":now.astimezone(timezone(timedelta(hours=9))).isoformat(),
         "baseline_commit":BASE_COMMIT,"checkpoint_commit":git("rev-parse","HEAD"),"checkpoint_tree":git("rev-parse","HEAD^{tree}"),
         "hashes":{name:sha(HERE/name) for name in names},"phase09_freeze_sha256":sha(P9/"freeze.json"),
         "model_sha256":sha(HERE/"calibration/model.json"),
         "boundary":"Local freeze after one known-data calibration and before implementer/math/evaluator opens new holdout. Same-model author, shared grammar. Not external preregistration."})

def verify():
    verify_base()
    record = load(HERE/"freeze.json")
    for name,digest in record["hashes"].items():
        assert sha(HERE/name)==digest,name
    assert sha(P9/"freeze.json")==record["phase09_freeze_sha256"]
    assert fitted_model(HERE/"calibration")==load(HERE/"calibration/model.json"),"Frozen model refit differs"
    return record

def run(output,session,compare):
    stage("frozen_sources_verification")
    verify()
    import audit
    from features import extract
    from time_model import predict
    from scoring import score
    started = datetime.now(timezone.utc).isoformat()
    stage("known_data_audit_and_saved_model_refit_witness")
    save(output/"audit.json",audit.run())
    refit = fitted_model(HERE/"calibration")
    model = load(HERE/"calibration/model.json")
    assert refit == model
    save(output/"model_refit.json",refit)
    stage("holdout_untimed_preservation_and_feature_extraction")
    streams = load(HERE/"data/holdout.json.gz")
    began = perf_counter()
    features,checked = extract(streams)
    extraction_elapsed = perf_counter()-began
    save(output/"holdout_features.json",features)
    save_evaluation(output,"holdout",checked)
    spec = importlib.util.spec_from_file_location("phase09_data_profile",P9/"data_profile.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    save(output/"data_profile.json",module.profile(streams))
    predictions = predict(model,features["records"])
    save(output/"predictions.json",predictions)
    seal = {"sealed_at_utc":datetime.now(timezone.utc).isoformat(),"phase10_freeze_sha256":sha(HERE/"freeze.json"),
            "model_sha256":sha(HERE/"calibration/model.json"),"data_sha256":sha(HERE/"data/holdout.json.gz"),
            "features_sha256":sha(output/"holdout_features.json"),"predictions_sha256":sha(output/"predictions.json"),
            "untimed_audit_and_feature_wall_seconds":extraction_elapsed,
            "boundary":"Audit/feature wall duration includes four-path preservation/gold plus two extra trace replays; not minimal predictor-only cost, and excluded from runtime comparison. Predictions sealed before this session's timing."}
    save(output/"prediction_receipt.json",seal)
    stage("deterministic_comparison_after_prediction_seal")
    compared = []
    if compare:
        for name in DETERMINISTIC:
            equal = (output/name).read_bytes()==(compare/name).read_bytes()
            compared.append({"file":name,"byte_identical":equal})
            assert equal,name
    stage(session+"_holdout_timing")
    timing = worker(HERE/"data/holdout.json.gz",output,session)
    assert timing["started_at_utc"] > seal["sealed_at_utc"]
    stage(session+"_scoring")
    scored = score(predictions,timing)
    save(output/"scores.json",scored)
    save(output/"receipt.json",{"started_at_utc":started,"finished_at_utc":datetime.now(timezone.utc).isoformat(),
         "status":"passed","meaning_of_passed":"Execution and preservation; not H10 support", "session":session,
         "predictions_sealed_before_timing":True,"model_refitted_on_reproduction_timing":False,
         "compared":compared,"preservation_failures":len(checked["failures"]),
         "files":{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}})
    print(json.dumps({"session":session,"streams":len(streams),"prefixes":checked["prefixes"],
                      "errors":scored["mean_normalized_absolute_error"],"numerical_rule_passed":scored["numerical_rule_passed"],"compared":compared}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    for name in ("calibrate","freeze","verify","run"):
        mode.add_argument("--"+name,action="store_true")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--session",choices=("primary","reproduction"),default="primary")
    parser.add_argument("--compare",type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze(); print("Local Phase10 model/code/data freeze saved; holdout contents not displayed."); return
    if args.verify:
        verify(); print("Phase10 frozen source/data/model and Phase09 original source hashes verified."); return
    if args.output is None: parser.error("--output must name a new directory")
    output = args.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    try:
        if args.calibrate: calibrate(output)
        else: run(output,args.session,args.compare.resolve() if args.compare else None)
    except Exception as error:
        save(output/"failure_receipt.json",{"status":"failed","stage":STAGE,
             "started_at_utc":started,"failed_at_utc":datetime.now(timezone.utc).isoformat(),
             "error_type":type(error).__name__,"error":str(error),"traceback":traceback.format_exc(),
             "progress_exists":(output/"timing.progress.json").exists(),
             "existing_files":{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()},
             "boundary":"Partial artifacts retained. No successful hypothesis conclusion or automatic rerun."})
        raise

if __name__ == "__main__":
    main()

