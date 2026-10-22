"""Independent gold interpreter and strict answer-contract evaluator.

Gold is read here, never imported by scoped.py. Full-history returns raw
evidence, not a fabricated prediction. No statistical independence assumption.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path
from statistics import mean

import scoped


def fields(entities):
    return tuple((e, name) for e in entities for name in ("time", "place"))


def requested_fields(query, entities):
    """Evaluator contract by exact string table, independent of parser regex."""
    table = {"두 모임의 현재 시간을 알려줘.": tuple((e, "time") for e in entities)}
    for e in entities:
        table[f"{e} 모임은 지금 몇 시야?"] = ((e, "time"),)
        table[f"{e} 모임의 시간과 장소를 알려줘."] = ((e, "time"), (e, "place"))
    return table.get(query)


def advance(states, ev, positions, finite_domains=None):
    """Exact joint branch interpreter; supports evaluator-only compound events."""
    kind = ev["kind"]
    if kind == "sequence":
        for child in ev["events"]:
            states = advance(states, child, positions, finite_domains)
        return states
    if kind == "noop":
        return states
    result = set()
    for state in states:
        if kind in ("havoc", "scoped_top"):
            assert finite_domains is not None
            targets = list(positions) if kind == "havoc" else [tuple(f) for f in ev["scope"]]
            for chosen in itertools.product(*(finite_domains[f] for f in targets)):
                new = list(state)
                for f, value in zip(targets, chosen):
                    new[positions[f]] = value
                result.add(tuple(new))
            continue
        targets = ev["targets"] if kind == "maybe_set" else [ev["target"]]
        for target in targets:
            new = list(state)
            index = positions[tuple(target)]
            if kind in ("set", "maybe_set"):
                new[index] = ev["value"]
            elif kind == "copy":
                new[index] = state[positions[tuple(ev["source"])]]
            elif kind == "add":
                # None is an uninitialized diagnostic marker, not an arbitrary
                # finite gold value. Every corpus full history initializes all fields.
                new[index] = None if state[index] is None else state[index] + ev["value"]
            else:
                raise ValueError(kind)
            result.add(tuple(new))
    return result


def exact_states(events, entities, initial=None, finite_domains=None):
    universe = fields(entities)
    positions = {f: i for i, f in enumerate(universe)}
    states = {tuple(None for _ in universe)} if initial is None else set(initial)
    for ev in events:
        states = advance(states, ev, positions, finite_domains)
    return states


def project(states, requested, entities):
    universe = fields(entities)
    positions = [universe.index(f) for f in requested]
    return {tuple(state[i] for i in positions) for state in states}


def gold_writes(ev, universe):
    if ev["kind"] == "sequence":
        return set().union(*(gold_writes(child, universe) for child in ev["events"]))
    if ev["kind"] == "noop":
        return set()
    if ev["kind"] == "maybe_set":
        return {tuple(f) for f in ev["targets"]}
    if ev["kind"] == "havoc":
        return set(universe)
    if ev["kind"] == "scoped_top":
        return {tuple(f) for f in ev["scope"]}
    return {tuple(ev["target"])}


def assess(public, result, gold_states):
    """Never iterate only the keys returned by the system under test."""
    requested = requested_fields(public["query"], public["entities"])
    status = result["status"]
    expected = set() if requested is None else {f"{e}.{f}" for e, f in requested}
    prediction = result["prediction"]
    raw_only = status in ("full_history", "integrity_failure")
    allowed = {"certified_model", "ambiguous", "opaque_fallback", "unsupported_query", "full_history", "integrity_failure"}
    schema_error = status not in allowed or not isinstance(prediction, dict)
    if not isinstance(prediction, dict):
        prediction = {}
    serialized = json.dumps(public["records"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    valid_snapshot = ([r["seq"] for r in public["records"]] == list(range(public["snapshot"]["head"] + 1))
                      and hashlib.sha256(serialized).hexdigest() == public["snapshot"]["digest"])
    schema_error |= (status == "integrity_failure") == valid_snapshot
    if raw_only:
        schema_error |= bool(prediction)
    if status in ("full_history", "opaque_fallback", "unsupported_query"):
        schema_error |= result["selected"] != list(range(len(public["records"])))
    containment = None
    false_cert = False
    gold_singleton = None
    gold_projection = None
    if requested is None:
        schema_error |= status not in ("unsupported_query", "full_history", "integrity_failure") or bool(prediction)
        false_cert = status == "certified_model"
    else:
        gold_projection = project(gold_states, requested, public["entities"])
        gold_singleton = len(gold_projection) == 1
        if not raw_only:
            schema_error |= set(prediction) != expected or status == "unsupported_query"
            for key in expected & set(prediction):
                values = prediction[key]
                if values is not None and (not isinstance(values, list) or not values):
                    schema_error = True
                elif values is not None:
                    field_type = int if key.endswith(".time") else str
                    schema_error |= any(type(value) is not field_type for value in values)
            if status == "certified_model":
                schema_error |= any(not isinstance(prediction.get(key), list) or len(prediction[key]) != 1 for key in expected)
            containment = not schema_error
            if containment:
                for answer in gold_projection:
                    for field, value in zip(requested, answer):
                        values = prediction[f"{field[0]}.{field[1]}"]
                        if values is not None and value not in values:
                            containment = False
            if status == "certified_model":
                claimed = None if schema_error else tuple(prediction[f"{e}.{f}"][0] for e, f in requested)
                false_cert = schema_error or gold_projection != {claimed}
    return {"supported": requested is not None, "schema_error": bool(schema_error),
            "false_certification": bool(false_cert),
            "containment_violation": None if containment is None else not containment,
            "gold_singleton": gold_singleton,
            "gold_joint_answer_count": None if gold_projection is None else len(gold_projection)}


def evaluate_case(case, query, method):
    # Explicit whitelist: adding labels to `case` never changes selector input.
    public = {k: copy.deepcopy(case["public"][k]) for k in ("records", "entities", "snapshot")}
    public["query"] = query
    kwargs = {}
    if method == "oracle_scoped":
        kwargs["oracle_scopes"] = [sorted(gold_writes(ev, fields(public["entities"]))) for ev in case["gold"]]
    result = scoped.run(public, method, **kwargs)
    truth = exact_states(case["gold"], public["entities"])
    assessed = assess(public, result, truth)
    req = requested_fields(query, public["entities"])
    selected = result["selected"]
    if sorted(set(selected)) != selected or any(i < 0 or i >= len(case["gold"]) for i in selected):
        assessed["schema_error"] = True
        evidence_equal = False
    elif req is not None:
        selected_truth = exact_states([case["gold"][i] for i in selected], public["entities"])
        evidence_equal = project(truth, req, public["entities"]) == project(selected_truth, req, public["entities"])
    else:
        evidence_equal = selected == list(range(len(case["gold"])))
    full_bytes = len(scoped.render(public, range(len(public["records"])), "full_history").encode("utf-8"))
    return {"case_id": case["id"], "family": case["family"], "split": case["split"],
            "query": query, "method": method, **result, **assessed,
            "selected_gold_projection_equal": evidence_equal,
            "records": len(public["records"]), "full_bytes": full_bytes,
            "actual_full_history": selected == list(range(len(public["records"])))}


def summarize(rows):
    counts = Counter(r["status"] for r in rows)
    supported = [r for r in rows if r["supported"]]
    single = [r for r in supported if r["gold_singleton"]]
    out = sum(r["output_bytes"] for r in rows)
    full = sum(r["full_bytes"] for r in rows)
    total_cost = {key: sum(r["cost"][key] for r in rows) for key in (
        "hash_serialized_bytes", "hash_calls", "records_visited", "cheap_calls", "cheap_source_bytes",
        "contract_calls", "contract_source_bytes", "detail_calls", "detail_source_bytes",
        "reparse_calls", "reparse_source_bytes", "abstract_steps", "source_work_bytes", "output_plus_source_work_proxy",
        "oracle_metadata_fields")}
    return {"queries": len(rows), "histories": len({r["case_id"] for r in rows}),
            "supported_queries": len(supported), "unsupported_queries": len(rows) - len(supported),
            "status_counts": dict(counts), "schema_errors": sum(r["schema_error"] for r in rows),
            "false_certifications": sum(r["false_certification"] for r in rows),
            "containment_violations": sum(r["containment_violation"] is True for r in rows),
            "containment_evaluated": sum(r["containment_violation"] is not None for r in rows),
            "certification_coverage": counts["certified_model"] / len(rows),
            "gold_singleton_supported": len(single),
            "certified_gold_singleton": sum(r["status"] == "certified_model" for r in single),
            "gold_singleton_certification_recall": sum(r["status"] == "certified_model" for r in single) / len(single) if single else None,
            "gold_ambiguous_supported": sum(not r["gold_singleton"] for r in supported),
            "analysis_ambiguity_on_gold_singleton": sum(r["status"] == "ambiguous" for r in single),
            "actual_full_history_queries": sum(r["actual_full_history"] for r in rows),
            "strict_source_reductions_vs_full": sum(len(r["selected"]) < r["records"] for r in rows),
            "selected_gold_projection_failures": sum(not r["selected_gold_projection_equal"] for r in rows),
            "proper_scope_events": sum(t["proper_scope"] for r in rows for t in r["scope_trace"]),
            "scoped_detail_avoided": sum(t["proper_scope"] and t["detail_avoided"] for r in rows for t in r["scope_trace"]),
            "output_bytes": out, "full_output_bytes": full,
            "output_reduction_vs_full_percent": 100 * (1 - out / full),
            "cost": total_cost}


def compare(rows, new="text_scoped", base="frozen_lazy"):
    pair = {}
    for row in rows:
        if row["method"] in (new, base):
            pair.setdefault((row["case_id"], row["query"]), {})[row["method"]] = row
    pairs = list(pair.values())
    before = sum(p[base]["output_bytes"] for p in pairs)
    after = sum(p[new]["output_bytes"] for p in pairs)
    pb = sum(p[base]["cost"]["output_plus_source_work_proxy"] for p in pairs)
    pn = sum(p[new]["cost"]["output_plus_source_work_proxy"] for p in pairs)
    return {"new": new, "base": base, "paired_queries": len(pairs),
            "strict_output_reductions": sum(p[new]["output_bytes"] < p[base]["output_bytes"] for p in pairs),
            "strict_record_reductions": sum(len(p[new]["selected"]) < len(p[base]["selected"]) for p in pairs),
            "output_increases": sum(p[new]["output_bytes"] > p[base]["output_bytes"] for p in pairs),
            "new_certifications": sum(p[new]["status"] == "certified_model" and p[base]["status"] != "certified_model" for p in pairs),
            "lost_certifications": sum(p[new]["status"] != "certified_model" and p[base]["status"] == "certified_model" for p in pairs),
            "before_output_bytes": before, "after_output_bytes": after,
            "output_reduction_percent": 100 * (1 - after / before),
            "before_work_proxy": pb, "after_work_proxy": pn,
            "work_proxy_reduction_percent": 100 * (1 - pn / pb),
            "work_proxy_increases": sum(p[new]["cost"]["output_plus_source_work_proxy"] > p[base]["cost"]["output_plus_source_work_proxy"] for p in pairs),
            "detail_calls_before": sum(p[base]["cost"]["detail_calls"] for p in pairs),
            "detail_calls_after": sum(p[new]["cost"]["detail_calls"] for p in pairs)}


def strip_timing(value):
    if isinstance(value, dict):
        return {key: strip_timing(item) for key, item in value.items() if key != "local_seconds"}
    if isinstance(value, list):
        return [strip_timing(item) for item in value]
    return value
