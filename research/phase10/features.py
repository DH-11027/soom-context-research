"""Offline untimed trace features. Gold/family/time are not model inputs.

The exact P9 on/off contract is rechecked before reading its instrumented
ledger as an untimed branch-count witness. Primary timing never imports this.
Full-stream trace extraction performs real work; this is not an online gate.
"""
from collections import defaultdict
from bridge import B9, E9, METHODS, evaluator, prepare

FEATURES = ("stream_constant", "queries", "records_visited", "raw_encode_bytes",
            "saved_stage_calls", "saved_stage_characters", "exact_probe_bytes",
            "encoded_context_payload_bytes", "admission_attempts", "policy_control_actions")
STAGES = ("cheap", "contract", "detail")

def vector(public_stream, fresh_rows, selective_rows, characters):
    """Explicit whitelist; no labels, IDs, gold, future annotation or timing."""
    assert len(public_stream) == len(fresh_rows) == len(selective_rows)
    f = lambda key: sum(r["audit"][key] for r in fresh_rows)
    s = lambda key: sum(r["audit"][key] for r in selective_rows)
    c = lambda key: sum(r["cost"][key] for r in selective_rows)
    context_bytes = 0
    for (public, namespace), row in zip(public_stream, selective_rows):
        if row["cost"]["control_events"].get("context_access", 0):
            context_bytes += len(B9.P8R.encode((B9.P8R.SEMANTIC_FINGERPRINT, namespace, tuple(public["entities"]))))
    result = {"stream_constant": 1, "queries": len(public_stream),
              "records_visited": f("cheap_calls"), "raw_encode_bytes": f("cheap_source_bytes"),
              "saved_stage_calls": sum(f(stage + "_calls") - s(stage + "_calls") for stage in STAGES),
              "saved_stage_characters": characters[METHODS[0]] - characters[METHODS[1]],
              "exact_probe_bytes": c("key_probe_bytes"),
              "encoded_context_payload_bytes": c("value_encode_bytes") + context_bytes,
              "admission_attempts": c("admission_attempts"),
              "policy_control_actions": c("control_actions")}
    assert tuple(result) == FEATURES
    assert all(type(x) is int and x >= 0 for x in result.values())
    return result

def character_trace(public_stream, expected):
    """Additional untimed replay; actual trace characters, not inferred bytes."""
    V = evaluator()
    result = {}
    for method in METHODS:
        factory, run = E9.components(method)
        cache = factory()
        chars = 0
        for index, (public, namespace) in enumerate(public_stream):
            with V.actual_work(method, cache) as recorded:
                value = run(public, cache, namespace)
            counts, trace, policy = recorded
            old = expected[method][index]
            assert counts == old["audit"], "Character replay invocation mismatch"
            assert V.digest(trace) == old["audit_trace_sha256"], "Character replay trace mismatch"
            assert V.digest(policy) == old["policy_trace_sha256"], "Character replay policy mismatch"
            observation_keys = ("status", "reason", "prediction", "selected", "output_bytes", "remaining_input_facts", "scope_trace")
            assert {k: v for k, v in value.items() if k != "cost"} == {
                k: old[k] for k in observation_keys if k in old}, "Character replay observation mismatch"
            chars += sum(len(event[1]) for event in trace if event[0] in STAGES)
        result[method] = chars
    return result

def extract(streams):
    V = evaluator()
    checked = V.evaluate(streams)
    assert not checked["failures"], "Preservation or gold contract failed"
    grouped = defaultdict(lambda: defaultdict(list))
    for row in checked["rows"]:
        grouped[row["stream_id"]][row["method"]].append(row)
    records = []
    for stream, public_stream in zip(streams, prepare(streams)):
        rows = grouped[stream["id"]]
        characters = character_trace(public_stream, rows)
        values = vector(public_stream, rows["fresh_instrumented"], rows["selective_instrumented"], characters)
        p8 = {method: sum(row["cost"]["phase08_work_score"] for row in rows[method])
              for method in ("fresh_instrumented", "selective_instrumented")}
        records.append({"stream_id": stream["id"], "family": stream["family"],
                        "base_stream": stream.get("base_stream"), "features": values,
                        "stage_characters": characters, "p8_fresh": p8["fresh_instrumented"],
                        "p8_selective": p8["selective_instrumented"],
                        "p8_delta": p8["selective_instrumented"] - p8["fresh_instrumented"]})
    return {"feature_order": list(FEATURES), "records": records,
            "boundary": "Offline complete-stream untimed diagnostic replay; no online availability or extraction-cost savings claim. Family/base_stream are reporting/group-CV metadata only."}, checked

