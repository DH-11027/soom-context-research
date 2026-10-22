"""Pre-freeze authored checks. Never opens Phase09 holdout or its builder."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from bindings import P6, P8E, P8R, ROOT, S7, verify_sources
import erase
import evaluator
import execution
import off_selective

HERE = Path(__file__).resolve().parent
ENTITIES = ["가람", "노을"]
NS = "phase09-audit-v1"
SET = "가람 모임 시간은 8시로 확정해줘."


def quote(n=400, character="가", deep=True):
    payload = character * n
    return (f"표현 연습:「{payload}」라는 문장을 써봤어. 약속은 그대로야." if deep
            else f"예시일 뿐이야:「{payload}」 실제 변경은 없어.")


def public(texts, query="가람 모임은 지금 몇 시야?", entities=None):
    records = [{"seq": i, "id": f"p9-audit-{i}", "text": text} for i, text in enumerate(texts)]
    return {"records": records, "entities": list(entities or ENTITIES), "query": query,
            "snapshot": P6.BASE.snapshot(records)}


def paired_sequence(sequence):
    components = {m: execution.components(m) for m in execution.METHODS}
    caches = {m: components[m][0]() for m in execution.METHODS}
    checks = []
    for name, source, namespace in sequence:
        outputs, traces, policies, counters = {}, {}, {}, {}
        for method in execution.METHODS:
            fresh_public = deepcopy(source)
            with evaluator.actual_work(method, caches[method]) as record:
                result = components[method][1](fresh_public, caches[method], namespace)
            counters[method], traces[method], policies[method] = record
            outputs[method] = evaluator.observe(fresh_public, result)
            assert fresh_public == source, (name, method, "input changed")
            assert not evaluator.state_invariants(caches[method]), (name, method)
        reference = outputs["fresh_instrumented"]
        assert all(value == reference for value in outputs.values()), name
        for on, off in evaluator.ON_OFF:
            assert traces[on] == traces[off], (name, "execution trace")
            assert policies[on] == policies[off], (name, "policy trace")
            assert counters[on] == counters[off], (name, "counts")
        assert evaluator.policy_state(caches["selective_instrumented"]) == evaluator.policy_state(caches["selective_uninstrumented"]), (name, "pi")
        checks.append({"name": name, "status": reference[0]["status"],
                       "fresh_actual_work": counters["fresh_uninstrumented"],
                       "selective_actual_work": counters["selective_uninstrumented"],
                       "retained_bytes": caches["selective_uninstrumented"].retained_bytes,
                       "entries": len(caches["selective_uninstrumented"].entries)})
    return checks


def state_mutants():
    def seeded():
        cache = off_selective.SelectiveCache()
        for text in (quote(400, "가"), quote(410, "나"), quote(400, "가")):
            off_selective.run(public([SET, text]), cache, namespace=NS)
        assert len(cache.entries) == 2
        return cache

    def item(cache):
        return next(iter(cache.entries.values()))

    def alter_key(cache, context=False):
        key = next(iter(cache.entries))
        a, b = key
        changed = (a[:-1] + b"!", b) if context else (a, b[:-1] + b"?")
        value = cache.entries.pop(key)
        cache.entries[changed] = value

    def stage_length(cache):
        value = item(cache)
        stages = dict(value["stages"])
        val, length = stages["detail"]
        stages["detail"] = (val, length + 1)
        value["stages"] = MappingProxyType(stages)

    def stage_value(cache):
        value = item(cache)
        stages = dict(value["stages"])
        old, length = stages["detail"]
        new = dict(old)
        new["kind"] = "havoc"
        stages["detail"] = (P8R.immutable(new), length)
        value["stages"] = MappingProxyType(stages)

    mutations = [
        ("resident_hit_count", lambda c: item(c).__setitem__("hits", item(c)["hits"] + 1)),
        ("surplus", lambda c: item(c).__setitem__("surplus", item(c)["surplus"] + 1)),
        ("logical_size", lambda c: item(c).__setitem__("size", item(c)["size"] + 1)),
        ("characters", lambda c: item(c).__setitem__("characters", item(c)["characters"] + 1)),
        ("entry_order", lambda c: item(c).__setitem__("order", item(c)["order"] + 1)),
        ("next_order", lambda c: setattr(c, "next_order", c.next_order + 1)),
        ("length_directory", lambda c: c.lengths.update([item(c)["characters"]])),
        ("retained_bytes", lambda c: setattr(c, "retained_bytes", c.retained_bytes + 1)),
        ("raw_exact_key", lambda c: alter_key(c)),
        ("context_exact_key", lambda c: alter_key(c, True)),
        ("stage_payload_length", stage_length),
        ("stage_semantic_value", stage_value),
        ("dictionary_insertion_order", lambda c: setattr(c, "entries", dict(reversed(list(c.entries.items()))))),
        ("capacity", lambda c: setattr(c, "max_bytes", c.max_bytes - 1)),
        ("directory_mode", lambda c: setattr(c, "directory", not c.directory)),
    ]
    results = []
    for name, mutate in mutations:
        original, broken = seeded(), seeded()
        assert evaluator.policy_state(original) == evaluator.policy_state(broken)
        mutate(broken)
        source = public([SET])  # No long-record access: answer can remain identical.
        a = off_selective.run(source, original, namespace=NS)
        b = off_selective.run(source, broken, namespace=NS)
        equal_answer = evaluator.observe(source, a) == evaluator.observe(source, b)
        different_state = evaluator.policy_state(original) != evaluator.policy_state(broken)
        assert equal_answer and different_state, name
        results.append({"name": name, "observations_equal": True, "state_mutant_detected": True})
    return results


def erased_hit_counterexample():
    class MissingPolicyHit(off_selective.SelectiveCache):
        def get(self, key):
            item = self.entries.get(key)
            return None if item is None else item["stages"]

    a, b = off_selective.SelectiveCache(), MissingPolicyHit()
    old, new = quote(10800, "가"), quote(11200, "나")
    rows = []
    for text in (old, old, new):
        source = public([SET, text])
        before_a, before_b = evaluator.policy_state(a), evaluator.policy_state(b)
        good = off_selective.run(source, a, namespace=NS)
        bad = off_selective.run(source, b, namespace=NS)
        assert evaluator.observe(source, good) == evaluator.observe(source, bad)
        rows.append({"observations_equal": True,
                     "state_equal": evaluator.policy_state(a) == evaluator.policy_state(b),
                     "good_entries": len(a.entries), "bad_entries": len(b.entries),
                     "good_policy_entries_changed": before_a["entries"] != evaluator.policy_state(a)["entries"],
                     "bad_policy_entries_changed": before_b["entries"] != evaluator.policy_state(b)["entries"]})
    assert rows[0]["state_equal"] and not rows[1]["state_equal"]
    assert next(iter(a.entries))[1] == old.encode("utf-8")
    assert next(iter(b.entries))[1] == new.encode("utf-8")
    ga, ba = next(iter(a.entries.values())), next(iter(b.entries.values()))
    assert ga["size"] + ba["size"] > P8R.MAX_BYTES
    assert ga["surplus"] < ba["surplus"] <= 2 * ga["surplus"]
    return {"name": "deleting_policy_hit_update_changes_victim_decision",
            "steps": rows, "default_capacity_unchanged": True,
            "old_surplus": ga["surplus"], "new_surplus": ba["surplus"],
            "old_size": ga["size"], "new_size": ba["size"],
            "explanation": "The two answers stay equal. On the second visit hit state diverges; on the third visit the valid policy rejects B, while the mutant evicts A and admits B."}


def original_instrumented_identity(sequence):
    checks = []
    for method, name in (("fresh_instrumented", "fresh"), ("selective_instrumented", "selective")):
        factory, run = execution.components(method)
        actual, original = factory(), P8E.new_cache(name)
        for label, source, namespace in sequence:
            a = run(deepcopy(source), actual, namespace)
            b = P8E.run(name, deepcopy(source), original, namespace)
            a["cost"].pop("local_seconds")
            b["cost"].pop("local_seconds")
            assert a == b, (method, label, "original P08 result and all non-time cost fields")
            assert evaluator.policy_state(actual) == evaluator.policy_state(original), (method, label)
            checks.append({"method": method, "case": label, "exact_non_time_result_equal": True,
                           "exact_policy_state_equal": True})
    return checks


def evaluator_mutants():
    texts = [SET, "가람 모임 장소는 카페로 확정해줘.", "노을 모임 시간은 10시로 확정해줘.",
             "노을 모임 장소는 카페로 확정해줘."]
    source = public(texts, query="두 모임의 현재 시간을 알려줘.")
    gold = [{"kind": "set", "target": ["가람", "time"], "value": 8},
            {"kind": "set", "target": ["가람", "place"], "value": "카페"},
            {"kind": "set", "target": ["노을", "time"], "value": 10},
            {"kind": "set", "target": ["노을", "place"], "value": "카페"}]
    step = {"public": source, "gold": gold, "gold_applicable": True,
            "expected_integrity": "valid", "question_contract": {"supported": True,
                "required_fields": [["가람", "time"], ["노을", "time"]]}}
    result = P6.run(source, "text_scoped")
    assert result["status"] == "certified_model"
    valid = S7.assess(step, source, result)
    assert not any(valid[k] for k in ("schema_error", "structural_error", "false_certification", "containment_violation"))
    assert valid["selected_gold_projection_equal"] is True
    tests = [
        ("empty_certification", lambda r: r.update(prediction={})),
        ("missing_required_field", lambda r: r["prediction"].pop("노을.time")),
        ("wrong_singleton", lambda r: r["prediction"].update({"가람.time": [99]})),
        ("non_singleton_certification", lambda r: r["prediction"].update({"가람.time": [8, 99]})),
        ("wrong_scalar_type", lambda r: r["prediction"].update({"가람.time": ["8"]})),
        ("unsupported_misclassification", lambda r: r.update(status="unsupported_query", prediction={})),
        ("missing_causal_record", lambda r: r.update(selected=[2])),
        ("partial_fallback", lambda r: r.update(status="opaque_fallback", prediction={"가람.time": None, "노을.time": None}, selected=[2])),
        ("false_integrity_failure", lambda r: r.update(status="integrity_failure", prediction={}, selected=[], output_bytes=0)),
    ]
    checks = []
    for name, mutate in tests:
        bad = deepcopy(result)
        mutate(bad)
        assessed = S7.assess(step, source, bad)
        detected = (any(assessed[k] for k in ("structural_error", "schema_error", "false_certification", "containment_violation"))
                    or assessed["selected_gold_projection_equal"] is False)
        assert detected, name
        checks.append({"name": name, "detected": True})
    altered = deepcopy(step)
    altered.update({"gold": [{"invented": "future label"}], "family": "new family", "future_hits": 10000})
    assert S7.public_of(step) == S7.public_of(altered)
    return checks


def run():
    verify_sources()
    generated = erase.build()
    for name, value in generated.items():
        assert (HERE / name).read_bytes() == value, name
    deep = quote()
    source = public([SET, deep])
    edited = public([SET, deep[:-1] + "?"])
    bad_hash = deepcopy(source)
    bad_hash["records"][0]["text"] = "가람 모임 시간은 9시로 확정해줘."
    bad_order = deepcopy(source)
    bad_order["records"][1]["seq"] = 3
    bad_order["snapshot"] = P6.BASE.snapshot(bad_order["records"])
    copy = "노을 모임 시간은 가람 모임 시간과 같게 맞춰줘."
    historical = ["가람 모임 시간은 10시로 확정해줘.", copy,
                  "가람 모임 시간은 11시로 확정해줘.", deep]
    copied = public(historical, query="노을 모임은 지금 몇 시야?")
    historical[0] = "가람 모임 시간은 12시로 확정해줘."
    changed_copy = public(historical, query="노을 모임은 지금 몇 시야?")
    long_a, long_b = quote(10800, "다"), quote(11200, "라")
    collision = quote(len(deep) - len(quote(0, deep=False)), "나", deep=False)
    assert len(collision) == len(deep)
    sequence = [
        ("cold", source, NS), ("warm", source, NS),
        ("same_length_exact_edit", edited, NS), ("restore_exact", source, NS),
        ("same_length_cheap_false_positive", public([SET, collision]), NS),
        ("ordered_entities", public([SET, deep], entities=list(reversed(ENTITIES))), NS),
        ("membership", public([SET, deep], entities=ENTITIES + ["새봄"]), NS),
        ("namespace", source, NS + "-v2"),
        ("copy_before_edit", copied, NS), ("copy_after_source_edit", changed_copy, NS),
        ("proper_scope_time", public([SET, "가람 모임 장소만 다시 정해줘.", deep]), NS),
        ("proper_scope_both", public([SET, "가람 모임 장소만 다시 정해줘.", deep], query="가람 모임의 시간과 장소를 알려줘."), NS),
        ("duplicate_raw_same_query", public([SET, deep, deep]), NS),
        ("invalid_digest", bad_hash, NS), ("invalid_order", bad_order, NS),
        ("unsupported", public([SET, deep], query="왜 그 시간이야?"), NS),
        ("empty", public([]), NS),
        ("large_default_capacity_a", public([SET, long_a]), NS),
        ("large_default_capacity_b", public([SET, long_b]), NS),
        ("large_default_capacity_b_warm", public([SET, long_b]), NS),
    ]
    pairs = paired_sequence(sequence)
    known_development = json.loads((ROOT / "research/phase08/data/development.json").read_text())
    checked = evaluator.evaluate(known_development)
    assert not checked["failures"], checked["failures"][:3]
    assert not checked["exact_policy_state_mismatches"]
    original_checks = original_instrumented_identity(sequence)
    mutants = state_mutants()
    hit_counterexample = erased_hit_counterexample()
    gold_mutants = evaluator_mutants()
    return {"passed": True, "phase09_holdout_read": False,
            "erasure_source_identity": {name: hashlib.sha256(content).hexdigest() for name, content in generated.items()},
            "authored_prefix_checks": pairs,
            "authored_prefix_count": len(pairs),
            "phase08_development_queries": checked["prefixes"],
            "phase08_development_summary": checked["summary"],
            "phase08_development_observation_comparisons": checked["exact_observation_comparisons"],
            "phase08_development_execution_trace_comparisons": checked["exact_on_off_execution_trace_comparisons"],
            "state_mutants": mutants, "hit_erasure_counterexample": hit_counterexample,
            "evaluator_mutants": gold_mutants,
            "original_phase08_instrumented_identity": original_checks,
            "public_whitelist_label_independence": True,
            "failures": [],
            "boundary": "Authored same-model development audit; no primary timing, no Phase09 holdout, no external natural-language validation."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps({"passed": result["passed"], "authored_prefix_count": result["authored_prefix_count"],
                      "phase08_development_queries": result["phase08_development_queries"],
                      "state_mutants": len(result["state_mutants"]),
                      "evaluator_mutants": len(result["evaluator_mutants"]),
                      "phase09_holdout_read": result["phase09_holdout_read"]}, ensure_ascii=False))
