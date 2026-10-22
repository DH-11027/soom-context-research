"""Correctness-only replay with exact prefix/state/trace comparisons.

This module is NEVER imported by the primary timing worker. Temporary wrappers
measure actual invocations here, not in the uninstrumented benchmark. Gold and
family labels stay outside execution.components() and its public input.
"""
from collections import Counter
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json

from bindings import P6, P8E, P8R, ROOT, S7
import execution
import off_fresh
import off_selective

METHODS = execution.METHODS
STAGES = P8R.STAGES
ON_OFF = (("fresh_instrumented", "fresh_uninstrumented"),
          ("selective_instrumented", "selective_uninstrumented"))
AUDIT_FIELDS = ("cheap_calls", "contract_calls", "detail_calls",
                "cheap_source_bytes", "contract_source_bytes", "detail_source_bytes",
                "snapshot_calls", "snapshot_serialized_bytes", "render_calls",
                "rendered_bytes", "policy_possible_calls", "policy_get_calls",
                "policy_admit_calls", "policy_insertions", "policy_evictions")


def exact(value):
    """Type-aware, detached equality representation; no hash-based comparison."""
    if isinstance(value, Mapping):
        return ("mapping", tuple((exact(k), exact(v)) for k, v in value.items()))
    if isinstance(value, tuple):
        return ("tuple", tuple(exact(v) for v in value))
    if isinstance(value, list):
        return ("list", tuple(exact(v) for v in value))
    if isinstance(value, (set, frozenset)):
        return (type(value).__name__, tuple(sorted((exact(v) for v in value), key=repr)))
    return (type(value).__name__, value)


def serializable(value):
    if isinstance(value, bytes):
        return {"exact_bytes_hex": value.hex()}
    if isinstance(value, Mapping):
        return {str(k): serializable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serializable(v) for v in value]
    return value


def encoded(value):
    return json.dumps(serializable(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(value):
    # Only compact receipt/output serialization. Equality is checked beforehand.
    return hashlib.sha256(encoded(value)).hexdigest()


def policy_state(cache):
    """pi: all next-decision state, including exact key and insertion order."""
    if cache is None:
        return None
    return {
        "directory": cache.directory,
        "max_entries": cache.max_entries,
        "max_bytes": cache.max_bytes,
        "entries": tuple((key, exact(item["stages"]), item["size"], item["characters"],
                          item["surplus"], item["hits"], item["order"])
                         for key, item in cache.entries.items()),
        "lengths": tuple(sorted(cache.lengths.items())),
        "retained_bytes": cache.retained_bytes,
        "next_order": cache.next_order,
    }


def state_invariants(cache):
    if cache is None:
        return []
    failures = []
    if cache.retained_bytes != sum(x["size"] for x in cache.entries.values()):
        failures.append("retained_sum")
    if cache.retained_bytes > cache.max_bytes or len(cache.entries) > cache.max_entries:
        failures.append("capacity")
    if cache.lengths != Counter(x["characters"] for x in cache.entries.values()):
        failures.append("directory_counter")
    for key, item in cache.entries.items():
        stages = item["stages"]
        if tuple(stages) != STAGES:
            failures.append("complete_stage_order")
            continue
        if stages["cheap"][0]["kind"] != "havoc" or stages["contract"][0][0] is not None:
            failures.append("global_complete_eligibility")
        payload = sum(length for _, length in stages.values())
        if any(length != len(P8R.encode(value)) for value, length in stages.values()):
            failures.append("payload_length")
        if item["size"] != len(key[0]) + len(key[1]) + payload + P8R.META_BYTES:
            failures.append("logical_size")
        if item["surplus"] != len(key[1]) - len(key[0]) - payload - P8R.ACTION_WEIGHT * P8R.WARM_ACTIONS:
            failures.append("surplus")
        if not 0 <= item["hits"] <= P8R.HIT_CAP or item["surplus"] <= 0:
            failures.append("hit_or_surplus_range")
        if len(key[1].decode("utf-8")) != item["characters"]:
            failures.append("raw_characters")
        if item["order"] >= cache.next_order:
            failures.append("next_order")
    return failures


def observe(public, result):
    payload = S7.render_result(public, result)
    return ({key: deepcopy(value) for key, value in result.items() if key != "cost"}, payload)


@contextmanager
def actual_work(method, cache):
    """Patch only the chosen synchronous correctness run; always restore."""
    counts = {field: 0 for field in AUDIT_FIELDS}
    trace, policy_trace, originals = [], [], []

    def replace(obj, attr, replacement):
        # All patched module members exist. Cache methods may be class members.
        own = attr in vars(obj)
        originals.append((obj, attr, getattr(obj, attr), own))
        setattr(obj, attr, replacement)

    module = P8E.B7.P6 if method == "fresh_instrumented" else P6
    parse_original = module.BASE.parse

    def parse(text, entities, deep=False):
        stage = "detail" if deep else "cheap"
        counts[stage + "_calls"] += 1
        counts[stage + "_source_bytes"] += len(text.encode("utf-8"))
        value = parse_original(text, entities, deep=deep)
        trace.append((stage, text, tuple(entities), exact(value)))
        return value

    replace(module.BASE, "parse", parse)
    scope_owner = off_fresh if method == "fresh_uninstrumented" else module
    scope_original = scope_owner.scope_from_text

    def scope(text, entities):
        counts["contract_calls"] += 1
        counts["contract_source_bytes"] += len(text.encode("utf-8"))
        value = scope_original(text, entities)
        trace.append(("contract", text, tuple(entities), exact(value)))
        return value

    replace(scope_owner, "scope_from_text", scope)
    digest_owner = off_fresh if method.endswith("_uninstrumented") else module
    digest_original = digest_owner.counted_digest

    def snapshot(records, *args):
        raw = json.dumps(records, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
        counts["snapshot_calls"] += 1
        counts["snapshot_serialized_bytes"] += len(raw)
        result = digest_original(records, *args)
        trace.append(("snapshot", raw, result))
        return result

    replace(digest_owner, "counted_digest", snapshot)
    render_owner = off_fresh if method == "fresh_uninstrumented" else module
    render_original = render_owner.render

    def render(public, selected, status):
        result = render_original(public, selected, status)
        payload = result.encode("utf-8")
        counts["render_calls"] += 1
        counts["rendered_bytes"] += len(payload)
        trace.append(("render", tuple(selected), status, payload))
        return result

    replace(render_owner, "render", render)

    if cache is not None:
        possible_original, get_original, admit_original = cache.possible, cache.get, cache.admit

        def possible(characters, *args):
            counts["policy_possible_calls"] += 1
            value = possible_original(characters, *args)
            policy_trace.append(("possible", characters, value))
            return value

        def get(key, *args):
            counts["policy_get_calls"] += 1
            before = policy_state(cache)
            value = get_original(key, *args)
            policy_trace.append(("get", key, exact(value), before, policy_state(cache)))
            return value

        def admit(key_factory, context, raw_size, characters, values, *args):
            counts["policy_admit_calls"] += 1
            before = policy_state(cache)
            result = admit_original(key_factory, context, raw_size, characters, values, *args)
            after = policy_state(cache)
            old_keys, new_keys = {x[0] for x in before["entries"]}, {x[0] for x in after["entries"]}
            counts["policy_insertions"] += len(new_keys - old_keys)
            counts["policy_evictions"] += len(old_keys - new_keys)
            policy_trace.append(("admit", context, raw_size, characters, exact(values), before, after))
            return result

        replace(cache, "possible", possible)
        replace(cache, "get", get)
        replace(cache, "admit", admit)
    try:
        yield counts, trace, policy_trace
    finally:
        for obj, attr, original, own in reversed(originals):
            if own:
                setattr(obj, attr, original)
            else:
                delattr(obj, attr)


def summary(rows):
    gold = [r for r in rows if r["gold_evaluated"]]
    certified = [r for r in gold if r["status"] == "certified_model"]
    costs = [r["cost"] for r in rows if "cost" in r]
    state_cost_keys = {"cache_retained_bytes", "cache_entries", "cache_peak_bytes",
                       "cache_peak_entries", "directory_entries"}
    cost_keys = sorted({k for c in costs for k, v in c.items()
                        if type(v) is int and k not in state_cost_keys})
    return {
        "queries": len(rows), "streams": len({r["stream_id"] for r in rows}),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "valid_snapshots": sum(r["valid_snapshot"] for r in rows),
        "valid_supported": sum(r["valid_snapshot"] and r["supported"] for r in rows),
        "gold_evaluated": len(gold), "gold_excluded": len(rows) - len(gold),
        "gold_exclusion_reasons": dict(Counter(r["gold_exclusion_reason"] for r in rows if not r["gold_evaluated"])),
        "certified_gold_evaluated": len(certified),
        "false_certifications": sum(r["false_certification"] for r in certified),
        "containment_evaluated": sum(r["containment_violation"] is not None for r in gold),
        "containment_violations": sum(r["containment_violation"] is True for r in gold),
        "gold_projection_evaluated": sum(r["selected_gold_projection_equal"] is not None for r in gold),
        "gold_projection_failures": sum(r["selected_gold_projection_equal"] is False for r in gold),
        "structural_errors": sum(r["structural_error"] or r["schema_error"] for r in rows),
        "parity_failure_rows": sum(bool(r["parity_failures"]) for r in rows),
        "actual_full_history": sum(r["actual_full_history"] for r in rows),
        "output_bytes": sum(r["output_bytes"] for r in rows),
        "max_retained_bytes_at_step_end": max((r["policy_retained_bytes"] for r in rows), default=0),
        "max_entries_at_step_end": max((r["policy_entries"] for r in rows), default=0),
        "instrumented_peak_retained_bytes": max((c["cache_peak_bytes"] for c in costs), default=None),
        "instrumented_peak_entries": max((c["cache_peak_entries"] for c in costs), default=None),
        "separate_audit_actual_work": {k: sum(r["audit"][k] for r in rows) for k in AUDIT_FIELDS},
        "instrumented_cost": ({k: sum(c.get(k, 0) for c in costs) for k in cost_keys} if costs else None),
        "instrumented_control_events": (dict(sum((Counter(c.get("control_events", {})) for c in costs), Counter())) if costs else None),
        "boundary": "Actual invocation counters belong to a separate wrapped correctness replay, never primary timing. No synthetic cost ledger is attached to an uninstrumented result.",
    }


def evaluate(streams):
    rows, state_rows, failures = [], [], []
    for stream in streams:
        parts = {m: execution.components(m) for m in METHODS}
        caches = {m: parts[m][0]() for m in METHODS}
        for index, step in enumerate(stream["steps"]):
            observations, traces, policies, outcomes = {}, {}, {}, {}
            for method in METHODS:
                public = S7.public_of(step)
                before = deepcopy(public)
                with actual_work(method, caches[method]) as recorded:
                    result = parts[method][1](public, caches[method], step["parser_namespace"])
                counts, traces[method], policies[method] = recorded
                obs = observations[method] = observe(public, result)
                assessed = S7.assess(step, public, result)
                cost = result.get("cost")
                core = {k: v for k, v in result.items() if k != "cost"}
                row = {"stream_id": stream["id"], "family": stream["family"], "split": stream["split"],
                       "step_index": index, "step_id": step["step_id"], "method": method,
                       "namespace": step["parser_namespace"], **core, **assessed,
                       "gold_exclusion_reason": (None if assessed["gold_evaluated"] else
                           "invalid_snapshot" if not assessed["valid_snapshot"] else "undefined_membership_projection"),
                       "actual_full_history": bool(public["records"]) and result["selected"] == list(range(len(public["records"]))),
                       "rendered_sha256": hashlib.sha256(obs[1]).hexdigest(),
                       "audit": counts, "audit_trace_sha256": digest(traces[method]),
                       "audit_trace_events": len(traces[method]),
                       "policy_trace_sha256": digest(policies[method]),
                       "policy_trace_events": len(policies[method]),
                       "policy_retained_bytes": caches[method].retained_bytes if caches[method] is not None else 0,
                       "policy_entries": len(caches[method].entries) if caches[method] is not None else 0,
                       "parity_failures": []}
                if cost is not None:
                    row["cost"] = {k: v for k, v in cost.items() if k != "local_seconds"}
                    for stage in STAGES:
                        if cost[stage + "_calls"] != counts[stage + "_calls"]:
                            row["parity_failures"].append(stage + "_counter_disagreement")
                    if cost["hash_calls"] != counts["snapshot_calls"] or cost["hash_serialized_bytes"] != counts["snapshot_serialized_bytes"]:
                        row["parity_failures"].append("snapshot_counter_disagreement")
                elif method.endswith("_instrumented"):
                    row["parity_failures"].append("missing_instrumented_cost")
                if public != before:
                    row["parity_failures"].append("public_input_mutated")
                if core["output_bytes"] != len(obs[1]):
                    row["parity_failures"].append("render_length")
                if method != METHODS[0] and observations[method] != observations[METHODS[0]]:
                    row["parity_failures"].append("exact_observation_vs_fresh_instrumented")
                row["parity_failures"] += ["state_invariant:" + x for x in state_invariants(caches[method])]
                if (not assessed["valid_snapshot"] or not assessed["supported"]) and any(counts[k] for k in ("policy_possible_calls", "policy_get_calls", "policy_admit_calls", "cheap_calls", "contract_calls", "detail_calls")):
                    row["parity_failures"].append("early_exit_policy_or_parser_access")
                outcomes[method] = row
                rows.append(row)
            for on, off in ON_OFF:
                if traces[on] != traces[off]:
                    outcomes[off]["parity_failures"].append("exact_actual_execution_trace")
                if policies[on] != policies[off]:
                    outcomes[off]["parity_failures"].append("exact_policy_decision_trace")
                if outcomes[on]["audit"] != outcomes[off]["audit"]:
                    outcomes[off]["parity_failures"].append("actual_execution_counts")
            common = lambda trace: [x for x in trace if x[0] in ("snapshot", "render")]
            for method in METHODS[1:]:
                if common(traces[method]) != common(traces[METHODS[0]]):
                    outcomes[method]["parity_failures"].append("full_snapshot_and_render_trace")
            a, b = (policy_state(caches[m]) for m in ("selective_instrumented", "selective_uninstrumented"))
            state_equal = a == b  # exact bytes and values, not serialized hashes
            if not state_equal:
                outcomes["selective_uninstrumented"]["parity_failures"].append("exact_prefix_policy_state")
            state_row = {"stream_id": stream["id"], "step_index": index,
                         "exact_policy_state_equal": state_equal,
                         "exact_policy_trace_equal": policies["selective_instrumented"] == policies["selective_uninstrumented"],
                         "instrumented_state": serializable(a)}
            if not state_equal:
                state_row["uninstrumented_state"] = serializable(b)
            state_rows.append(state_row)
            for row in outcomes.values():
                if (row["parity_failures"] or row["structural_error"] or row["schema_error"]
                        or row["false_certification"] or row["containment_violation"]
                        or row["selected_gold_projection_equal"] is False):
                    failures.append({k: row[k] for k in ("stream_id", "step_index", "method", "parity_failures", "structural_error", "schema_error", "false_certification", "containment_violation", "selected_gold_projection_equal")})
    prefixes = len(state_rows)
    return {"summary": {m: summary([r for r in rows if r["method"] == m]) for m in METHODS},
            "prefixes": prefixes, "exact_observation_comparisons": 3 * prefixes,
            "exact_on_off_execution_trace_comparisons": 2 * prefixes,
            "exact_policy_state_mismatches": sum(not x["exact_policy_state_equal"] for x in state_rows),
            "exact_policy_trace_mismatches": sum(not x["exact_policy_trace_equal"] for x in state_rows),
            "failures": failures, "rows": rows, "state_rows": state_rows,
            "boundary": "Same-model correctness audit. These wrappers are excluded from primary timing; repeated steps and four method rows are not independent conversations."}


def regressions():
    """Known Phase08 holdout/development plus older regressions, not new data."""
    streams = []
    for name in ("holdout", "development"):
        corpus = json.loads((ROOT / f"research/phase08/data/{name}.json").read_text())
        for stream in corpus:
            stream["id"] = "phase08-" + name + "-" + stream["id"]
            stream["split"] = "known_development_regression"
            stream["family"] = "phase08_" + name + "_" + stream["family"]
        streams.extend(corpus)
    return streams + P8E.regressions()
