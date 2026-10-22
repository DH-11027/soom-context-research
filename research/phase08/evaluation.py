"""Paired chronological evaluation; labels never reach the raw-only runtime."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter
from types import MappingProxyType

import runtime
from frozen import ROOT

# Original Phase07 modules are loaded read-only under their original bindings.
sys.path.insert(0, str(ROOT / "research/phase07"))
import baseline as B7
import cached as C7
import study as S7
sys.path.pop(0)

METHODS = ("fresh", "lru", "selective", "no_directory")
STAGES = runtime.STAGES
PARITY = S7.PARITY
SUM_FIELDS = (
    "hash_serialized_bytes", "hash_calls", "records_visited", "cheap_calls", "cheap_source_bytes",
    "contract_calls", "contract_source_bytes", "detail_calls", "detail_source_bytes",
    "reparse_calls", "reparse_source_bytes", "abstract_steps", "source_work_bytes",
    "output_plus_source_work_proxy", "cache_overhead_bytes", "phase07_work_proxy", "phase08_work_score",
    *runtime.BYTE_FIELDS, *runtime.COUNT_FIELDS,
    *(s + suffix for s in STAGES for suffix in ("_requests", "_reused")),
)
SUM_FIELDS = tuple(dict.fromkeys(SUM_FIELDS))


class MeteredLRU(C7.ParseCache):
    """Read-only algorithm wrapper. Adds declared control events, not new policy."""
    def get(self, key, cost):
        runtime.action(cost, "exact_lookup")
        previous_hits = cost["cache_entry_hits"]
        result = super().get(key, cost)
        if cost["cache_entry_hits"] != previous_hits:
            runtime.action(cost, "lru_touch")
        return result

    def put(self, key, stages, cost):
        runtime.action(cost, "capacity_check")
        if not self.max_entries or not self.max_bytes:
            return
        runtime.action(cost, "candidate_arithmetic")
        payload = sum(size for _, size in stages.values())
        size = sum(map(len, key)) + payload
        if size > self.max_bytes:
            cost["cache_oversize"] += 1
            return
        runtime.action(cost, "write_membership_check")
        if key in self.entries:
            runtime.action(cost, "entry_replacement")
            self.retained_bytes -= self.entries.pop(key)[1]
        while self.entries and (len(self.entries) >= self.max_entries or self.retained_bytes + size > self.max_bytes):
            runtime.action(cost, "entry_removal", 4)
            _, (_, removed) = self.entries.popitem(last=False)
            self.retained_bytes -= removed
            cost["cache_evictions"] += 1
        runtime.action(cost, "entry_initialization", runtime.META_BYTES // 8)
        self.entries[key] = (MappingProxyType(dict(stages)), size)
        self.retained_bytes += size
        self.peak_bytes = max(self.peak_bytes, self.retained_bytes)
        self.peak_entries = max(self.peak_entries, len(self.entries))
        cost["cache_writes"] += 1
        cost["cache_write_bytes"] += size


def new_cache(method):
    if method == "fresh":
        return None
    if method == "lru":
        return MeteredLRU()
    return runtime.SelectiveCache(directory=method != "no_directory")


def run(method, public, cache, namespace="v1"):
    if method in ("selective", "no_directory"):
        return runtime.run(public, cache, namespace=namespace)
    # C7 initializes cost internally. A transparent subclass cannot add fields
    # before get(), so action() is deliberately tolerant of missing fields.
    start = perf_counter()
    result = C7.run(public, cache, namespace=namespace)
    cost = result["cost"]
    for key in (*runtime.COUNT_FIELDS, *runtime.BYTE_FIELDS):
        cost.setdefault(key, 0)
    cost.setdefault("control_events", {})
    if method == "lru":
        runtime.action(cost, "stage_slot_check", sum(cost[s + "_requests"] for s in STAGES))
        runtime.action(cost, "stage_payload_prepare", sum(cost[s + "_calls"] for s in STAGES))
    cost["phase08_work_score"] = cost["phase07_work_proxy"] + runtime.ACTION_WEIGHT * cost["control_actions"]
    cost["directory_entries"] = 0
    cost["local_seconds"] = perf_counter() - start
    return result


def summary(rows):
    gold = [r for r in rows if r["gold_evaluated"]]
    cert = [r for r in gold if r["status"] == "certified_model"]
    return {
        "queries": len(rows), "streams": len({r["stream_id"] for r in rows}),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "valid_snapshots": sum(r["valid_snapshot"] for r in rows),
        "valid_supported": sum(r["valid_snapshot"] and r["supported"] for r in rows),
        "gold_evaluated": len(gold), "gold_excluded": len(rows) - len(gold),
        "gold_exclusion_reasons": dict(Counter(r["gold_exclusion_reason"] for r in rows if not r["gold_evaluated"])),
        "certified_gold_evaluated": len(cert),
        "false_certifications": sum(r["false_certification"] for r in cert),
        "containment_evaluated": sum(r["containment_violation"] is not None for r in gold),
        "containment_violations": sum(r["containment_violation"] is True for r in gold),
        "gold_projection_evaluated": sum(r["selected_gold_projection_equal"] is not None for r in gold),
        "gold_projection_failures": sum(r["selected_gold_projection_equal"] is False for r in gold),
        "parity_failures": sum(bool(r["parity_failures"]) for r in rows),
        "structural_errors": sum(r["structural_error"] or r["schema_error"] for r in rows),
        "actual_full_history": sum(r["actual_full_history"] for r in rows),
        "output_bytes": sum(r["output_bytes"] for r in rows),
        "cost": {key: sum(r["cost"][key] for r in rows) for key in SUM_FIELDS},
        "control_events": dict(sum((Counter(r["cost"]["control_events"]) for r in rows), Counter())),
        "max_retained_bytes": max((r["cost"]["cache_peak_bytes"] for r in rows), default=0),
        "max_entries": max((r["cost"]["cache_peak_entries"] for r in rows), default=0),
    }


def compare(rows, candidate="selective", reference="fresh", weight=runtime.ACTION_WEIGHT):
    pairs = {}
    for row in rows:
        if row["method"] in (candidate, reference):
            pairs.setdefault((row["stream_id"], row["step_index"]), {})[row["method"]] = row
    score = lambda r: r["cost"]["phase07_work_proxy"] + weight * r["cost"]["control_actions"]
    calls = lambda r: sum(r["cost"][s + "_calls"] for s in STAGES)
    before = sum(score(p[reference]) for p in pairs.values())
    after = sum(score(p[candidate]) for p in pairs.values())
    cb, ca = (sum(calls(p[m]) for p in pairs.values()) for m in (reference, candidate))
    streams = []
    for sid in sorted({key[0] for key in pairs}):
        cumulative, deltas = 0, []
        for key in sorted(k for k in pairs if k[0] == sid):
            p = pairs[key]
            cumulative += score(p[candidate]) - score(p[reference])
            deltas.append(cumulative)
        streams.append({"stream_id": sid, "cumulative_delta": deltas,
            "first_strict_break_even_step": next((i+1 for i, x in enumerate(deltas) if x < 0), None),
            "sustained_break_even_step": next((i+1 for i in range(len(deltas)) if all(x < 0 for x in deltas[i:])), None),
            "total_delta": deltas[-1] if deltas else 0})
    return {"candidate": candidate, "reference": reference, "control_action_weight": weight,
            "paired_queries": len(pairs), "before_score": before, "after_score": after,
            "score_change_percent": 100 * (after / before - 1) if before else None,
            "parser_executions_before": cb, "parser_executions_after": ca,
            "parser_execution_reduction_percent": 100 * (1 - ca / cb) if cb else None,
            "queries_with_fewer_parser_executions": sum(calls(p[candidate]) < calls(p[reference]) for p in pairs.values()),
            "queries_with_lower_score": sum(score(p[candidate]) < score(p[reference]) for p in pairs.values()),
            "queries_with_equal_score": sum(score(p[candidate]) == score(p[reference]) for p in pairs.values()),
            "streams": streams}


def evaluate(streams):
    rows = []
    for stream in streams:
        caches = {m: new_cache(m) for m in METHODS}
        for index, step in enumerate(stream["steps"]):
            outcomes = {}
            reference_payload = None
            for method in METHODS:
                public = S7.public_of(step)  # explicit four-field whitelist
                result = run(method, public, caches[method], step["parser_namespace"])
                payload = S7.render_result(public, result)
                assessed = S7.assess(step, public, result)
                row = {"stream_id": stream["id"], "family": stream["family"], "split": stream["split"],
                       "step_index": index, "step_id": step["step_id"], "method": method,
                       "namespace": step["parser_namespace"], **result, **assessed,
                       "gold_exclusion_reason": (None if assessed["gold_evaluated"] else
                           "invalid_snapshot" if not assessed["valid_snapshot"] else "undefined_membership_projection"),
                       "actual_full_history": bool(public["records"]) and result["selected"] == list(range(len(public["records"]))),
                       "rendered_sha256": hashlib.sha256(payload).hexdigest(), "parity_failures": []}
                outcomes[method] = row
                ref = outcomes["fresh"]
                if method == "fresh":
                    reference_payload = payload
                elif payload != reference_payload:
                    row["parity_failures"].append("rendered_exact_bytes")
                for key in (*PARITY, "rendered_sha256"):
                    if row.get(key) != ref.get(key):
                        row["parity_failures"].append(key)
                for stage in STAGES:
                    cost = row["cost"]
                    if cost[stage+"_requests"] != ref["cost"][stage+"_calls"]:
                        row["parity_failures"].append(stage + "_logical_requests")
                    if cost[stage+"_requests"] != cost[stage+"_calls"] + cost[stage+"_reused"]:
                        row["parity_failures"].append(stage + "_ledger")
                cost = row["cost"]
                if cost["cache_retained_bytes"] > runtime.MAX_BYTES or cost["cache_entries"] > runtime.MAX_ENTRIES:
                    row["parity_failures"].append("memory_budget")
                if (not row["valid_snapshot"] or not row["supported"]) and (cost["cache_lookups"] or cost["control_actions"]):
                    row["parity_failures"].append("early_exit_cache_access")
                if any(cost[k] != ref["cost"][k] for k in ("hash_serialized_bytes", "hash_calls")):
                    row["parity_failures"].append("snapshot_work")
                if cost["control_actions"] != sum(cost["control_events"].values()):
                    row["parity_failures"].append("control_ledger")
                if cost["cache_overhead_bytes"] != sum(cost[k] for k in runtime.BYTE_FIELDS):
                    row["parity_failures"].append("cache_byte_ledger")
                if cost["phase07_work_proxy"] != cost["output_plus_source_work_proxy"] + cost["cache_overhead_bytes"]:
                    row["parity_failures"].append("p7_ledger")
                if cost["phase08_work_score"] != cost["phase07_work_proxy"] + runtime.ACTION_WEIGHT * cost["control_actions"]:
                    row["parity_failures"].append("p8_ledger")
                if row["output_bytes"] != len(payload):
                    row["parity_failures"].append("render_length")
                if method == "no_directory":
                    a, b = caches["selective"], caches["no_directory"]
                    if a.entries != b.entries or a.lengths != b.lengths or a.retained_bytes != b.retained_bytes:
                        row["parity_failures"].append("directory_ablation_state")
                    selective_cost = outcomes["selective"]["cost"]
                    if any(cost[s+"_calls"] != selective_cost[s+"_calls"] for s in STAGES):
                        row["parity_failures"].append("directory_ablation_calls")
                    if selective_cost["phase08_work_score"] > cost["phase08_work_score"]:
                        row["parity_failures"].append("directory_ablation_score")
                rows.append(row)
    failures = [{k: r[k] for k in ("stream_id", "step_index", "method", "parity_failures", "structural_error",
                                  "schema_error", "false_certification", "containment_violation", "selected_gold_projection_equal")}
                for r in rows if r["parity_failures"] or r["structural_error"] or r["schema_error"] or r["false_certification"]
                or r["containment_violation"] or r["selected_gold_projection_equal"] is False]
    return {"summary": {m: summary([r for r in rows if r["method"] == m]) for m in METHODS},
            "comparisons": {m: compare(rows, m) for m in METHODS if m != "fresh"},
            "selective_vs_lru": compare(rows, "selective", "lru"),
            "directory_ablation": compare(rows, "selective", "no_directory"),
            "sensitivity": {str(w): compare(rows, weight=w) for w in (0, 8, 32, 128)},
            "families": {f: {m: compare([r for r in rows if r["family"] == f], m) for m in METHODS if m != "fresh"}
                         for f in sorted({r["family"] for r in rows})},
            "failures": failures, "rows": B7.E6.strip_timing(rows)}


def benchmark(streams, repeats=7):
    def once(method, subset):
        start = perf_counter()
        for stream in subset:
            cache = new_cache(method)
            for step in stream["steps"]:
                run(method, step["public"], cache, step["parser_namespace"])
        return perf_counter() - start

    groups = {"all": streams, **{f: [s for s in streams if s["family"] == f] for f in sorted({s["family"] for s in streams})}}
    result = {}
    for label, subset in groups.items():
        samples = {m: [] for m in METHODS}
        for method in METHODS:
            once(method, subset)
        for i in range(repeats):
            for method in METHODS[i % len(METHODS):] + METHODS[:i % len(METHODS)]:
                samples[method].append(once(method, subset))
        result[label] = {"streams": len(subset), "queries": sum(len(s["steps"]) for s in subset),
                         "methods": {m: {"samples_seconds": x, "median_seconds": median(x),
                                         "min_seconds": min(x), "max_seconds": max(x)} for m, x in samples.items()}}
    meds = result["all"]["methods"]
    return {"repeats": repeats, "cold_each_stream_and_repeat": True, "groups": result,
            "scope": "Instrumented full local path, cache construction, validation, parser, policy, inference and rendering; no imports/data loading/gold/LLM",
            "selective_vs_fresh_percent": 100 * (meds["selective"]["median_seconds"] / meds["fresh"]["median_seconds"] - 1),
            "statistical_significance_tested": False}


def regressions():
    historical = json.loads((ROOT / "research/phase07/data/holdout.json").read_text())
    for stream in historical:
        stream["id"] = "phase07-" + stream["id"]
        stream["family"] = "phase07_known_development"
        stream["split"] = "known_development_regression"
    return historical + S7.regressions()
