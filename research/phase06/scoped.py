"""Query-directed scoped TOP, research only. No gold or fixture imports.

The scope grammar supplies only may-write sets, never new exact values.
Its soundness is conditional on the controlled-language frame semantics.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from time import perf_counter

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("phase06_frozen_engine", HERE.parent / "phase05/revision02/engine.py")
BASE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BASE)
VERSION = "research-06.0"
METHODS = ("full_history", "frozen_lazy", "global_control", "text_scoped", "text_scoped_eager", "oracle_scoped")


def scope_from_text(text, entities):
    """Return (may_write, rule) or (None, 'global'). Full-string whitelist.

    None denotes the whole public field universe. No substring heuristics,
    extracted value, implied alias, quoted commands, or guessed negation.
    """
    names = "(?:" + "|".join(re.escape(e) for e in entities) + ")"
    patterns = (
        (fr"({names}) 모임 장소는 (?:도서관|공원|카페)로 바꿔줘\.", "place", "place_replace"),
        (fr"({names}) 모임 장소는 (?:도서관|공원|카페)로 확정해줘\. 시간은 건드리지 않아\.", "place", "place_frame"),
        (fr"({names}) 모임 시간은 -?\d+시로 재합의했어\. 장소는 그대로야\.", "time", "time_frame"),
        (fr"({names}) 모임 장소는 {names} 모임 장소와 같게 맞춰줘\.", "place", "place_copy"),
        (fr"({names}) 모임 장소만 다시 정해줘\.", "place", "place_undetermined"),
        (fr"({names}) 모임 시간만 다시 정해줘\.", "time", "time_undetermined"),
    )
    for pattern, field, rule in patterns:
        found = re.fullmatch(pattern, text)
        if found:
            return frozenset(((found[1], field),)), rule
    return None, "global"


def scoped_top(writes):
    return {"kind": "scoped_top", "scope": frozenset(writes)}


def writes(ev, universe):
    return set(ev["scope"]) if ev["kind"] == "scoped_top" else BASE.writes(ev, universe)


def preimage(ev, demand, universe):
    if ev["kind"] == "scoped_top":
        return set(demand) - ev["scope"]
    return BASE.preimage(ev, demand, universe)


def step(state, ev):
    """One abstract product transfer, including localized forgetting."""
    result = dict(state)
    kind = ev["kind"]
    if kind in ("havoc", "scoped_top"):
        for field in state if kind == "havoc" else ev["scope"]:
            result[field] = None
    elif kind == "set":
        result[ev["target"]] = frozenset((ev["value"],))
    elif kind == "copy":
        result[ev["target"]] = state[ev["source"]]
    elif kind == "add":
        old = state[ev["target"]]
        result[ev["target"]] = None if old is None else frozenset(x + ev["value"] for x in old)
    elif kind == "maybe_set":
        for field in ev["targets"]:
            if state[field] is not None:
                result[field] = state[field] | {ev["value"]}
    elif kind != "noop":
        raise ValueError(kind)
    return result


def execute(events, universe):
    state = {f: None for f in universe}
    for ev in events:
        state = step(state, ev)
    return state


def render(public, indices, status):
    expected = public["snapshot"]
    return (f"[연구 {VERSION}; 범위=0..{expected['head']}; sha256={expected['digest']}; 판정={status}]\n"
            + f"현재 질문: {public['query']}\n"
            + "".join(f"[기록 {i}] {public['records'][i]['text']}\n" for i in sorted(indices)))


def new_cost(public):
    return {"hash_serialized_bytes": 0, "hash_calls": 0,
            "records_visited": 0, "cheap_calls": 0, "cheap_source_bytes": 0,
            "contract_calls": 0, "contract_source_bytes": 0,
            "detail_calls": 0, "detail_source_bytes": 0,
            "reparse_calls": 0, "reparse_source_bytes": 0,
            "abstract_steps": 0, "oracle_metadata_fields": 0,
            "oracle_annotation_cost_measured": False}


def counted_digest(records, cost):
    serialized = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    cost["hash_serialized_bytes"] += len(serialized)
    cost["hash_calls"] += 1
    return hashlib.sha256(serialized).hexdigest()


def validate(public, cost):
    records, expected = public["records"], public["snapshot"]
    if [r["seq"] for r in records] != list(range(expected["head"] + 1)):
        return "record_gap_or_order"
    if counted_digest(records, cost) != expected["digest"]:
        return "snapshot_mismatch"
    return None


def finish(result, cost, start):
    cost["source_work_bytes"] = sum(cost[k] for k in (
        "hash_serialized_bytes", "cheap_source_bytes", "contract_source_bytes", "detail_source_bytes", "reparse_source_bytes"))
    cost["output_plus_source_work_proxy"] = result["output_bytes"] + cost["source_work_bytes"]
    cost["local_seconds"] = perf_counter() - start
    result["cost"] = cost
    return result


def frozen(public):
    """Call unchanged frozen algorithm; instrument parse invocations in memory.

    Identical JSON/SHA semantics are instrumented without an extra serialization.
    Validation, parsing, inference and rendering run within the timed section.
    This synchronous helper must not be invoked concurrently in one interpreter.
    """
    cost = new_cost(public)
    original = BASE.parse
    original_interpret = BASE.interpret
    original_digest = BASE.history_digest
    visited = 0

    def counted(text, entities, deep=False):
        nonlocal visited
        prefix = "detail" if deep else "cheap"
        cost[prefix + "_calls"] += 1
        cost[prefix + "_source_bytes"] += len(text.encode("utf-8"))
        if not deep:
            visited += 1
        return original(text, entities, deep)

    def counted_interpret(events, universe):
        cost["abstract_steps"] += len(events)
        return original_interpret(events, universe)

    start = perf_counter()
    BASE.parse = counted
    BASE.interpret = counted_interpret
    BASE.history_digest = lambda records: counted_digest(records, cost)
    try:
        result = BASE.run(public, "lazy")
    finally:
        BASE.parse = original
        BASE.interpret = original_interpret
        BASE.history_digest = original_digest
    cost["records_visited"] = visited
    result["scope_trace"] = []
    return finish(result, cost, start)


def run(public, method="text_scoped", *, oracle_scopes=None):
    if method not in METHODS:
        raise ValueError(method)
    if method != "oracle_scoped" and oracle_scopes is not None:
        raise ValueError("Oracle annotations are forbidden for text-only methods")
    if method == "oracle_scoped" and oracle_scopes is None:
        raise ValueError("Oracle method requires explicit gold may-write annotations")
    if method == "frozen_lazy":
        return frozen(public)
    cost = new_cost(public)
    start = perf_counter()
    records, entities = public["records"], public["entities"]
    error = validate(public, cost)
    if error:
        return finish({"status": "integrity_failure", "reason": error, "prediction": {},
                       "selected": [], "output_bytes": 0, "scope_trace": []}, cost, start)
    requested = BASE.parse_query(public["query"], entities)
    if method == "full_history" or requested is None:
        status = "full_history" if method == "full_history" else "unsupported_query"
        selected = list(range(len(records)))
        return finish({"status": status, "prediction": {}, "selected": selected,
                       "output_bytes": len(render(public, selected, status).encode("utf-8")),
                       "scope_trace": []}, cost, start)

    universe = BASE.facts(entities)
    cache, trace = {}, []

    def read(index, demand):
        if index in cache:
            return cache[index]
        text = records[index]["text"]
        size = len(text.encode("utf-8"))
        cost["records_visited"] += 1
        cost["cheap_calls"] += 1
        cost["cheap_source_bytes"] += size
        ev = BASE.parse(text, entities)
        if ev["kind"] == "havoc":
            if method == "oracle_scoped":
                w = frozenset(tuple(x) for x in oracle_scopes[index])
                cost["oracle_metadata_fields"] += len(w)
                if not w <= set(universe):
                    raise ValueError("Oracle scope outside public universe")
                rule = "oracle"
            else:
                cost["contract_calls"] += 1
                cost["contract_source_bytes"] += size
                known, rule = scope_from_text(text, entities)
                w = frozenset(universe) if known is None else known
                if method == "global_control":
                    w = frozenset(universe)
            relevant = bool(set(demand) & w)
            trace.append({"index": index, "rule": rule, "may_write": [list(f) for f in sorted(w)],
                          "proper_scope": len(w) < len(universe), "detail_avoided": not relevant})
            if relevant:
                cost["detail_calls"] += 1
                cost["detail_source_bytes"] += size
                ev = BASE.parse(text, entities, deep=True)
            if ev["kind"] == "havoc":
                ev = scoped_top(w)
        cache[index] = ev
        return ev

    if method == "text_scoped_eager":
        for index in range(len(records)):
            read(index, universe)
    demand, selected = set(requested), []
    for index in range(len(records) - 1, -1, -1):
        if not demand:
            break
        ev = read(index, demand)
        if demand & writes(ev, universe):
            selected.append(index)
            demand = preimage(ev, demand, universe)
    selected.sort()
    abstract = execute((cache[index] for index in selected), universe)
    cost["abstract_steps"] = len(selected)
    unresolved = any(cache[index]["kind"] in ("havoc", "scoped_top") for index in selected)
    certified = all(abstract[f] is not None and len(abstract[f]) == 1 for f in requested)
    status = "certified_model" if certified else "opaque_fallback" if unresolved or demand else "ambiguous"
    if status == "opaque_fallback":
        selected = list(range(len(records)))
    prediction = {f"{f[0]}.{f[1]}": None if abstract[f] is None else sorted(abstract[f], key=repr)
                  for f in sorted(requested)}
    return finish({"status": status, "prediction": prediction, "selected": selected,
                   "output_bytes": len(render(public, selected, status).encode("utf-8")),
                   "remaining_input_facts": sorted(demand), "scope_trace": trace}, cost, start)
