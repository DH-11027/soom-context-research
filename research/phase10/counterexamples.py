"""Untimed, pre-freeze witnesses for the limits of an offline time predictor.

This module does not open any Phase10 holdout, fit on elapsed-time samples, or
benchmark an implementation. Frozen instrumented paths run only as ledger and
branch witnesses; their internal local_seconds fields are discarded. The exact
production feature.vector function is exercised on explicitly constructed data.
"""
import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
from statistics import mean, median

from bridge import B9, E9, METHODS, evaluator, verify_base
from features import FEATURES, STAGES, vector
from time_model import RIDGE, solve


def quote_bytes(length, letter):
    prefix, suffix = "표현 연습:「", "」라는 문장을 써봤어. 약속은 그대로야."
    text = prefix + letter * (length - len((prefix + suffix).encode())) + suffix
    assert len(text.encode()) == length
    return text


def public(text, entities=("aa", "bb")):
    texts = [f"{entities[0]} 모임 시간은 8시로 확정해줘.",
             f"{entities[1]} 모임 시간은 9시로 확정해줘.", text]
    records = [{"seq": i, "id": f"counterexample-{i}", "text": t} for i, t in enumerate(texts)]
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"records": records, "entities": list(entities),
            "query": f"{entities[0]} 모임은 지금 몇 시야?",
            "snapshot": {"head": len(records) - 1, "digest": hashlib.sha256(raw).hexdigest()}}


def feature_witness(publics):
    """Run the four fixed methods, checking exact prefix trace/state contracts.

    No gold is needed for these source-level counterexamples. The feature
    whitelist is the actual Phase10 vector(), supplied with audited real calls
    and original instrumented ledger rows. This is separate from main timing.
    """
    V = evaluator()
    parts = {m: E9.components(m) for m in E9.METHODS}
    caches = {m: parts[m][0]() for m in parts}
    rows = {m: [] for m in parts}
    chars = {m: 0 for m in METHODS}
    states = []
    raw_traces = {m: [] for m in parts}
    for p in publics:
        observations, traces, policies = {}, {}, {}
        for method, (_, run) in parts.items():
            before = deepcopy(p)
            with V.actual_work(method, caches[method]) as captured:
                result = run(p, caches[method], "v1")
            counts, traces[method], policies[method] = captured
            assert p == before
            assert not V.state_invariants(caches[method])
            observations[method] = V.observe(p, result)
            row = {"audit": counts}
            if "cost" in result:
                row["cost"] = {k: v for k, v in result["cost"].items() if k != "local_seconds"}
            rows[method].append(row)
            raw_traces[method].extend(traces[method])
            if method in chars:
                chars[method] += sum(len(e[1]) for e in traces[method] if e[0] in STAGES)
        assert all(observations[m] == observations[E9.METHODS[0]] for m in parts)
        for on, off in V.ON_OFF:
            assert traces[on] == traces[off]
            assert policies[on] == policies[off]
            assert rows[on][-1]["audit"] == rows[off][-1]["audit"]
        assert V.policy_state(caches["selective_instrumented"]) == V.policy_state(caches["selective_uninstrumented"])
        states.append(V.policy_state(caches["selective_uninstrumented"]))
    values = vector(tuple((p, "v1") for p in publics), rows["fresh_instrumented"],
                    rows["selective_instrumented"], chars)
    cache = caches["selective_uninstrumented"]
    return {"features": values, "states": states, "rows": rows,
            "resident_raw": [key[1] for key in cache.entries],
            "trace_sha256": {m: V.digest(trace) for m, trace in raw_traces.items()}}


def small_summary(run):
    return {"features": run["features"],
            "resident_raw_sha256_in_insertion_order": [hashlib.sha256(x).hexdigest() for x in run["resident_raw"]],
            "trace_sha256": run["trace_sha256"]}


def audit():
    verify_base()
    # JSON/raw/character lengths agree, while escaping the public entity names
    # produces different regex sources in the unchanged parser and scope code.
    text = quote_bytes(1600, "x")
    plain = feature_witness([public(text, ("aa", "bb")) for _ in range(4)])
    escaped = feature_witness([public(text, ("[]", "bb")) for _ in range(4)])
    assert plain["features"] == escaped["features"]
    assert plain["trace_sha256"] != escaped["trace_sha256"]
    names = ["(?:" + "|".join(re.escape(e) for e in entities) + ")"
             for entities in (("aa", "bb"), ("[]", "bb"))]
    assert names[0] != names[1] and len(names[0]) != len(names[1])

    # Equal aggregate features do not reconstruct insertion order or suffice as
    # a Markov policy state. A capacity tie exposes the omitted ordering.
    a, b, c = (public(quote_bytes(n, letter)) for n, letter in ((20000, "a"), (20000, "b"), (30000, "c")))
    ab, ba = feature_witness([a, b]), feature_witness([b, a])
    assert ab["features"] == ba["features"]
    assert ab["states"][-1] != ba["states"][-1]
    assert set(ab["resident_raw"]) == set(ba["resident_raw"])
    abc, bac = feature_witness([a, b, c]), feature_witness([b, a, c])
    assert abc["features"] == bac["features"]
    assert abc["resident_raw"] == [b["records"][-1]["text"].encode(), c["records"][-1]["text"].encode()]
    assert bac["resident_raw"] == [a["records"][-1]["text"].encode(), c["records"][-1]["text"].encode()]
    abca, baca = feature_witness([a, b, c, a]), feature_witness([b, a, c, a])
    assert abca["features"]["saved_stage_calls"] == 0
    assert baca["features"]["saved_stage_calls"] == 3

    # Algebraic bounds use stipulated costs; they are not measurements of any
    # Python implementation, CPU, workload, or corpus.
    initial, saving, hits = Fraction(4), Fraction(1), 5
    stop, continuation = initial, initial - hits * saving
    assert stop > 0 > continuation
    targets, prediction = (Fraction(-2), Fraction(4)), Fraction(1)
    radius = abs(targets[1] - targets[0]) / 2
    assert max(abs(prediction - t) for t in targets) == radius
    for p in (Fraction(x, 2) for x in range(-20, 21)):
        assert max(abs(p - t) for t in targets) >= radius

    first, second = (0, 0, 100), (0, 100, 0)
    sum_medians = median(first) + median(second)
    median_sum = median([a + b for a, b in zip(first, second)])
    assert sum_medians == 0 and median_sum == 100

    # A rank-one standardized design attains the p=10 conditioning upper bound.
    p = len(FEATURES)
    gram = [[1.0 + (RIDGE if j == k else 0) for k in range(p)] for j in range(p)]
    theta = solve(gram, [1.0] * p)
    assert max(abs(x - 1 / (p + RIDGE)) for x in theta) < 1e-11
    residual = max(abs(sum(gram[j][k] * theta[k] for k in range(p)) - 1) for j in range(p))
    assert residual < 1e-11

    actual = [-.04] * 4 + [.04] * 44
    predicted = [.04] * 48
    error = mean(abs(a - b) for a, b in zip(actual, predicted))
    balanced_accuracy = (0 / 4 + 44 / 44) / 2
    assert error < .01 and balanced_accuracy == .5
    tau = Fraction(3, 100)
    checked = 0
    for actual_value in (Fraction(-1, 5), Fraction(-1, 25), Fraction(1, 25), Fraction(1, 5)):
        for predicted_value in (Fraction(x, 100) for x in range(-30, 31)):
            wrong = (actual_value < 0) != (predicted_value < 0)
            if wrong:
                assert abs(actual_value - predicted_value) >= abs(actual_value) >= tau
            checked += 1

    return {"scope": "Constructed development witnesses only; no Phase10 holdout read or elapsed-time benchmark.",
            "feature_order": list(FEATURES),
            "same_features_different_regex_inputs": {
                "left": small_summary(plain), "right": small_summary(escaped),
                "entity_regex_sources": names, "regex_source_lengths": list(map(len, names)),
                "feature_vectors_equal": True, "raw_execution_traces_equal": False,
                "time_relation": "unmeasured; different regex inputs alone do not prove different elapsed times"},
            "same_features_different_order_and_future_reuse": {
                "ab": small_summary(ab), "ba": small_summary(ba),
                "abc": small_summary(abc), "bac": small_summary(bac),
                "prefix_feature_vectors_equal": True, "prefix_policy_states_equal": False,
                "abca_saved_stage_calls": abca["features"]["saved_stage_calls"],
                "baca_saved_stage_calls": baca["features"]["saved_stage_calls"],
                "time_relation": "unmeasured; observed future parser-call differences are not a CPU-time inequality"},
            "abstract_same_prefix_opposite_final_costs": {
                "initial_cost": str(initial), "per_hit_saving": str(saving), "extra_hits": hits,
                "stop_cost": str(stop), "continued_cost": str(continuation),
                "assumptions": "stipulated positive setup cost and positive warm saving; no CPU calibration"},
            "abstract_feature_collision_error_radius": {
                "targets": list(map(str, targets)), "best_common_prediction": str(prediction),
                "unavoidable_max_absolute_error": str(radius)},
            "median_is_not_additive": {"first": first, "second": second,
                "sum_of_medians": sum_medians, "median_of_sums": median_sum},
            "ridge_rank_one_witness": {"features": p, "lambda": RIDGE,
                "unique_theta": theta, "normal_equation_residual": residual,
                "exact_spectral_condition_number": (p + RIDGE) / RIDGE,
                "boundary": "Abstract standardized design; no causal component-price identification"},
            "small_mean_error_does_not_imply_balanced_sign_accuracy": {
                "streams": 48, "speedups": 4, "slowdowns": 44,
                "normalized_mean_absolute_error": error, "balanced_accuracy": balanced_accuracy,
                "boundary": "Constructed normalized targets, not elapsed-time observations"},
            "material_sign_error_bound_grid": {"exact_rational_cases_checked": checked, "margin": str(tau)},
            "actual_on_off_contract_failures": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    data = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(data)
        print(f"Untimed counterexamples verified: {args.output}")
    else:
        print(data, end="")


if __name__ == "__main__":
    main()
