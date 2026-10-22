"""Bounded immutable pure-stage memoization. No gold/data imports.

Snapshot, demand, execution and evidence rendering are recomputed per query.
Exact bytes keys resolve hash collisions by equality (no digest-only keys).
"""
from collections import OrderedDict
from collections.abc import Mapping
from types import MappingProxyType
from time import perf_counter
import json

from baseline import P6, SEMANTIC_FINGERPRINT

METHODS = ("fresh", "disabled", "reset", "lru")
MAX_ENTRIES, MAX_BYTES = 64, 65536
EXTRA = (
    "key_build_bytes", "key_probe_bytes", "value_encode_bytes", "cache_read_payload_bytes", "cache_write_bytes",
    "cache_lookups", "cache_entry_hits", "cache_entry_misses", "cache_writes", "cache_evictions",
    "cache_oversize", "cheap_requests", "contract_requests", "detail_requests",
    "cheap_reused", "contract_reused", "detail_reused",
)

def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return [plain(v) for v in sorted(value, key=repr)]
    return value

def encode(value):
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def immutable(value):
    if isinstance(value, Mapping):
        return MappingProxyType({k: immutable(v) for k, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(immutable(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(immutable(v) for v in value)
    return value

class ParseCache:
    def __init__(self, max_entries=MAX_ENTRIES, max_bytes=MAX_BYTES):
        if max_entries < 0 or max_bytes < 0:
            raise ValueError("negative capacity")
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self.entries = OrderedDict()
        self.retained_bytes = self.peak_bytes = self.peak_entries = 0

    def clear(self):
        self.entries.clear()
        self.retained_bytes = 0

    def get(self, key, cost):
        cost["cache_lookups"] += 1
        cost["key_probe_bytes"] += sum(map(len, key))
        item = self.entries.get(key)
        if item is None:
            cost["cache_entry_misses"] += 1
            return {}
        cost["cache_entry_hits"] += 1
        self.entries.move_to_end(key)
        return item[0]

    def put(self, key, stages, cost):
        if not self.max_entries or not self.max_bytes:
            return
        # Slots hold (immutable value, canonical payload length); encoding is
        # performed only when a stage is first computed, not on cache hits.
        payload = sum(size for _, size in stages.values())
        size = sum(map(len, key)) + payload
        if size > self.max_bytes:
            cost["cache_oversize"] += 1
            return
        if key in self.entries:
            self.retained_bytes -= self.entries.pop(key)[1]
        while self.entries and (len(self.entries) >= self.max_entries or self.retained_bytes + size > self.max_bytes):
            _, (_, removed) = self.entries.popitem(last=False)
            self.retained_bytes -= removed
            cost["cache_evictions"] += 1
        self.entries[key] = (MappingProxyType(dict(stages)), size)
        self.retained_bytes += size
        self.peak_bytes = max(self.peak_bytes, self.retained_bytes)
        self.peak_entries = max(self.peak_entries, len(self.entries))
        cost["cache_writes"] += 1
        cost["cache_write_bytes"] += size

def new_cache(method):
    return None if method == "fresh" else ParseCache(0, 0) if method == "disabled" else ParseCache()

def finish(result, cost, start, cache):
    result = P6.finish(result, cost, start)
    cost["cache_overhead_bytes"] = sum(cost[k] for k in
        ("key_build_bytes", "key_probe_bytes", "value_encode_bytes", "cache_read_payload_bytes", "cache_write_bytes"))
    cost["phase07_work_proxy"] = cost["output_plus_source_work_proxy"] + cost["cache_overhead_bytes"]
    cost["cache_retained_bytes"] = 0 if cache is None else cache.retained_bytes
    cost["cache_entries"] = 0 if cache is None else len(cache.entries)
    cost["cache_peak_bytes"] = 0 if cache is None else cache.peak_bytes
    cost["cache_peak_entries"] = 0 if cache is None else cache.peak_entries
    cost["local_seconds"] = perf_counter() - start
    return result

def run(public, cache=None, *, namespace="v1"):
    start = perf_counter()
    if cache is None:
        result = P6.run(public, "text_scoped")
        cost = result["cost"]
        cost.update({k: 0 for k in EXTRA})
        for stage in ("cheap", "contract", "detail"):
            cost[stage + "_requests"] = cost[stage + "_calls"]
        return finish(result, cost, start, None)
    cost = P6.new_cost(public)
    cost.update({k: 0 for k in EXTRA})
    records, entities = public["records"], public["entities"]
    error = P6.validate(public, cost)
    if error:
        return finish({"status": "integrity_failure", "reason": error, "prediction": {},
            "selected": [], "output_bytes": 0, "scope_trace": []}, cost, start, cache)
    requested = P6.BASE.parse_query(public["query"], entities)
    if requested is None:
        selected = list(range(len(records)))
        status = "unsupported_query"
        return finish({"status": status, "prediction": {}, "selected": selected,
            "output_bytes": len(P6.render(public, selected, status).encode()), "scope_trace": []}, cost, start, cache)
    context = encode((SEMANTIC_FINGERPRINT, namespace, tuple(entities)))
    cost["key_build_bytes"] += len(context)
    universe = P6.BASE.facts(entities)
    query_events, trace = {}, []

    def read(index, demand):
        if index in query_events:
            return query_events[index]
        text = records[index]["text"]
        text_bytes = text.encode("utf-8")
        size = len(text_bytes)
        cost["records_visited"] += 1
        cost["key_build_bytes"] += size
        key = (context, text_bytes)
        previous = cache.get(key, cost)
        stages = dict(previous)
        updated = False

        def stage(name):
            nonlocal updated
            cost[name + "_requests"] += 1
            if name in stages:
                value, length = stages[name]
                cost[name + "_reused"] += 1
                cost["cache_read_payload_bytes"] += length
                return value
            cost[name + "_calls"] += 1
            cost[name + "_source_bytes"] += size
            value = P6.scope_from_text(text, entities) if name == "contract" else P6.BASE.parse(text, entities, deep=name == "detail")
            frozen = immutable(value)
            length = len(encode(value))
            cost["value_encode_bytes"] += length
            stages[name] = (frozen, length)
            updated = True
            return frozen

        ev = stage("cheap")
        if ev["kind"] == "havoc":
            known, rule = stage("contract")
            w = frozenset(universe) if known is None else known
            relevant = bool(set(demand) & w)
            trace.append({"index": index, "rule": rule, "may_write": [list(f) for f in sorted(w)],
                          "proper_scope": len(w) < len(universe), "detail_avoided": not relevant})
            if relevant:
                ev = stage("detail")
            if ev["kind"] == "havoc":
                ev = P6.scoped_top(w)
        if updated:
            cache.put(key, stages, cost)
        query_events[index] = ev
        return ev

    demand, selected = set(requested), []
    for index in range(len(records) - 1, -1, -1):
        if not demand:
            break
        ev = read(index, demand)
        if demand & P6.writes(ev, universe):
            selected.append(index)
            demand = P6.preimage(ev, demand, universe)
    selected.sort()
    abstract = P6.execute((query_events[i] for i in selected), universe)
    cost["abstract_steps"] = len(selected)
    unresolved = any(query_events[i]["kind"] in ("havoc", "scoped_top") for i in selected)
    certified = all(abstract[f] is not None and len(abstract[f]) == 1 for f in requested)
    status = "certified_model" if certified else "opaque_fallback" if unresolved or demand else "ambiguous"
    if status == "opaque_fallback":
        selected = list(range(len(records)))
    prediction = {f"{f[0]}.{f[1]}": None if abstract[f] is None else sorted(abstract[f], key=repr) for f in sorted(requested)}
    return finish({"status": status, "prediction": prediction, "selected": selected,
        "output_bytes": len(P6.render(public, selected, status).encode("utf-8")),
        "remaining_input_facts": sorted(demand), "scope_trace": trace}, cost, start, cache)
