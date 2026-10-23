"""External whole-interval timers. No audit hooks, tracing, or counters in off paths."""
from collections import Counter
import gc
from itertools import permutations
import math
import os
import platform
import random
from statistics import median, quantiles
import sys
from time import perf_counter_ns

from bindings import E8
import runtime_off as OFF

METHODS = ("fresh_instrumented", "fresh_uninstrumented", "selective_instrumented", "selective_uninstrumented")
REPEATS = 24
CYCLES = 3
SEED = 2026102309
BOOTSTRAPS = 10000
PRACTICAL_RATIO = 0.95
STREAM_REPEATS = 8
STREAM_CYCLES = 5


def fresh_on(public, cache, namespace):
    return E8.run("fresh", public, cache, namespace)


def fresh_off(public, cache, namespace):
    return OFF.run_fresh(public)


def selective_on(public, cache, namespace):
    return E8.run("selective", public, cache, namespace)


def selective_off(public, cache, namespace):
    return OFF.run_selective(public, cache, namespace=namespace)


RUNNERS = dict(zip(METHODS, (fresh_on, fresh_off, selective_on, selective_off)))
FACTORIES = dict(zip(METHODS, (lambda: None, lambda: None, E8.runtime.SelectiveCache, OFF.SelectiveCache)))


def prepare(streams):
    # Labels and future-step metadata are absent from each runtime call.
    return [tuple(({k: step["public"][k] for k in ("records", "entities", "snapshot", "query")},
                   step["parser_namespace"]) for step in stream["steps"]) for stream in streams]


def workload(runner, factory, prepared, cycles):
    for _ in range(cycles):
        for stream in prepared:
            cache = factory()
            for public, namespace in stream:
                runner(public, cache, namespace)


def measure(method, prepared, cycles):
    runner, factory = RUNNERS[method], FACTORIES[method]
    # Both clocks are outside the entire workload, including cache construction
    # and destruction. Imports, loading, preparation and reporting are outside.
    begin = perf_counter_ns()
    workload(runner, factory, prepared, cycles)
    elapsed = perf_counter_ns() - begin
    return {"elapsed_ns": elapsed, "cycles": cycles, "seconds_per_workload": elapsed / cycles / 1e9}


def percentile(values, probability):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * probability
    low = math.floor(pos)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (pos - low)


def paired_comparison(blocks, candidate, reference):
    ratios = [b["measurements"][candidate]["elapsed_ns"] / b["measurements"][reference]["elapsed_ns"] for b in blocks]
    rng = random.Random(SEED + 1)
    resampled = [median(rng.choices(ratios, k=len(ratios))) for _ in range(BOOTSTRAPS)]
    ci = [percentile(resampled, p) for p in (0.025, 0.975)]
    halves = [median(ratios[:len(ratios)//2]), median(ratios[len(ratios)//2:])]
    support = ci[1] < PRACTICAL_RATIO and all(x < PRACTICAL_RATIO for x in halves)
    practical_rejected = ci[0] > PRACTICAL_RATIO
    return {"candidate": candidate, "reference": reference, "paired_ratios": ratios,
            "median_paired_ratio": median(ratios), "change_percent": 100 * (median(ratios) - 1),
            "conditional_bootstrap_95_interval": ci, "first_and_second_half_median_ratios": halves,
            "practical_margin_ratio": PRACTICAL_RATIO,
            "decision": "supports_practical_speedup" if support else "rejects_practical_speedup_here" if practical_rejected else "inconclusive",
            "faster_blocks": sum(x < 1 for x in ratios), "blocks": len(ratios),
            "inference_scope": "fixed corpus and local timing session; resampling unit is complete four-method block, not dialogue or step; exchangeability assumed, serial dependence not excluded"}


def summarize(blocks):
    methods = {}
    for method in METHODS:
        samples = [b["measurements"][method]["seconds_per_workload"] for b in blocks]
        methods[method] = {"samples_seconds": samples, "median_seconds": median(samples),
                           "min_seconds": min(samples), "max_seconds": max(samples),
                           "q25_seconds": percentile(samples, .25), "q75_seconds": percentile(samples, .75)}
    comparisons = {"primary_off_vs_off": paired_comparison(blocks, METHODS[3], METHODS[1]),
                   "instrumented_selective_vs_fresh": paired_comparison(blocks, METHODS[2], METHODS[0]),
                   "fresh_erasure": paired_comparison(blocks, METHODS[1], METHODS[0]),
                   "selective_erasure": paired_comparison(blocks, METHODS[3], METHODS[2])}
    interaction = []
    for b in blocks:
        t = {m: b["measurements"][m]["seconds_per_workload"] for m in METHODS}
        interaction.append((t[METHODS[2]] - t[METHODS[3]]) - (t[METHODS[0]] - t[METHODS[1]]))
    return {"methods": methods, "comparisons": comparisons,
            "erasure_difference_in_differences_seconds": interaction,
            "interaction_caution": "descriptive paired difference only; allocation/GC/branch/cache effects prevent exact additive component attribution"}


def supplementary(streams):
    """Separate descriptive stream and first-step timings, not primary replacements."""
    groups = [(s["id"], [s], s["family"], STREAM_CYCLES) for s in streams]
    first_steps = [dict(s, steps=s["steps"][:1]) for s in streams]
    groups.append(("all_first_steps", first_steps, "all_first_steps", 10))
    rng = random.Random(SEED + 2)
    rng.shuffle(groups)
    results = {}
    pair = (METHODS[1], METHODS[3])
    for label, subset, family, cycles in groups:
        prepared = prepare(subset)
        for method in pair:
            workload(RUNNERS[method], FACTORIES[method], prepared, 1)
        rows = []
        for i in range(STREAM_REPEATS):
            order = pair if i % 2 == 0 else pair[::-1]
            measurements = {method: measure(method, prepared, cycles) for method in order}
            rows.append({"order": list(order), "measurements": measurements})
        ratios = [r["measurements"][pair[1]]["elapsed_ns"] / r["measurements"][pair[0]]["elapsed_ns"] for r in rows]
        results[label] = {"family": family, "queries": sum(len(s["steps"]) for s in subset), "blocks": rows,
                          "median_paired_ratio": median(ratios), "change_percent": 100 * (median(ratios) - 1),
                          "methods": {m: {"median_seconds": median(r["measurements"][m]["seconds_per_workload"] for r in rows)} for m in pair}}
    return results


def run(streams):
    if not gc.isenabled():
        raise RuntimeError("Protocol requires ordinary GC enabled")
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("Launch timing with PYTHONHASHSEED=0")
    original_affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    if original_affinity is not None:
        os.sched_setaffinity(0, {original_affinity[0]})
    environment = {"python": platform.python_version(), "implementation": platform.python_implementation(),
                   "platform": platform.platform(), "machine": platform.machine(), "libc": platform.libc_ver(),
                   "hashseed": os.environ.get("PYTHONHASHSEED"), "gc_enabled": gc.isenabled(),
                   "gc_thresholds": gc.get_threshold(), "original_affinity": original_affinity,
                   "timing_affinity": sorted(os.sched_getaffinity(0)) if original_affinity is not None else None,
                   "clock": "time.perf_counter_ns"}
    prepared = prepare(streams)
    orders = list(permutations(METHODS))
    random.Random(SEED).shuffle(orders)
    assert len(orders) == REPEATS
    for method in METHODS:
        workload(RUNNERS[method], FACTORIES[method], prepared, 1)
    blocks = []
    for i, order in enumerate(orders):
        measurements = {method: measure(method, prepared, CYCLES) for method in order}
        blocks.append({"block": i, "order": list(order), "measurements": measurements})
    result = {"environment": environment, "repeats": REPEATS, "cycles_per_interval": CYCLES,
              "streams": len(streams), "steps": sum(len(s["steps"]) for s in streams),
              "blocks": blocks, "summary": summarize(blocks),
              "scope": "cache construction/destruction, full snapshot validation, parsers, keys/payloads, policy, current-state execution and identical rendering; imports/loading/gold/audits excluded",
              "cold": "empty parser cache per stream and cycle, not cold CPU/OS caches",
              "outliers_removed": 0, "supplementary": supplementary(streams)}
    if original_affinity is not None:
        os.sched_setaffinity(0, set(original_affinity))
    return result
