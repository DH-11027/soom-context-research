"""Development-only adversarial checks for Phase07 memoization.

All examples are authored here. No regression or held-out fixture is loaded.
Negative controls deliberately omit a key component; they are not findings
against the implemented cache. Run: python research/phase07/audit.py
"""
from copy import deepcopy
import json

from baseline import P6, verify_sources
import cached


ENTITIES = ("가람", "노을")
QUERY = "가람 모임은 지금 몇 시야?"


def public(texts, query=QUERY, entities=ENTITIES, ids=None):
    records = [
        {"seq": i, "id": ids[i] if ids else f"audit-{i}", "text": text}
        for i, text in enumerate(texts)
    ]
    return {
        "records": records,
        "entities": list(entities),
        "query": query,
        "snapshot": P6.BASE.snapshot(records),
    }


def semantic_result(result):
    return {k: v for k, v in result.items() if k != "cost"}


def actual_calls(result):
    return sum(result["cost"][f"{stage}_calls"]
               for stage in ("cheap", "contract", "detail"))


def logical_calls(result):
    return sum(result["cost"][f"{stage}_requests"]
               for stage in ("cheap", "contract", "detail"))


def run():
    verify_sources()
    checks = []
    counterexamples = []

    def check(name, source, cache, namespace="v1"):
        before = deepcopy(source)
        expected = P6.run(source, "text_scoped")
        observed = cached.run(source, cache, namespace=namespace)
        assert semantic_result(observed) == semantic_result(expected), name
        assert source == before, (name, "public input mutated")
        for stage in ("cheap", "contract", "detail"):
            assert observed["cost"][f"{stage}_requests"] == expected["cost"][f"{stage}_calls"], (name, stage)
        for key in ("hash_calls", "hash_serialized_bytes"):
            assert observed["cost"][key] == expected["cost"][key], (name, key)
        if cache is not None:
            assert cache.retained_bytes == sum(item[1] for item in cache.entries.values()), name
            assert cache.retained_bytes <= cache.max_bytes, name
            assert len(cache.entries) <= cache.max_entries, name
        checks.append({"name": name, "status": observed["status"],
                       "actual_parser_calls": actual_calls(observed),
                       "logical_parser_requests": logical_calls(observed),
                       "cache_lookups": observed["cost"]["cache_lookups"]})
        return observed

    ten = "가람 모임 시간은 10시로 확정해줘."
    eleven = "가람 모임 시간은 11시로 확정해줘."
    twelve = "가람 모임 시간은 12시로 확정해줘."
    deep = "가람 약속, 최종 시각은 11시로 적어둘게."
    cache = cached.ParseCache()
    first = public([ten], ids=["same-id"])
    edited = public([eleven], ids=["same-id"])
    check("same_id_original", first, cache)
    changed = check("same_id_changed_text", edited, cache)
    assert changed["prediction"] == {"가람.time": [11]}
    bad_id_cache = {first["records"][0]["id"]: P6.BASE.parse(ten, list(ENTITIES))}
    stale = bad_id_cache[edited["records"][0]["id"]]
    correct = P6.BASE.parse(eleven, list(ENTITIES))
    assert stale["value"] == 10 and correct["value"] == 11
    counterexamples.append({"name": "id_only_key_stale_edit", "negative_control": True,
                           "id": "same-id", "cached_value": 10, "correct_value": 11,
                           "implemented_cache_prediction": changed["prediction"]})

    cheap = P6.BASE.parse(deep, list(ENTITIES), deep=False)
    detailed = P6.BASE.parse(deep, list(ENTITIES), deep=True)
    assert cheap["kind"] == "havoc" and detailed["kind"] == "set"
    counterexamples.append({"name": "stage_omitted_real_parser_collision", "negative_control": True,
                           "text": deep, "cheap_kind": cheap["kind"],
                           "deep_kind": detailed["kind"], "deep_value": detailed["value"]})
    warm_cache = cached.ParseCache()
    cold = check("deep_stage_cold", public([deep]), warm_cache)
    warm = check("deep_stage_warm", public([deep]), warm_cache)
    reset = check("deep_stage_reset", public([deep]), cached.ParseCache())
    assert actual_calls(cold) > actual_calls(warm) == 0
    assert actual_calls(reset) == actual_calls(cold)
    assert logical_calls(cold) == logical_calls(warm) == logical_calls(reset) > 0
    stages = next(iter(warm_cache.entries.values()))[0]
    assert stages["cheap"][0]["kind"] == "havoc"
    assert stages["detail"][0]["kind"] == "set"

    absent = P6.BASE.parse(ten, ["새봄", "한결"])
    assert correct["kind"] == "set" and absent["kind"] == "havoc"
    counterexamples.append({"name": "entity_environment_omitted", "negative_control": True,
                           "text": ten, "original_entities": list(ENTITIES),
                           "changed_entities": ["새봄", "한결"],
                           "original_kind": P6.BASE.parse(ten, list(ENTITIES))["kind"],
                           "changed_kind": absent["kind"]})
    check("entity_membership_changed", public([ten], "새봄 모임은 지금 몇 시야?", ("새봄", "한결")), cache)
    ordered = check("entity_order_changed", public([ten], entities=tuple(reversed(ENTITIES))), cache)
    assert ordered["cost"]["cache_entry_misses"] > 0

    history = [ten, "노을 모임 시간은 20시로 확정해줘.",
               "노을 모임 시간은 가람 모임 시간과 같게 맞춰줘.", eleven]
    historical_cache = cached.ParseCache()
    before_copy = check("historical_copy_original", public(history, "노을 모임은 지금 몇 시야?"), historical_cache)
    history[0] = twelve
    after_copy = check("historical_copy_source_edited", public(history, "노을 모임은 지금 몇 시야?"), historical_cache)
    assert before_copy["prediction"] == {"노을.time": [10]}
    assert after_copy["prediction"] == {"노을.time": [12]}
    counterexamples.append({"name": "cached_historical_copy_value", "negative_control": True,
                           "copy_text_unchanged": history[2], "stale_source_value": 10,
                           "correct_source_value_after_edit": 12,
                           "final_source_value_both_histories": 11,
                           "implemented_cache_prediction": after_copy["prediction"]})

    ns_cache = cached.ParseCache()
    check("namespace_v1_cold", public([deep]), ns_cache, "v1")
    check("namespace_v1_warm", public([deep]), ns_cache, "v1")
    namespace_changed = check("namespace_v2_cold", public([deep]), ns_cache, "v2")
    assert namespace_changed["cost"]["cache_entry_misses"] > 0
    assert actual_calls(namespace_changed) == actual_calls(cold)
    def toy_parser(version, x):
        return x if version == "v1" else x + 1
    toy_bad_cache = {10: toy_parser("v1", 10)}
    assert toy_bad_cache[10] != toy_parser("v2", 10)
    counterexamples.append({"name": "namespace_semantic_change_toy_only", "negative_control": True,
                           "toy_function": "f(v1,x)=x; f(v2,x)=x+1", "stale": 10, "correct": 11,
                           "boundary": "The production parser does not change semantics with namespace; the real test checks isolation only."})

    scope_text = "가람 모임 장소만 다시 정해줘."
    scoped_history = [ten, scope_text]
    scoped_cache = cached.ParseCache()
    scoped_time = check("proper_scope_time_query", public(scoped_history), scoped_cache)
    scoped_both = check("proper_scope_both_query", public(scoped_history, "가람 모임의 시간과 장소를 알려줘."), scoped_cache)
    check("proper_scope_time_query_again", public(scoped_history), scoped_cache)
    assert scoped_time["scope_trace"] and scoped_time["scope_trace"][0]["detail_avoided"]
    assert not scoped_both["scope_trace"][0]["detail_avoided"]
    scope, _ = P6.scope_from_text(scope_text, list(ENTITIES))
    assert scope is not None and P6.BASE.parse(scope_text, list(ENTITIES), deep=True)["kind"] == "havoc"

    operations = [
        ("append_correction", [ten, eleven]),
        ("valid_reorder", [eleven, ten]),
        ("delete", [eleven]),
        ("reinsert", [ten, eleven]),
        ("duplicate_exact_text_different_id", [ten, ten]),
        ("empty_history", []),
    ]
    for name, texts in operations:
        check(name, public(texts), cache)
    invalid = deepcopy(first)
    invalid["records"][0]["text"] = eleven
    rejected = check("stale_snapshot_after_text_edit", invalid, cache)
    assert rejected["status"] == "integrity_failure" and rejected["cost"]["cache_lookups"] == 0
    invalid_seq = public([ten, eleven])
    invalid_seq["records"][1]["seq"] = 7
    invalid_seq["snapshot"] = P6.BASE.snapshot(invalid_seq["records"])
    rejected_seq = check("invalid_sequence_even_with_fresh_digest", invalid_seq, cache)
    assert rejected_seq["status"] == "integrity_failure" and rejected_seq["cost"]["cache_lookups"] == 0
    unsupported = check("unsupported_query", public([deep], "왜 그 시간이야?"), cache)
    assert unsupported["status"] == "unsupported_query" and logical_calls(unsupported) == 0
    assert unsupported["cost"]["cache_lookups"] == 0
    check("invalid_snapshot_repaired", edited, cache)
    check("fresh_api_without_cache", public([deep]), None)

    immutable_checks = []
    def rejects_mutation(name, operation):
        try:
            operation()
        except (TypeError, AttributeError):
            immutable_checks.append(name)
        else:
            raise AssertionError((name, "mutation accepted"))
    rejects_mutation("stage_table", lambda: stages.__setitem__("cheap", (None, 0)))
    rejects_mutation("event_mapping", lambda: stages["detail"][0].__setitem__("kind", "havoc"))
    rejects_mutation("event_nested_targets", lambda: stages["detail"][0]["targets"].append(("노을", "time")))
    source_value = {"nested": [{"value": 10}], "set": {("가람", "time")}}
    frozen = cached.immutable(source_value)
    source_value["nested"][0]["value"] = 99
    source_value["set"].clear()
    assert frozen["nested"][0]["value"] == 10 and len(frozen["set"]) == 1
    immutable_checks.append("producer_alias_isolated")
    warm["prediction"]["가람.time"][0] = -999
    check("result_alias_does_not_mutate_cache", public([deep]), warm_cache)

    disabled = check("disabled_zero_capacity", public([deep]), cached.ParseCache(0, 0))
    assert actual_calls(disabled) == actual_calls(cold)
    assert disabled["cost"]["cache_writes"] == 0
    tiny = cached.ParseCache(max_entries=1, max_bytes=1)
    oversized = check("oversize_bypass", public([deep]), tiny)
    assert oversized["cost"]["cache_oversize"] > 0 and not tiny.entries
    evict = cached.ParseCache(max_entries=2, max_bytes=65536)
    eviction_results = [check(f"lru_order_{i}", public([text]), evict)
                        for i, text in enumerate([ten, eleven, ten, twelve, eleven])]
    assert sum(r["cost"]["cache_entry_hits"] for r in eviction_results) == 1
    assert sum(r["cost"]["cache_entry_misses"] for r in eviction_results) == 4
    assert sum(r["cost"]["cache_evictions"] for r in eviction_results) == 2
    one = cached.ParseCache()
    check("byte_capacity_measure_one", public([ten]), one)
    one_size = one.retained_bytes
    byte_bound = cached.ParseCache(max_entries=64, max_bytes=one_size)
    byte_results = [check(f"byte_bound_{i}", public([text]), byte_bound)
                    for i, text in enumerate([ten, eleven, ten])]
    assert sum(r["cost"]["cache_evictions"] for r in byte_results) == 2
    evict.clear()
    assert evict.retained_bytes == 0 and not evict.entries
    clear_result = check("explicit_clear_recomputes", public([ten]), evict)
    assert clear_result["cost"]["cache_entry_hits"] == 0

    result = {
        "passed": True,
        "development_only": True,
        "heldout_read": False,
        "parity_check_count": len(checks),
        "parity_checks": checks,
        "negative_control_counterexamples": counterexamples,
        "nonvacuity": {"cold_actual_calls": actual_calls(cold),
                       "warm_actual_calls": actual_calls(warm),
                       "reset_actual_calls": actual_calls(reset),
                       "logical_requests_each": logical_calls(cold),
                       "persistent_vs_reset_parser_reduction": actual_calls(reset) - actual_calls(warm)},
        "immutability_checks": immutable_checks,
        "capacity_checks": {"oversize_bypassed": True, "entry_lru_evictions": 2,
                            "byte_budget_evictions": 2, "accounting_matches_entries": True},
        "limitations": [
            "These are authored development checks, not independent evaluation or a proof for arbitrary inputs.",
            "The namespace semantic-change counterexample uses a declared toy pure function; the production parser is unchanged.",
            "No actual query-local TOP versus detailed-exact-result counterexample is established: the tested proper-scope sentence stays havoc under the current deep grammar. Cross-query demand changes are checked for reference parity only.",
            "Serialized retained-byte limits are checked; Python object overhead, allocator behavior and RSS are outside this bound.",
            "Parser execution reduction is established here; whole-cost and wall-time improvement require the preregistered comparative study.",
        ],
    }
    json.dumps(result, ensure_ascii=False)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
