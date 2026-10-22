"""Authored development checks of Phase08, not unseen semantic evaluation.

No holdout, builder, evaluation data, family label, or future request is read.
Tests target conditional parity, exact keys, declared cost accounting, capacity,
small online counterexamples, and evaluator mutants using authored tiny gold.
Failed assertions stop the experiment.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json

import frozen
import runtime


P6 = runtime.P6
ENTITIES = ["가람", "노을"]
QUERY = "가람 모임은 지금 몇 시야?"
SET = "가람 모임 시간은 8시로 확정해줘."
NS = "audit-v1"


def public(texts, *, query=QUERY, entities=None, ids=None):
    records = [{"seq": i, "id": ids[i] if ids else f"audit-{i}", "text": text}
               for i, text in enumerate(texts)]
    return {"records": records, "entities": list(entities or ENTITIES),
            "query": query, "snapshot": P6.BASE.snapshot(records)}


def quote(n=400, character="가", *, deep=True):
    payload = character * n
    return (f"표현 연습:「{payload}」라는 문장을 써봤어. 약속은 그대로야." if deep
            else f"예시일 뿐이야:「{payload}」 실제 변경은 없어.")


def semantic(result):
    return {k: v for k, v in result.items() if k != "cost"}


def rendered(source, result):
    return b"" if result["status"] == "integrity_failure" else P6.render(source, result["selected"], result["status"]).encode("utf-8")


def calls(result):
    return sum(result["cost"][s + "_calls"] for s in runtime.STAGES)


def delta(reference, result):
    return result["cost"]["phase08_work_score"] - reference["cost"]["output_plus_source_work_proxy"]


def cache_state(cache):
    # Canonical rendering only for auditing; not used by the policy or timing.
    return [
        (key, runtime.plain(item["stages"]), item["size"], item["characters"], item["surplus"], item["hits"], item["order"])
        for key, item in cache.entries.items()]


def run():
    frozen.verify_sources()
    expected = hashlib.sha256("|".join(frozen.SOURCE_HASHES.values()).encode()).hexdigest()
    assert runtime.SEMANTIC_FINGERPRINT == expected
    checks, counterexamples, formulas = [], [], []

    def check(name, source, cache, namespace=NS):
        before = deepcopy(source)
        reference = P6.run(source, "text_scoped")
        result = runtime.run(source, cache, namespace=namespace)
        assert semantic(reference) == semantic(result), name
        assert rendered(source, reference) == rendered(source, result), (name, "rendered bytes")
        assert source == before, (name, "input mutation")
        cost = result["cost"]
        for stage in runtime.STAGES:
            assert cost[stage + "_requests"] == reference["cost"][stage + "_calls"], (name, stage)
            assert cost[stage + "_requests"] == cost[stage + "_calls"] + cost[stage + "_reused"], (name, stage)
        for key in ("hash_calls", "hash_serialized_bytes", "reparse_calls", "reparse_source_bytes"):
            assert cost[key] == reference["cost"][key], (name, key)
        assert cost["cache_overhead_bytes"] == sum(cost[k] for k in runtime.BYTE_FIELDS), name
        assert cost["phase07_work_proxy"] == cost["output_plus_source_work_proxy"] + cost["cache_overhead_bytes"], name
        assert cost["control_actions"] == sum(cost["control_events"].values()), name
        assert cost["phase08_work_score"] == cost["phase07_work_proxy"] + runtime.ACTION_WEIGHT * cost["control_actions"], name
        assert cache.retained_bytes == sum(item["size"] for item in cache.entries.values()), name
        assert cache.retained_bytes <= cache.max_bytes and len(cache.entries) <= cache.max_entries, name
        assert cache.peak_bytes <= cache.max_bytes and cache.peak_entries <= cache.max_entries, name
        assert cache.lengths == Counter(item["characters"] for item in cache.entries.values()), name
        assert cost["directory_entries"] == len(cache.lengths), name
        for key, item in cache.entries.items():
            assert set(item["stages"]) == set(runtime.STAGES), name
            assert item["stages"]["cheap"][0]["kind"] == "havoc", name
            assert item["stages"]["contract"][0][0] is None, name
            payload = sum(length for _, length in item["stages"].values())
            assert item["size"] == len(key[0]) + len(key[1]) + payload + runtime.META_BYTES, name
            assert item["surplus"] == len(key[1]) - len(key[0]) - payload - runtime.ACTION_WEIGHT * runtime.WARM_ACTIONS, name
            assert item["surplus"] > 0 and 0 <= item["hits"] <= runtime.HIT_CAP, name
            assert len(key[1].decode("utf-8")) == item["characters"], name
        checks.append({"name": name, "status": result["status"],
                       "actual_calls": calls(result), "fresh_calls": calls(reference),
                       "delta_work_score": delta(reference, result),
                       "cache_hits": cost["cache_entry_hits"], "entries": len(cache.entries)})
        return reference, result

    deep = quote()
    source = public([SET, deep])
    cache = runtime.SelectiveCache()
    base_cold, cold = check("deep_bundle_cold", source, cache)
    base_warm, warm = check("deep_bundle_warm", source, cache)
    assert cold["cost"]["cache_writes"] == 1 and cold["cost"]["cache_lookups"] == 0
    assert warm["cost"]["cache_entry_hits"] == 1
    assert calls(base_warm) == 4 and calls(warm) == 1
    entry = next(iter(cache.entries.values()))
    assert entry["stages"]["cheap"][0]["kind"] == "havoc"
    assert entry["stages"]["detail"][0]["kind"] == "noop"
    C = len(runtime.encode((runtime.SEMANTIC_FINGERPRINT, NS, tuple(ENTITIES))))
    L = len(deep.encode("utf-8"))
    R = sum(length for _, length in entry["stages"].values())
    assert cold["cost"]["control_actions"] == 25
    assert warm["cost"]["control_actions"] == 9
    cold_expected = 2 * C + 2 * L + 2 * R + 25 * runtime.ACTION_WEIGHT
    warm_expected = 2 * C - L + R + 9 * runtime.ACTION_WEIGHT
    assert delta(base_cold, cold) == cold_expected
    assert delta(base_warm, warm) == warm_expected
    assert cold["cost"]["key_build_bytes"] == C + L
    assert cold["cost"]["key_probe_bytes"] == 0
    assert cold["cost"]["value_encode_bytes"] == R
    assert cold["cost"]["cache_write_bytes"] == C + L + R
    assert warm["cost"]["key_build_bytes"] == C + L
    assert warm["cost"]["key_probe_bytes"] == C + L
    assert warm["cost"]["cache_read_payload_bytes"] == R
    assert warm["cost"]["value_encode_bytes"] == warm["cost"]["cache_write_bytes"] == 0
    formulas.append({"name": "one_deep_plus_short_set", "C": C, "L": L, "R": R,
                     "cold_actual": delta(base_cold, cold), "cold_expected": cold_expected,
                     "warm_actual": delta(base_warm, warm), "warm_expected": warm_expected,
                     "cold_actions": 25, "warm_actions": 9, "residual": 0})
    two_step_delta = cold_expected + warm_expected
    assert two_step_delta > 0 and calls(cold) + calls(warm) < calls(base_cold) + calls(base_warm)
    counterexamples.append({"name": "positive_hit_and_parser_reduction_but_two_step_loss",
                           "steps": 2, "delta_work_score": two_step_delta,
                           "actual_calls": calls(cold) + calls(warm),
                           "fresh_calls": calls(base_cold) + calls(base_warm)})
    total = two_step_delta
    for i in range(6):
        a, b = check(f"deep_warm_repeat_{i}", source, cache)
        assert delta(a, b) == warm_expected
        total += delta(a, b)
    assert total < 0
    formulas.append({"name": "eight_repeats_include_cold", "actual": total,
                     "expected": cold_expected + 7 * warm_expected, "residual": 0,
                     "boundary": "Authored development example, not independent performance evaluation"})
    counterexamples.append({"name": "stop_after_first_admission", "steps": 1,
                           "delta_work_score": cold_expected,
                           "explanation": "No future recurrence is guaranteed by an observed profitable warm surplus."})

    # Same number of Unicode characters is not semantic identity.
    edited = deep[:-1] + "?"
    assert len(edited) == len(deep) and len(edited.encode()) == L
    _, changed = check("same_id_same_length_exact_text_edit", public([SET, edited], ids=["a", "same-id"]), cache)
    assert changed["status"] == "opaque_fallback"
    assert changed["cost"]["cache_entry_hits"] == 0 and changed["cost"]["detail_calls"] == 1
    _, restored = check("restored_exact_text", public([SET, deep], ids=["a", "same-id"]), cache)
    assert restored["status"] == "certified_model" and restored["cost"]["cache_entry_hits"] == 1
    counterexamples.append({"name": "length_only_key_is_unsound", "negative_control": True,
                           "same_characters": len(deep), "original_status": "certified_model",
                           "edited_status": "opaque_fallback", "implemented_exact_key_hit_on_edit": False})
    cheap_collision = quote(len(deep) - len(quote(0, deep=False)), character="나", deep=False)
    assert len(cheap_collision) == len(deep)
    a, b = check("long_cheap_false_positive_same_character_length", public([SET, cheap_collision]), cache)
    assert b["cost"]["cache_entry_misses"] == 1 and b["cost"]["detail_calls"] == 0
    assert b["cost"]["cache_writes"] == 0 and delta(a, b) > 0
    counterexamples.append({"name": "length_directory_false_positive_cost", "delta_work_score": delta(a, b),
                           "actual_execution_reduction": calls(a) - calls(b), "semantic_failure": False})

    # Context components are not replaced by the negative-filter observation.
    for name, roster, namespace in (
        ("ordered_entities_changed", list(reversed(ENTITIES)), NS),
        ("entity_membership_changed", ENTITIES + ["새봄"], NS),
        ("namespace_changed", ENTITIES, "audit-v2"),
    ):
        _, b = check(name, public([SET, deep], entities=roster), cache, namespace)
        assert b["cost"]["cache_entry_hits"] == 0 and b["cost"]["detail_calls"] == 1
    check("original_context_revisited", source, cache)

    # No query-local TOP, prediction or historical copy value is stored.
    ten = "가람 모임 시간은 10시로 확정해줘."
    eleven = "가람 모임 시간은 11시로 확정해줘."
    twelve = "가람 모임 시간은 12시로 확정해줘."
    copy = "노을 모임 시간은 가람 모임 시간과 같게 맞춰줘."
    historical = [ten, copy, eleven, deep]
    _, old = check("historical_copy_first", public(historical, query="노을 모임은 지금 몇 시야?"), cache)
    historical[0] = twelve
    _, now = check("historical_copy_source_edit", public(historical, query="노을 모임은 지금 몇 시야?"), cache)
    assert old["prediction"] == {"노을.time": [10]} and now["prediction"] == {"노을.time": [12]}
    scope_text = "가람 모임 장소만 다시 정해줘."
    _, time_only = check("proper_scope_time_only", public([ten, scope_text, deep]), cache)
    _, both = check("proper_scope_current_demand_changed", public([ten, scope_text, deep], query="가람 모임의 시간과 장소를 알려줘."), cache)
    assert time_only["scope_trace"][1]["detail_avoided"]
    assert not both["scope_trace"][1]["detail_avoided"]
    assert P6.BASE.parse(deep, ENTITIES)["kind"] == P6.BASE.parse(scope_text, ENTITIES)["kind"] == "havoc"
    counterexamples.append({"name": "cheap_unknown_does_not_determine_future_stage_count", "negative_control": True,
                           "deep_quote_requests": 3, "irrelevant_scoped_record_requests": 2,
                           "same_cheap_kind": "havoc", "boundary": "Natural query-local paths, not an oracle admission feature"})

    for name, texts in (("valid_reorder", [eleven, ten, deep]),
                        ("valid_delete", [eleven, deep]),
                        ("valid_reinsert", [ten, eleven, deep]),
                        ("duplicate_exact_raw_distinct_records", [SET, deep, deep]),
                        ("empty_history", [])):
        check(name, public(texts), cache)

    # All failures happen before persistent-cache or policy access.
    stale = deepcopy(source)
    stale["records"][0]["text"] = eleven
    invalid_order = public([SET, deep])
    invalid_order["records"][1]["seq"] = 10
    invalid_order["snapshot"] = P6.BASE.snapshot(invalid_order["records"])
    for name, invalid in (("stale_snapshot_even_when_cache_warm", stale), ("invalid_sequence_with_current_digest", invalid_order)):
        before = cache_state(cache)
        _, b = check(name, invalid, cache)
        assert b["status"] == "integrity_failure" and b["cost"]["cache_lookups"] == b["cost"]["control_actions"] == 0
        assert cache_state(cache) == before
    before = cache_state(cache)
    _, b = check("unsupported_does_not_prefill_cache", public([SET, deep], query="왜 그 시간이야?"), cache)
    assert b["status"] == "unsupported_query" and b["cost"]["control_actions"] == 0 and calls(b) == 0
    assert cache_state(cache) == before

    mutation_checks = []
    def rejects(name, operation):
        try:
            operation()
        except (TypeError, AttributeError):
            mutation_checks.append(name)
        else:
            raise AssertionError((name, "mutation accepted"))
    stages = entry["stages"]
    rejects("stage_table", lambda: stages.__setitem__("cheap", (None, 0)))
    rejects("event_mapping", lambda: stages["detail"][0].__setitem__("kind", "havoc"))
    rejects("nested_targets", lambda: stages["detail"][0]["targets"].append(("노을", "time")))
    mutable = {"nested": [{"value": 8}], "targets": {("가람", "time")}}
    frozen_value = runtime.immutable(mutable)
    mutable["nested"][0]["value"] = 99
    mutable["targets"].clear()
    assert frozen_value["nested"][0]["value"] == 8 and len(frozen_value["targets"]) == 1
    mutation_checks.append("producer_alias_isolated")
    warm["prediction"]["가람.time"][0] = -999
    _, b = check("result_alias_isolated", source, cache)
    assert b["prediction"] == {"가람.time": [8]}

    # Bounded memory, cold cost and all-or-nothing victim plans.
    _, disabled = check("capacity_zero", source, runtime.SelectiveCache(max_entries=0, max_bytes=0))
    assert disabled["cost"]["cache_writes"] == 0 and calls(disabled) == 4
    _, oversize = check("individual_oversize", source, runtime.SelectiveCache(max_bytes=10))
    assert oversize["cost"]["cache_oversize"] == 1 and oversize["cost"]["cache_writes"] == 0
    e = C + L + R + runtime.META_BYTES
    pair = runtime.SelectiveCache(max_bytes=2 * e)
    check("combined_capacity_first", source, pair)
    check("combined_capacity_exact_fit", public([SET, quote(character="나")]), pair)
    assert pair.retained_bytes == 2 * e and len(pair.entries) == 2
    over_pair = runtime.SelectiveCache(max_bytes=2 * e)
    check("combined_capacity_over_first", source, over_pair)
    _, b = check("combined_capacity_plus_three_bytes", public([SET, quote(401, "나")]), over_pair)
    assert b["cost"]["cache_evictions"] == 1 and len(over_pair.entries) == 1
    assert over_pair.retained_bytes == e + 3
    formulas.append({"name": "combined_capacity_boundary", "exact_pair_bytes": 2 * e,
                     "plus_one_korean_character_bytes": 2 * e + 3, "budget": 2 * e,
                     "larger_candidate_evictions": 1})

    pinned = runtime.SelectiveCache(max_entries=1)
    popular = public([SET, quote(800, "다")])
    for i in range(6):
        check(f"popular_resident_{i}", popular, pinned)
    state = cache_state(pinned)
    missed_delta = 0
    for i in range(4):
        a, b = check(f"new_smaller_repeated_rejected_{i}", source, pinned)
        assert b["cost"]["admission_reject_capacity"] == 1 and b["cost"]["cache_writes"] == 0
        assert b["cost"]["cache_entry_hits"] == 0
        assert cache_state(pinned) == state, "rejected victim plan mutated resident"
        missed_delta += delta(a, b)
    assert missed_delta > 0
    counterexamples.append({"name": "popular_stale_resident_blocks_smaller_recurrent_item",
                           "new_item_visits": 4, "new_item_admitted": False,
                           "new_item_work_score_excess": missed_delta,
                           "explanation": "Past hit weights have no aging; future popularity is not known."})

    # A negative filter avoids exact probes at distinct lengths. Its ablation
    # still preserves semantics, but can spend substantially more on misses.
    filter_on = runtime.SelectiveCache(directory=True)
    filter_off = runtime.SelectiveCache(directory=False)
    check("directory_enabled_seed", source, filter_on)
    check("directory_disabled_seed", source, filter_off)
    different_length_cheap = public([SET, quote(700, "라", deep=False)])
    a, on = check("directory_negative_filter_distinct_length", different_length_cheap, filter_on)
    _, off = check("directory_ablation_distinct_length", different_length_cheap, filter_off)
    assert on["cost"]["cache_lookups"] == 0 and off["cost"]["cache_lookups"] == 1
    assert semantic(on) == semantic(off)
    assert delta(a, on) < delta(a, off)

    # Hit count remains bounded; no hundreds of parser invocations are needed
    # to test saturation of a past-only scalar field.
    saturated = runtime.SelectiveCache()
    check("hit_cap_seed", source, saturated)
    for item in saturated.entries.values():
        item["hits"] = runtime.HIT_CAP
    check("bounded_hit_counter_saturation", source, saturated)
    assert all(item["hits"] == runtime.HIT_CAP for item in saturated.entries.values())

    # The baseline wrapper may add a control ledger but must not silently alter
    # any original P7 byte, call, retention or eviction counter.
    import evaluation
    original = evaluation.C7.ParseCache(max_entries=2, max_bytes=6000)
    metered = evaluation.MeteredLRU(max_entries=2, max_bytes=6000)
    lru_checks = []
    chronology = [source, source, public([eleven, deep]), public([SET, quote(500, "마")]),
                  public([SET, quote(800, "바")]), public([SET, quote(3000, "사")]),
                  source, invalid_order, stale, public([SET, deep], query="왜 그 시간이야?")]
    for i, src in enumerate(chronology):
        old = evaluation.C7.run(src, original, namespace=NS)
        new = evaluation.run("lru", src, metered, namespace=NS)
        assert semantic(old) == semantic(new), ("metered_lru", i)
        assert rendered(src, old) == rendered(src, new), ("metered_lru_render", i)
        for key, value in old["cost"].items():
            if key != "local_seconds":
                assert new["cost"][key] == value, ("metered_lru_cost", i, key)
        assert list(original.entries) == list(metered.entries), ("metered_lru_order", i)
        assert original.retained_bytes == metered.retained_bytes
        lru_checks.append({"step": i, "status": old["status"],
                           "original_p7": old["cost"]["phase07_work_proxy"],
                           "metered_p7": new["cost"]["phase07_work_proxy"],
                           "added_control_actions": new["cost"]["control_actions"]})

    # Label independence is checked through a public-only whitelist. These tiny
    # labels belong to the evaluator and are never passed to runtime.run.
    gold_public = public([SET, "가람 모임 장소는 카페로 확정해줘.",
                          "노을 모임 시간은 10시로 확정해줘.",
                          "노을 모임 장소는 카페로 확정해줘.", deep],
                         query="두 모임의 현재 시간을 알려줘.")
    gold = [{"kind": "set", "target": ["가람", "time"], "value": 8},
            {"kind": "set", "target": ["가람", "place"], "value": "카페"},
            {"kind": "set", "target": ["노을", "time"], "value": 10},
            {"kind": "set", "target": ["노을", "place"], "value": "카페"},
            {"kind": "noop"}]
    gold_step = {"public": gold_public, "gold": gold, "gold_applicable": True,
                 "expected_integrity": "valid", "parser_namespace": NS,
                 "question_contract": {"supported": True, "required_fields": [["가람", "time"], ["노을", "time"]]}}
    assert set(evaluation.S7.public_of(gold_step)) == {"records", "entities", "snapshot", "query"}
    altered_labels = deepcopy(gold_step)
    altered_labels.update({"gold": [{"made_up": "future label"}], "family": "adversarial", "future_hits": 999999})
    assert evaluation.S7.public_of(altered_labels) == evaluation.S7.public_of(gold_step)
    valid_result = P6.run(gold_public, "text_scoped")
    assert valid_result["status"] == "certified_model"
    valid_assess = evaluation.S7.assess(gold_step, gold_public, valid_result)
    assert not any(valid_assess[k] for k in ("structural_error", "schema_error", "false_certification", "containment_violation"))
    assert valid_assess["selected_gold_projection_equal"] is True
    mutants = []

    def mutant(name, modify):
        result = deepcopy(valid_result)
        modify(result)
        judged = evaluation.S7.assess(gold_step, gold_public, result)
        detected = (judged["structural_error"] or judged["schema_error"] or judged["false_certification"]
                    or judged["containment_violation"] or judged["selected_gold_projection_equal"] is False)
        assert detected, ("undetected_evaluator_mutant", name)
        mutants.append({"name": name, "detected": True, "assessment": judged})

    mutant("empty_certified_prediction", lambda r: r.update(prediction={}))
    mutant("missing_required_field", lambda r: r["prediction"].pop("노을.time"))
    mutant("incorrect_singleton", lambda r: r["prediction"].update({"가람.time": [99]}))
    mutant("non_singleton_certification", lambda r: r["prediction"].update({"가람.time": [8, 99]}))
    mutant("wrong_scalar_type", lambda r: r["prediction"].update({"가람.time": ["8"]}))
    mutant("unsupported_for_supported_query", lambda r: r.update(status="unsupported_query", prediction={}))
    mutant("selected_evidence_omits_causal_set", lambda r: r.update(selected=[2]))
    mutant("partial_fallback", lambda r: r.update(status="opaque_fallback", prediction={"가람.time": None, "노을.time": None}, selected=[4]))
    mutant("integrity_failure_on_valid_snapshot", lambda r: r.update(status="integrity_failure", prediction={}, selected=[], output_bytes=0))

    return {"passed": True, "development_only": True, "heldout_read": False,
            "parity_check_count": len(checks), "checks": checks, "failures": [],
            "formula_checks": formulas, "counterexamples": counterexamples,
            "metered_lru_original_p7_checks": lru_checks,
            "evaluator_mutants": mutants, "public_whitelist_invariant": True,
            "immutability_checks": mutation_checks,
            "source_hashes_verified": dict(frozen.SOURCE_HASHES),
            "limits": [
                "Same-model authored development checks, not independent semantic or performance evaluation.",
                "P8 is P7 logical byte-work plus declared weighted control actions; it is not real CPU cycles, RAM traffic, tokens or prices.",
                "Hit saturation test sets a past-hit metadata value to its declared cap; it does not alter parser functions or cache values.",
                "Namespace rotation checks isolation, not a deployed parser semantic upgrade.",
                "No concurrent mutation, external reader verification, natural-language correctness or physical RSS bound is established.",
            ]}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
