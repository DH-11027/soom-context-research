"""Independent concrete execution check of slices, beyond corpus templates.

Checks every length-four program over nine known operators, three questions.
The product-domain approximation is NOT used to evaluate concrete outputs here.
"""

import hashlib
import itertools
import json
from pathlib import Path

import engine

HERE = Path(__file__).resolve().parent
ENTITIES = ["가람", "노을"]
FACTS = [(e, f) for e in ENTITIES for f in ("time", "place")]
POSITIONS = {f: i for i, f in enumerate(FACTS)}


def execute(events):
    states = {(None,) * len(FACTS)}
    for ev in events:
        next_states = set()
        for old in states:
            if ev["kind"] == "noop":
                next_states.add(old)
                continue
            choices = ev["targets"] if ev["kind"] == "maybe_set" else [ev["target"]]
            for target in choices:
                state = list(old)
                p = POSITIONS[tuple(target)]
                if ev["kind"] in ("set", "maybe_set"):
                    state[p] = ev["value"]
                elif ev["kind"] == "copy":
                    state[p] = old[POSITIONS[tuple(ev["source"])]]
                elif ev["kind"] == "add":
                    state[p] = None if old[p] is None else old[p] + ev["value"]
                else:
                    raise ValueError(ev["kind"])
                next_states.add(tuple(state))
        states = next_states
    return states


def alphabet():
    items = []
    for entity in ENTITIES:
        for value in (0, 1):
            items.append((f"{entity} 모임 시간은 {value}시로 확정해줘.", engine.event("set", (entity, "time"), value)))
    for target, source in (("가람", "노을"), ("노을", "가람")):
        items.append((f"{target} 모임 시간은 {source} 모임 시간과 같게 맞춰줘.", engine.event("copy", (target, "time"), source=(source, "time"))))
    for entity in ENTITIES:
        items.append((f"{entity} 모임 시간을 1시간 뒤로 옮겨줘.", engine.event("add", (entity, "time"), 1)))
    items.append(("가람 모임과 노을 모임 중 하나의 시간은 1시로 확정해줘.", engine.event("maybe_set", value=1, targets=[("가람", "time"), ("노을", "time")])))
    return items


def run():
    operators = alphabet()
    base = [
        ("가람 모임 시간은 0시로 확정해줘.", engine.event("set", ("가람", "time"), 0)),
        ("노을 모임 시간은 1시로 확정해줘.", engine.event("set", ("노을", "time"), 1)),
    ]
    queries = [("가람 모임은 지금 몇 시야?", [0]), ("노을 모임은 지금 몇 시야?", [2]), ("두 모임의 현재 시간을 알려줘.", [0, 2])]
    comparisons = 0
    for program in itertools.product(range(len(operators)), repeat=4):
        stream = base + [operators[i] for i in program]
        records = [{"seq": i, "id": f"source-{i}", "text": text} for i, (text, _) in enumerate(stream)]
        full_states = execute([ev for _, ev in stream])
        for query, columns in queries:
            outcome = engine.run({"records": records, "entities": ENTITIES, "snapshot": engine.snapshot(records), "query": query}, "lazy")
            reduced_states = execute([stream[i][1] for i in outcome["selected"]])
            projection = lambda states: {tuple(s[i] for i in columns) for s in states}
            assert projection(full_states) == projection(reduced_states), (program, query, outcome)
            assert outcome["detail_calls"] == 0
            comparisons += 1
    # Explicit counterexample to byte minimality: +1 followed by -1 cancels.
    cancellation = [base[0],
                    ("가람 모임 시간을 1시간 뒤로 옮겨줘.", engine.event("add", ("가람", "time"), 1)),
                    ("가람 모임 시간을 1시간 앞으로 옮겨줘.", engine.event("add", ("가람", "time"), -1))]
    records = [{"seq": i, "id": f"cancel-{i}", "text": text} for i, (text, _) in enumerate(cancellation)]
    public = {"records": records, "entities": ENTITIES, "snapshot": engine.snapshot(records), "query": queries[0][0]}
    result = engine.run(public)
    full = {s[0] for s in execute([ev for _, ev in cancellation])}
    short = {s[0] for s in execute([cancellation[0][1]])}
    assert full == short == {0} and result["selected"] == [0, 1, 2]
    cancellation_result = {"selected_by_slice": result["selected"], "equivalent_shorter_indices": [0],
                           "answer": 0, "slice_bytes": result["output_bytes"],
                           "shorter_bytes": len(engine.render(records, [0], public["query"], public["snapshot"], "certified_model").encode("utf-8")),
                           "interpretation": "Dependency slicing preserves outputs but is not minimum-byte optimization. Removing a single relative update alone would change the answer."}
    # Hashes attest frozen study files, not the validity of language semantics.
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    for name, expected in protocol["hashes"].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected
    result = {"programs": len(operators) ** 4, "questions_per_program": 3,
              "concrete_projection_comparisons": comparisons, "all_equal": True,
              "minimum_byte_counterexample": cancellation_result,
              "frozen_hashes_match": True,
              "limits": "Finite controlled operators; separate concrete evaluator by same author. Does not certify natural-language parsing."}
    (HERE / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
