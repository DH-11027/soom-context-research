"""Public development fixtures; deliberately seen before Phase08 freeze."""
from copy import deepcopy
import hashlib
import json

ENTITIES = ["가람", "누리"]


def event(kind, target=None, value=None, source=None, targets=None):
    return {"kind": kind, "target": target, "value": value, "source": source, "targets": targets or []}


def initialized():
    text, gold = [], []
    for i, entity in enumerate(ENTITIES):
        text.extend([f"{entity} 모임 시간은 {8+i}시로 확정해줘.", f"{entity} 모임 장소는 카페로 확정해줘."])
        gold.extend([event("set", [entity, "time"], 8+i), event("set", [entity, "place"], "카페")])
    return text, gold


def quote(characters, *, cheap=False, letter="가"):
    prefix, suffix = (("예시일 뿐이야:「", "」 실제 변경은 없어.") if cheap
                      else ("표현 연습:「", "」라는 문장을 써봤어. 약속은 그대로야."))
    return prefix + letter * max(0, characters - len(prefix) - len(suffix)) + suffix


def step(texts, gold, index, *, query=None, entities=None, namespace="v1", invalid=None, gold_applicable=True):
    entities = ENTITIES if entities is None else entities
    query = f"{ENTITIES[0]} 모임은 지금 몇 시야?" if query is None else query
    records = [{"id": f"dev-{i}", "seq": i, "text": t} for i, t in enumerate(texts)]
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    snapshot = {"head": len(records)-1, "digest": hashlib.sha256(raw).hexdigest()}
    if invalid == "digest":
        snapshot["digest"] = "0" * 64
    elif invalid == "seq":
        records[-1]["seq"] += 2
    table = {"두 모임의 현재 시간을 알려줘.": [[e, "time"] for e in entities]}
    for e in entities:
        table[f"{e} 모임은 지금 몇 시야?"] = [[e, "time"]]
        table[f"{e} 모임의 시간과 장소를 알려줘."] = [[e, "time"], [e, "place"]]
    req = table.get(query)
    return {"step_id": f"dev-step-{index}", "parser_namespace": namespace,
            "public": {"records": records, "entities": list(entities), "snapshot": snapshot, "query": query},
            "gold": deepcopy(gold), "gold_applicable": gold_applicable,
            "expected_integrity": "invalid" if invalid else "valid",
            "question_contract": {"supported": req is not None, "required_fields": req or []}}


def build():
    streams = []

    def add(name, steps):
        streams.append({"id": "dev-"+name, "family": name, "split": "development", "steps": steps})

    initial, gold = initialized()
    add("short_repeat", [step(initial, gold, i) for i in range(8)])
    for name, text in (("deep_repeat", quote(1600)), ("cheap_repeat", quote(1600, cheap=True))):
        add(name, [step(initial+[text], gold+[event("noop")], i) for i in range(12)])
    add("deep_one_use", [step(initial+[quote(1800)], gold+[event("noop")], 0)])
    add("length_collision", [step(initial+[quote(1600, cheap=i % 2 == 1)], gold+[event("noop")], i) for i in range(12)])
    for name, n in (("fit", 9000), ("pressure", 14000)):
        texts = initial + [quote(n), quote(n+1, letter="나")]
        add(name, [step(texts, gold+[event("noop"), event("noop")], i) for i in range(10)])
    add("stale_popular_resident", [step(initial+[quote(19000 if i < 4 else 16000, letter="가" if i < 4 else "나")],
                                       gold+[event("noop")], i) for i in range(12)])
    steps = []
    for i in range(12):
        texts, labels = deepcopy(initial), deepcopy(gold)
        texts[0] = f"가람 모임 시간은 {i+1}시로 확정해줘."
        labels[0]["value"] = i+1
        texts += ["누리 모임 시간은 가람 모임 시간과 같게 맞춰줘.", quote(1400)]
        labels += [event("copy", ["누리", "time"], source=["가람", "time"]), event("noop")]
        steps.append(step(texts, labels, i, query="누리 모임은 지금 몇 시야?" if i != 5 else "누가 약속에 왔어?",
                          namespace="v2" if i >= 6 else "v1", invalid="digest" if i == 8 else "seq" if i == 9 else None,
                          entities=list(reversed(ENTITIES)) if i == 10 else ENTITIES))
    add("state_version_integrity", steps)
    return streams
