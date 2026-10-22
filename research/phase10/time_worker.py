"""External elapsed-time worker using unchanged Phase09 off implementations.

No feature extractor, audit wrapper, model or profiler is imported. One fixed
calibration session OR one fixed holdout session; all raw samples are retained.
"""
import argparse
from datetime import datetime, timezone
import gc
import math
import os
from pathlib import Path
import platform
import random
from statistics import median
import sys
from time import perf_counter_ns, get_clock_info
from bridge import E9, METHODS, load, prepare, save, sha, verify_base

CALIBRATION_ROUNDS = 12
HOLDOUT_ROUNDS = 24
REPLAYS = 7
WHOLE_ROUNDS = 16
WHOLE_REPLAYS = 2
BOOTSTRAPS = 4000
SEEDS = {"calibration": 20261022100, "primary": 20261022101, "reproduction": 20261022102}

def percentile(values, fraction):
    values = sorted(values)
    x = (len(values)-1)*fraction
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] + (x-lo)*(values[hi]-values[lo])

def stats(values):
    return {"median_us": median(values), "min_us": min(values), "max_us": max(values),
            "q25_us": percentile(values, .25), "q75_us": percentile(values, .75)}

def summary(rounds, seed):
    differences = [r["microseconds"][METHODS[1]] - r["microseconds"][METHODS[0]] for r in rounds]
    fresh = median(r["microseconds"][METHODS[0]] for r in rounds)
    delta = median(differences)
    blocks = [differences[i:i+2] for i in range(0, len(differences), 2)]
    rng = random.Random(seed)
    boot = [median([v for _ in blocks for v in rng.choice(blocks)]) for _ in range(BOOTSTRAPS)]
    interval = [percentile(boot, .025), percentile(boot, .975)]
    relative = [x / fresh for x in interval]
    label = "speedup" if relative[1] < -.03 else "slowdown" if relative[0] > .03 else "unresolved"
    return {"fresh_median_us": fresh, "paired_delta_median_us": delta,
            "delta_over_fresh_median": delta/fresh,
            "delta_bootstrap_95pct_us": interval,
            "delta_interval_divided_by_fixed_fresh_median": relative,
            "material_label": label,
            "methods": {m: stats([r["microseconds"][m] for r in rounds]) for m in METHODS},
            "boundary": "Individual cycle-bootstrap delta interval, normalized by fixed marginal fresh median; not a joint ratio CI or simultaneous 48-stream guarantee. Blocks assumed exchangeable."}

def timed(prepared, pair, replays):
    gc.collect()
    start = perf_counter_ns()
    for _ in range(replays):
        E9.workload(prepared, *pair)
    return (perf_counter_ns()-start)/(1000*replays)

def environment():
    try:
        cpu = next(line.split(":",1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name"))
    except (OSError, StopIteration):
        cpu = None
    clock = get_clock_info("perf_counter")
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "libc": platform.libc_ver(), "cpu_model": cpu,
            "hash_seed": os.getenv("PYTHONHASHSEED"), "gc_enabled": gc.isenabled(),
            "gc_threshold": gc.get_threshold(),
            "clock": {k:getattr(clock,k) for k in ("implementation","monotonic","adjustable","resolution")}}

def run(streams, session, progress):
    verify_base()
    assert not {"features", "evaluator", "audit", "time_model"} & set(sys.modules), "Timing process must not import audit/model"
    assert sys.getprofile() is None and sys.gettrace() is None
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None
    affinity_error = None
    if affinity:
        try:
            os.sched_setaffinity(0,{affinity[0]})
        except OSError as error:
            affinity_error = repr(error)
    gc.enable()
    seed = SEEDS[session]
    rng = random.Random(seed)
    prepared = prepare(streams)
    pairs = {m:E9.components(m) for m in METHODS}
    nrounds = CALIBRATION_ROUNDS if session == "calibration" else HOLDOUT_ROUNDS
    rows = [{"stream_id":s["id"], "family":s["family"], "queries":len(s["steps"]),
             "warmups":[], "rounds":[]} for s in streams]
    started = datetime.now(timezone.utc).isoformat()
    for index, subset in enumerate(prepared):
        order = list(METHODS)
        rng.shuffle(order)
        rows[index]["warmups"].append({"order":order,"microseconds":{m:timed((subset,),pairs[m],REPLAYS) for m in order}})
    schedules = []
    for _ in streams:
        order = []
        for _ in range(nrounds//2):
            first = list(METHODS)
            rng.shuffle(first)
            order.extend([first, list(reversed(first))])
        schedules.append(order)
    global_orders = []
    for round_index in range(nrounds):
        sequence = list(range(len(streams)))
        rng.shuffle(sequence)
        global_orders.append([streams[i]["id"] for i in sequence])
        for index in sequence:
            order = schedules[index][round_index]
            values = {m:timed((prepared[index],),pairs[m],REPLAYS) for m in order}
            rows[index]["rounds"].append({"round":round_index,"order":order,"microseconds":values})
        progress.write_text(__import__("json").dumps({"completed_rounds":round_index+1,"target_rounds":nrounds,"streams":rows,"global_stream_orders":global_orders}))
    per_stream_finished = datetime.now(timezone.utc).isoformat()
    # Prespecified secondary workload measurement, separate from per-stream data.
    whole = None
    if session != "calibration":
        warmup = {m:timed(prepared,pairs[m],WHOLE_REPLAYS) for m in METHODS}
        whole_rows = []
        for cycle in range(WHOLE_ROUNDS//2):
            first = list(METHODS)
            rng.shuffle(first)
            for order in (first,list(reversed(first))):
                whole_rows.append({"round":len(whole_rows),"order":order,
                    "microseconds":{m:timed(prepared,pairs[m],WHOLE_REPLAYS) for m in order}})
        whole = {"warmup":warmup,"rounds":whole_rows,"replays":WHOLE_REPLAYS,
                 "summary":summary(whole_rows,seed+10000)}
    for index, row in enumerate(rows):
        row["summary"] = summary(row["rounds"],seed+index+1)
    return {"session":session,"environment":environment(),"seed":seed,
            "affinity_before":affinity,"affinity_during":sorted(os.sched_getaffinity(0)) if affinity else None,
            "affinity_error":affinity_error,"started_at_utc":started,
            "per_stream_finished_at_utc":per_stream_finished,"finished_at_utc":datetime.now(timezone.utc).isoformat(),
            "rounds_per_stream":nrounds,"replays_per_interval":REPLAYS,"bootstrap_samples":BOOTSTRAPS,
            "streams":rows,"global_stream_orders":global_orders,"whole_workload":whole,
            "scope":"Unchanged P9 off: cold cache creation/destruction, complete validation, parsing, key/payload/policy, current demand/state/copy/render. Import/loading/gold/features/model/GC precollection excluded.",
            "cold":"Parser cache starts empty each stream and each replay; CPU/OS caches not flushed.",
            "boundary":"Repeated measurements of fixed synthetic streams, not independent conversations. Raw samples and warmups retained without outlier deletion."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--session",required=True,choices=tuple(SEEDS))
    args = parser.parse_args()
    assert not args.output.exists() and not args.output.with_suffix(".progress.json").exists()
    result = run(load(args.data),args.session,args.output.with_suffix(".progress.json"))
    result["input_sha256"] = sha(args.data)
    save(args.output,result)
    print(__import__("json").dumps({"session":args.session,"streams":len(result["streams"]),"rounds_per_stream":result["rounds_per_stream"],"whole":result["whole_workload"]["summary"] if result["whole_workload"] else None}))

if __name__ == "__main__":
    main()

