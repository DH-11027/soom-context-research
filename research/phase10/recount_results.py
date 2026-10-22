"""Phase10 independent post-freeze raw recount; imports no research implementation.

Only Python's standard library is used. This is a deterministic raw-artifact
audit, not a new benchmark. It does not rerun the policy, parser, or timing.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import median, mean
from fractions import Fraction

HERE = Path(__file__).resolve().parent
METHODS = ("fresh_instrumented", "fresh_uninstrumented", "selective_instrumented", "selective_uninstrumented")
PAIRS = (("fresh_instrumented", "fresh_uninstrumented"),
         ("selective_instrumented", "selective_uninstrumented"))
OBS = ("status", "reason", "prediction", "selected", "output_bytes", "remaining_input_facts", "scope_trace", "rendered_sha256")
STATE_COST = {"cache_retained_bytes", "cache_entries", "cache_peak_bytes", "cache_peak_entries", "directory_entries"}
OFF = ("fresh_uninstrumented", "selective_uninstrumented")
MODELS = ("trace_ridge", "zero_change", "per_query", "p8_calibrated")
FEATURES = ("stream_constant", "queries", "records_visited", "raw_encode_bytes",
            "saved_stage_calls", "saved_stage_characters", "exact_probe_bytes",
            "encoded_context_payload_bytes", "admission_attempts", "policy_control_actions")
DETERMINISTIC = ("audit.json", "model_refit.json", "holdout_features.json", "predictions.json",
                 "holdout_results.json", "holdout_rows.json.gz", "holdout_states.json.gz", "data_profile.json")


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(x) for x in value]
    if isinstance(value, (set, frozenset)):
        return [plain(x) for x in sorted(value, key=repr)]
    return value


def encoded(value):
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def unexact(value):
    """Decode the stored type-tagged policy stage representation."""
    kind, body = value
    if kind == "mapping":
        return {unexact(k): unexact(v) for k, v in body}
    if kind == "tuple":
        return tuple(unexact(x) for x in body)
    if kind == "list":
        return [unexact(x) for x in body]
    if kind == "frozenset":
        return frozenset(unexact(x) for x in body)
    if kind == "set":
        return set(unexact(x) for x in body)
    if kind == "bytes":
        return bytes.fromhex(body["exact_bytes_hex"])
    assert kind in ("str", "int", "bool", "NoneType", "float"), kind
    return body


def check_state(state):
    assert state["max_entries"] == 64 and state["max_bytes"] == 65536 and state["directory"] is True
    entries = state["entries"]
    assert len(entries) <= 64
    keys, sizes, lengths = [], [], []
    for entry in entries:
        key, stages, size, characters, surplus, hits, order = entry
        context, raw = (bytes.fromhex(x["exact_bytes_hex"]) for x in key)
        keys.append((context, raw))
        decoded = unexact(stages)
        assert tuple(decoded) == ("cheap", "contract", "detail")
        assert decoded["cheap"][0]["kind"] == "havoc"
        assert decoded["contract"][0][0] is None
        payload = sum(slot[1] for slot in decoded.values())
        assert all(len(encoded(value)) == length for value, length in decoded.values())
        assert size == len(context) + len(raw) + payload + 80
        assert surplus == len(raw) - len(context) - payload - 64 and surplus > 0
        assert len(raw.decode("utf-8")) == characters
        assert 0 <= hits <= 255 and 0 <= order < state["next_order"]
        sizes.append(size)
        lengths.append(characters)
    assert len(set(keys)) == len(keys)
    assert [x[-1] for x in entries] == sorted(x[-1] for x in entries)
    assert sum(sizes) == state["retained_bytes"] <= 65536
    assert sorted(Counter(lengths).items()) == [tuple(x) for x in state["lengths"]]


def recount_dataset(directory, label):
    rows_path = directory / f"{label}_rows.json.gz"
    states_path = directory / f"{label}_states.json.gz"
    summary_path = directory / f"{label}_results.json"
    rows, states, stored = load(rows_path), load(states_path), load(summary_path)
    pairs = {}
    for r in rows:
        key = (r["stream_id"], r["step_index"])
        assert r["method"] not in pairs.setdefault(key, {}), ("duplicate row", key)
        pairs[key][r["method"]] = r
        assert not r["parity_failures"] and not r["structural_error"] and not r["schema_error"]
        assert not r["false_certification"] and not r["containment_violation"]
        assert r["selected_gold_projection_equal"] is not False
        is_on = r["method"] in ("fresh_instrumented", "selective_instrumented")
        assert ("cost" in r) == is_on
        if is_on:
            cost, audit = r["cost"], r["audit"]
            for stage in ("cheap", "contract", "detail"):
                assert cost[stage + "_calls"] == audit[stage + "_calls"]
                assert cost[stage + "_source_bytes"] == audit[stage + "_source_bytes"]
                assert cost[stage + "_requests"] == cost[stage + "_calls"] + cost[stage + "_reused"]
            assert cost["hash_calls"] == audit["snapshot_calls"]
            assert cost["hash_serialized_bytes"] == audit["snapshot_serialized_bytes"]
            assert cost["control_actions"] == sum(cost["control_events"].values())
            byte_fields = ("key_build_bytes", "key_probe_bytes", "value_encode_bytes", "cache_read_payload_bytes", "cache_write_bytes")
            assert cost["cache_overhead_bytes"] == sum(cost[k] for k in byte_fields)
            assert cost["phase07_work_proxy"] == cost["output_plus_source_work_proxy"] + cost["cache_overhead_bytes"]
            assert cost["phase08_work_score"] == cost["phase07_work_proxy"] + 8 * cost["control_actions"]
            if r["method"] == "selective_instrumented":
                assert cost["cache_lookups"] == audit["policy_get_calls"]
                assert cost["admission_attempts"] == audit["policy_admit_calls"]
                assert cost["cache_writes"] == audit["policy_insertions"]
                assert cost["cache_evictions"] == audit["policy_evictions"]
        assert r["output_bytes"] == r["audit"]["rendered_bytes"]
        if not r["valid_snapshot"] or not r["supported"]:
            assert not any(r["audit"][k] for k in ("cheap_calls", "contract_calls", "detail_calls", "policy_possible_calls", "policy_get_calls", "policy_admit_calls"))
    for key, pair in pairs.items():
        assert set(pair) == set(METHODS), key
        reference = pair[METHODS[0]]
        for row in pair.values():
            # Distinguish absence from a present field with None.
            assert {k: row[k] for k in OBS if k in row} == {k: reference[k] for k in OBS if k in reference}
        for on, off in PAIRS:
            for field in ("audit", "audit_trace_sha256", "audit_trace_events", "policy_trace_sha256", "policy_trace_events", "policy_retained_bytes", "policy_entries"):
                assert pair[on][field] == pair[off][field], (key, field)
    assert len(pairs) == stored["prefixes"] == len(states)
    state_keys = [(s["stream_id"], s["step_index"]) for s in states]
    assert len(set(state_keys)) == len(states) and set(state_keys) == set(pairs)
    assert len(rows) == 4 * len(pairs)
    assert stored["exact_observation_comparisons"] == 3 * len(pairs)
    assert stored["exact_on_off_execution_trace_comparisons"] == 2 * len(pairs)
    assert not stored["failures"] and not stored["exact_policy_state_mismatches"] and not stored["exact_policy_trace_mismatches"]
    previous = {}
    for row in states:
        key = (row["stream_id"], row["step_index"])
        assert row["exact_policy_state_equal"] and row["exact_policy_trace_equal"]
        assert "uninstrumented_state" not in row
        state = row["instrumented_state"]
        check_state(state)
        record = pairs[key]["selective_uninstrumented"]
        assert record["policy_retained_bytes"] == state["retained_bytes"]
        assert record["policy_entries"] == len(state["entries"])
        if row["stream_id"] in previous and (not record["valid_snapshot"] or not record["supported"]):
            assert state == previous[row["stream_id"]], key
        previous[row["stream_id"]] = state
    summaries = {}
    for method in METHODS:
        rr = [r for r in rows if r["method"] == method]
        gold = [r for r in rr if r["gold_evaluated"]]
        cert = [r for r in gold if r["status"] == "certified_model"]
        costs = [r["cost"] for r in rr if "cost" in r]
        cost_keys = {k for c in costs for k, v in c.items() if type(v) is int and k not in STATE_COST}
        fresh = {
            "queries": len(rr), "streams": len({r["stream_id"] for r in rr}),
            "status_counts": dict(Counter(r["status"] for r in rr)),
            "valid_snapshots": sum(r["valid_snapshot"] for r in rr),
            "valid_supported": sum(r["valid_snapshot"] and r["supported"] for r in rr),
            "gold_evaluated": len(gold), "gold_excluded": len(rr) - len(gold),
            "gold_exclusion_reasons": dict(Counter(r["gold_exclusion_reason"] for r in rr if not r["gold_evaluated"])),
            "certified_gold_evaluated": len(cert),
            "false_certifications": sum(r["false_certification"] for r in cert),
            "containment_evaluated": sum(r["containment_violation"] is not None for r in gold),
            "containment_violations": sum(r["containment_violation"] is True for r in gold),
            "gold_projection_evaluated": sum(r["selected_gold_projection_equal"] is not None for r in gold),
            "gold_projection_failures": sum(r["selected_gold_projection_equal"] is False for r in gold),
            "structural_errors": sum(r["structural_error"] or r["schema_error"] for r in rr),
            "parity_failure_rows": sum(bool(r["parity_failures"]) for r in rr),
            "actual_full_history": sum(r["actual_full_history"] for r in rr),
            "output_bytes": sum(r["output_bytes"] for r in rr),
            "max_retained_bytes_at_step_end": max((r["policy_retained_bytes"] for r in rr), default=0),
            "max_entries_at_step_end": max((r["policy_entries"] for r in rr), default=0),
            "instrumented_peak_retained_bytes": max((c["cache_peak_bytes"] for c in costs), default=None),
            "instrumented_peak_entries": max((c["cache_peak_entries"] for c in costs), default=None),
            "separate_audit_actual_work": {k: sum(r["audit"][k] for r in rr) for k in rr[0]["audit"]},
            "instrumented_cost": ({k: sum(c.get(k, 0) for c in costs) for k in sorted(cost_keys)} if costs else None),
            "instrumented_control_events": (dict(sum((Counter(c.get("control_events", {})) for c in costs), Counter())) if costs else None),
        }
        for field, value in fresh.items():
            assert value == stored["summary"][method][field], (method, field)
        summaries[method] = fresh
    return {"rows": len(rows), "prefixes": len(pairs), "summary": summaries,
            "state_records_checked": len(states), "mismatches": 0,
            "source_sha256": {p.name: sha(p) for p in (rows_path, states_path, summary_path)},
            "boundary": "Raw persisted trace hashes rechecked here; exact traces and two live policy states were compared in the separate execution audit, not reconstructed from a lone digest."}


def assert_close(a, b, path=""):
    """Fixed recount tolerance, not a frozen hypothesis threshold."""
    if isinstance(a, dict):
        assert set(a) <= set(b), (path, set(a) - set(b))
        for key, value in a.items():
            assert_close(value, b[key], path + "/" + str(key))
    elif isinstance(a, (tuple, list)):
        assert len(a) == len(b), path
        for i, (left, right) in enumerate(zip(a, b)):
            assert_close(left, right, path + "/" + str(i))
    elif type(a) is float:
        assert math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-9), (path, a, b)
    else:
        assert a == b, (path, a, b)


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    left = math.floor(position)
    weight = position - left
    right = min(left + 1, len(ordered) - 1)
    # Weighted endpoints, independently of worker's difference interpolation.
    return ordered[left] * (1 - weight) + ordered[right] * weight


def timing_summary(rounds, seed):
    differences = []
    for i, row in enumerate(rounds):
        assert row["round"] == i and set(row["order"]) == set(OFF)
        assert all(math.isfinite(row["microseconds"][m]) and row["microseconds"][m] > 0 for m in OFF)
        differences.append(row["microseconds"][OFF[1]] - row["microseconds"][OFF[0]])
    assert len(rounds) % 2 == 0
    for i in range(0, len(rounds), 2):
        assert rounds[i]["order"] == list(reversed(rounds[i + 1]["order"]))
    blocks = [differences[i:i+2] for i in range(0, len(differences), 2)]
    rng = random.Random(seed)
    samples = []
    for _ in range(4000):
        selected = []
        for _ in range(len(blocks)):
            selected.extend(blocks[rng.randrange(len(blocks))])
        samples.append(median(selected))
    fresh = median(row["microseconds"][OFF[0]] for row in rounds)
    delta = median(differences)
    low, high = quantile(samples, .025), quantile(samples, .975)
    label = "speedup" if high / fresh < -.03 else "slowdown" if low / fresh > .03 else "unresolved"
    return {"fresh_median_us": fresh, "paired_delta_median_us": delta,
            "delta_over_fresh_median": delta/fresh,
            "delta_bootstrap_95pct_us": [low, high],
            "delta_interval_divided_by_fixed_fresh_median": [low/fresh, high/fresh],
            "material_label": label,
            "methods": {m: {"median_us": median(v := [r["microseconds"][m] for r in rounds]),
                             "min_us": min(v), "max_us": max(v),
                             "q25_us": quantile(v, .25), "q75_us": quantile(v, .75)} for m in OFF}}


def recount_timing(path):
    saved = load(path)
    session = saved["session"]
    seed = {"primary": 20261022101, "reproduction": 20261022102}[session]
    assert saved["seed"] == seed
    assert saved["rounds_per_stream"] == 24 and saved["replays_per_interval"] == 7
    assert saved["bootstrap_samples"] == 4000 and len(saved["streams"]) == 48
    identifiers = [row["stream_id"] for row in saved["streams"]]
    assert len(set(identifiers)) == 48
    rng = random.Random(seed)
    for row in saved["streams"]:
        order = list(OFF)
        rng.shuffle(order)
        assert len(row["warmups"]) == 1 and row["warmups"][0]["order"] == order
        assert all(row["warmups"][0]["microseconds"][m] > 0 for m in OFF)
    schedules = []
    for _ in identifiers:
        orders = []
        for _ in range(12):
            first = list(OFF)
            rng.shuffle(first)
            orders.extend([first, first[::-1]])
        schedules.append(orders)
    assert len(saved["global_stream_orders"]) == 24
    for r in range(24):
        permutation = list(range(48))
        rng.shuffle(permutation)
        assert saved["global_stream_orders"][r] == [identifiers[i] for i in permutation]
        for i, row in enumerate(saved["streams"]):
            assert row["rounds"][r]["order"] == schedules[i][r]
    streams = []
    for i, row in enumerate(saved["streams"]):
        assert len(row["rounds"]) == 24
        calculated = timing_summary(row["rounds"], seed + i + 1)
        assert_close(calculated, row["summary"], row["stream_id"])
        streams.append({"stream_id": row["stream_id"], "family": row["family"],
                        "queries": row["queries"], **calculated})
    whole = saved["whole_workload"]
    assert whole["replays"] == 2 and len(whole["rounds"]) == 16
    assert set(whole["warmup"]) == set(OFF)
    for cycle in range(8):
        first = list(OFF)
        rng.shuffle(first)
        assert whole["rounds"][2*cycle]["order"] == first
        assert whole["rounds"][2*cycle+1]["order"] == first[::-1]
    total = timing_summary(whole["rounds"], seed + 10000)
    assert_close(total, whole["summary"], "whole")
    return {"session": session, "streams": streams, "whole_workload": total,
            "material_label_counts": dict(Counter(row["material_label"] for row in streams)),
            "raw_rounds": 48*24, "bootstrap_samples_each": 4000,
            "per_stream_schedule_seed_exact": True, "global_stream_schedule_seed_exact": True,
            "warmups_retained_excluded_from_main": True, "whole_rounds": 16,
            "source_sha256": sha(path),
            "boundary": "Same fixed streams; two-round blocks, not conversations, resampled. Fixed marginal fresh median divides delta interval; no joint ratio CI or simultaneous familywise guarantee."}


def recount_features(results):
    dataset = load(HERE / "data/holdout.json.gz")
    saved = load(results / "holdout_features.json")
    rows = load(results / "holdout_rows.json.gz")
    states = load(results / "holdout_states.json.gz")
    by_key = {(r["stream_id"], r["step_index"], r["method"]): r for r in rows}
    records = {r["stream_id"]: r for r in saved["records"]}
    assert len(records) == len(saved["records"]) == len(dataset) == 48
    fingerprints = set()
    for state in states:
        for entry in state["instrumented_state"]["entries"]:
            context = json.loads(bytes.fromhex(entry[0][0]["exact_bytes_hex"]))
            fingerprints.add(json.dumps(context[0], sort_keys=True))
    assert len(fingerprints) == 1
    fingerprint = json.loads(next(iter(fingerprints)))
    totals = Counter()
    for stream in dataset:
        sid = stream["id"]
        frows = [by_key[sid, i, "fresh_instrumented"] for i in range(len(stream["steps"]))]
        srows = [by_key[sid, i, "selective_instrumented"] for i in range(len(stream["steps"]))]
        context_bytes = 0
        for i, step in enumerate(stream["steps"]):
            for method in METHODS:
                row = by_key[sid, i, method]
                assert row["gold_evaluated"] == step["gold_applicable"]
                assert row["supported"] == step["question_contract"]["supported"]
                assert row["valid_snapshot"] == (step["expected_integrity"] == "valid")
                assert row["namespace"] == step["parser_namespace"]
            if srows[i]["cost"]["control_events"].get("context_access", 0) > 0:
                context_bytes += len(encoded([fingerprint, step["parser_namespace"], step["public"]["entities"]]))
        actual = records[sid]
        counts = lambda rr, name: sum(r["audit"][name] for r in rr)
        ledger = lambda name: sum(r["cost"][name] for r in srows)
        expected = {"stream_constant": 1, "queries": len(stream["steps"]),
                    "records_visited": counts(frows, "cheap_calls"),
                    "raw_encode_bytes": counts(frows, "cheap_source_bytes"),
                    "saved_stage_calls": sum(counts(frows, s+"_calls")-counts(srows, s+"_calls")
                                               for s in ("cheap", "contract", "detail")),
                    "saved_stage_characters": actual["stage_characters"][OFF[0]]-actual["stage_characters"][OFF[1]],
                    "exact_probe_bytes": ledger("key_probe_bytes"),
                    "encoded_context_payload_bytes": context_bytes+ledger("value_encode_bytes"),
                    "admission_attempts": ledger("admission_attempts"),
                    "policy_control_actions": ledger("control_actions")}
        assert tuple(expected) == tuple(actual["features"]) == FEATURES
        assert expected == actual["features"], sid
        assert actual["p8_fresh"] == sum(r["cost"]["phase08_work_score"] for r in frows)
        assert actual["p8_selective"] == sum(r["cost"]["phase08_work_score"] for r in srows)
        assert actual["p8_delta"] == actual["p8_selective"]-actual["p8_fresh"]
        totals.update(expected)
    return {"streams": len(records), "feature_totals": dict(totals),
            "corpus_and_row_contracts_checked": len(rows),
            "character_boundary": "Saved stage-character totals came from the separate trace replay. This recount checks their difference; it does not reconstruct original strings from trace hashes or rerun parsing.",
            "sources_sha256": {"holdout_features.json": sha(results/"holdout_features.json"),
                               "data/holdout.json.gz": sha(HERE/"data/holdout.json.gz")}}


def recount_predictions(results):
    model = load(HERE/"calibration/model.json")
    feature_file = load(results/"holdout_features.json")
    saved = load(results/"predictions.json")
    assert model["feature_order"] == feature_file["feature_order"] == list(FEATURES)
    original = {r["stream_id"]: r for r in saved["predictions"]}
    assert len(original) == len(saved["predictions"]) == 48
    out, max_difference = [], 0.0
    for record in feature_file["records"]:
        x = record["features"]
        values = {
            "trace_ridge": math.fsum(model["coefficients_us_per_feature"][name]*x[name] for name in FEATURES),
            "zero_change": 0.0,
            "per_query": model["per_query_baseline_us"]*x["queries"],
            "p8_calibrated": model["p8_nonnegative_scale_us_per_point"]*record["p8_delta"]}
        row = {"stream_id": record["stream_id"], "predicted_delta_us": values,
               "raw_p8_sign": 1 if record["p8_delta"] >= 0 else -1,
               "always_slowdown_sign": 1}
        assert_close(row, original[row["stream_id"]], row["stream_id"])
        max_difference = max(max_difference, abs(values["trace_ridge"]-original[row["stream_id"]]["predicted_delta_us"]["trace_ridge"]))
        out.append(row)
    assert load(results/"model_refit.json") == model
    return {"predictions": out, "maximum_dotproduct_difference_us": max_difference,
            "frozen_model_sha256": sha(HERE/"calibration/model.json"),
            "stored_predictions_sha256": sha(results/"predictions.json"),
            "no_model_refitting_performed_by_recounter": True,
            "boundary": "Independent fsum dot products of the frozen coefficients and sealed feature vectors; tiny floating differences are compared with recount tolerance."}


def independently_score(predictions, timing):
    mapping = {r["stream_id"]: r for r in predictions["predictions"]}
    rows = []
    for row in timing["streams"]:
        p = mapping[row["stream_id"]]["predicted_delta_us"]
        delta, fresh = row["paired_delta_median_us"], row["fresh_median_us"]
        rows.append({"stream_id": row["stream_id"], "family": row["family"], "queries": row["queries"],
                     "delta_us": delta, "fresh_us": fresh, "material_label": row["material_label"],
                     "predicted_delta_us": p,
                     "normalized_absolute_error": {m: abs(p[m]-delta)/fresh for m in MODELS}})
    errors = {m: math.fsum(row["normalized_absolute_error"][m] for row in rows)/len(rows) for m in MODELS}
    best = min(errors[m] for m in MODELS if m != "trace_ridge")
    passed = best > 0 and errors["trace_ridge"] <= .10 and errors["trace_ridge"] <= .75*best
    families, horizons = {}, {}
    for family in sorted({row["family"] for row in rows}):
        subset = [r for r in rows if r["family"] == family]
        families[family] = {m: math.fsum(r["normalized_absolute_error"][m] for r in subset)/len(subset) for m in MODELS}
    for horizon in sorted({row["queries"] for row in rows}):
        subset = [r for r in rows if r["queries"] == horizon]
        horizons[str(horizon)] = {m: math.fsum(r["normalized_absolute_error"][m] for r in subset)/len(subset) for m in MODELS}
    return {"streams": len(rows), "mean_normalized_absolute_error": errors,
            "best_baseline_error": best, "model_error_divided_by_best_baseline": errors["trace_ridge"]/best if best else None,
            "numerical_rule_passed": passed, "family_errors": families, "horizon_errors": horizons, "rows": rows}


def independently_joint(predictions, a, b):
    pp = {r["stream_id"]: r for r in predictions["predictions"]}
    left = {r["stream_id"]: r for r in a["rows"]}
    right = {r["stream_id"]: r for r in b["rows"]}
    assert set(pp) == set(left) == set(right)
    common = [sid for sid in left if left[sid]["material_label"] == right[sid]["material_label"]
              and left[sid]["material_label"] in ("speedup", "slowdown")]
    counts = {label: sum(left[sid]["material_label"] == label for sid in common) for label in ("speedup", "slowdown")}
    sign_models = ("trace_ridge", "per_query", "p8_calibrated", "raw_p8", "always_slowdown")
    exact, signs = {}, {}
    for model in sign_models:
        correct, mistakes = dict.fromkeys(counts, 0), []
        for sid in common:
            sign = (pp[sid]["raw_p8_sign"] if model == "raw_p8" else 1 if model == "always_slowdown"
                    else -1 if pp[sid]["predicted_delta_us"][model] < 0 else 1)
            label = "speedup" if sign < 0 else "slowdown"
            truth = left[sid]["material_label"]
            correct[truth] += int(label == truth)
            if label != truth:
                mistakes.append(sid)
        exact[model] = ((Fraction(correct["speedup"], counts["speedup"])
                         + Fraction(correct["slowdown"], counts["slowdown"]))/2
                        if all(counts.values()) else None)
        signs[model] = {"correct_by_class": correct,
                       "balanced_accuracy": float(exact[model]) if exact[model] is not None else None,
                       "mistake_streams": mistakes}
    identifiable = all(value >= 4 for value in counts.values())
    best = max(exact[m] for m in sign_models if m != "trace_ridge") if all(counts.values()) else None
    sign_pass = bool(identifiable and exact["trace_ridge"] >= Fraction(3, 4)
                     and exact["trace_ridge"]-best >= Fraction(1, 10))
    numerical = a["numerical_rule_passed"] and b["numerical_rule_passed"]
    supported = numerical and sign_pass
    return {"H10_supported": supported, "numerical_rule_both_sessions": numerical,
            "common_resolved_streams": common, "common_resolved_counts": counts,
            "excluded_from_sign_only": {sid: [left[sid]["material_label"], right[sid]["material_label"]]
                                        for sid in left if sid not in common},
            "sign_question_identifiable_under_rule": identifiable, "sign_rule_passed": sign_pass,
            "sign_predictions": signs, "best_baseline_balanced_accuracy": float(best) if best is not None else None,
            "conclusion": ("supported_on_fixed_holdout" if supported else "not_supported_numerical_rule" if not numerical
                           else "not_supported_sign_rule" if identifiable else "not_established_sign_classes_insufficient"),
            "exact_balanced_accuracy_fractions": {m: str(value) if value is not None else None for m, value in exact.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE/"results")
    parser.add_argument("--reproduction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Never replace an independent recount"
    compared = []
    for name in DETERMINISTIC:
        original, repeated = args.results/name, args.reproduction/name
        assert original.read_bytes() == repeated.read_bytes(), name
        compared.append({"file": name, "byte_identical": True, "sha256": sha(original)})
    dataset = recount_dataset(args.results, "holdout")
    features = recount_features(args.results)
    predictions = recount_predictions(args.results)
    primary = recount_timing(args.results/"timing.json")
    reproduction = recount_timing(args.reproduction/"timing.json")
    scores_a, scores_b = independently_score(predictions, primary), independently_score(predictions, reproduction)
    assert_close(scores_a, load(args.results/"scores.json"), "primary_scores")
    assert_close(scores_b, load(args.reproduction/"scores.json"), "reproduction_scores")
    combined = independently_joint(predictions, scores_a, scores_b)
    seals = {}
    for label, directory in (("primary", args.results), ("reproduction", args.reproduction)):
        receipt = load(directory/"receipt.json")
        seal = load(directory/"prediction_receipt.json")
        timing = load(directory/"timing.json")
        assert receipt["status"] == "passed" and receipt["preservation_failures"] == 0
        assert seal["sealed_at_utc"] < timing["started_at_utc"]
        assert seal["model_sha256"] == sha(HERE/"calibration/model.json")
        assert seal["data_sha256"] == sha(HERE/"data/holdout.json.gz")
        assert seal["features_sha256"] == sha(directory/"holdout_features.json")
        assert seal["predictions_sha256"] == sha(directory/"predictions.json")
        for filename, digest in receipt["files"].items():
            assert sha(directory/filename) == digest, (label, filename)
        seals[label] = {"sealed_at_utc": seal["sealed_at_utc"], "worker_started_at_utc": timing["started_at_utc"],
                        "model_sha256": seal["model_sha256"], "predictions_sha256": seal["predictions_sha256"],
                        "all_receipt_hashes_match": True}
    result = {"implementation_functions_imported": [], "new_timing_sessions": 0,
              "deterministic_reproduction": compared, "holdout": dataset,
              "feature_recount": features, "prediction_recount": predictions,
              "primary_timing": primary, "reproduction_timing": reproduction,
              "primary_scores": scores_a, "reproduction_scores": scores_b,
              "combined": combined, "prediction_seals": seals,
              "boundary": "Postfreeze independent arithmetic recount, not a new timing or external validation. Same stored artifacts and fixed hypotheses; raw-state schema checks adapted from Phase09's standard-library-only recount."}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"raw_rows": dataset["rows"], "prefixes": dataset["prefixes"],
                      "primary_E": scores_a["mean_normalized_absolute_error"],
                      "reproduction_E": scores_b["mean_normalized_absolute_error"],
                      "combined": {k: combined[k] for k in ("H10_supported", "numerical_rule_both_sessions", "common_resolved_counts", "conclusion")}}, ensure_ascii=False))


if __name__ == "__main__":
    main()

