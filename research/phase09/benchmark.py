"""External whole-workload timing. No gold/audit execution, trace or monkeypatch.

Run in its own interpreter. All raw samples, including warmups, are retained.
One invocation is a fixed 40-round session; never stop for a favorable result.
Original instrumented wrappers and their evaluation modules are imported before
timing; their gold assessors are not called in any timed workload.
"""
import argparse
from datetime import datetime, timezone
import gc
import gzip
import json
import math
import os
from pathlib import Path
import platform
import random
from statistics import median
import sys
from time import get_clock_info, perf_counter_ns

from bindings import HERE, ROOT, sha, verify_sources
from execution import METHODS, components, workload

ROUNDS = 40
REPLAYS = 3
WARMUPS = 2
DIAGNOSTIC_ROUNDS = 8
BOOTSTRAPS = 20000
PRIMARY_SEED = 2026102209
REPRODUCTION_SEED = 2026102210
BOOTSTRAP_SEED = 902026
PRACTICAL_MARGIN = 0.03
ORDERS = ((0, 1, 3, 2), (1, 2, 0, 3), (2, 3, 1, 0), (3, 0, 2, 1))


def load_data(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def prepare(streams, first_only=False):
    # Fresh dicts carry only public input fields. Gold/family never reach run().
    return tuple(tuple(({k: step["public"][k] for k in ("records", "entities", "snapshot", "query")},
                         step["parser_namespace"])
                       for step in (stream["steps"][:1] if first_only else stream["steps"]))
                 for stream in streams)


def percentile(values, p):
    values = sorted(values)
    x = (len(values) - 1) * p
    a, b = math.floor(x), math.ceil(x)
    return values[a] + (x - a) * (values[b] - values[a])


def paired_summary(rounds, candidate, reference):
    logs = [math.log(r["seconds"][candidate] / r["seconds"][reference]) for r in rounds]
    # Resample complete consecutive four-round order-balanced cycles, never
    # individual questions. This is uncertainty of this fixed workload's
    # repeated measurements, not sampling uncertainty of conversations.
    assert len(logs) % 4 == 0
    cycles = [logs[i:i + 4] for i in range(0, len(logs), 4)]
    rng = random.Random(BOOTSTRAP_SEED)
    estimates = []
    for _ in range(BOOTSTRAPS):
        sample = [x for _ in cycles for x in rng.choice(cycles)]
        estimates.append(math.exp(median(sample)))
    ratio = math.exp(median(logs))
    low, high = percentile(estimates, .025), percentile(estimates, .975)
    if high < 1 - PRACTICAL_MARGIN:
        decision = "material_speedup_observed"
    elif low > 1 + PRACTICAL_MARGIN:
        decision = "material_slowdown_observed"
    elif low >= 1 - PRACTICAL_MARGIN and high <= 1 + PRACTICAL_MARGIN:
        decision = "within_practical_margin"
    else:
        decision = "inconclusive_under_frozen_local_rule"
    return {"candidate": candidate, "reference": reference,
            "paired_median_ratio": ratio, "change_percent": 100 * (ratio - 1),
            "measurement_bootstrap_95pct_ratio": [low, high],
            "decision": decision,
            "bootstrap_unit": "four consecutive order-balanced rounds of the same fixed workload",
            "cycles": len(cycles), "bootstrap_samples": BOOTSTRAPS,
            "assumption": "cycles are sufficiently exchangeable; arbitrary inter-cycle host drift is not covered",
            "population_inference": False}


def distribution(values):
    return {"median_seconds": median(values), "min_seconds": min(values), "max_seconds": max(values),
            "q25_seconds": percentile(values, .25), "q75_seconds": percentile(values, .75)}


def timed(prepared, pair, replays):
    factory, run = pair
    gc.collect()  # equal initial collection outside both methods' intervals
    start = perf_counter_ns()
    for _ in range(replays):
        workload(prepared, factory, run)
    elapsed = perf_counter_ns() - start
    return elapsed / (1e9 * replays)


def environment():
    try:
        cpu_model = next(x.split(":", 1)[1].strip() for x in Path("/proc/cpuinfo").read_text().splitlines()
                         if x.startswith("model name"))
    except (OSError, StopIteration):
        cpu_model = None
    clock = get_clock_info("perf_counter")
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(), "libc": platform.libc_ver(),
            "cpu_model": cpu_model, "python_hash_seed": os.getenv("PYTHONHASHSEED"),
            "gc_enabled": gc.isenabled(), "gc_threshold": gc.get_threshold(),
            "clock": {k: getattr(clock, k) for k in ("implementation", "monotonic", "adjustable", "resolution")}}


def run(streams, seed, progress_path=None):
    before_affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    affinity_error = None
    if before_affinity:
        try:
            os.sched_setaffinity(0, {before_affinity[0]})
        except OSError as error:
            affinity_error = repr(error)
    verify_sources()
    assert sys.gettrace() is None and sys.getprofile() is None, "Primary timing forbids trace/profiler"
    assert "evaluator" not in sys.modules and "audit" not in sys.modules, "Use a separate timing process"
    gc.enable()
    prepared = prepare(streams)
    pairs = {m: components(m) for m in METHODS}
    warmups = []
    for _ in range(WARMUPS):
        warmups.append({m: timed(prepared, pairs[m], REPLAYS) for m in METHODS})
    rng = random.Random(seed)
    schedule = []
    for _ in range(ROUNDS // 4):
        group = list(ORDERS)
        rng.shuffle(group)
        schedule.extend(group)
    rounds = []
    started = datetime.now(timezone.utc).isoformat()
    for index, order in enumerate(schedule):
        row = {"round": index, "order": [METHODS[i] for i in order], "seconds": {}}
        for method in row["order"]:
            row["seconds"][method] = timed(prepared, pairs[method], REPLAYS)
        rounds.append(row)
        if progress_path:
            progress_path.write_text(json.dumps({"completed_rounds": len(rounds), "target": ROUNDS,
                "order_seed": seed, "warmups": warmups, "rounds": rounds}))
    main_finished = datetime.now(timezone.utc).isoformat()
    comparisons = {
        "primary": paired_summary(rounds, "selective_uninstrumented", "fresh_uninstrumented"),
        "instrumented": paired_summary(rounds, "selective_instrumented", "fresh_instrumented"),
        "fresh_erasure": paired_summary(rounds, "fresh_uninstrumented", "fresh_instrumented"),
        "selective_erasure": paired_summary(rounds, "selective_uninstrumented", "selective_instrumented"),
    }
    # Separate descriptive runs; no per-stream timer is inserted into main.
    diagnostics = {}
    for stream in streams:
        subsets = {"whole_stream": prepare([stream]), "first_step_cold": prepare([stream], True)}
        item = {"family": stream["family"], "queries": len(stream["steps"])}
        for label, subset in subsets.items():
            samples = {m: [] for m in METHODS}
            for i in range(DIAGNOSTIC_ROUNDS):
                for n in ORDERS[i % 4]:
                    method = METHODS[n]
                    samples[method].append(timed(subset, pairs[method], 1))
            item[label] = {"samples_seconds": samples, "methods": {m: distribution(v) for m, v in samples.items()}}
        diagnostics[stream["id"]] = item
    medians = {m: distribution([r["seconds"][m] for r in rounds]) for m in METHODS}
    return {"environment": environment(), "affinity_before": before_affinity,
            "affinity_during": sorted(os.sched_getaffinity(0)) if before_affinity else None,
            "affinity_error": affinity_error, "started_at_utc": started,
            "main_finished_at_utc": main_finished, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "order_seed": seed, "rounds_count": ROUNDS, "replays_per_interval": REPLAYS,
            "warmups": warmups, "rounds": rounds, "methods": medians, "comparisons": comparisons,
            "ratio_of_marginal_medians": medians["selective_uninstrumented"]["median_seconds"] / medians["fresh_uninstrumented"]["median_seconds"],
            "diagnostics": diagnostics, "streams": len(streams), "queries": sum(len(s["steps"]) for s in streams),
            "scope": "cold cache construction/destruction, full snapshot validation, parse, key/payload, unchanged policy, current state/copy, evidence render; excludes import/loading/gold/audit/GC precollection",
            "cold_definition": "parser cache empty per stream per replay; Python/CPU/OS caches not flushed",
            "interpretation": "on-off deltas are total implementation effects with interactions, not additive component CPU costs"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--session", choices=("primary", "reproduction"), default="primary")
    args = parser.parse_args()
    assert not args.output.exists(), "Do not overwrite a timing session"
    streams = load_data(args.data)
    result = run(streams, PRIMARY_SEED if args.session == "primary" else REPRODUCTION_SEED,
                 args.output.with_suffix(".progress.json"))
    result["input_sha256"] = sha(args.data)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"session": args.session, "primary": result["comparisons"]["primary"],
                      "medians": {m: r["median_seconds"] for m, r in result["methods"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()

