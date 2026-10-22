"""Post-freeze author-side data/raw-artifact recount; no runtime imports.

No new selector or timing execution. This is another same-model artifact audit,
not external semantic validation. The persisted state has one live-comparison
witness plus equality flags, not independently stored on/off states.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
METHODS = ("fresh_instrumented", "fresh_uninstrumented", "selective_instrumented", "selective_uninstrumented")
BIG = {"long_cheap", "long_deep_repeat", "long_deep_churn", "fit_working_set",
       "pressure_working_set", "phase_shift", "same_length_misses", "revisions_copy_context",
       "integrity_unsupported_recovery"}
OBS = ("status", "reason", "prediction", "selected", "output_bytes", "remaining_input_facts", "scope_trace", "rendered_sha256")


def load(path):
    b = path.read_bytes()
    return json.loads(gzip.decompress(b) if path.suffix == ".gz" else b)


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def identities(steps):
    return {"steps": len(steps),
        "exact_records": len({canonical(q["public"]["records"]) for q in steps}),
        "ordered_raw_histories": len({canonical([r["text"] for r in q["public"]["records"]]) for q in steps}),
        "raw_plus_ordered_entities": len({canonical([[r["text"] for r in q["public"]["records"]], q["public"]["entities"]]) for q in steps}),
        "public_plus_namespace": len({canonical([q["public"], q["parser_namespace"]]) for q in steps})}


def recount_timing(timing):
    rounds = timing["rounds"]
    medians = {m: median(r["seconds"][m] for r in rounds) for m in METHODS}
    assert len(rounds) == 40
    for m in METHODS:
        assert medians[m] == timing["methods"][m]["median_seconds"]
    pairs = {"primary": (METHODS[3], METHODS[1]), "instrumented": (METHODS[2], METHODS[0]),
             "fresh_erasure": (METHODS[1], METHODS[0]), "selective_erasure": (METHODS[3], METHODS[2])}
    comparisons = {}
    for name, (candidate, reference) in pairs.items():
        ratio = math.exp(median(math.log(r["seconds"][candidate]) - math.log(r["seconds"][reference]) for r in rounds))
        assert math.isclose(ratio, timing["comparisons"][name]["paired_median_ratio"], rel_tol=1e-12)
        comparisons[name] = {"paired_ratio": ratio, "paired_percent": 100 * (ratio - 1)}
    stream_table = {}
    family_table = {}
    total_fresh = total_selective = cold_fresh = cold_selective = 0.0
    wins, losses, cold_wins = [], [], []
    for sid, item in timing["diagnostics"].items():
        whole = item["whole_stream"]["samples_seconds"]
        cold = item["first_step_cold"]["samples_seconds"]
        assert all(len(values) == 8 for values in whole.values())
        assert all(len(values) == 8 for values in cold.values())
        f, s = median(whole[METHODS[1]]), median(whole[METHODS[3]])
        cf, cs = median(cold[METHODS[1]]), median(cold[METHODS[3]])
        for name, values in (("whole_stream", whole), ("first_step_cold", cold)):
            for method, values_m in values.items():
                assert median(values_m) == item[name]["methods"][method]["median_seconds"]
        total_fresh += f
        total_selective += s
        cold_fresh += cf
        cold_selective += cs
        (wins if s < f else losses).append(sid)
        if cs < cf:
            cold_wins.append(sid)
        stream_table[sid] = {"family": item["family"], "fresh_seconds": f, "selective_seconds": s,
                             "whole_percent": 100 * (s / f - 1), "first_step_percent": 100 * (cs / cf - 1)}
        family = family_table.setdefault(item["family"], {"fresh_seconds": 0.0, "selective_seconds": 0.0})
        family["fresh_seconds"] += f
        family["selective_seconds"] += s
    for item in family_table.values():
        item["percent"] = 100 * (item["selective_seconds"] / item["fresh_seconds"] - 1)
    big_fresh = sum(v["fresh_seconds"] for k, v in family_table.items() if k in BIG)
    return {"method_medians_seconds": medians, "comparisons": comparisons,
        "ratio_of_marginal_medians": medians[METHODS[3]] / medians[METHODS[1]],
        "diagnostic_stream_wins": wins, "diagnostic_stream_losses": losses,
        "diagnostic_cold_stream_wins": cold_wins,
        "diagnostic_sum_stream_medians": {"fresh": total_fresh, "selective": total_selective,
                                           "percent": 100 * (total_selective / total_fresh - 1)},
        "diagnostic_sum_first_step_medians": {"fresh": cold_fresh, "selective": cold_selective,
                                              "percent": 100 * (cold_selective / cold_fresh - 1)},
        "big_family_diagnostic_fresh_share": big_fresh / total_fresh,
        "families": family_table, "streams": stream_table,
        "boundary": "stream/cold diagnostics are separate executions, not an additive decomposition of primary timing; intervals not recomputed here"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reproduction-timing", type=Path, default=HERE / "reproduction_timing.json")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    paths = {"corpus": HERE / "data/holdout.json.gz", "rows": HERE / "results/holdout_rows.json.gz",
             "states": HERE / "results/holdout_states.json.gz", "profile": HERE / "results/data_profile.json",
             "summary": HERE / "results/holdout_results.json", "timing": HERE / "results/timing.json",
             "reproduction_timing": args.reproduction_timing}
    corpus, rows, states = (load(paths[k]) for k in ("corpus", "rows", "states"))
    profile, summary = load(paths["profile"]), load(paths["summary"])
    steps = {(s["id"], i): q for s in corpus for i, q in enumerate(s["steps"])}
    valid = [q for q in steps.values() if q["expected_integrity"] == "valid"]
    gold = [q for q in steps.values() if q["gold_applicable"]]
    assert len(steps) == 432 and len(rows) == 1728 and len(states) == 432
    duplicate_counts = {"all": identities(list(steps.values())), "valid": identities(valid),
                        "gold_exact_typed_arrays": len({canonical(q["gold"]) for q in gold})}
    assert duplicate_counts["all"] == profile["all"] and duplicate_counts["valid"] == profile["valid"]
    assert duplicate_counts["gold_exact_typed_arrays"] == profile["distinct_exact_typed_events"]
    grouped = {}
    for r in rows:
        key = (r["stream_id"], r["step_index"])
        assert r["method"] not in grouped.setdefault(key, {})
        grouped[key][r["method"]] = r
        q = steps[key]
        assert r["valid_snapshot"] == (q["expected_integrity"] == "valid")
        assert r["gold_evaluated"] == q["gold_applicable"]
        assert r["supported"] == q["question_contract"]["supported"]
        assert not r["parity_failures"] and not r["schema_error"] and not r["structural_error"]
        assert not r["false_certification"] and not r["containment_violation"]
        assert r["selected_gold_projection_equal"] is not False
    for pair in grouped.values():
        assert set(pair) == set(METHODS)
        reference = {k: pair[METHODS[0]][k] for k in OBS if k in pair[METHODS[0]]}
        assert all({k: r[k] for k in OBS if k in r} == reference for r in pair.values())
        for on, off in ((METHODS[0], METHODS[1]), (METHODS[2], METHODS[3])):
            for key in ("audit", "audit_trace_sha256", "policy_trace_sha256", "policy_retained_bytes", "policy_entries"):
                assert pair[on][key] == pair[off][key]
    for record in states:
        assert record["exact_policy_state_equal"] and record["exact_policy_trace_equal"]
        state = record["instrumented_state"]
        rr = grouped[record["stream_id"], record["step_index"]][METHODS[3]]
        assert state["retained_bytes"] == rr["policy_retained_bytes"]
        assert len(state["entries"]) == rr["policy_entries"]
        assert sum(e[2] for e in state["entries"]) == state["retained_bytes"] <= 65536
        assert sorted(Counter(e[3] for e in state["entries"]).items()) == [tuple(t) for t in state["lengths"]]
    methods = {}
    families = {}
    for method in METHODS:
        rr = [r for r in rows if r["method"] == method]
        counts = {"queries": len(rr), "status_counts": dict(Counter(r["status"] for r in rr)),
            "valid_supported": sum(r["valid_snapshot"] and r["supported"] for r in rr),
            "gold_evaluated": sum(r["gold_evaluated"] for r in rr),
            "certified_gold_evaluated": sum(r["gold_evaluated"] and r["status"] == "certified_model" for r in rr),
            "containment_evaluated": sum(r["containment_violation"] is not None for r in rr),
            "gold_projection_evaluated": sum(r["selected_gold_projection_equal"] is not None for r in rr),
            "actual_full_history": sum(r["actual_full_history"] for r in rr),
            "output_bytes": sum(r["output_bytes"] for r in rr)}
        for k, v in counts.items():
            assert summary["summary"][method][k] == v, (method, k)
        counts["audit_sums"] = {k: sum(r["audit"][k] for r in rr) for k in rr[0]["audit"]}
        assert counts["audit_sums"] == summary["summary"][method]["separate_audit_actual_work"]
        if "cost" in rr[0]:
            costs = {k: sum(r["cost"][k] for r in rr) for k in summary["summary"][method]["instrumented_cost"]}
            assert costs == summary["summary"][method]["instrumented_cost"]
            counts["cost_sums"] = costs
        methods[method] = counts
    for family in sorted({s["family"] for s in corpus}):
        family_rows = [r for r in rows if r["family"] == family]
        families[family] = {m: {"P7": sum(r["cost"]["phase07_work_proxy"] for r in family_rows if r["method"] == m),
                                  "P8": sum(r["cost"]["phase08_work_score"] for r in family_rows if r["method"] == m),
                                  "calls": sum(sum(r["audit"][s + "_calls"] for s in ("cheap", "contract", "detail"))
                                               for r in family_rows if r["method"] == m)}
                           for m in (METHODS[0], METHODS[2])}
    originals, reproduction = (recount_timing(load(paths[k])) for k in ("timing", "reproduction_timing"))
    big_share = sum(v[METHODS[0]]["P7"] for f, v in families.items() if f in BIG) / methods[METHODS[0]]["cost_sums"]["phase07_work_proxy"]
    out = {"passed": True, "rows": len(rows), "prefixes": len(states), "duplicates": duplicate_counts,
        "methods": methods, "families_cost": families, "big_families": sorted(BIG),
        "big_family_fresh_P7_share": big_share,
        "original_timing": originals, "reproduction_timing": reproduction,
        "diagnostic_wins_both_sessions": sorted(set(originals["diagnostic_stream_wins"]) & set(reproduction["diagnostic_stream_wins"])),
        "diagnostic_sign_flip_streams": sorted(set(originals["diagnostic_stream_wins"]) ^ set(reproduction["diagnostic_stream_wins"])),
        "source_sha256": {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()},
        "boundary": "same-model data author raw-artifact recount, not external independent semantic validation; no new timing or selector execution"}
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": True, "rows": len(rows), "state_records": len(states),
        "big_family_fresh_P7_share": big_share,
        "original_diagnostic_wins": len(originals["diagnostic_stream_wins"]),
        "reproduction_diagnostic_wins": len(reproduction["diagnostic_stream_wins"]),
        "both_diagnostic_wins": len(out["diagnostic_wins_both_sessions"]),
        "sign_flips": len(out["diagnostic_sign_flip_streams"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
