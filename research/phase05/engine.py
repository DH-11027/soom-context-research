"""Offline query-directed backward slicing with conservative text refinement.

The finite grammar describes PLAN values, not execution in the real world.
Unknown language is havoc, never evidence that a message is irrelevant.
No gold labels, fixture imports, model/API calls, production paths or I/O.
"""

import hashlib
import json
import re

VERSION = "research-05.1"
NOOPS = {
    "다른 이야기: 오늘은 구름 사진을 찍었어.",
    "다른 이야기: 책에서 정원에 관한 글을 읽었어.",
}
DEEP_NOOPS = {
    "참고로 남기는 감상이야. 오늘 하늘빛이 참 맑았어.",
    "책갈피 색을 골라 봤어. 일정 계획에 관한 말은 아니야.",
}


def event(kind, target=None, value=None, source=None, targets=None):
    return {"kind": kind, "target": target, "value": value,
            "source": source, "targets": targets or []}


def facts(entities):
    return tuple((entity, field) for entity in entities for field in ("time", "place"))


def parse(text, entities, deep=False):
    """Full-string recognition; default is a conservative universal effect."""
    names = "(?:" + "|".join(re.escape(e) for e in entities) + ")"
    if text in NOOPS or (deep and text in DEEP_NOOPS):
        return event("noop")
    match = re.fullmatch(fr"({names}) 모임 시간은 (-?\d+)시로 확정해줘\.", text)
    if match:
        return event("set", (match[1], "time"), int(match[2]))
    match = re.fullmatch(fr"({names}) 모임 장소는 (도서관|공원|카페)로 확정해줘\.", text)
    if match:
        return event("set", (match[1], "place"), match[2])
    match = re.fullmatch(fr"({names}) 모임 시간을 (\d+)시간 (뒤|앞)로 옮겨줘\.", text)
    if match:
        return event("add", (match[1], "time"), int(match[2]) * (1 if match[3] == "뒤" else -1))
    match = re.fullmatch(fr"({names}) 모임 시간은 ({names}) 모임 시간과 같게 맞춰줘\.", text)
    if match:
        return event("copy", (match[1], "time"), source=(match[2], "time"))
    match = re.fullmatch(fr"({names}) 모임과 ({names}) 모임 중 하나의 시간은 (-?\d+)시로 확정해줘\.", text)
    if match:
        return event("maybe_set", value=int(match[3]), targets=[(match[1], "time"), (match[2], "time")])
    if re.fullmatch(r"예시일 뿐이야:「[^\n]*」 실제 변경은 없어\.", text):
        return event("noop")
    if deep:
        match = re.fullmatch(fr"({names}) 약속, 최종 시각은 (-?\d+)시로 적어둘게\.", text)
        if match:
            return event("set", (match[1], "time"), int(match[2]))
        match = re.fullmatch(fr"({names}) 약속을 지금보다 한 시간 늦추자\.", text)
        if match:
            return event("add", (match[1], "time"), 1)
        match = re.fullmatch(fr"({names}) 약속 장소는 (도서관|공원|카페)로 적어둘게\.", text)
        if match:
            return event("set", (match[1], "place"), match[2])
        if re.fullmatch(r"표현 연습:「[^\n]*」라는 문장을 써봤어\. 약속은 그대로야\.", text):
            return event("noop")
    return event("havoc")


def parse_query(query, entities):
    names = "(?:" + "|".join(re.escape(e) for e in entities) + ")"
    match = re.fullmatch(fr"({names}) 모임은 지금 몇 시야\?", query)
    if match:
        return {(match[1], "time")}
    match = re.fullmatch(fr"({names}) 모임의 시간과 장소를 알려줘\.", query)
    if match:
        return {(match[1], "time"), (match[1], "place")}
    if query == "두 모임의 현재 시간을 알려줘.":
        return {(e, "time") for e in entities}
    return None


def writes(ev, universe):
    if ev["kind"] == "havoc":
        return set(universe)
    if ev["kind"] == "maybe_set":
        return set(ev["targets"])
    return {ev["target"]} if ev["target"] else set()


def preimage(ev, demand, universe):
    """Which input facts can affect the demanded output facts?"""
    kind = ev["kind"]
    hit = demand & writes(ev, universe)
    if not hit:
        return set(demand)
    if kind == "havoc":
        return set()  # Overapproximation: all outputs arbitrary; cannot certify.
    if kind in ("add", "maybe_set"):
        return set(demand)
    result = demand - hit
    if kind == "copy":
        result.add(ev["source"])
    return result


def interpret(events, universe):
    """Product powerset abstraction. None is TOP; correlations are discarded."""
    state = {f: None for f in universe}
    for ev in events:
        kind, target = ev["kind"], ev["target"]
        if kind == "havoc":
            state = {f: None for f in universe}
        elif kind == "set":
            state[target] = frozenset((ev["value"],))
        elif kind == "copy":
            state[target] = state[ev["source"]]
        elif kind == "add":
            old = state[target]
            state[target] = None if old is None else frozenset(x + ev["value"] for x in old)
        elif kind == "maybe_set":
            for f in ev["targets"]:
                if state[f] is not None:
                    state[f] = state[f] | {ev["value"]}
    return state


def history_digest(records):
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def snapshot(records):
    return {"head": len(records) - 1, "digest": history_digest(records)}


def validate(records, expected):
    if [r["seq"] for r in records] != list(range(expected["head"] + 1)):
        return "record_gap_or_order"
    if history_digest(records) != expected["digest"]:
        return "snapshot_mismatch"
    return None


def render(records, indices, query, expected, status):
    # Receipt cost counts. Hash establishes byte identity, NOT semantic truth.
    header = f"[연구 {VERSION}; 범위=0..{expected['head']}; sha256={expected['digest']}; 판정={status}]\n"
    return header + f"현재 질문: {query}\n" + "".join(f"[기록 {i}] {records[i]['text']}\n" for i in sorted(indices))


def run(public, mode="lazy"):
    records, entities, query = public["records"], public["entities"], public["query"]
    expected = public["snapshot"]
    error = validate(records, expected)
    if error:
        return {"status": "integrity_failure", "reason": error, "prediction": {}, "selected": [],
                "cheap_reads": 0, "detail_calls": 0, "detail_source_bytes": 0, "output_bytes": 0}
    universe = facts(entities)
    requested = parse_query(query, entities)
    calls, detail_bytes, cheap_reads = 0, 0, 0
    cache = {}

    def read(i, detailed=False):
        nonlocal calls, detail_bytes, cheap_reads
        if i not in cache:
            cache[i] = parse(records[i]["text"], entities)
            cheap_reads += 1
        if detailed and cache[i]["kind"] == "havoc":
            cache[i] = parse(records[i]["text"], entities, deep=True)
            calls += 1
            detail_bytes += len(records[i]["text"].encode("utf-8"))
        return cache[i]

    if requested is None:
        selected = list(range(len(records)))
        output = render(records, selected, query, expected, "unsupported_query")
        return {"status": "unsupported_query", "prediction": {}, "selected": selected,
                "cheap_reads": 0, "detail_calls": 0, "detail_source_bytes": 0,
                "output_bytes": len(output.encode("utf-8"))}
    if mode == "eager":
        for i in range(len(records)):
            read(i, detailed=True)
    if mode not in ("eager", "lazy", "cheap", "drop_unknown"):
        raise ValueError(mode)
    demand, selected = set(requested), []
    for i in range(len(records) - 1, -1, -1):
        if not demand:
            break
        ev = read(i, detailed=mode == "lazy")
        if mode == "drop_unknown" and ev["kind"] == "havoc":
            ev = event("noop")
            cache[i] = ev
        if demand & writes(ev, universe):
            selected.append(i)
            demand = preimage(ev, demand, universe)
    selected.sort()
    abstract = interpret([cache[i] for i in selected], universe)
    unknown = any(cache[i]["kind"] == "havoc" for i in selected)
    certified = all(abstract[f] is not None and len(abstract[f]) == 1 for f in requested)
    status = "certified_model" if certified else "opaque_fallback" if unknown or demand else "ambiguous"
    if status == "opaque_fallback":
        # No semantic compactness claim is made when a relevant opaque event remains.
        selected = list(range(len(records)))
    prediction = {f"{f[0]}.{f[1]}": None if abstract[f] is None else sorted(abstract[f], key=repr) for f in sorted(requested)}
    output = render(records, selected, query, expected, status)
    return {"status": status, "prediction": prediction, "selected": selected,
            "cheap_reads": cheap_reads, "detail_calls": calls, "detail_source_bytes": detail_bytes,
            "output_bytes": len(output.encode("utf-8")), "remaining_input_facts": sorted(demand)}
