"""Selective pure-stage reuse; raw-only, online, bounded, research only.

The character-length directory is a negative filter, never a semantic key.
Only results already obtained on the current natural path can be admitted.
No prediction, query-local TOP, historical copy value or future is cached.
"""
from collections import Counter
from collections.abc import Mapping
from functools import cmp_to_key
from time import perf_counter
from types import MappingProxyType
import json

from frozen import P6, SEMANTIC_FINGERPRINT

STAGES = ("cheap", "contract", "detail")
MAX_ENTRIES, MAX_BYTES = 64, 65536
MIN_CHARS, HIT_CAP = 256, 255
META_BYTES = 80  # logical per-entry control/directory allowance, NOT Python RSS
ACTION_WEIGHT = 8  # work points per declared control action, NOT measured bytes
WARM_ACTIONS = 8  # len, directory, context, get, hit update, three slot reads
BYTE_FIELDS = ("key_build_bytes", "key_probe_bytes", "value_encode_bytes",
               "cache_read_payload_bytes", "cache_write_bytes")
COUNT_FIELDS = ("cache_lookups", "cache_entry_hits", "cache_entry_misses", "cache_writes",
                "cache_evictions", "cache_oversize", "admission_attempts", "admission_reject_gain",
                "admission_reject_capacity", "directory_skips", "short_bypasses", "control_actions")


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


def action(cost, name, count=1):
    cost["control_actions"] = cost.get("control_actions", 0) + count
    events = cost.setdefault("control_events", {})
    events[name] = events.get(name, 0) + count


def new_cost(public):
    cost = P6.new_cost(public)
    cost.update({k: 0 for k in (*BYTE_FIELDS, *COUNT_FIELDS)})
    cost.update({s + suffix: 0 for s in STAGES for suffix in ("_requests", "_reused")})
    cost["control_events"] = {}
    return cost


class SelectiveCache:
    """Greedy admission by observed warm surplus and bounded past hits.

    Victim ranking and benefit comparisons are heuristic, not predictions of
    the actual future or a solution of the capacity-constrained offline optimum.
    """
    def __init__(self, *, directory=True, max_entries=MAX_ENTRIES, max_bytes=MAX_BYTES):
        if min(max_entries, max_bytes) < 0:
            raise ValueError("negative capacity")
        self.directory = directory
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self.entries = {}
        self.lengths = Counter()
        self.retained_bytes = self.peak_bytes = self.peak_entries = 0
        self.next_order = 0

    def possible(self, characters, cost):
        if self.directory:
            action(cost, "length_directory_lookup")
            possible = self.lengths.get(characters, 0) > 0
        else:
            action(cost, "resident_presence_lookup")
            possible = bool(self.entries)
        if not possible:
            cost["directory_skips"] += 1
        return possible

    def get(self, key, cost):
        action(cost, "exact_lookup")
        cost["cache_lookups"] += 1
        cost["key_probe_bytes"] += sum(map(len, key))
        item = self.entries.get(key)
        if item is None:
            cost["cache_entry_misses"] += 1
            return None
        cost["cache_entry_hits"] += 1
        action(cost, "bounded_hit_update")
        item["hits"] = min(HIT_CAP, item["hits"] + 1)
        return item["stages"]

    def admit(self, key_factory, context, raw_size, characters, values, cost):
        """Caller checked full global three-stage eligibility after real parsing."""
        cost["admission_attempts"] += 1
        stages = {}
        for name in STAGES:
            action(cost, "stage_payload_prepare")
            value = values[name]
            length = len(encode(value))
            cost["value_encode_bytes"] += length
            stages[name] = (immutable(value), length)
        payload = sum(size for _, size in stages.values())
        action(cost, "candidate_arithmetic", 2)
        surplus = raw_size - len(context) - payload - ACTION_WEIGHT * WARM_ACTIONS
        size = len(context) + raw_size + payload + META_BYTES
        action(cost, "positive_surplus_check")
        if surplus <= 0:
            cost["admission_reject_gain"] += 1
            return
        action(cost, "capacity_check")
        if not self.max_entries or size > self.max_bytes:
            cost["cache_oversize"] += 1
            cost["admission_reject_capacity"] += 1
            return
        victims = []
        if (len(self.entries) + 1 > self.max_entries
                or self.retained_bytes + size > self.max_bytes):
            ranked = []
            for key, item in self.entries.items():
                action(cost, "resident_score_read")
                weight = (item["hits"] + 1) * item["surplus"]
                ranked.append((key, item, weight))

            def order(left, right):
                action(cost, "density_comparison")
                a, b = left[2] * right[1]["size"], right[2] * left[1]["size"]
                if a != b:
                    return -1 if a < b else 1
                return (left[1]["order"] > right[1]["order"]) - (left[1]["order"] < right[1]["order"])

            ranked.sort(key=cmp_to_key(order))
            freed, lost = 0, 0
            for key, item, weight in ranked:
                action(cost, "victim_plan_step")
                victims.append(key)
                freed += item["size"]
                lost += weight
                if (len(self.entries) - len(victims) + 1 <= self.max_entries
                        and self.retained_bytes - freed + size <= self.max_bytes):
                    break
            action(cost, "victim_benefit_check")
            if surplus <= lost:
                cost["admission_reject_capacity"] += 1
                return
        # No mutation until the complete capacity/benefit plan is accepted.
        for victim in victims:
            action(cost, "entry_removal", 4)
            item = self.entries.pop(victim)
            self.retained_bytes -= item["size"]
            self.lengths[item["characters"]] -= 1
            if not self.lengths[item["characters"]]:
                del self.lengths[item["characters"]]
            cost["cache_evictions"] += 1
        key = key_factory()
        action(cost, "entry_initialization", META_BYTES // 8)
        self.entries[key] = {"stages": MappingProxyType(stages), "size": size,
                             "characters": characters, "surplus": surplus,
                             "hits": 0, "order": self.next_order}
        self.next_order += 1
        self.lengths[characters] += 1
        self.retained_bytes += size
        self.peak_bytes = max(self.peak_bytes, self.retained_bytes)
        self.peak_entries = max(self.peak_entries, len(self.entries))
        cost["cache_writes"] += 1
        cost["cache_write_bytes"] += size - META_BYTES


def finish(result, cost, start, cache):
    P6.finish(result, cost, start)
    cost["cache_overhead_bytes"] = sum(cost[k] for k in BYTE_FIELDS)
    cost["phase07_work_proxy"] = cost["output_plus_source_work_proxy"] + cost["cache_overhead_bytes"]
    cost["phase08_work_score"] = cost["phase07_work_proxy"] + ACTION_WEIGHT * cost["control_actions"]
    cost["cache_retained_bytes"] = cache.retained_bytes
    cost["cache_entries"] = len(cache.entries)
    cost["cache_peak_bytes"] = cache.peak_bytes
    cost["cache_peak_entries"] = cache.peak_entries
    cost["directory_entries"] = len(cache.lengths)
    cost["local_seconds"] = perf_counter() - start
    return result


def run(public, cache, *, namespace="v1"):
    start = perf_counter()
    cost = new_cost(public)
    records, entities = public["records"], public["entities"]
    error = P6.validate(public, cost)
    if error:
        return finish({"status": "integrity_failure", "reason": error, "prediction": {},
                       "selected": [], "output_bytes": 0, "scope_trace": []}, cost, start, cache)
    requested = P6.BASE.parse_query(public["query"], entities)
    if requested is None:
        selected, status = list(range(len(records))), "unsupported_query"
        return finish({"status": status, "prediction": {}, "selected": selected,
                       "output_bytes": len(P6.render(public, selected, status).encode()),
                       "scope_trace": []}, cost, start, cache)
    context = None

    def get_context():
        nonlocal context
        action(cost, "context_access")
        if context is None:
            context = encode((SEMANTIC_FINGERPRINT, namespace, tuple(entities)))
            cost["key_build_bytes"] += len(context)
        return context

    universe = P6.BASE.facts(entities)
    query_events, trace = {}, []

    def read(index, demand):
        if index in query_events:
            return query_events[index]
        text = records[index]["text"]
        raw = text.encode("utf-8")  # same size observation as frozen fresh
        size = len(raw)
        cost["records_visited"] += 1
        action(cost, "character_length_gate")
        characters = len(text)
        eligible = characters >= MIN_CHARS
        key, ctx, cached_stages = None, None, None

        def get_key():
            nonlocal key
            if key is None:
                # P7 logical convention charges L even though raw is also used
                # for the common parser-source size observation above.
                cost["key_build_bytes"] += size
                key = (ctx, raw)
            return key

        if not eligible:
            cost["short_bypasses"] += 1
        elif cache.possible(characters, cost):
            ctx = get_context()
            cached_stages = cache.get(get_key(), cost)
        values = {}

        def stage(name):
            cost[name + "_requests"] += 1
            if cached_stages is not None:
                action(cost, "cached_stage_read")
                value, length = cached_stages[name]
                cost[name + "_reused"] += 1
                cost["cache_read_payload_bytes"] += length
                return value
            cost[name + "_calls"] += 1
            cost[name + "_source_bytes"] += size
            value = (P6.scope_from_text(text, entities) if name == "contract"
                     else P6.BASE.parse(text, entities, deep=name == "detail"))
            if eligible:
                action(cost, "stage_observation")
                values[name] = value
            return value

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
        if eligible and cached_stages is None:
            # Avoid context construction on cheap-only and scoped-only paths.
            action(cost, "bundle_eligibility")
            if (set(values) == set(STAGES) and values["cheap"]["kind"] == "havoc"
                    and values["contract"][0] is None):
                if ctx is None:
                    ctx = get_context()
                cache.admit(get_key, ctx, size, characters, values, cost)
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
    prediction = {f"{f[0]}.{f[1]}": None if abstract[f] is None else sorted(abstract[f], key=repr)
                  for f in sorted(requested)}
    return finish({"status": status, "prediction": prediction, "selected": selected,
                   "output_bytes": len(P6.render(public, selected, status).encode()),
                   "remaining_input_facts": sorted(demand), "scope_trace": trace}, cost, start, cache)
