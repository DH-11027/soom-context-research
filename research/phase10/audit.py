"""Bounded, untimed pre-freeze audit using only known Phase09 development data.

No Phase10 holdout, timer, benchmark worker, or new elapsed-time observation.
Wrappers below are diagnostic and restored in finally blocks.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import math
from statistics import median

from bridge import B9, E9, METHODS, P9, evaluator, load, prepare, save, verify_base
import features
import time_model

OBS_FIELDS = ("status", "reason", "prediction", "selected", "output_bytes",
              "remaining_input_facts", "scope_trace")
STAGES = ("cheap", "contract", "detail")
FIXTURES = ("long_deep_repeat-00", "long_deep_repeat-02", "fit_working_set-01",
            "same_length_misses-00", "integrity_unsupported_recovery-00")


def known_fixtures():
    known = load(P9 / "data/holdout.json.gz")
    result = []
    for suffix in FIXTURES:
        stream = deepcopy(next(s for s in known if s["id"] == "p9-holdout-" + suffix))
        stream["steps"] = stream["steps"][:4]
        result.append(stream)
    assert len(result) == 5 and sum(len(s["steps"]) for s in result) == 20
    return result


def independent_vector(public_stream):
    """Direct actual operations; never reads the main vector or its cost totals."""
    V = evaluator()
    traces_by_method, totals, encoded_lengths = {}, {}, []
    per_prefix = []
    original_encode = E9.off_selective.encode
    for method in METHODS:
        factory, run = E9.components(method)
        traced_cache, plain_cache = factory(), factory()
        traces, policies = [], []
        total = Counter()
        for index, (public, namespace) in enumerate(public_stream):
            source = deepcopy(public)
            plain_value = run(deepcopy(public), plain_cache, namespace)
            step_encodes = []

            def encode(value):
                result = original_encode(value)
                is_context = (isinstance(value, tuple) and len(value) == 3
                              and value[0] == B9.P8R.SEMANTIC_FINGERPRINT)
                step_encodes.append(("context" if is_context else "payload", len(result)))
                return result

            if method == "selective_uninstrumented":
                E9.off_selective.encode = encode
            try:
                with V.actual_work(method, traced_cache) as recorded:
                    traced_value = run(public, traced_cache, namespace)
            finally:
                E9.off_selective.encode = original_encode
            counts, trace, policy = recorded
            assert public == source, "Diagnostic mutated input"
            assert V.observe(public, plain_value) == V.observe(public, traced_value)
            assert V.policy_state(plain_cache) == V.policy_state(traced_cache)
            total.update(counts)
            traces.extend(trace)
            policies.extend(policy)
            if method == "selective_uninstrumented":
                assert sum(kind == "context" for kind, _ in step_encodes) <= 1
                encoded_lengths.extend(step_encodes)
                per_prefix.append({"step_index": index,
                    "context_encodes": sum(kind == "context" for kind, _ in step_encodes),
                    "payload_encodes": sum(kind == "payload" for kind, _ in step_encodes),
                    "probe_bytes": sum(len(e[1][0]) + len(e[1][1]) for e in policy if e[0] == "get"),
                    "admissions": sum(e[0] == "admit" for e in policy),
                    "plain_vs_traced_observation_equal": True,
                    "plain_vs_traced_policy_state_equal": True})
        traces_by_method[method] = (traces, policies)
        totals[method] = total

    # Count declared P8 action invocations directly, independently of summing its ledger.
    factory, run = E9.components("selective_instrumented")
    cache = factory()
    actions = Counter()
    original_action = B9.P8R.action

    def action(cost, name, count=1):
        actions[name] += count
        return original_action(cost, name, count)

    B9.P8R.action = action
    try:
        for public, namespace in public_stream:
            run(deepcopy(public), cache, namespace)
    finally:
        B9.P8R.action = original_action

    fresh_trace = traces_by_method[METHODS[0]][0]
    selective_trace, policy = traces_by_method[METHODS[1]]
    fresh_stages = [e for e in fresh_trace if e[0] in STAGES]
    selective_stages = [e for e in selective_trace if e[0] in STAGES]
    result = {
        "stream_constant": 1,
        "queries": len(public_stream),
        "records_visited": sum(e[0] == "cheap" for e in fresh_trace),
        "raw_encode_bytes": sum(len(e[1].encode("utf-8")) for e in fresh_trace if e[0] == "cheap"),
        "saved_stage_calls": len(fresh_stages) - len(selective_stages),
        "saved_stage_characters": sum(len(e[1]) for e in fresh_stages) - sum(len(e[1]) for e in selective_stages),
        "exact_probe_bytes": sum(len(e[1][0]) + len(e[1][1]) for e in policy if e[0] == "get"),
        "encoded_context_payload_bytes": sum(length for _, length in encoded_lengths),
        "admission_attempts": sum(e[0] == "admit" for e in policy),
        "policy_control_actions": sum(actions.values()),
    }
    assert tuple(result) == features.FEATURES
    return result, {"prefixes": per_prefix, "declared_control_events": dict(actions),
                    "encoding_calls": dict(Counter(kind for kind, _ in encoded_lengths)),
                    "on_off_actual_stage_totals": {m: {s: totals[m][s + "_calls"] for s in STAGES}
                                                  for m in METHODS}}


def reject_mutant(function):
    try:
        function()
    except (AssertionError, KeyError, ValueError):
        return True
    return False


def replay_mutants(public_stream, expected):
    """Mutate only this additional replay after the original four-path check."""
    original = E9.components
    outcomes = []
    for field in ("scope_trace", "prediction"):
        def broken_components(method):
            factory, run = original(method)
            if method != "fresh_uninstrumented":
                return factory, run

            def broken(public, cache, namespace):
                value = run(public, cache, namespace)
                value.pop(field)
                return value
            return factory, broken

        E9.components = broken_components
        try:
            detected = reject_mutant(lambda: features.character_trace(public_stream, expected))
        finally:
            E9.components = original
        assert detected, "Character replay accepted missing Obs field: " + field
        outcomes.append({"mutant": "character_replay_missing_" + field, "detected": True})
    return outcomes


def cholesky_solve(matrix, rhs):
    """Independent SPD solver, unlike the implementation's Gauss-Jordan solver."""
    n = len(rhs)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            value = matrix[i][j] - sum(lower[i][k] * lower[j][k] for k in range(j))
            lower[i][j] = math.sqrt(value) if i == j else value / lower[j][j]
    intermediate = []
    for i in range(n):
        intermediate.append((rhs[i] - sum(lower[i][k] * intermediate[k] for k in range(i))) / lower[i][i])
    solution = [0.0] * n
    for i in range(n - 1, -1, -1):
        solution[i] = (intermediate[i] - sum(lower[k][i] * solution[k] for k in range(i + 1, n))) / lower[i][i]
    return solution


def model_audit():
    """Constructed numeric inputs only: these are NOT measured runtime samples."""
    paired = {"rounds": [{"microseconds": dict(zip(METHODS, pair))}
                         for pair in ((10, 110), (100, 101), (110, 112))]}
    assert time_model.target(paired) == (2, 100)  # Difference of medians would be 10.
    records, timing = [], {"streams": []}
    for i in range(24):
        vector = {name: 1 if j == 0 else (i + 1) % 4 + 1 if j == 1 else
                  0 if j == 9 else ((i + 3) * (j + 5) + i * i) % 37
                  for j, name in enumerate(features.FEATURES)}
        identifier = "numeric-unit-" + str(i)
        records.append({"stream_id": identifier, "family": "unit-family-" + str(i % 4),
                        "base_stream": "unit-base-" + str(i // 2),
                        "features": vector, "p8_delta": (i - 12) * 13})
        fresh = (90 + 2*i, 110 + 3*i, 105 + 4*i, 120 + 2*i, 95 + 3*i)
        offsets = (-11, 5, -2, 17, 0)
        timing["streams"].append({"stream_id": identifier, "rounds": [
            {"microseconds": {METHODS[0]: f, METHODS[1]: f + 3*i - 10 + d}}
            for f, d in zip(fresh, offsets)]})
    model = time_model.fit(records, timing)
    assert model["ridge_lambda"] == .01
    # Reconstruct the beta-coordinate weighted normal equations without RMS-normalized design.
    target = []
    for row in timing["streams"]:
        f = median(r["microseconds"][METHODS[0]] for r in row["rounds"])
        d = median(r["microseconds"][METHODS[1]] - r["microseconds"][METHODS[0]] for r in row["rounds"])
        target.append((d, f))
    n, p = len(records), len(features.FEATURES)
    x = [[r["features"][name] for name in features.FEATURES] for r in records]
    mean_square = [sum(row[j] ** 2 / f ** 2 for row, (_, f) in zip(x, target)) / n for j in range(p)]
    penalty_square = [value or 1.0 for value in mean_square]
    gram = [[sum(row[j] * row[k] / f ** 2 for row, (_, f) in zip(x, target)) / n
             + (.01 * penalty_square[j] if j == k else 0) for k in range(p)] for j in range(p)]
    rhs = [sum(row[j] * d / f ** 2 for row, (d, f) in zip(x, target)) / n for j in range(p)]
    beta = cholesky_solve(gram, rhs)
    differences = [abs(model["coefficients_us_per_feature"][name] - value)
                   for name, value in zip(features.FEATURES, beta)]
    assert max(differences) < 1e-9
    for name, value in zip(features.FEATURES, penalty_square):
        j = features.FEATURES.index(name)
        assert math.isclose(model["feature_rms_of_x_over_fresh_us"][j], math.sqrt(value), rel_tol=1e-12)
    pq = median(d / row["features"]["queries"] for row, (d, _) in zip(records, target))
    assert model["per_query_baseline_us"] == pq
    numerator = sum(row["p8_delta"] * d / f ** 2 for row, (d, f) in zip(records, target))
    denominator = sum(row["p8_delta"] ** 2 / f ** 2 for row, (_, f) in zip(records, target))
    assert math.isclose(model["p8_nonnegative_scale_us_per_point"], max(0.0, numerator / denominator), rel_tol=1e-12)

    multiplied = deepcopy(timing)
    for item in multiplied["streams"]:
        for row in item["rounds"]:
            row["microseconds"] = {k: v * 1000 for k, v in row["microseconds"].items()}
    unit_model = time_model.fit(records, multiplied)
    assert all(math.isclose(unit_model["coefficients_us_per_feature"][name],
                            model["coefficients_us_per_feature"][name] * 1000,
                            rel_tol=1e-8, abs_tol=1e-8) for name in features.FEATURES)
    extras = deepcopy(timing)
    extras["streams"].append({"stream_id": "UNUSED_HOLDOUT", "rounds": [
        {"microseconds": {METHODS[0]: 1, METHODS[1]: 10**30}}]})
    assert time_model.fit(records, extras) == model
    predicted = time_model.predict(model, records)
    poisoned = deepcopy(records)
    for row in poisoned:
        row.update(family="POISON", gold="POISON", timing_us=-10**90, future_label="POISON")
    assert time_model.predict(model, poisoned) == predicted
    zero_p8 = deepcopy(records)
    for row in zero_p8:
        row["p8_delta"] = 0
    zero_model = time_model.fit(zero_p8, timing)
    assert zero_model["p8_nonnegative_scale_us_per_point"] == 0
    opposite_p8 = deepcopy(records)
    for row, (delta, _) in zip(opposite_p8, target):
        row["p8_delta"] = -delta
    assert time_model.fit(opposite_p8, timing)["p8_nonnegative_scale_us_per_point"] == 0
    zero_predictions = time_model.predict(zero_model, zero_p8)
    # Explicit decision convention: an exact P8 tie predicts slowdown, not mathematical sign(0).
    assert all(r["raw_p8_sign"] == 1 for r in zero_predictions["predictions"])
    assert all(r["predicted_delta_us"]["zero_change"] == 0 for r in predicted["predictions"])
    folds = time_model.grouped_cv(records, timing)["folds"]
    for fold in folds:
        expected = {r["stream_id"] for r in records if r["family"] == fold["held_out_family"]}
        assert {r["stream_id"] for r in fold["predictions"]} == expected
        assert fold["training_streams"] == len(records) - len(expected)
    return {"synthetic_numeric_records": len(records), "real_timing_samples": 0,
            "paired_target_counterexample": {"median_paired_delta": 2, "difference_of_medians": 10},
            "independent_solver": "Cholesky in beta coordinates",
            "max_coefficient_absolute_difference": max(differences),
            "ridge_includes_stream_constant": True,
            "zero_column_rms_fallback_checked": True,
            "common_time_unit_rescaling_checked": True,
            "unused_timing_and_report_metadata_ignored": True,
            "p8_zero_tie_predicts_slowdown": True,
            "p8_nonnegative_slope_checked": True,
            "leave_family_out_partitions_checked": len(folds)}


def scoring_audit():
    """Logical numeric fixtures, never measured durations or holdout data."""
    from scoring import score, joint

    def observed(identifier, delta, label):
        return {"stream_id": identifier, "family": "numeric-scoring-only", "queries": 1,
                "summary": {"paired_delta_median_us": delta, "fresh_median_us": 100,
                            "material_label": label}}

    def prediction(identifier, ridge, per_query=10, p8=20):
        return {"stream_id": identifier,
                "predicted_delta_us": {"trace_ridge": ridge, "zero_change": 0,
                                       "per_query": per_query, "p8_calibrated": p8},
                "raw_p8_sign": 1, "always_slowdown_sign": 1}

    zero = {"predictions": [prediction("zero", 0, 0, 0)]}
    zero_score = score(zero, {"streams": [observed("zero", 0, "unresolved")]})
    assert zero_score["best_baseline_error"] == 0
    assert zero_score["model_error_divided_by_best_baseline"] is None
    assert not zero_score["numerical_rule_passed"]

    failed = {"predictions": [prediction("failed", 80, 40, 50)]}
    failed_score = score(failed, {"streams": [observed("failed", 10, "unresolved")]})
    failure_joint = joint(failed, failed_score, failed_score)
    assert not failure_joint["sign_question_identifiable_under_rule"]
    assert failure_joint["conclusion"] == "not_supported_numerical_rule"
    assert not failure_joint["H10_supported"]

    predictions = {"predictions": []}
    original, repeated = {"streams": []}, {"streams": []}
    for i in range(10):
        identifier = "common-" + str(i)
        first_label = "speedup" if i < 4 or i == 8 else "slowdown" if i < 9 else "unresolved"
        second_label = "slowdown" if i >= 8 else first_label
        first_delta = -10 if first_label == "speedup" else 10
        second_delta = -10 if second_label == "speedup" else 10
        predictions["predictions"].append(prediction(identifier, first_delta))
        original["streams"].append(observed(identifier, first_delta, first_label))
        repeated["streams"].append(observed(identifier, second_delta, second_label))
    a, b = score(predictions, original), score(predictions, repeated)
    common = joint(predictions, a, b)
    assert a["streams"] == b["streams"] == 10
    assert common["common_resolved_counts"] == {"speedup": 4, "slowdown": 4}
    assert common["common_resolved_streams"] == ["common-" + str(i) for i in range(8)]
    assert set(common["excluded_from_sign_only"]) == {"common-8", "common-9"}
    assert math.isclose(b["mean_normalized_absolute_error"]["trace_ridge"], .02)
    assert common["sign_predictions"]["trace_ridge"]["balanced_accuracy"] == 1
    assert common["best_baseline_balanced_accuracy"] == .5
    assert common["H10_supported"]

    # Exact threshold: 5/6 - 11/15 = 1/10. Rounded float addition can reject it.
    boundary_predictions = {"predictions": []}
    boundary_scores = {"rows": [], "numerical_rule_passed": True}
    for i in range(19):
        identifier = "exact-ba-" + str(i)
        label = "speedup" if i < 4 else "slowdown"
        model_sign = -1 if i < 4 or i >= 14 else 1
        baseline_sign = -1 if i < 4 or i >= 11 else 1
        row = prediction(identifier, model_sign, 1, baseline_sign)
        row["raw_p8_sign"] = baseline_sign
        boundary_predictions["predictions"].append(row)
        boundary_scores["rows"].append({"stream_id": identifier, "material_label": label})
    boundary = joint(boundary_predictions, boundary_scores, boundary_scores)
    assert boundary["common_resolved_counts"] == {"speedup": 4, "slowdown": 15}
    assert boundary["sign_predictions"]["trace_ridge"]["correct_by_class"] == {"speedup": 4, "slowdown": 10}
    assert boundary["sign_predictions"]["raw_p8"]["correct_by_class"] == {"speedup": 4, "slowdown": 7}
    displayed_model = boundary["sign_predictions"]["trace_ridge"]["balanced_accuracy"]
    displayed_best = boundary["best_baseline_balanced_accuracy"]
    assert not (displayed_model >= displayed_best + .10), "Fixture must expose old float rejection"
    assert boundary["sign_rule_passed"] and boundary["H10_supported"]
    return {"real_timing_samples": 0, "zero_error_tie_is_not_25pct_improvement": True,
            "numeric_failure_precedes_unidentified_sign_label": True,
            "common_resolved_excludes_sign_flip_and_unresolved": True,
            "all_10_fixture_streams_retained_in_numeric_error": True,
            "common_resolved_fixture_counts": common["common_resolved_counts"],
            "positive_support_logic_fixture_checked": True,
            "exact_balanced_accuracy_boundary": {
                "class_counts": boundary["common_resolved_counts"],
                "model_correct": {"speedup": 4, "slowdown": 10},
                "best_baseline_correct": {"speedup": 4, "slowdown": 7},
                "exact_model_ba": "5/6", "exact_best_baseline_ba": "11/15", "exact_gap": "1/10",
                "displayed_model_ba": displayed_model, "displayed_best_baseline_ba": displayed_best,
                "old_float_comparison_passes": False, "exact_count_comparison_passes": True}}


def run():
    verify_base()
    streams = known_fixtures()
    result, checked = features.extract(streams)
    assert not checked["failures"]
    by_id = {r["stream_id"]: r for r in result["records"]}
    grouped = defaultdict(lambda: defaultdict(list))
    for row in checked["rows"]:
        grouped[row["stream_id"]][row["method"]].append(row)
    witnesses, mutants = [], []
    for stream, public_stream in zip(streams, prepare(streams)):
        independent, evidence = independent_vector(public_stream)
        record = by_id[stream["id"]]
        assert independent == record["features"], (stream["id"], independent, record["features"])
        witnesses.append({"stream_id": stream["id"], "features": independent, **evidence})
        # Single-coordinate corruption must not be hidden by an aggregate equality.
        for name in features.FEATURES:
            corrupted = dict(record["features"])
            corrupted[name] += 1
            assert corrupted != independent
        rows = grouped[stream["id"]]
        polluted_fresh, polluted_selective = deepcopy(rows["fresh_instrumented"]), deepcopy(rows["selective_instrumented"])
        for row in polluted_fresh + polluted_selective:
            row.update(family="POISON", gold={"future": 10**99}, timing_us=-10**99, stream_id="POISON")
        assert features.vector(public_stream, polluted_fresh, polluted_selective, record["stage_characters"]) == independent
    for name in features.FEATURES:
        mutants.append({"mutant": "feature_coordinate_plus_one:" + name, "detected": True,
                        "checked_streams": len(streams)})

    fit = next(w for w in witnesses if "fit_working_set" in w["stream_id"])
    assert all(p["context_encodes"] == 1 for p in fit["prefixes"])
    fit_rows = grouped[fit["stream_id"]]["selective_instrumented"]
    naive_context = sum(r["cost"]["control_events"].get("context_access", 0) for r in fit_rows)
    assert naive_context > sum(p["context_encodes"] for p in fit["prefixes"])
    mutants.append({"mutant": "context_encode_once_per_access", "detected": True,
                    "actual_encodes": 4, "naive_access_count": naive_context})

    oversized = next(w for w in witnesses if w["stream_id"].endswith("long_deep_repeat-02"))
    oversize_rows = grouped[oversized["stream_id"]]["selective_instrumented"]
    assert sum(r["cost"]["cache_writes"] for r in oversize_rows) == 0
    assert oversized["features"]["admission_attempts"] == 4
    assert oversized["encoding_calls"]["payload"] == 12
    mutants.append({"mutant": "drop_encoding_of_rejected_admissions", "detected": True,
                    "writes": 0, "actual_payload_encodes": 12})

    reused = next(r for r in result["records"] if r["stream_id"].endswith("long_deep_repeat-00"))
    fr = grouped[reused["stream_id"]]["fresh_instrumented"]
    sr = grouped[reused["stream_id"]]["selective_instrumented"]
    saved_bytes = sum(sum(a["audit"][s+"_source_bytes"]-b["audit"][s+"_source_bytes"] for s in STAGES)
                      for a, b in zip(fr, sr))
    assert saved_bytes != reused["features"]["saved_stage_characters"]
    mutants.append({"mutant": "utf8_bytes_substituted_for_unicode_characters", "detected": True,
                    "saved_bytes": saved_bytes, "saved_characters": reused["features"]["saved_stage_characters"]})
    fit_public = prepare([next(s for s in streams if s["id"] == fit["stream_id"])])[0]
    record_occurrences = sum(len(p["records"]) for p, _ in fit_public)
    assert record_occurrences != fit["features"]["records_visited"]
    mutants.append({"mutant": "all_records_substituted_for_actual_visits", "detected": True,
                    "all_records": record_occurrences, "actual_visits": fit["features"]["records_visited"]})
    mutants.extend(replay_mutants(prepare(streams)[0], grouped[streams[0]["id"]]))
    mathematics = model_audit()
    return {"status": "passed", "known_phase09_streams": len(streams), "prefixes": 20,
            "new_holdout_opened": False, "new_timing_sessions": 0,
            "four_path_preservation_failures": len(checked["failures"]),
            "feature_exact_equal_streams": len(witnesses),
            "plain_vs_traced_exact_prefix_comparisons": 40,
            "feature_and_replay_mutants": mutants, "feature_witnesses": witnesses,
            "numeric_model_checks": mathematics, "scoring_logic_checks": scoring_audit(),
            "boundary": "Known-data bounded implementation checks; same-model role separation, not external verification. P8 actions are declared branch counts, not CPU instructions. Synthetic numeric time inputs are not benchmark observations."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    save(args.output, run())
    print("Untimed Phase10 audit passed: 20 known prefixes; no new holdout or timing.")
