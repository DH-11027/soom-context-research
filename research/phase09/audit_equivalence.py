"""Independent same-model erasure/state audit; NEVER imported by timed calls.

It deliberately instruments parser/hash calls during correctness replay only.
Direct objects/bytes are compared; SHA-256 below is a compact receipt, not the
equality predicate. The historical Phase08 modules are used without modification.
"""
from collections import Counter
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from bindings import E8, P6, ROOT
import runtime_off as OFF

METHODS = ("fresh_instrumented", "fresh_uninstrumented",
           "selective_instrumented", "selective_uninstrumented")
STAGES = ("cheap", "contract", "detail")
OBS_KEYS = ("status", "reason", "prediction", "selected", "output_bytes",
            "remaining_input_facts", "scope_trace")
STATE_KEYS = ("directory", "max_entries", "max_bytes", "retained_bytes", "next_order")
ENTRY_KEYS = ("stages", "size", "characters", "surplus", "hits", "order")


def canonical(value):
    """Type-preserving canonical data for direct comparison, independent of OFF."""
    if isinstance(value, bytes):
        return ("bytes", value.hex())
    if isinstance(value, Mapping):
        return ("mapping", tuple(sorted(((canonical(k), canonical(v)) for k, v in value.items()), key=repr)))
    if isinstance(value, tuple):
        return ("tuple", tuple(map(canonical, value)))
    if isinstance(value, list):
        return ("list", tuple(map(canonical, value)))
    if isinstance(value, (set, frozenset)):
        return ("frozenset" if isinstance(value, frozenset) else "set", tuple(sorted(map(canonical, value), key=repr)))
    return (type(value).__name__, value)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def observation(public, result):
    payload = E8.S7.render_result(public, result)
    # Presence is observable: an absent field is not the same as field=None.
    # Unexpected result fields must not silently disappear through a whitelist.
    return canonical({key: value for key, value in result.items() if key != "cost"}), payload


def policy_state(cache):
    if cache is None:
        return None
    return canonical({
        "config_and_counters": {key: getattr(cache, key) for key in STATE_KEYS},
        "entries_in_iteration_order": [(key, {name: item[name] for name in ENTRY_KEYS})
                                        for key, item in cache.entries.items()],
        "directory_in_iteration_order": list(cache.lengths.items()),
    })


def immutable_value(value):
    if isinstance(value, Mapping):
        return isinstance(value, MappingProxyType) and all(immutable_value(v) for v in value.values())
    if isinstance(value, tuple):
        return all(immutable_value(v) for v in value)
    if isinstance(value, frozenset):
        return all(immutable_value(v) for v in value)
    return not isinstance(value, (list, set, dict, bytearray))


def state_errors(cache):
    if cache is None:
        return []
    errors = []
    entries = list(cache.entries.items())
    if cache.retained_bytes != sum(item["size"] for _, item in entries):
        errors.append("retained_sum")
    if cache.lengths != Counter(item["characters"] for _, item in entries):
        errors.append("directory_contents")
    if not (0 <= cache.retained_bytes <= cache.max_bytes and len(entries) <= cache.max_entries):
        errors.append("capacity")
    orders = [item["order"] for _, item in entries]
    if len(orders) != len(set(orders)) or any(order >= cache.next_order for order in orders):
        errors.append("insertion_order")
    for key, item in entries:
        if len(key) != 2 or any(not isinstance(x, bytes) for x in key):
            errors.append("exact_key_types")
            continue
        context, raw = key
        if item["characters"] != len(raw.decode("utf-8")):
            errors.append("character_length")
        if set(item["stages"]) != set(STAGES) or not immutable_value(item["stages"]):
            errors.append("complete_immutable_stages")
        payload = sum(length for _, length in item["stages"].values())
        if item["size"] != len(context) + len(raw) + payload + 80:
            errors.append("logical_size")
        if item["surplus"] != len(raw) - len(context) - payload - 64:
            errors.append("surplus")
        if not 0 <= item["hits"] <= 255:
            errors.append("bounded_hits")
    return errors


@contextmanager
def actual_calls():
    """Trace the called pure functions and full digest inputs, outside timing."""
    calls, hashes, originals = [], [], []
    semantic_modules = []
    for module in (P6, E8.C7.P6, OFF.P6):
        if all(module is not old for old in semantic_modules):
            semantic_modules.append(module)
    bases = []
    for module in semantic_modules:
        if all(module.BASE is not old for old in bases):
            bases.append(module.BASE)
    try:
        for base in bases:
            original = base.parse
            def parse(text, entities, deep=False, _original=original):
                calls.append(("detail" if deep else "cheap", text, tuple(entities)))
                return _original(text, entities, deep=deep)
            originals.append((base, "parse", original))
            base.parse = parse
        # OFF fresh keeps a direct alias of scope_from_text; patch that public
        # module binding too, rather than falsely counting only P6 lookups.
        for module in [*semantic_modules, OFF]:
            original = module.scope_from_text
            def scope(text, entities, _original=original):
                calls.append(("contract", text, tuple(entities)))
                return _original(text, entities)
            originals.append((module, "scope_from_text", original))
            module.scope_from_text = scope
        original_sha = hashlib.sha256
        def sha(data=b"", *args, **kwargs):
            hashes.append(bytes(data))
            return original_sha(data, *args, **kwargs)
        originals.append((hashlib, "sha256", original_sha))
        hashlib.sha256 = sha
        yield calls, hashes
    finally:
        for obj, name, original in reversed(originals):
            setattr(obj, name, original)
        assert all(getattr(obj, name) is original for obj, name, original in originals)


def restoration_audit():
    """An exceptional audit exit must not leak hooks into later timing."""
    bindings = [(P6.BASE, "parse"), (E8.C7.P6.BASE, "parse"),
                (P6, "scope_from_text"), (E8.C7.P6, "scope_from_text"),
                (OFF, "scope_from_text"), (hashlib, "sha256")]
    before = [getattr(obj, name) for obj, name in bindings]
    class AuditSentinel(Exception):
        pass
    try:
        with actual_calls():
            raise AuditSentinel()
    except AuditSentinel:
        pass
    assert all(getattr(obj, name) is original for (obj, name), original in zip(bindings, before))
    return {"exceptional_exit_bindings_restored": len(bindings), "identity_checks_passed": True}


def run_method(method, public, cache, namespace):
    if method == "fresh_instrumented":
        return E8.run("fresh", public, None, namespace)
    if method == "fresh_uninstrumented":
        return OFF.run_fresh(public)
    if method == "selective_instrumented":
        return E8.run("selective", public, cache, namespace)
    if method == "selective_uninstrumented":
        return OFF.run_selective(public, cache, namespace=namespace)
    raise ValueError(method)


def clean(value):
    """Remove historical time fields only; preserve all measured ledgers."""
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items() if key != "local_seconds"}
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def evaluate(streams):
    rows, failures = [], []
    for stream in streams:
        caches = {"fresh_instrumented": None, "fresh_uninstrumented": None,
                  "selective_instrumented": E8.runtime.SelectiveCache(),
                  "selective_uninstrumented": OFF.SelectiveCache()}
        for index, step in enumerate(stream["steps"]):
            outcomes, observations, traces, states = {}, {}, {}, {}
            for method in METHODS:
                public = {key: deepcopy(step["public"][key])
                          for key in ("records", "entities", "snapshot", "query")}
                before_public = deepcopy(public)
                before_state = policy_state(caches[method])
                with actual_calls() as trace:
                    result = run_method(method, public, caches[method], step["parser_namespace"])
                calls, hashes = trace
                assessed = E8.S7.assess(step, public, result)
                observed = observation(public, result)
                state = policy_state(caches[method])
                errors = state_errors(caches[method])
                if public != before_public:
                    errors.append("public_mutation")
                if result["status"] in ("integrity_failure", "unsupported_query") and state != before_state:
                    errors.append("early_exit_state_mutation")
                counts = {stage: sum(call[0] == stage for call in calls) for stage in STAGES}
                source_bytes = {stage: sum(len(call[1].encode()) for call in calls if call[0] == stage)
                                for stage in STAGES}
                if "cost" in result:
                    if any(counts[stage] != result["cost"][stage + "_calls"] for stage in STAGES):
                        errors.append("actual_calls_vs_original_ledger")
                    if len(hashes) != result["cost"]["hash_calls"] or sum(map(len, hashes)) != result["cost"]["hash_serialized_bytes"]:
                        errors.append("actual_hash_vs_original_ledger")
                else:
                    if any(key in result for key in ("control_events", "local_seconds", "phase07_work_proxy")):
                        errors.append("off_ledger_leak")
                if result["output_bytes"] != len(observed[1]):
                    errors.append("render_length")
                row = {"stream_id": stream["id"], "family": stream["family"],
                       "step_index": index, "method": method, **clean(result), **assessed,
                       "actual_parser_calls": counts, "actual_parser_source_bytes": source_bytes,
                       "actual_hash_calls": len(hashes), "actual_hash_bytes": sum(map(len, hashes)),
                       "actual_call_sequence_sha256": digest(canonical(calls)),
                       "actual_hash_inputs_sha256": digest(canonical(hashes)),
                       "observation_sha256": digest(observed[0]),
                       "rendered_sha256": hashlib.sha256(observed[1]).hexdigest(),
                       "policy_state_sha256": digest(state), "policy_errors": errors,
                       "parity_errors": []}
                outcomes[method], observations[method], traces[method], states[method] = row, observed, trace, state
            for method in METHODS:
                row = outcomes[method]
                if observations[method] != observations["fresh_instrumented"]:
                    row["parity_errors"].append("exact_observation")
                if method.endswith("_uninstrumented"):
                    reference = method.replace("_uninstrumented", "_instrumented")
                    if traces[method] != traces[reference]:
                        row["parity_errors"].append("exact_parser_hash_trace")
                    if states[method] != states[reference]:
                        row["parity_errors"].append("exact_policy_state")
                if (row["policy_errors"] or row["parity_errors"] or row["structural_error"] or
                        row["schema_error"] or row["false_certification"] or row["containment_violation"] or
                        row["selected_gold_projection_equal"] is False):
                    failures.append({key: row[key] for key in ("stream_id", "step_index", "method", "policy_errors",
                         "parity_errors", "structural_error", "schema_error", "false_certification",
                         "containment_violation", "selected_gold_projection_equal")})
                rows.append(row)
    return {"summary": summarize(rows), "failures": failures, "rows": rows,
            "audit_boundary": "Parser/hash monkeypatch used only in this untimed audit; same-model role separation; no external semantic validation."}


def summarize(rows):
    result = {}
    for method in METHODS:
        subset = [row for row in rows if row["method"] == method]
        result[method] = {
            "steps": len(subset), "streams": len({row["stream_id"] for row in subset}),
            "status_counts": dict(sorted(Counter(row["status"] for row in subset).items())),
            "valid_snapshots": sum(row["valid_snapshot"] for row in subset),
            "valid_supported": sum(row["valid_snapshot"] and row["supported"] for row in subset),
            "gold_evaluated": sum(row["gold_evaluated"] for row in subset),
            "certified_gold": sum(row["gold_evaluated"] and row["status"] == "certified_model" for row in subset),
            "false_certifications": sum(row["false_certification"] for row in subset),
            "containment_evaluated": sum(row["containment_violation"] is not None for row in subset),
            "containment_violations": sum(row["containment_violation"] is True for row in subset),
            "projection_evaluated": sum(row["selected_gold_projection_equal"] is not None for row in subset),
            "projection_failures": sum(row["selected_gold_projection_equal"] is False for row in subset),
            "observation_failures": sum("exact_observation" in row["parity_errors"] for row in subset),
            "state_failures": sum("exact_policy_state" in row["parity_errors"] for row in subset),
            "call_trace_failures": sum("exact_parser_hash_trace" in row["parity_errors"] for row in subset),
            "structural_errors": sum(row["structural_error"] or row["schema_error"] for row in subset),
            "policy_errors": sum(bool(row["policy_errors"]) for row in subset),
            "actual_parser_calls": {stage: sum(row["actual_parser_calls"][stage] for row in subset) for stage in STAGES},
            "actual_parser_source_bytes": sum(sum(row["actual_parser_source_bytes"].values()) for row in subset),
            "actual_hash_calls": sum(row["actual_hash_calls"] for row in subset),
            "actual_hash_bytes": sum(row["actual_hash_bytes"] for row in subset),
            "output_bytes": sum(row["output_bytes"] for row in subset),
        }
    return result


def mutation_audit():
    """Ensure answers alone cannot pass policy-state audit; no mutant is timed."""
    cache = E8.runtime.SelectiveCache()
    value = MappingProxyType({"kind": "noop"})
    stages = MappingProxyType({name: (value, 15) for name in STAGES})
    key = (b"context", b"r" * 1024)
    cache.entries[key] = {"stages": stages, "size": 1156, "characters": 1024,
                          "surplus": 908, "hits": 3, "order": 0}
    cache.lengths[1024] = 1
    cache.retained_bytes, cache.next_order = 1156, 1
    reference = policy_state(cache)
    mutations = {
        "hit_update_removed": lambda: cache.entries[key].__setitem__("hits", 2),
        "surplus_changed": lambda: cache.entries[key].__setitem__("surplus", 907),
        "entry_order_changed": lambda: cache.entries[key].__setitem__("order", 1),
        "next_order_changed": lambda: setattr(cache, "next_order", 2),
        "directory_changed": lambda: cache.lengths.__setitem__(1024, 2),
        "retained_changed": lambda: setattr(cache, "retained_bytes", 1155),
        "exact_raw_changed_same_length": lambda: cache.entries.__setitem__((b"context", b"s" * 1024), cache.entries.pop(key)),
        "stage_value_changed": lambda: cache.entries[key].__setitem__("stages", MappingProxyType({name: (MappingProxyType({"kind": "havoc"}), 15) for name in STAGES})),
    }
    detected = []
    for name, mutate in mutations.items():
        saved_entries = {k: dict(v) for k, v in cache.entries.items()}
        saved_lengths = Counter(cache.lengths)
        saved_retained, saved_next = cache.retained_bytes, cache.next_order
        mutate()
        assert policy_state(cache) != reference, name
        detected.append(name)
        cache.entries = saved_entries
        cache.lengths = saved_lengths
        cache.retained_bytes, cache.next_order = saved_retained, saved_next
    result = {"status": "integrity_failure", "reason": None, "prediction": {},
              "selected": [], "output_bytes": 0, "scope_trace": []}
    observed = observation({}, result)
    observation_mutants = {
        "missing_reason_vs_explicit_none": {k: v for k, v in result.items() if k != "reason"},
        "missing_prediction": {k: v for k, v in result.items() if k != "prediction"},
        "unexpected_result_field": dict(result, unexpected=None),
    }
    for name, mutant in observation_mutants.items():
        assert observation({}, mutant) != observed, name
    return {"state_mutants_detected": detected, "count": len(detected),
            "observation_mutants_detected": list(observation_mutants), "observation_count": len(observation_mutants),
            "total_mutants": len(detected) + len(observation_mutants),
            "boundary": "Deliberately corrupted synthetic resident state checks the auditor, not a defect observed in the runtime."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "research/phase08/data/holdout.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    streams = json.loads(args.data.read_text())
    result = evaluate(streams)
    result["mutation_audit"] = mutation_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summary": result["summary"], "failures": len(result["failures"]),
                      "mutation_audit": result["mutation_audit"]}, ensure_ascii=False))
    if result["failures"]:
        raise SystemExit(1)
