"""Offline mathematical experiments. Standard library only; no SOOM imports or APIs.

All coverage labels and cost units are synthetic. This is not a language-model
benchmark, a tokenizer measurement, or a production context-selection policy.
Run: python -X utf8 experiment.py
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product
from math import log2
from pathlib import Path
import hashlib
import json
import platform
import random
import statistics
import time

SEED = 20261022
N_WORLDS = 80
NOISE_LEVELS = (0.0, 0.05, 0.1, 0.2, 0.4)


@dataclass(frozen=True)
class Variant:
    name: str
    kind: str
    cost: float
    cover: tuple[float, ...]


def variants(name, summary_cost, summary_cover, raw_cover, raw_cost=None):
    zero = (0.0,) * len(raw_cover)
    return (
        Variant(name, "omit", 0, zero),
        Variant(name, "index", 10, zero),
        Variant(name, "summary", summary_cost, tuple(summary_cover)),
        Variant(name, "original", raw_cost or 3 * summary_cost, tuple(raw_cover)),
    )


def plans_for(groups):
    return tuple(product(*(range(len(group)) for group in groups)))


def costs_for(groups, plans, shared_summary_frame=20):
    result = []
    for plan in plans:
        selected = [groups[i][j] for i, j in enumerate(plan)]
        result.append(sum(v.cost for v in selected) + (
            shared_summary_frame if any(v.kind == "summary" for v in selected) else 0
        ))
    return result


def gains_for(covers, weights, baseline, plans):
    values = []
    for plan in plans:
        best = list(baseline)
        for i, j in enumerate(plan):
            if j < 2:  # indexes have no answer coverage in this one-step toy
                continue
            for f, value in enumerate(covers[i][j]):
                if value > best[f]:
                    best[f] = value
        values.append(sum(w * (b - p) for w, b, p in zip(weights, best, baseline)))
    return values


def covers_for(groups):
    return [[variant.cover for variant in group] for group in groups]


def solve(gains, costs, price):
    # Tie break by lower cost, then the fixed enumeration order.
    return max(range(len(gains)), key=lambda i: (gains[i] - price * costs[i], -costs[i], -i))


def fixed_cases():
    names = ("api", "api_repeat", "payments", "compute", "section_quote", "shopping", "ui")
    dimensions = (0, 0, 1, 2, 3, 4, 5)
    summary_costs = (100, 130, 90, 160, 700, 90, 70)
    groups = []
    for name, dimension, cost in zip(names, dimensions, summary_costs):
        raw = [0.0] * 7
        raw[dimension] = 1.0
        summary = [0.9 * x for x in raw]
        if name == "section_quote":
            summary[dimension] = 0.0  # literal quotation cannot be recovered from this summary
        groups.append(variants(name, cost, summary, raw))
    plans = plans_for(groups)
    costs = costs_for(groups, plans)
    baseline = [0.0] * 6 + [1.0]  # current prompt-status information is already protected
    queries = {
        "current_prompt_only": (0, 0, 0, 0, 0, 0, 1),
        "api_followup": (5, 0, 0, 0, 0, 0, 0),
        "api_and_payments": (5, 4, 0, 0, 0, 0, 0),
        "exact_section_quote": (0, 0, 0, 10, 0, 0, 0),
    }
    rows = []
    for query, weights in queries.items():
        gains = gains_for(covers_for(groups), weights, baseline, plans)
        chosen = solve(gains, costs, 0.003)
        rows.append({
            "query": query,
            "selected": [f"{groups[i][j].name}:{groups[i][j].kind}"
                         for i, j in enumerate(plans[chosen]) if j],
            "cost_units": costs[chosen], "coverage_gain": gains[chosen],
            "objective": gains[chosen] - 0.003 * costs[chosen],
        })
    assert not rows[0]["selected"]
    assert rows[3]["selected"] == ["section_quote:original"]
    # Monotonicity is a property of exact optimization with FIXED gains/costs/options.
    gains = gains_for(covers_for(groups), queries["api_and_payments"], baseline, plans)
    sweep = []
    for price in (0.0, 0.0005, 0.001, 0.003, 0.01, 0.02, 0.05, 0.1):
        chosen = solve(gains, costs, price)
        sweep.append({"lambda": price, "cost_units": costs[chosen], "gain": gains[chosen]})
    assert all(a["cost_units"] >= b["cost_units"] for a, b in zip(sweep, sweep[1:]))
    return {"plans_per_query": len(plans), "lambda": 0.003, "cases": rows, "price_sweep": sweep}


def entropy(values):
    counts = Counter(values)
    return -sum((n / len(values)) * log2(n / len(values)) for n in counts.values())


def counterexamples():
    # Reproduce Krause & Guestrin (2005), Example 1, rather than assume that
    # arbitrary task-relevant mutual information has diminishing returns.
    samples = [(a, b, a ^ b) for a in (0, 1) for b in (0, 1)]
    target = [s[2] for s in samples]
    info = {}
    for label, columns in (("A", (0,)), ("B", (1,)), ("A_and_B", (0, 1))):
        observed = [tuple(s[i] for i in columns) for s in samples]
        joint = list(zip(target, observed))
        info[label] = entropy(target) + entropy(observed) - entropy(joint)
    assert info == {"A": 0.0, "B": 0.0, "A_and_B": 1.0}
    utility = {0: 0.0, 1: 0.6, 2: 1.2}
    cost = {0: 0.0, 1: 1.0, 2: 1.1}  # 0.9 shared frame plus 0.1 per item
    scores = {str(n): utility[n] - cost[n] for n in utility}
    assert scores["1"] < 0 < scores["2"]
    return {
        "xor_mutual_information_bits": info,
        "shared_frame_objectives": scores,
        "shared_frame_positive_marginal_greedy_items": 0,
        "shared_frame_exact_optimum_items": 2,
    }


def make_world(seed):
    rng = random.Random(seed)
    weights = [rng.uniform(0.2, 1.0) if rng.random() > 0.25 else 0.0 for _ in range(6)]
    groups = []
    for i in range(5):
        raw = [float(rng.random() < 0.38) for _ in range(6)]
        if not any(raw):
            raw[rng.randrange(6)] = 1.0
        if i == 4:  # a repeated source about the same facts
            raw = list(groups[0][3].cover)
        summary = [0.9 * x if rng.random() < 0.75 else 0.0 for x in raw]
        groups.append(variants(f"g{i}", rng.randint(25, 75), summary, raw, rng.randint(110, 230)))
    return groups, weights, [0.4, 0.0, 0.0, 0.0, 0.0, 0.0]


def clip(value):
    return max(0.0, min(1.0, value))


def perturb(covers, weights, sigma, seed):
    rng = random.Random(seed)
    estimated_weights = [clip(w + sigma * rng.gauss(0, 1)) for w in weights]
    estimated_covers = []
    for group in covers:
        estimated_group = []
        for j, coverage in enumerate(group):
            estimated_group.append(tuple(
                clip(a + sigma * rng.gauss(0, 1)) if j >= 2 else 0.0 for a in coverage
            ))
        estimated_covers.append(estimated_group)
    return estimated_covers, estimated_weights


def noise_experiment():
    plans = tuple(product(range(4), repeat=5))
    samples = {sigma: [] for sigma in NOISE_LEVELS}
    bound_checks = 0
    for world in range(N_WORLDS):
        groups, weights, baseline = make_world(SEED + world)
        covers = covers_for(groups)
        costs = costs_for(groups, plans)
        true_gains = gains_for(covers, weights, baseline, plans)
        true_scores = [g - 0.003 * c for g, c in zip(true_gains, costs)]
        oracle = solve(true_gains, costs, 0.003)
        for sigma in NOISE_LEVELS:
            # Same underlying Gaussian draws at each sigma within each world.
            estimated_covers, estimated_weights = perturb(covers, weights, sigma, SEED + 10000 + world)
            estimated_gains = gains_for(estimated_covers, estimated_weights, baseline, plans)
            chosen = solve(estimated_gains, costs, 0.003)
            regret = max(0.0, true_scores[oracle] - true_scores[chosen])
            epsilon = max(abs(a - b) for a, b in zip(true_gains, estimated_gains))
            weight_error = sum(abs(a - b) for a, b in zip(weights, estimated_weights))
            coverage_error = [max(abs(covers[i][j][f] - estimated_covers[i][j][f])
                                  for i in range(5) for j in range(4)) for f in range(6)]
            upper_epsilon = weight_error + sum(w * e for w, e in zip(weights, coverage_error))
            assert regret <= 2 * epsilon + 1e-10
            assert epsilon <= upper_epsilon + 1e-10
            bound_checks += 1
            samples[sigma].append({
                "world": world, "regret": regret, "epsilon": epsilon,
                "epsilon_bound": upper_epsilon, "oracle_cost": costs[oracle],
                "chosen_cost": costs[chosen], "oracle_plan": plans[oracle],
                "chosen_plan": plans[chosen], "oracle_objective": true_scores[oracle],
                "chosen_true_objective": true_scores[chosen],
            })
    rows = []
    for sigma, observations in samples.items():
        regrets = [o["regret"] for o in observations]
        worst = max(observations, key=lambda o: o["regret"])
        rows.append({
            "sigma": sigma, "worlds": N_WORLDS,
            "mean_regret": statistics.mean(regrets), "max_regret": max(regrets),
            "positive_regret_worlds": sum(r > 1e-10 for r in regrets),
            "mean_epsilon": statistics.mean(o["epsilon"] for o in observations),
            "worst_case": worst,
        })
    assert rows[0]["max_regret"] == 0
    return {
        "seed": SEED, "worlds": N_WORLDS, "plans_per_world": len(plans),
        "lambda": 0.003, "rows": rows, "bound_checks_passed": bound_checks,
        "samples": {str(sigma): obs for sigma, obs in samples.items()},
    }


def run_all():
    started = time.perf_counter()
    results = {
        "scope": "synthetic offline research only; no production changes or model calls",
        "cost_unit": "arbitrary synthetic units, not measured tokens",
        "python": platform.python_version(),
        "counterexamples": counterexamples(), "fixed_cases": fixed_cases(),
        "noise": noise_experiment(),
    }
    results["elapsed_seconds"] = time.perf_counter() - started
    return results


def summary(results):
    noise = {k: v for k, v in results["noise"].items() if k != "samples"}
    return {**results, "noise": noise}


if __name__ == "__main__":
    result = run_all()
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    target = Path(__file__).resolve().parent / "results.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary(result), ensure_ascii=False, indent=2))
