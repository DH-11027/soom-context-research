"""Post-freeze data-author artifact review. No runtime/model/scoring imports.

Reads frozen corpus, raw audit rows, frozen feature/prediction records, and saved
timing samples. No selector, fitting, feature extraction, or timing is executed.
All derived claims remain same-model synthetic-artifact audits.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import mean, median

HERE = Path(__file__).resolve().parent
FI, FO, SI, SO = ("fresh_instrumented", "fresh_uninstrumented", "selective_instrumented", "selective_uninstrumented")
METHODS = (FI, FO, SI, SO)
STAGES = ("cheap", "contract", "detail")
MODELS = ("trace_ridge", "zero_change", "per_query", "p8_calibrated")
BIG = {"long_cheap", "long_deep_repeat", "long_deep_churn", "fit_working_set", "pressure_working_set",
       "phase_shift", "same_length_misses", "revisions_copy_context", "integrity_unsupported_recovery"}


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-8), (a, b)


def duplicates(steps):
    return {"steps": len(steps),
        "exact_records": len({canonical(q["public"]["records"]) for q in steps}),
        "ordered_raw_histories": len({canonical([r["text"] for r in q["public"]["records"]]) for q in steps}),
        "raw_plus_ordered_entities": len({canonical([[r["text"] for r in q["public"]["records"]], q["public"]["entities"]]) for q in steps}),
        "public_plus_namespace": len({canonical([q["public"], q["parser_namespace"]]) for q in steps})}


def quantile(sorted_values, fraction):
    where = (len(sorted_values) - 1) * fraction
    left = int(where)
    right = min(left + 1, len(sorted_values) - 1)
    return sorted_values[left] + (where - left) * (sorted_values[right] - sorted_values[left])


def raw_time(rounds, seed, stored):
    """Recompute paired difference, fixed-denominator labels and 2-round blocks."""
    f = median(r["microseconds"][FO] for r in rounds)
    s = median(r["microseconds"][SO] for r in rounds)
    d = [r["microseconds"][SO] - r["microseconds"][FO] for r in rounds]
    paired = median(d)
    blocks = [d[i:i + 2] for i in range(0, len(d), 2)]
    rng = random.Random(seed)
    draws = []
    for _ in range(4000):
        indices = [rng.randrange(len(blocks)) for _ in blocks]
        draws.append(median(v for index in indices for v in blocks[index]))
    draws.sort()
    interval = [quantile(draws, .025), quantile(draws, .975)]
    label = "speedup" if interval[1] < -.03 * f else "slowdown" if interval[0] > .03 * f else "unresolved"
    close(f, stored["fresh_median_us"])
    close(paired, stored["paired_delta_median_us"])
    for a, b in zip(interval, stored["delta_bootstrap_95pct_us"]):
        close(a, b)
    assert label == stored["material_label"]
    return {"fresh_median_us": f, "selective_median_us": s, "paired_delta_us": paired,
        "paired_delta_over_fresh": paired / f, "marginal_median_difference_us": s - f,
        "delta_interval_us": interval, "relative_interval_fixed_fresh": [v / f for v in interval],
        "material_label": label}


def source_cost(rows):
    return {"queries": len(rows), "actual_calls": sum(sum(r["audit"][s + "_calls"] for s in STAGES) for r in rows),
        "parser_source_bytes": sum(sum(r["audit"][s + "_source_bytes"] for s in STAGES) for r in rows),
        "snapshot_bytes": sum(r["audit"]["snapshot_serialized_bytes"] for r in rows),
        "output_bytes": sum(r["output_bytes"] for r in rows),
        "P7": sum(r["cost"]["phase07_work_proxy"] for r in rows),
        "P8": sum(r["cost"]["phase08_work_score"] for r in rows),
        "control_actions": sum(r["cost"]["control_actions"] for r in rows)}


def unicode_counts(raw_counts):
    categories = Counter()
    width = Counter()
    raw_with_supplementary = 0
    for text, repeats in raw_counts.items():
        unique_categories, unique_width = Counter(), Counter()
        for ch in text:
            value = ord(ch)
            category = ("ascii" if value <= 127 else "hangul" if 0xAC00 <= value <= 0xD7A3 or
                        0x1100 <= value <= 0x11FF or 0x3130 <= value <= 0x318F else
                        "supplementary" if value > 0xFFFF else "other_bmp")
            unique_categories[category] += 1
            unique_width[1 if value <= 127 else 2 if value <= 2047 else 3 if value <= 65535 else 4] += 1
        for k, v in unique_categories.items():
            categories[k] += v * repeats
        for k, v in unique_width.items():
            width[k] += v * repeats
        raw_with_supplementary += repeats * bool(unique_categories["supplementary"])
    return {"codepoint_category_occurrences": dict(categories), "utf8_width_occurrences": dict(width),
            "raw_record_occurrences_with_supplementary": raw_with_supplementary,
            "boundary": "Counts repeated raw occurrences; supplementary codepoints here come from authored emoji payloads, not an emoji semantic test."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    paths = {"corpus": HERE / "data/holdout.json.gz", "rows": HERE / "results/holdout_rows.json.gz",
        "states": HERE / "results/holdout_states.json.gz", "profile": HERE / "results/data_profile.json",
        "summary": HERE / "results/holdout_results.json", "features": HERE / "results/holdout_features.json",
        "predictions": HERE / "results/predictions.json", "model": HERE / "calibration/model.json",
        "calibration_features": HERE / "calibration/calibration_features.json",
        "primary_timing": HERE / "results/timing.json", "reproduction_timing": HERE / "reproduction_timing.json",
        "primary_scores": HERE / "results/scores.json", "reproduction_scores": HERE / "reproduction_scores.json"}
    loaded = {k: load(p) for k, p in paths.items()}
    corpus, rows, states = (loaded[k] for k in ("corpus", "rows", "states"))
    steps = {(s["id"], i): q for s in corpus for i, q in enumerate(s["steps"])}
    by_stream = {s["id"]: s for s in corpus}
    assert len(corpus) == 48 and len(steps) == 1176 and len(rows) == 4704 and len(states) == 1176
    grouped = defaultdict(dict)
    for r in rows:
        key = (r["stream_id"], r["step_index"])
        assert r["method"] not in grouped[key]
        grouped[key][r["method"]] = r
        q = steps[key]
        assert r["valid_snapshot"] == (q["expected_integrity"] == "valid")
        assert r["supported"] == q["question_contract"]["supported"]
        assert r["gold_evaluated"] == q["gold_applicable"]
        assert not (r["schema_error"] or r["structural_error"] or r["parity_failures"])
        assert not r["false_certification"] and not r["containment_violation"]
        assert r["selected_gold_projection_equal"] is not False
    obs = ("status", "reason", "prediction", "selected", "output_bytes", "remaining_input_facts", "scope_trace", "rendered_sha256")
    for pair in grouped.values():
        assert set(pair) == set(METHODS)
        reference = {k: pair[FI][k] for k in obs if k in pair[FI]}
        assert all({k: r[k] for k in obs if k in r} == reference for r in pair.values())
        for on, off in ((FI, FO), (SI, SO)):
            for k in ("audit", "audit_trace_sha256", "policy_trace_sha256", "policy_retained_bytes", "policy_entries"):
                assert pair[on][k] == pair[off][k]
    for witness in states:
        assert witness["exact_policy_state_equal"] and witness["exact_policy_trace_equal"]
        state = witness["instrumented_state"]
        assert len(state["entries"]) <= 64
        assert state["retained_bytes"] == sum(e[2] for e in state["entries"]) <= 65536
        assert sorted(Counter(e[3] for e in state["entries"]).items()) == [tuple(v) for v in state["lengths"]]
    counts, costs = {}, {}
    for m in METHODS:
        rr = [r for r in rows if r["method"] == m]
        counts[m] = {"status_counts": dict(Counter(r["status"] for r in rr)),
            "valid_supported": sum(r["valid_snapshot"] and r["supported"] for r in rr),
            "gold_evaluated": sum(r["gold_evaluated"] for r in rr),
            "certified_gold_evaluated": sum(r["gold_evaluated"] and r["status"] == "certified_model" for r in rr),
            "containment_evaluated": sum(r["containment_violation"] is not None for r in rr),
            "gold_projection_evaluated": sum(r["selected_gold_projection_equal"] is not None for r in rr),
            "actual_full_history": sum(r["actual_full_history"] for r in rr),
            "output_bytes": sum(r["output_bytes"] for r in rr)}
        for k, v in counts[m].items():
            assert loaded["summary"]["summary"][m][k] == v
        if m in (FI, SI):
            costs[m] = source_cost(rr)
    valid = [q for q in steps.values() if q["expected_integrity"] == "valid"]
    gold = [q for q in steps.values() if q["gold_applicable"]]
    dup = {"all": duplicates(list(steps.values())), "valid": duplicates(valid),
           "gold_exact_typed_arrays": len({canonical(q["gold"]) for q in gold})}
    assert dup["all"] == loaded["profile"]["all"] and dup["valid"] == loaded["profile"]["valid"]
    assert dup["gold_exact_typed_arrays"] == loaded["profile"]["distinct_exact_typed_events"]
    raw_counts = Counter(r["text"] for q in steps.values() for r in q["public"]["records"])
    unicode = unicode_counts(raw_counts)
    lengths = [len(t.encode()) for t in raw_counts]
    distribution = {"record_occurrences": sum(raw_counts.values()), "unique_raw_strings": len(raw_counts),
        "record_bytes_min_max": [min(lengths), max(lengths)],
        "record_characters_min_max": [min(map(len, raw_counts)), max(map(len, raw_counts))],
        "record_characters_threshold_occurrences": {
            "below_256": sum(n for t, n in raw_counts.items() if len(t) < 256),
            "at_least_256": sum(n for t, n in raw_counts.items() if len(t) >= 256)},
        "record_byte_band_occurrences": dict(Counter({label: sum(n for t, n in raw_counts.items()
            if lower <= len(t.encode()) < upper) for label, lower, upper in
            (("below_850", 0, 850), ("850_to_2100", 850, 2101), ("2101_to_6999", 2101, 7000),
             ("7000_to_19000", 7000, 19001), ("19001_to_47999", 19001, 48000),
             ("48000_to_63000", 48000, 63001), ("63001_to_67999", 63001, 68000),
             ("68000_and_above", 68000, 10 ** 30))})),
        "raw_bytes_sum_over_steps": sum(len(t.encode()) * n for t, n in raw_counts.items()),
        "unicode": unicode, "streams": {}}
    for s in corpus:
        sid = s["id"]
        qraw = [r["text"] for q in s["steps"] for r in q["public"]["records"]]
        longs = {r["text"] for q in s["steps"] for r, e in zip(q["public"]["records"], q["gold"])
                 if e["kind"] == "noop" and len(r["text"]) >= 256}
        simultaneous = max(sum(len(r["text"].encode()) for r, e in zip(q["public"]["records"], q["gold"])
            if e["kind"] == "noop" and len(r["text"]) >= 256) for q in s["steps"])
        distribution["streams"][sid] = {"family": s["family"], "queries": len(s["steps"]),
            "author_design": s["author_design"], "max_record_bytes": max(len(t.encode()) for t in qraw),
            "raw_bytes_occurrences": sum(len(t.encode()) for t in qraw), "long_noop_unique_raws": len(longs),
            "long_noop_unique_raw_pool_bytes": sum(len(t.encode()) for t in longs),
            "simultaneous_long_noop_raw_bytes_max": simultaneous,
            "individually_oversize_raw_occurrences": sum(len(t.encode()) > 65536 for t in qraw),
            "records_with_supplementary": sum(any(ord(c) > 65535 for c in t) for t in qraw)}
        working_set = s["author_design"]["working_set"]
        if working_set:
            assert simultaneous == working_set["simultaneous_quote_raw_bytes"]
            if s["family"] in {"fit_working_set", "pressure_working_set"}:
                assert len(longs) == working_set["quote_pool_count"]
                assert sum(len(t.encode()) for t in longs) == working_set["simultaneous_quote_raw_bytes"]
    feats = {r["stream_id"]: r for r in loaded["features"]["records"]}
    preds = {r["stream_id"]: r for r in loaded["predictions"]["predictions"]}
    model = loaded["model"]
    training = loaded["calibration_features"]["records"]
    assert set(feats) == set(preds) == set(by_stream)
    bounds, outside = {}, defaultdict(list)
    for name in model["feature_order"]:
        train_min = min(r["features"][name] for r in training)
        train_max = max(r["features"][name] for r in training)
        assert {"min": train_min, "max": train_max} == model["training_feature_bounds"][name]
        lower = [sid for sid, r in feats.items() if r["features"][name] < train_min]
        upper = [sid for sid, r in feats.items() if r["features"][name] > train_max]
        bounds[name] = {"training_min": train_min, "training_max": train_max,
                       "holdout_min": min(r["features"][name] for r in feats.values()),
                       "holdout_max": max(r["features"][name] for r in feats.values()),
                       "below": lower, "above": upper}
        for sid in lower + upper:
            outside[sid].append(name)
    stream_costs, cold_costs = {}, {m: source_cost([r for r in rows if r["method"] == m and r["step_index"] == 0]) for m in (FI, SI)}
    for sid in by_stream:
        stream_costs[sid] = {m: source_cost([r for r in rows if r["method"] == m and r["stream_id"] == sid]) for m in (FI, SI)}
        phi = feats[sid]["features"]
        fresh, sel = stream_costs[sid][FI], stream_costs[sid][SI]
        assert phi["queries"] == len(by_stream[sid]["steps"])
        assert phi["saved_stage_calls"] == fresh["actual_calls"] - sel["actual_calls"]
        assert feats[sid]["p8_delta"] == sel["P8"] - fresh["P8"]
        predicted = sum(model["coefficients_us_per_feature"][name] * phi[name] for name in model["feature_order"])
        close(predicted, preds[sid]["predicted_delta_us"]["trace_ridge"])
    sessions = {}
    for session in ("primary", "reproduction"):
        time, score = loaded[session + "_timing"], loaded[session + "_scores"]
        target = {}
        for i, row in enumerate(time["streams"]):
            sid = row["stream_id"]
            target[sid] = raw_time(row["rounds"], time["seed"] + i + 1, row["summary"])
            t = target[sid]
            t.update(family=row["family"], queries=row["queries"], outside_training_axes=outside[sid],
                     predicted_delta_us=preds[sid]["predicted_delta_us"], p8_delta=feats[sid]["p8_delta"])
            t["errors"] = {m: abs(t["predicted_delta_us"][m] - t["paired_delta_us"]) / t["fresh_median_us"] for m in MODELS}
        errors = {m: mean(t["errors"][m] for t in target.values()) for m in MODELS}
        for m, e in errors.items():
            close(e, score["mean_normalized_absolute_error"][m])
        families, horizons = {}, {}
        for groups, key in ((families, "family"), (horizons, "queries")):
            for value in sorted({t[key] for t in target.values()}):
                chosen = [sid for sid, t in target.items() if t[key] == value]
                table = {"streams": len(chosen), "queries": sum(target[sid]["queries"] for sid in chosen),
                    "fresh_stream_medians_sum_us": sum(target[sid]["fresh_median_us"] for sid in chosen),
                    "selective_stream_medians_sum_us": sum(target[sid]["selective_median_us"] for sid in chosen),
                    "paired_delta_stream_medians_sum_us": sum(target[sid]["paired_delta_us"] for sid in chosen),
                    "mean_normalized_trace_error": mean(target[sid]["errors"]["trace_ridge"] for sid in chosen),
                    "cost": {m: {k: sum(stream_costs[sid][m][k] for sid in chosen) for k in costs[m]} for m in (FI, SI)}}
                groups[str(value)] = table
        fresh_sum = sum(t["fresh_median_us"] for t in target.values())
        whole = time["whole_workload"]
        whole_recount = raw_time(whole["rounds"], time["seed"] + 10000, whole["summary"])
        top = sorted(target, key=lambda sid: target[sid]["errors"]["trace_ridge"], reverse=True)[:8]
        sessions[session] = {"mean_normalized_errors": errors,
            "material_labels": dict(Counter(t["material_label"] for t in target.values())),
            "point_delta_signs": dict(Counter("gain" if t["paired_delta_us"] < 0 else
                "loss" if t["paired_delta_us"] > 0 else "equal" for t in target.values())),
            "p8_gain_material_labels": dict(Counter(t["material_label"] for t in target.values() if t["p8_delta"] < 0)),
            "negative_point_streams": [sid for sid, t in target.items() if t["paired_delta_us"] < 0],
            "fresh_stream_medians_sum_us": fresh_sum,
            "selective_stream_medians_sum_us": sum(t["selective_median_us"] for t in target.values()),
            "big_family_fresh_time_share": sum(t["fresh_median_us"] for t in target.values() if t["family"] in BIG) / fresh_sum,
            "horizon64_fresh_time_share": sum(t["fresh_median_us"] for t in target.values() if t["queries"] == 64) / fresh_sum,
            "out_of_axis_bounds_mean_error": mean(t["errors"]["trace_ridge"] for sid, t in target.items() if outside[sid]),
            "within_axis_bounds_mean_error": mean(t["errors"]["trace_ridge"] for sid, t in target.items() if not outside[sid]),
            "families": families, "horizons": horizons, "whole_direct_timing": whole_recount,
            "worst_error_streams": [{"stream_id": sid, **target[sid]} for sid in top], "all_streams": target}
    step_deltas = [pair[SI]["cost"]["phase08_work_score"] - pair[FI]["cost"]["phase08_work_score"] for pair in grouped.values()]
    stream_deltas = {sid: c[SI]["P8"] - c[FI]["P8"] for sid, c in stream_costs.items()}
    common = {label: [sid for sid in by_stream if all(sessions[k]["all_streams"][sid]["material_label"] == label for k in sessions)]
              for label in ("speedup", "slowdown")}
    output = {"passed": True, "denominators": counts, "duplicates": dup, "distribution": distribution,
        "policy_state_witness_maxima": {"retained_bytes": max(s["instrumented_state"]["retained_bytes"] for s in states),
            "entries": max(len(s["instrumented_state"]["entries"]) for s in states)},
        "total_cost": costs, "cold_first_step_cost": cold_costs,
        "p8_step_sign_counts": dict(Counter("gain" if v < 0 else "loss" if v > 0 else "equal" for v in step_deltas)),
        "p8_stream_sign_counts": dict(Counter("gain" if v < 0 else "loss" if v > 0 else "equal" for v in stream_deltas.values())),
        "p8_gain_streams": [sid for sid, v in stream_deltas.items() if v < 0],
        "feature_bounds": bounds, "outside_training_axes": {sid: names for sid, names in outside.items() if names},
        "axis_bounds_note": "Raw-coordinate training min/max only; inside a bounding box does not prove joint-distribution coverage or lack of extrapolation.",
        "sessions": sessions, "common_material_streams": common,
        "big_family_fresh_P8_share": sum(c[FI]["P8"] for sid, c in stream_costs.items() if by_stream[sid]["family"] in BIG) / costs[FI]["P8"],
        "big_family_fresh_parser_bytes_share": sum(c[FI]["parser_source_bytes"] for sid, c in stream_costs.items() if by_stream[sid]["family"] in BIG) / costs[FI]["parser_source_bytes"],
        "source_sha256": {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()},
        "boundary": "Post-freeze same-model data-author audit. No new selector execution or timing; stream-time shares sum separately measured stream medians and do not decompose direct whole-workload timing."}
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": True, "rows": len(rows), "prefixes": len(states),
        "out_of_bounds_streams": len(output["outside_training_axes"]),
        "p8_step_sign_counts": output["p8_step_sign_counts"], "p8_stream_sign_counts": output["p8_stream_sign_counts"],
        "primary_labels": sessions["primary"]["material_labels"], "reproduction_labels": sessions["reproduction"]["material_labels"],
        "common_material_counts": {k: len(v) for k, v in common.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
