"""Freeze and evaluate text-only dependency refinement on synthetic plan logs."""

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter

import engine
from fixtures import FAMILIES, build_case, build_corpus

HERE = Path(__file__).resolve().parent
MODES = ("drop_unknown", "cheap", "eager", "lazy")


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(name):
    return hashlib.sha256((HERE / name).read_bytes()).hexdigest()


def freeze():
    if (HERE / "protocol.json").exists():
        raise SystemExit("Frozen protocol already exists; do not overwrite.")
    corpus = build_corpus()
    dump("corpus.json", corpus)
    dump("protocol.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Prototype query-directed backward dependency slicing and demand refinement, no production change",
        "n_cases": len(corpus), "paired_queries_per_case": 2,
        "splits": {"main": "12 families x 16 parameterizations", "stress": "12 families x 12 prewritten unrecognized paraphrases"},
        "input_boundary": "Engine receives only seq, opaque id, text, entity roster, query and complete snapshot digest. Gold transitions, family and split are excluded.",
        "semantic_boundary": "Controlled planned-state language. All records are authoritative plan updates or explicit quotes/noops. This does not establish real execution or unrestricted Korean semantics.",
        "methods": MODES,
        "algorithm": "One reverse pass; unknown may affect every fact; detailed parser called only for unresolved suffix on demand; strong set kills only its own field; copy follows source at that historical position; opaque relevant text falls back to full raw history",
        "costs": "Rendered UTF-8 bytes including receipt and query, detailed-parser source bytes/call count, cheap parse count; snapshot hashing reads all bytes; no real token or LLM latency measurement",
        "metrics": ["false singleton certification", "abstract answer containment", "certification coverage", "ambiguity and fallback rates", "output bytes", "detailed parse calls", "source bytes to detailed parser"],
        "checks": ["lazy/eager abstract answer parity", "raw-input-only interface", "query-specific field retention", "temporal copy", "snapshot faults", "long-prefix and long-suffix work counts"],
        "constraints": "No production API, model API, embeddings, tokenizer or DB access; no claim of optimal byte cost; no IID confidence intervals",
        "hashes": {name: sha(name) for name in ("engine.py", "fixtures.py", "study.py", "corpus.json")},
    })
    print(json.dumps({"frozen_cases": len(corpus), "query_cases": 2 * len(corpus)}, ensure_ascii=False))


def concrete(case):
    """Independent exact branch semantics. Does NOT parse natural language."""
    facts = engine.facts(case["public"]["entities"])
    positions = {f: i for i, f in enumerate(facts)}
    states = {tuple(None for _ in facts)}
    for ev in case["gold"]:
        new_states = set()
        for state in states:
            kind = ev["kind"]
            if kind == "noop":
                new_states.add(state)
                continue
            if kind == "maybe_set":
                for target in ev["targets"]:
                    new = list(state)
                    new[positions[tuple(target)]] = ev["value"]
                    new_states.add(tuple(new))
                continue
            new = list(state)
            pos = positions[tuple(ev["target"])]
            if kind == "set":
                new[pos] = ev["value"]
            elif kind == "add":
                new[pos] += ev["value"]
            elif kind == "copy":
                new[pos] = state[positions[tuple(ev["source"])]]
            else:
                raise ValueError(kind)
            new_states.add(tuple(new))
        states = new_states
    return {f"{f[0]}.{f[1]}": {s[i] for s in states} for i, f in enumerate(facts)}


def evaluate(case, query, mode):
    public = {**case["public"], "query": query}
    result = engine.run(public, mode)
    gold = concrete(case)
    false_cert = False
    containment = True
    for fact, values in result["prediction"].items():
        if values is not None and not gold[fact] <= set(values):
            containment = False
        if result["status"] == "certified_model" and set(values) != gold[fact]:
            false_cert = True
    full_text = engine.render(public["records"], list(range(len(public["records"]))), query, public["snapshot"], "full_history")
    return {"case_id": case["id"], "split": case["split"], "family": case["family"], "query": query,
            "mode": mode, **result, "false_certification": false_cert,
            "containment_violation": not containment,
            "full_bytes": len(full_text.encode("utf-8")), "records": len(public["records"])}


def summarize(rows):
    result = {}
    for split in ("main", "stress"):
        result[split] = {}
        for mode in MODES:
            sample = [r for r in rows if r["split"] == split and r["mode"] == mode]
            total_full = sum(r["full_bytes"] for r in sample)
            total_out = sum(r["output_bytes"] for r in sample)
            total_detail = sum(r["detail_source_bytes"] for r in sample)
            calls = sum(r["detail_calls"] for r in sample)
            result[split][mode] = {
                "question_cases": len(sample), "status_counts": dict(Counter(r["status"] for r in sample)),
                "false_certifications": sum(r["false_certification"] for r in sample),
                "containment_violations": sum(r["containment_violation"] for r in sample),
                "mean_output_bytes": mean(r["output_bytes"] for r in sample),
                "mean_full_bytes": mean(r["full_bytes"] for r in sample),
                "output_byte_reduction_percent": 100 * (1 - total_out / total_full),
                "mean_detail_calls": mean(r["detail_calls"] for r in sample),
                "total_detail_calls": calls, "detail_source_bytes": total_detail,
                "mean_cheap_reads": mean(r["cheap_reads"] for r in sample),
                "bytes_after_output_plus_detail": total_out + total_detail,
                "output_plus_detail_proxy_reduction_percent": 100 * (1 - (total_out + total_detail) / total_full),
                "per_call_overhead_break_even_bytes": (total_full - total_out - total_detail) / calls if calls else None,
            }
    return result


def fault_checks():
    case = build_case("absolute_reset", 0)
    public = {**case["public"], "query": case["queries"][0]}
    results = {}
    missing = copy.deepcopy(public)
    missing["records"].pop(-1)
    results["dropped_tail_record"] = engine.run(missing)["status"]
    modified = copy.deepcopy(public)
    modified["records"][-1]["text"] += " 정정"
    results["modified_record"] = engine.run(modified)["status"]
    reordered = copy.deepcopy(public)
    reordered["records"][-1], reordered["records"][-2] = reordered["records"][-2], reordered["records"][-1]
    results["reordered_records"] = engine.run(reordered)["status"]
    assert set(results.values()) == {"integrity_failure"}
    # An internally consistent old snapshot cannot prove no newer archive exists.
    old = copy.deepcopy(public)
    newer = copy.deepcopy(public)
    seq = len(newer["records"])
    newer["records"].append({"seq": seq, "id": "fresh-append", "text": "가람 모임 시간은 22시로 확정해줘."})
    newer["snapshot"] = engine.snapshot(newer["records"])
    old_result, fresh_result = engine.run(old), engine.run(newer)
    assert old_result["status"] == fresh_result["status"] == "certified_model"
    assert old_result["prediction"] != fresh_result["prediction"]
    results["internally_consistent_stale_snapshot"] = {"old_prediction": old_result["prediction"], "new_prediction": fresh_result["prediction"], "detected_without_fresh_head": False}
    return results


def scaling():
    rows = []
    for length in (16, 64, 256, 1024, 4096):
        for pattern in ("irrelevant_prefix", "irrelevant_suffix"):
            case = build_case("absolute_reset", 0, prefix_length=length if pattern == "irrelevant_prefix" else 0)
            if pattern == "irrelevant_suffix":
                for _ in range(length):
                    seq = len(case["public"]["records"])
                    case["public"]["records"].append({"seq": seq, "id": f"tail-{seq}", "text": "참고로 남기는 감상이야. 오늘 하늘빛이 참 맑았어."})
                case["public"]["snapshot"] = engine.snapshot(case["public"]["records"])
            public = {**case["public"], "query": case["queries"][0]}
            for mode in ("eager", "lazy"):
                start = perf_counter()
                outcome = engine.run(public, mode)
                elapsed = perf_counter() - start
                rows.append({"length": length, "pattern": pattern, "mode": mode,
                             "records": len(public["records"]), "cheap_reads": outcome["cheap_reads"],
                             "detail_calls": outcome["detail_calls"], "status": outcome["status"],
                             "seconds_one_local_run": elapsed})
    return rows


def run():
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    for name, value in protocol["hashes"].items():
        assert sha(name) == value, f"Frozen source changed: {name}"
    corpus = json.loads((HERE / "corpus.json").read_text(encoding="utf-8"))
    rows = []
    parity = 0
    for case in corpus:
        for query in case["queries"]:
            outcomes = {mode: evaluate(case, query, mode) for mode in MODES}
            lazy, eager = outcomes["lazy"], outcomes["eager"]
            assert (lazy["status"], lazy["prediction"], lazy["selected"]) == (eager["status"], eager["prediction"], eager["selected"])
            assert lazy["detail_calls"] <= eager["detail_calls"]
            for mode in ("cheap", "eager", "lazy"):
                assert not outcomes[mode]["false_certification"]
                assert not outcomes[mode]["containment_violation"]
            parity += 1
            rows.extend(outcomes.values())
    family_rows = []
    for split in ("main", "stress"):
        for family in FAMILIES:
            sample = [r for r in rows if r["split"] == split and r["family"] == family and r["mode"] == "lazy"]
            family_rows.append({"split": split, "family": family, "cases": len(sample),
                                "statuses": dict(Counter(r["status"] for r in sample)),
                                "mean_detail_calls": mean(r["detail_calls"] for r in sample)})
    result = {"protocol_sha256": sha("protocol.json"), "summary": summarize(rows),
              "families": family_rows, "rows": rows, "fault_checks": fault_checks(),
              "scaling": scaling(), "checks": {"frozen_hashes_match": True, "eager_lazy_parity_queries": parity,
                  "no_false_certification_for_conservative_modes_in_defined_corpus": True,
                  "lazy_detail_calls_never_exceed_eager": True},
              "limits": ["Synthetic controlled plan language, not free Korean or actual execution", "Same author designed grammar and corpus", "No independent model judge or tokenization", "Hash integrity does not prove current head or semantic correctness", "Abstract product domain can lose cross-entity correlations", "No byte-optimality theorem"]}
    dump("results.json", result)
    print(json.dumps({k: result[k] for k in ("summary", "fault_checks", "checks")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["--freeze"]:
        freeze()
    elif sys.argv[1:] == ["--run"]:
        run()
    else:
        argparse.ArgumentParser(description=__doc__).error("Use --freeze or --run")
