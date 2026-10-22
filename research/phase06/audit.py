"""Finite model, mutation, interface and minimal-counterexample checks."""
from __future__ import annotations

import copy
import itertools

import development
import evaluate
import scoped


def slice_typed(events, requested, universe):
    demand, selected = set(requested), []
    for i in range(len(events) - 1, -1, -1):
        if not demand:
            break
        if demand & scoped.writes(events[i], universe):
            selected.append(i)
            demand = scoped.preimage(events[i], demand, universe)
    return sorted(selected)


def model_audit():
    a, b = "은하", "새벽"
    universe = scoped.BASE.facts((a, b))
    ev = development.event
    prefix = [ev("set", (a, "time"), 0), ev("set", (b, "time"), 1),
              ev("set", (a, "place"), "도서관"), ev("set", (b, "place"), "공원")]
    alphabet = [ev("set", (a, "time"), 2), ev("set", (b, "time"), -1),
                ev("add", (a, "time"), 1), ev("add", (a, "time"), -1),
                ev("copy", (b, "time"), source=(a, "time")),
                ev("copy", (a, "time"), source=(b, "time")),
                ev("maybe_set", value=2, targets=[(a, "time"), (b, "time")]),
                ev("set", (a, "place"), "카페"), scoped.scoped_top({(a, "place")}),
                scoped.scoped_top({(a, "time")}), scoped.scoped_top(universe), ev("noop")]
    questions = [{(a, "time")}, {(a, "time"), (a, "place")}, {(b, "time")}, {(a, "time"), (b, "time")}]
    domains = {f: (0, 1) if f[1] == "time" else ("도서관", "공원") for f in universe}
    initial = set(itertools.product(*(domains[f] for f in universe)))
    checks = reductions = abstract_failures = concrete_failures = containment_failures = 0
    for program in itertools.product(range(len(alphabet)), repeat=3):
        events = prefix + [alphabet[i] for i in program]
        full_abstract = scoped.execute(events, universe)
        full_concrete = evaluate.exact_states(events, (a, b), initial, domains)
        for question in questions:
            requested = tuple(sorted(question))
            indices = slice_typed(events, question, universe)
            selected = [events[i] for i in indices]
            small_abstract = scoped.execute(selected, universe)
            abstract_failures += any(full_abstract[f] != small_abstract[f] for f in question)
            small_concrete = evaluate.exact_states(selected, (a, b), initial, domains)
            exact = evaluate.project(full_concrete, requested, (a, b))
            concrete_failures += exact != evaluate.project(small_concrete, requested, (a, b))
            containment_failures += any(small_abstract[f] is not None and value not in small_abstract[f]
                                        for answer in exact for f, value in zip(requested, answer))
            reductions += len(indices) < len(events)
            checks += 1
    assert abstract_failures == concrete_failures == containment_failures == 0
    assert reductions > 0
    # The prefix above resets all four coordinates: the 16-state initial SET
    # therefore becomes one full-program state, not 16 independent initial
    # conditions. Test per-input preservation separately without that prefix.
    # `domains` supplies finite havoc choices, not a closed value universe:
    # set/add operations can reach -1, 2, etc., and place set can reach cafe.
    def abstract_from_singleton(stream, initial_state):
        state = {field: frozenset((value,)) for field, value in zip(universe, initial_state)}
        for item in stream:
            state = scoped.step(state, item)
        return state

    per_input_checks = per_input_reductions = 0
    per_input_abstract_failures = per_input_concrete_failures = per_input_containment_failures = 0
    for program in itertools.product(range(len(alphabet)), repeat=2):
        events = [alphabet[i] for i in program]
        for initial_state in initial:
            full_abstract = abstract_from_singleton(events, initial_state)
            full_concrete = evaluate.exact_states(events, (a, b), {initial_state}, domains)
            for question in questions:
                requested = tuple(sorted(question))
                indices = slice_typed(events, question, universe)
                selected = [events[i] for i in indices]
                small_abstract = abstract_from_singleton(selected, initial_state)
                small_concrete = evaluate.exact_states(selected, (a, b), {initial_state}, domains)
                exact = evaluate.project(full_concrete, requested, (a, b))
                per_input_abstract_failures += any(full_abstract[f] != small_abstract[f] for f in question)
                per_input_concrete_failures += exact != evaluate.project(small_concrete, requested, (a, b))
                per_input_containment_failures += any(small_abstract[f] is not None and value not in small_abstract[f]
                                                     for answer in exact for f, value in zip(requested, answer))
                per_input_reductions += len(indices) < len(events)
                per_input_checks += 1
    assert per_input_checks == len(alphabet) ** 2 * len(initial) * len(questions)
    assert per_input_abstract_failures == per_input_concrete_failures == per_input_containment_failures == 0
    return {"operator_count": len(alphabet), "program_length": 3, "programs": len(alphabet) ** 3,
            "initial_states": len(initial), "question_sets": len(questions), "comparisons": checks,
            "reset_prefix": True, "effective_full_states_after_prefix": len(evaluate.exact_states(prefix, (a, b), initial, domains)),
            "finite_havoc_choices": {f"{e}.{field}": list(values) for (e, field), values in domains.items()},
            "havoc_choices_are_not_a_closed_value_universe": True,
            "abstract_projection_failures": abstract_failures, "concrete_projection_failures": concrete_failures,
            "containment_failures": containment_failures, "strict_record_reductions": reductions,
            "prefix_free_per_input": {"program_length": 2, "programs": len(alphabet) ** 2,
                                      "singleton_initial_states": len(initial), "question_sets": len(questions),
                                      "comparisons": per_input_checks,
                                      "abstract_projection_failures": per_input_abstract_failures,
                                      "concrete_projection_failures": per_input_concrete_failures,
                                      "containment_failures": per_input_containment_failures,
                                      "strict_record_reductions": per_input_reductions},
            "total_projection_comparisons": checks + per_input_checks,
            "nonvacuity_scope": "Record reductions here can arise from ordinary slicing; scope-specific gains are measured separately against global control in the corpus",
            "limits": "Finite typed model with scoped nondeterminism, not a language or IID evaluation"}


def mutation_audit():
    case = development.build()[0]
    public = {**case["public"], "query": case["queries"][0]}
    truth = evaluate.exact_states(case["gold"], public["entities"])
    normal = scoped.run(public)
    assert normal["status"] == "certified_model"
    key = next(iter(normal["prediction"]))
    mutations = {
        "empty_certification": {**normal, "prediction": {}},
        "wrong_value": {**normal, "prediction": {key: [999]}},
        "empty_value_list": {**normal, "prediction": {key: []}},
        "top_certified": {**normal, "prediction": {key: None}},
        "unrequested_key": {**normal, "prediction": {**normal["prediction"], "ghost.time": [8]}},
        "false_unsupported": {**normal, "status": "unsupported_query", "prediction": {}},
        "unknown_status": {**normal, "status": "nonsense"},
        "false_integrity_failure": {**normal, "status": "integrity_failure", "prediction": {}, "selected": []},
        "full_history_with_prediction": {**normal, "status": "full_history"},
        "nonmapping_prediction": {**normal, "prediction": None},
        "partial_fallback": {**normal, "status": "opaque_fallback", "prediction": {key: None}},
    }
    outcomes = {}
    for name, result in mutations.items():
        assessed = evaluate.assess(public, result, truth)
        assert assessed["schema_error"] or assessed["false_certification"] or assessed["containment_violation"], name
        outcomes[name] = assessed
    # Missing just one of two demanded fields is distinct from an empty dictionary.
    public2 = {**case["public"], "query": case["queries"][1]}
    partial = {**normal, "prediction": {key: [8]}}
    outcomes["missing_one_field"] = evaluate.assess(public2, partial, truth)
    assert outcomes["missing_one_field"]["false_certification"]
    # A honest TOP is safe but not an answer; it must not count as certified.
    top = {**normal, "status": "opaque_fallback", "prediction": {key: None},
           "selected": list(range(len(public["records"])))}
    outcomes["honest_top_control"] = evaluate.assess(public, top, truth)
    assert not outcomes["honest_top_control"]["containment_violation"]
    assert not outcomes["honest_top_control"]["false_certification"]
    return outcomes


def counterexamples():
    cases = {case["id"]: case for case in development.build()}
    # Inject a deliberately unsound may-write contract; it must cause and expose
    # a false singleton. This is not an error observed in the text-only method.
    case = cases["compound"]
    public = {**case["public"], "query": case["queries"][0]}
    universe = evaluate.fields(public["entities"])
    scopes = [evaluate.gold_writes(ev, universe) for ev in case["gold"]]
    scopes[-1] = {("은하", "place")}
    bad = scoped.run(public, "oracle_scoped", oracle_scopes=scopes)
    assessed = evaluate.assess(public, bad, evaluate.exact_states(case["gold"], public["entities"]))
    assert assessed["false_certification"] and assessed["containment_violation"]
    proper = scoped.run(public)
    assert proper["status"] == "opaque_fallback"
    # Demand for the unaffected time must survive when place becomes TOP.
    place = cases["place_disjoint"]
    partial_public = {**place["public"], "query": place["queries"][1]}
    partial = scoped.run(partial_public)
    assert partial["prediction"] == {"은하.place": None, "은하.time": [8]}
    temporal = cases["temporal_copy"]
    temporal_result = scoped.run({**temporal["public"], "query": temporal["queries"][2]})
    assert temporal_result["status"] == "opaque_fallback"
    # Information that chooses correlation is invisible in marginal read sets.
    correlated, anticorrelated = {(0, 0), (1, 1)}, {(0, 1), (1, 0)}
    marginals = lambda states: [{s[i] for s in states} for i in (0, 1)]
    assert marginals(correlated) == marginals(anticorrelated) and correlated != anticorrelated
    return {"underestimated_scope": {"records": public["records"], "query": public["query"],
                                       "bad_prediction": bad["prediction"], "bad_assessment": assessed,
                                       "text_only_status": proper["status"]},
            "partial_demand_preserved": partial["prediction"],
            "historical_copy_status": temporal_result["status"],
            "joint_correlation_counterexample": {"c0": sorted(correlated), "c1": sorted(anticorrelated),
                                                 "same_marginals": True, "same_joint": False}}


def integrity_and_interface():
    case = development.build()[0]
    public = {**case["public"], "query": case["queries"][0]}
    original = scoped.run(public)
    renamed = copy.deepcopy(public)
    for i, record in enumerate(renamed["records"]):
        record["id"] = f"unrelated-opaque-{10000-i}"
    renamed["snapshot"] = scoped.BASE.snapshot(renamed["records"])
    changed = scoped.run(renamed)
    assert (changed["status"], changed["prediction"], changed["selected"]) == (original["status"], original["prediction"], original["selected"])
    faults = {}
    for name in ("dropped", "edited", "reordered"):
        broken = copy.deepcopy(public)
        if name == "dropped":
            broken["records"].pop()
        elif name == "edited":
            broken["records"][-1]["text"] += " 수정"
        else:
            broken["records"][0], broken["records"][1] = broken["records"][1], broken["records"][0]
        faults[name] = scoped.run(broken)["status"]
    assert set(faults.values()) == {"integrity_failure"}
    try:
        scoped.run(public, "text_scoped", oracle_scopes=[])
        raise AssertionError("Oracle leaked to text method")
    except ValueError:
        pass
    # No field or semantic labels can sneak through the corpus adapter.
    poison = copy.deepcopy(case)
    poison["public"]["gold"] = "THIS MUST NEVER BE READ"
    normal_row = evaluate.evaluate_case(case, case["queries"][0], "text_scoped")
    poison_row = evaluate.evaluate_case(poison, case["queries"][0], "text_scoped")
    assert evaluate.strip_timing(normal_row) == evaluate.strip_timing(poison_row)
    return {"opaque_id_invariance": True, "snapshot_faults": faults,
            "text_only_rejects_oracle_arguments": True, "whitelisted_public_input": True}


def scope_grammar_checks():
    entities = ["은하", "새벽"]
    positive = [
        ("은하 모임 장소는 카페로 바꿔줘.", "place"),
        ("은하 모임 장소는 카페로 확정해줘. 시간은 건드리지 않아.", "place"),
        ("은하 모임 시간은 -3시로 재합의했어. 장소는 그대로야.", "time"),
        ("은하 모임 장소는 새벽 모임 장소와 같게 맞춰줘.", "place"),
        ("은하 모임 장소만 다시 정해줘.", "place"),
        ("은하 모임 시간만 다시 정해줘.", "time"),
    ]
    checks = []
    for text, field in positive:
        scope, rule = scoped.scope_from_text(text, entities)
        assert scope == {("은하", field)}
        negatives = ["이전 기록 인용: " + text,
                     text + " 아니, 그 말은 취소야.",
                     text + " 새벽 모임 시간을 한 시간 늦춰줘."]
        for negative in negatives:
            assert scoped.scope_from_text(negative, entities)[0] is None
        checks.append({"rule": rule, "positive": text, "negative_minimal_pairs": negatives})
    return {"positive_rules": len(positive), "negative_minimal_pairs": 3 * len(positive), "cases": checks,
            "boundary": "Tests full-string whitelist recognition; does not prove natural-language frame semantics"}


def run():
    return {"model": model_audit(), "evaluator_mutations": mutation_audit(),
            "counterexamples": counterexamples(), "integrity_and_interface": integrity_and_interface(),
            "scope_grammar": scope_grammar_checks()}
