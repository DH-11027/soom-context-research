"""Fixed normalized ridge delta-time predictor and predeclared baselines.

Training reference elapsed times enter WLS scaling, never holdout prediction.
Coefficients are predictive parameters, not causally identified CPU prices.
"""
import math
from statistics import median
from features import FEATURES

RIDGE = .01

def solve(matrix, target):
    a = [list(row) + [b] for row, b in zip(matrix, target)]
    n = len(a)
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(a[row][column]))
        assert abs(a[pivot][column]) > 1e-15, "Unexpected singular regularized system"
        a[column], a[pivot] = a[pivot], a[column]
        div = a[column][column]
        a[column] = [x / div for x in a[column]]
        for row in range(n):
            if row == column:
                continue
            multiplier = a[row][column]
            a[row] = [x - multiplier * y for x, y in zip(a[row], a[column])]
    return [row[-1] for row in a]

def target(record):
    rows = record["rounds"]
    fresh = median(row["microseconds"]["fresh_uninstrumented"] for row in rows)
    delta = median(row["microseconds"]["selective_uninstrumented"] - row["microseconds"]["fresh_uninstrumented"] for row in rows)
    return delta, fresh

def fit(records, timing):
    targets = {item["stream_id"]: target(item) for item in timing["streams"]}
    n, p = len(records), len(FEATURES)
    data = [(row, *targets[row["stream_id"]]) for row in records]
    normalized = [[row["features"][name] / fresh for name in FEATURES] for row, delta, fresh in data]
    scales = [math.sqrt(sum(row[j] ** 2 for row in normalized) / n) or 1.0 for j in range(p)]
    z = [[row[j] / scales[j] for j in range(p)] for row in normalized]
    y = [delta / fresh for row, delta, fresh in data]
    gram = [[sum(row[j] * row[k] for row in z) / n + (RIDGE if j == k else 0) for k in range(p)] for j in range(p)]
    rhs = [sum(row[j] * value for row, value in zip(z, y)) / n for j in range(p)]
    theta = solve(gram, rhs)
    beta = [theta[j] / scales[j] for j in range(p)]
    p8x = [row["p8_delta"] / fresh for row, delta, fresh in data]
    denominator = sum(x*x for x in p8x)
    p8scale = max(0.0, sum(x*v for x, v in zip(p8x, y)) / denominator) if denominator else 0.0
    residual = max(abs(sum(gram[j][k] * theta[k] for k in range(p)) - rhs[j]) for j in range(p))
    return {"feature_order": list(FEATURES), "ridge_lambda": RIDGE,
            "training_streams": n, "training_base_streams": len({r["base_stream"] for r in records}),
            "feature_rms_of_x_over_fresh_us": scales, "theta": theta,
            "coefficients_us_per_feature": dict(zip(FEATURES, beta)),
            "training_feature_bounds": {name:{"min":min(r["features"][name] for r in records),"max":max(r["features"][name] for r in records)} for name in FEATURES},
            "normal_equation_residual": residual,
            "per_query_baseline_us": median(delta / row["features"]["queries"] for row, delta, fresh in data),
            "p8_nonnegative_scale_us_per_point": p8scale,
            "target": "median paired (selective_us-fresh_us), training loss normalized by marginal median fresh_us",
            "boundary": "Predictive coefficients; no causal CPU unit-cost interpretation. No holdout timing or labels enter fit."}

def predict(model, records):
    assert model["feature_order"] == list(FEATURES)
    out = []
    for row in records:
        x = row["features"]
        assert tuple(x) == FEATURES
        values = {"trace_ridge": sum(model["coefficients_us_per_feature"][name] * x[name] for name in FEATURES),
                  "zero_change": 0.0,
                  "per_query": model["per_query_baseline_us"] * x["queries"],
                  "p8_calibrated": model["p8_nonnegative_scale_us_per_point"] * row["p8_delta"]}
        assert all(math.isfinite(x) for x in values.values())
        out.append({"stream_id": row["stream_id"], "predicted_delta_us": values,
                    "raw_p8_sign": -1 if row["p8_delta"] < 0 else 1,  # decision convention: exact zero -> slowdown
                    "always_slowdown_sign": 1})
    return {"predictions": out, "boundary": "All predictions computed from frozen coefficients and untimed whole-stream features before primary holdout timing; no online gate implemented."}

def grouped_cv(records, timing):
    outputs = []
    for family in sorted({r["family"] for r in records}):
        training = [r for r in records if r["family"] != family]
        held = [r for r in records if r["family"] == family]
        model = fit(training, timing)
        outputs.append({"held_out_family": family, "training_streams": len(training),
                        "coefficients_us_per_feature":model["coefficients_us_per_feature"], **predict(model, held)})
    return {"folds": outputs, "selection_performed": False,
            "boundary": "Prespecified leave-family-out development diagnostic only; no lambda/features/threshold selection from CV."}

