"""Descriptive serialization/length distribution, not independent sample counts."""
from collections import Counter
import json


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def profile(streams):
    steps = [s for stream in streams for s in stream["steps"]]
    valid = [s for s in steps if s["expected_integrity"] == "valid"]
    gold = [s for s in steps if s["gold_applicable"] and s["expected_integrity"] == "valid"]
    def duplicates(subset):
        return {
            "steps": len(subset),
            "exact_records": len({canonical(s["public"]["records"]) for s in subset}),
            "ordered_raw_histories": len({canonical([r["text"] for r in s["public"]["records"]]) for s in subset}),
            "raw_plus_ordered_entities": len({canonical(([r["text"] for r in s["public"]["records"]], s["public"]["entities"])) for s in subset}),
            "public_plus_namespace": len({canonical((s["public"], s["parser_namespace"])) for s in subset}),
        }
    families = {}
    for family in sorted({s["family"] for s in streams}):
        ss = [s for s in streams if s["family"] == family]
        qq = [q for s in ss for q in s["steps"]]
        raw = [r["text"] for q in qq for r in q["public"]["records"]]
        lengths = [len(t.encode()) for t in raw]
        bin_name = lambda n: "lt_1k" if n < 1000 else "1k_to_8k" if n < 8000 else "8k_to_55k" if n < 55000 else "ge_55k"
        snapshot_bytes = sum(len(canonical(q["public"]["records"]).encode()) for q in qq)
        families[family] = {"streams": len(ss), **duplicates(qq),
            "record_occurrences": len(raw), "distinct_raw_strings": len(set(raw)),
            "record_utf8_bytes_min": min(lengths, default=0), "record_utf8_bytes_max": max(lengths, default=0),
            "record_utf8_bytes_sum": sum(lengths), "snapshot_serialization_bytes_all_inputs": snapshot_bytes,
            "length_bin_occurrences": dict(Counter(bin_name(n) for n in lengths)),
            "distinct_exact_typed_events": len({canonical(q["gold"]) for q in qq if q["gold_applicable"] and q["expected_integrity"] == "valid"}),
            "step_counts_per_stream": [len(s["steps"]) for s in ss]}
    return {"streams": len(streams), "steps": len(steps), "all": duplicates(steps), "valid": duplicates(valid),
        "gold_steps": len(gold), "distinct_exact_typed_events": len({canonical(q["gold"]) for q in gold}),
        "families": families,
        "identity_definition": "canonical sorted-key JSON; list order, names and numeric constants preserved; not semantic equivalence or statistical independence",
        "length_sum_definition": "occurrences across snapshots, not unique source bytes or measured parser scanning",
        "natural_language_semantics": "not externally evaluated; long quote payload is controlled-grammar noop"}

