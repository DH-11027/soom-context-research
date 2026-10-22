"""Chronological paired evaluation. Gold never reaches cached.run."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from statistics import median
from time import perf_counter

import cached
from baseline import P6, E6

PARITY = ("status", "prediction", "selected", "output_bytes", "remaining_input_facts", "scope_trace", "reason")
STAGES = ("cheap", "contract", "detail")
SUM_COST = ("hash_serialized_bytes", "hash_calls", "records_visited", "cheap_calls", "cheap_source_bytes",
    "contract_calls", "contract_source_bytes", "detail_calls", "detail_source_bytes", "abstract_steps",
    "source_work_bytes", "output_plus_source_work_proxy", "cache_overhead_bytes", "phase07_work_proxy", *cached.EXTRA)

def public_of(step):
    return {k: deepcopy(step["public"][k]) for k in ("records", "entities", "snapshot", "query")}

def integrity(public):
    rec, snap = public["records"], public["snapshot"]
    raw = json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return ([r["seq"] for r in rec] == list(range(snap["head"] + 1))
            and hashlib.sha256(raw).hexdigest() == snap["digest"])

def render_result(public, result):
    return b"" if result["status"] == "integrity_failure" else P6.render(public, result["selected"], result["status"]).encode()

def assess(step, public, result):
    valid = integrity(public)
    req = E6.requested_fields(public["query"], public["entities"])
    contract = step["question_contract"]
    contract_ok = contract["supported"] == (req is not None) and sorted(map(tuple, contract["required_fields"])) == sorted(req or ())
    declared_valid = step["expected_integrity"] == "valid"
    structural_error = valid != declared_valid or not contract_ok or (result["status"] == "integrity_failure") == valid
    selected = result["selected"]
    structural_error |= sorted(set(selected)) != selected or any(i < 0 or i >= len(public["records"]) for i in selected)
    if valid and result["status"] in ("opaque_fallback", "unsupported_query"):
        structural_error |= selected != list(range(len(public["records"])))
    if not valid:
        structural_error |= bool(selected) or bool(result["prediction"]) or result["output_bytes"] != 0
    out = {"valid_snapshot": valid, "supported": req is not None,
           "gold_evaluated": valid and step["gold_applicable"],
           "structural_error": bool(structural_error), "schema_error": False,
           "false_certification": False, "containment_violation": None,
           "gold_singleton": None, "selected_gold_projection_equal": None}
    if out["gold_evaluated"]:
        assert len(step["gold"]) == len(public["records"])
        states = E6.exact_states(step["gold"], public["entities"])
        assert all(x is not None for s in states for x in s), "Uninitialized full gold state"
        out.update(E6.assess(public, result, states))
        if req is not None:
            partial = E6.exact_states([step["gold"][i] for i in selected], public["entities"])
            out["selected_gold_projection_equal"] = E6.project(states, req, public["entities"]) == E6.project(partial, req, public["entities"])
        else:
            out["selected_gold_projection_equal"] = selected == list(range(len(public["records"])))
    return out

def summary(rows):
    counts = Counter(r["status"] for r in rows)
    gold = [r for r in rows if r["gold_evaluated"]]
    cert = [r for r in gold if r["status"] == "certified_model"]
    totals = {k: sum(r["cost"][k] for r in rows) for k in SUM_COST}
    return {"queries": len(rows), "streams": len({r["stream_id"] for r in rows}),
        "status_counts": dict(counts), "valid_snapshots": sum(r["valid_snapshot"] for r in rows),
        "gold_evaluated": len(gold), "gold_excluded": len(rows)-len(gold),
        "certified_gold_evaluated": len(cert), "false_certifications": sum(r["false_certification"] for r in cert),
        "containment_evaluated": sum(r["containment_violation"] is not None for r in gold),
        "containment_violations": sum(r["containment_violation"] is True for r in gold),
        "structural_errors": sum(r["structural_error"] or r["schema_error"] for r in rows),
        "gold_projection_failures": sum(r["selected_gold_projection_equal"] is False for r in gold),
        "parity_failures": sum(bool(r["parity_failures"]) for r in rows),
        "actual_full_history": sum(r["actual_full_history"] for r in rows),
        "output_bytes": sum(r["output_bytes"] for r in rows),
        "cost": totals, "max_retained_bytes": max((r["cost"]["cache_peak_bytes"] for r in rows), default=0),
        "max_entries": max((r["cost"]["cache_peak_entries"] for r in rows), default=0)}

def compare(rows, candidate="lru", reference="fresh"):
    pairs = {}
    for r in rows:
        if r["method"] in (candidate, reference):
            pairs.setdefault((r["stream_id"], r["step_index"]), {})[r["method"]] = r
    cost_before = sum(p[reference]["cost"]["phase07_work_proxy"] for p in pairs.values())
    cost_after = sum(p[candidate]["cost"]["phase07_work_proxy"] for p in pairs.values())
    calls = lambda row: sum(row["cost"][s+"_calls"] for s in STAGES)
    call_before = sum(calls(p[reference]) for p in pairs.values())
    call_after = sum(calls(p[candidate]) for p in pairs.values())
    stream_data = []
    for stream in sorted({key[0] for key in pairs}):
        cumulative = 0
        deltas = []
        for key in sorted(k for k in pairs if k[0] == stream):
            p = pairs[key]
            cumulative += p[candidate]["cost"]["phase07_work_proxy"] - p[reference]["cost"]["phase07_work_proxy"]
            deltas.append(cumulative)
        first = next((i+1 for i, value in enumerate(deltas) if value < 0), None)
        stable = next((i+1 for i in range(len(deltas)) if all(v < 0 for v in deltas[i:])), None)
        stream_data.append({"stream_id": stream, "cumulative_proxy_delta": deltas,
                            "first_strict_break_even_step": first, "sustained_break_even_step": stable})
    return {"candidate": candidate, "reference": reference, "paired_queries": len(pairs),
        "before_proxy": cost_before, "after_proxy": cost_after,
        "proxy_change_percent": 100*(cost_after/cost_before-1) if cost_before else None,
        "parser_executions_before": call_before, "parser_executions_after": call_after,
        "parser_execution_reduction_percent": 100*(1-call_after/call_before) if call_before else None,
        "queries_with_fewer_parser_executions": sum(calls(p[candidate]) < calls(p[reference]) for p in pairs.values()),
        "queries_with_lower_proxy": sum(p[candidate]["cost"]["phase07_work_proxy"] < p[reference]["cost"]["phase07_work_proxy"] for p in pairs.values()),
        "streams": stream_data}

def evaluate(streams):
    rows = []
    for stream in streams:
        caches = {m: cached.new_cache(m) for m in cached.METHODS}
        for index, step in enumerate(stream["steps"]):
            outcomes = {}
            for method in cached.METHODS:
                if method == "reset":
                    caches[method].clear()
                public = public_of(step)
                result = cached.run(public, caches[method], namespace=step["parser_namespace"])
                payload = render_result(public, result)
                assessed = assess(step, public, result)
                row = {"stream_id": stream["id"], "family": stream["family"], "split": stream["split"],
                       "step_index": index, "step_id": step["step_id"], "method": method,
                       "namespace": step["parser_namespace"], **result, **assessed,
                       "actual_full_history": result["selected"] == list(range(len(public["records"]))) and bool(public["records"]),
                       "rendered_sha256": hashlib.sha256(payload).hexdigest(), "parity_failures": []}
                outcomes[method] = row
                reference = outcomes["fresh"]
                for key in (*PARITY, "rendered_sha256"):
                    if row.get(key) != reference.get(key):
                        row["parity_failures"].append(key)
                for stage in STAGES:
                    if row["cost"][stage+"_requests"] != reference["cost"][stage+"_calls"]:
                        row["parity_failures"].append(stage+"_logical_requests")
                if row["cost"]["cache_retained_bytes"] > cached.MAX_BYTES or row["cost"]["cache_entries"] > cached.MAX_ENTRIES:
                    row["parity_failures"].append("memory_budget")
                if not row["valid_snapshot"] and row["cost"]["cache_lookups"]:
                    row["parity_failures"].append("invalid_snapshot_cache_access")
                rows.append(row)
    summaries = {m: summary([r for r in rows if r["method"] == m]) for m in cached.METHODS}
    failures = [{k: r[k] for k in ("stream_id", "step_index", "method", "parity_failures", "structural_error", "schema_error", "false_certification", "containment_violation", "selected_gold_projection_equal")}
                for r in rows if r["parity_failures"] or r["structural_error"] or r["schema_error"] or r["false_certification"] or r["containment_violation"] or r["selected_gold_projection_equal"] is False]
    return {"summary": summaries, "comparisons": {m: compare(rows, m) for m in cached.METHODS if m != "fresh"},
        "cross_query_comparison": compare(rows, "lru", "reset"),
        "families": {f: compare([r for r in rows if r["family"] == f]) for f in sorted({r["family"] for r in rows})},
        "failures": failures, "rows": E6.strip_timing(rows)}

def benchmark(streams, repeats=7):
    def once(method, subset):
        start = perf_counter()
        for stream in subset:
            cache = cached.new_cache(method)
            for step in stream["steps"]:
                if method == "reset":
                    cache.clear()
                cached.run(step["public"], cache, namespace=step["parser_namespace"])
        return perf_counter()-start
    groups = {"all": streams, **{f: [s for s in streams if s["family"] == f] for f in sorted({s["family"] for s in streams})}}
    result = {}
    for label, subset in groups.items():
        samples = {m: [] for m in cached.METHODS}
        for method in cached.METHODS:
            once(method, subset)  # discard all warm-up caches
        for i in range(repeats):
            order = cached.METHODS[i%4:] + cached.METHODS[:i%4]
            for method in order:
                samples[method].append(once(method, subset))
        result[label] = {"streams": len(subset), "queries": sum(len(s["steps"]) for s in subset),
            "methods": {m: {"samples_seconds": values, "median_seconds": median(values),
                "min_seconds": min(values), "max_seconds": max(values)} for m, values in samples.items()}}
    return {"repeats": repeats, "cold_cache_each_stream_and_repeat": True,
            "scope": "instrumented local path, includes cache creation/hash/parsing/immutable encoding/LRU/inference/render; excludes imports, corpus loading, offline gold evaluation",
            "groups": result}

def regressions():
    from baseline import ROOT
    streams = []
    for name, relative in (("phase06", "research/phase06/data/holdout.json"), ("phase05", "research/phase05/corpus.json")):
        cases = json.loads((ROOT / relative).read_text())
        for case in cases:
            steps = []
            for i, query in enumerate(case["queries"]):
                public = deepcopy(case["public"])
                public["query"] = query
                req = E6.requested_fields(query, public["entities"])
                steps.append({"step_id": f"q{i}", "parser_namespace": "v1", "public": public,
                    "gold": case["gold"], "gold_applicable": True, "expected_integrity": "valid",
                    "question_contract": {"supported": req is not None, "required_fields": list(req or [])}})
            streams.append({"id": name+"-"+case["id"], "family": name+"_regression", "split": "regression", "steps": steps})
    return streams
