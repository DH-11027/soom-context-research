"""Post-diagnostic algorithm extension; freeze before its own evaluation.

Uses a new algebraic operator space. Not a blind natural-language holdout.
"""

import hashlib
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import audit
import engine
import reducer

HERE = Path(__file__).resolve().parent


def sha(name):
    return hashlib.sha256((HERE / name).read_bytes()).hexdigest()


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def freeze():
    if (HERE / "reduction_protocol.json").exists():
        raise SystemExit("Do not overwrite the extension freeze.")
    dump("reduction_protocol.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "trigger": "Observed morphology defect in ../reduction_diagnosis.json; corrected 앞으로 recognition and added non-vacuity assertions",
        "scope": "Minimum-byte subset of integer shifts in blocks with no other reads/writes of that fact; keep copies and all other barriers",
        "algorithm": "Exact signed-sum dynamic programming per independent block",
        "planned_checks": ["Every 4-operator program over 11 operators, 3 questions", "Every shift block of length 1..5 over -2,-1,1,2 versus all subsets", "No joining across an intermediate copy read", "Known operators round-trip as exact intended semantics", "Cancellation must be certified and strictly reduced", "At least one enumerated reduction must occur", "Reuse primary corpus as a posthoc regression, not fresh quality evaluation"],
        "limits": "Optimal inside each eligible block only; no global optimum or LLM quality claim; source reparse overhead counted",
        "hashes": {name: sha(name) for name in ("reducer.py", "reduction_study.py", "engine.py", "audit.py")},
    })
    print("extension frozen")


def public_from(stream, query):
    records = [{"seq": i, "id": f"typed-{i}", "text": text} for i, (text, _) in enumerate(stream)]
    return {"records": records, "entities": audit.ENTITIES, "snapshot": engine.snapshot(records), "query": query}


def run():
    protocol = json.loads((HERE / "reduction_protocol.json").read_text(encoding="utf-8"))
    for name, value in protocol["hashes"].items():
        assert sha(name) == value
    operators = audit.alphabet()
    for entity in audit.ENTITIES:
        operators.append((f"{entity} 모임 시간을 1시간 앞으로 옮겨줘.", engine.event("add", (entity, "time"), -1)))
    base = [("가람 모임 시간은 0시로 확정해줘.", engine.event("set", ("가람", "time"), 0)), ("노을 모임 시간은 1시로 확정해줘.", engine.event("set", ("노을", "time"), 1))]
    for text, expected in operators:
        assert engine.parse(text, audit.ENTITIES) == expected, text
    cancellation = [base[0], operators[6], operators[9]]
    cancelled_public = public_from(cancellation, "가람 모임은 지금 몇 시야?")
    cancelled = reducer.run(cancelled_public)
    assert cancelled["base"]["status"] == "certified_model"
    assert cancelled["base"]["selected"] == [0, 1, 2]
    assert cancelled["selected"] == [0]
    assert cancelled["output_bytes"] < cancelled["base"]["output_bytes"]
    queries = [("가람 모임은 지금 몇 시야?", [0]), ("노을 모임은 지금 몇 시야?", [2]), ("두 모임의 현재 시간을 알려줘.", [0, 2])]
    compared, improved, before, after = 0, 0, 0, 0
    examples = []
    for program in itertools.product(range(len(operators)), repeat=4):
        stream = base + [operators[i] for i in program]
        full_states = audit.execute([ev for _, ev in stream])
        for query, columns in queries:
            public = public_from(stream, query)
            result = reducer.run(public)
            reduced_states = audit.execute([stream[i][1] for i in result["selected"]])
            project = lambda states: {tuple(s[i] for i in columns) for s in states}
            assert project(full_states) == project(reduced_states)
            assert result["output_bytes"] <= result["base"]["output_bytes"]
            improved += result["output_bytes"] < result["base"]["output_bytes"]
            compared += 1
            before += result["base"]["output_bytes"]
            after += result["output_bytes"]
            if result["output_bytes"] < result["base"]["output_bytes"] and len(examples) < 4:
                examples.append({"records": public["records"], "query": query,
                                 "before_indices": result["base"]["selected"], "after_indices": result["selected"],
                                 "before_bytes": result["base"]["output_bytes"], "after_bytes": result["output_bytes"], "blocks": result["blocks"]})
    dp_checks = 0
    for size in range(1, 6):
        for deltas in itertools.product((-2, -1, 1, 2), repeat=size):
            block = [(i, delta, 60 + 3 * i + abs(delta)) for i, delta in enumerate(deltas)]
            answer = reducer.minimum_subset(block)
            candidates = []
            for mask in range(1 << size):
                subset = [item for i, item in enumerate(block) if mask & (1 << i)]
                if sum(x[1] for x in subset) == sum(deltas):
                    candidates.append((sum(x[2] for x in subset), tuple(x[0] for x in subset)))
            assert (answer["cost"], tuple(answer["selected"])) == min(candidates)
            dp_checks += 1
    # Intermediate read: B observes A after +1, before -1; no cross-read cancellation.
    middle_read = base + [operators[6], ("노을 모임 시간은 가람 모임 시간과 같게 맞춰줘.", engine.event("copy", ("노을", "time"), source=("가람", "time"))), operators[9]]
    public = public_from(middle_read, queries[2][0])
    guarded = reducer.run(public)
    assert guarded["selected"] == guarded["base"]["selected"]
    # Original corpus is posthoc regression only, including duplicate detailed parsing.
    corpus = json.loads((HERE.parent / "corpus.json").read_text(encoding="utf-8"))
    regression = {"queries": 0, "strictly_smaller": 0, "extra_detail_calls": 0, "extra_detail_source_bytes": 0}
    for case in corpus:
        for query in case["queries"]:
            result = reducer.run({**case["public"], "query": query})
            regression["queries"] += 1
            regression["strictly_smaller"] += result["output_bytes"] < result["base"]["output_bytes"]
            regression["extra_detail_calls"] += result["extra_detail_calls"]
            regression["extra_detail_source_bytes"] += result["extra_detail_source_bytes"]
    assert improved > 0, "Preservation without exercising reduction is insufficient validation"
    result = {"operator_programs": len(operators) ** 4, "concrete_projection_comparisons": compared,
              "all_outputs_preserved": True, "strictly_smaller_queries": improved,
              "before_total_bytes": before, "after_total_bytes": after,
              "additional_output_byte_reduction_percent": 100 * (1 - after / before),
              "exact_subset_dp_checks": dp_checks, "intermediate_read_barrier_preserved": True,
              "operator_round_trips": len(operators), "certified_cancellation_reduced": True,
              "cancellation_example": {"before_bytes": cancelled["base"]["output_bytes"], "after_bytes": cancelled["output_bytes"], "base_status": cancelled["base"]["status"], "prediction": cancelled["base"]["prediction"]},
              "posthoc_original_corpus_regression": regression, "examples": examples,
              "limits": "Enumerated algebraic programs with a fixed initial state, not an independently sampled language test; restricted optimality only"}
    dump("reduction_results.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "examples"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["--freeze"]:
        freeze()
    elif sys.argv[1:] == ["--run"]:
        run()
    else:
        raise SystemExit("Use --freeze or --run")
