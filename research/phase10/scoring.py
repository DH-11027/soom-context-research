"""Frozen hypothesis rules; all 48 streams retained in primary prediction error."""
from statistics import mean
from fractions import Fraction

MODELS = ("trace_ridge", "zero_change", "per_query", "p8_calibrated")

def score(predictions,timing):
    p = {row["stream_id"]:row for row in predictions["predictions"]}
    assert len(p) == len(predictions["predictions"]) == len(timing["streams"])
    assert set(p) == {row["stream_id"] for row in timing["streams"]}
    rows = []
    for observed in timing["streams"]:
        sid = observed["stream_id"]
        summary = observed["summary"]
        delta, fresh = summary["paired_delta_median_us"],summary["fresh_median_us"]
        values = p[sid]["predicted_delta_us"]
        rows.append({"stream_id":sid,"family":observed["family"],"queries":observed["queries"],
                     "delta_us":delta,"fresh_us":fresh,"material_label":summary["material_label"],
                     "predicted_delta_us":values,"normalized_absolute_error":{m:abs(values[m]-delta)/fresh for m in MODELS}})
    errors = {m:mean(row["normalized_absolute_error"][m] for row in rows) for m in MODELS}
    baseline = min(errors[m] for m in MODELS if m != "trace_ridge")
    # A zero-error baseline cannot be improved by 25%; a 0/0 tie is not success.
    passed = baseline > 0 and errors["trace_ridge"] <= .10 and errors["trace_ridge"] <= .75*baseline
    families = {family:{m:mean(row["normalized_absolute_error"][m] for row in rows if row["family"]==family) for m in MODELS}
                for family in sorted({row["family"] for row in rows})}
    horizons = {str(n):{m:mean(row["normalized_absolute_error"][m] for row in rows if row["queries"]==n) for m in MODELS}
                for n in sorted({row["queries"] for row in rows})}
    return {"streams":len(rows),"mean_normalized_absolute_error":errors,
            "best_baseline_error":baseline,"model_error_divided_by_best_baseline":errors["trace_ridge"]/baseline if baseline else None,
            "numerical_rule_passed":passed,"family_errors":families,"horizon_errors":horizons,"rows":rows,
            "boundary":"Each stream has equal weight. Denominator is observed marginal median fresh elapsed time; not a conversation-population estimate."}

def joint(predictions,primary,reproduction):
    p = {r["stream_id"]:r for r in predictions["predictions"]}
    a = {r["stream_id"]:r for r in primary["rows"]}
    b = {r["stream_id"]:r for r in reproduction["rows"]}
    assert set(a)==set(b)==set(p)
    common = [sid for sid in a if a[sid]["material_label"]==b[sid]["material_label"] and a[sid]["material_label"]!="unresolved"]
    counts = {label:sum(a[sid]["material_label"]==label for sid in common) for label in ("speedup","slowdown")}
    sign_models = ("trace_ridge","per_query","p8_calibrated","raw_p8","always_slowdown")
    signs, exact_balanced = {}, {}
    for model in sign_models:
        correct = {label:0 for label in counts}
        mistakes = []
        for sid in common:
            sign = p[sid]["raw_p8_sign"] if model=="raw_p8" else 1 if model=="always_slowdown" else (-1 if p[sid]["predicted_delta_us"][model]<0 else 1)
            predicted = "speedup" if sign<0 else "slowdown"
            actual = a[sid]["material_label"]
            correct[actual] += predicted==actual
            if predicted!=actual: mistakes.append(sid)
        balanced = mean(correct[k]/counts[k] for k in counts) if all(counts.values()) else None
        exact_balanced[model] = sum((Fraction(correct[k],counts[k]) for k in counts),Fraction(0))/2 if all(counts.values()) else None
        signs[model] = {"correct_by_class":correct,"balanced_accuracy":balanced,"mistake_streams":mistakes}
    identifiable = min(counts.values()) >= 4
    best = max(signs[m]["balanced_accuracy"] for m in sign_models if m!="trace_ridge") if all(counts.values()) else None
    best_exact = max(exact_balanced[m] for m in sign_models if m!="trace_ridge") if all(counts.values()) else None
    sign_pass = identifiable and exact_balanced["trace_ridge"] >= Fraction(3,4) and exact_balanced["trace_ridge"] >= best_exact+Fraction(1,10)
    numerical = primary["numerical_rule_passed"] and reproduction["numerical_rule_passed"]
    supported = numerical and sign_pass
    return {"H10_supported":supported,"numerical_rule_both_sessions":primary["numerical_rule_passed"] and reproduction["numerical_rule_passed"],
            "common_resolved_streams":common,"common_resolved_counts":counts,
            "excluded_from_sign_only":{sid:[a[sid]["material_label"],b[sid]["material_label"]] for sid in a if sid not in common},
            "sign_question_identifiable_under_rule":identifiable,"sign_rule_passed":bool(sign_pass),
            "sign_predictions":signs,"best_baseline_balanced_accuracy":best,
            "sign_threshold_arithmetic":"Exact integer-ratio Fractions; floating values are display only.",
            "conclusion":"supported_on_fixed_holdout" if supported else "not_supported_numerical_rule" if not numerical else "not_supported_sign_rule" if identifiable else "not_established_sign_classes_insufficient",
            "boundary":"Sign subset selected by two measurement sessions; individual CIs not simultaneous. All streams remain in numerical error. No online-policy or causal-cost claim."}

