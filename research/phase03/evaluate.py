"""Development, local protocol freeze, then separate synthetic evaluations.

Run --dev, --freeze, --test in that order. --test refuses changed source hashes.
The author wrote all templates: this is a local audit trail, not preregistration
with an independent institution or a blind external benchmark.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
import time

import extractor
import fixtures

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = ("extractor.py", "fixtures.py", "evaluate.py")
METHODS = ("nearest", "similarity", "selective")
POLICIES = ("all", "lexical_only", "nearest", "similarity", "selective", "selective_with_candidates")


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def selected(public, policy):
    if policy == "all":
        return {m["id"] for m in public["history"]}
    if policy == "selective_with_candidates":
        return extractor.select(public, "selective", retain_candidates=True)
    return extractor.select(public, policy)


def evaluate_case(case):
    # Gold is used only by the evaluator below, never passed into the extractor.
    public = case["public"]
    predictions = {method: extractor.extract(public["history"], method) for method in METHODS}
    full_bytes = sum(len(m["text"].encode("utf-8")) for m in public["history"])
    selections = {}
    for policy in POLICIES:
        selection = selected(public, policy)
        missing = [clause for clause in case["gold"]["required_any_of"] if not set(clause) & selection]
        selections[policy] = {"ids": sorted(selection), "missing": missing, "failed": bool(missing),
                              "bytes": sum(len(m["text"].encode("utf-8")) for m in public["history"] if m["id"] in selection)}
    return {"id": case["id"], "family": case["family"], "predictions": predictions,
            "selections": selections, "full_bytes": full_bytes}


def summarize(cases, rows):
    golds = {case["id"]: case["gold"] for case in cases}
    extraction = {}
    for method in METHODS:
        c = Counter()
        for row in rows:
            gold = golds[row["id"]]
            actual = {e["child"]: e for e in gold["events"]}
            prediction = row["predictions"][method]
            detected = {e["child"]: e for e in prediction["events"]}
            root_ids = set(prediction["roots"])
            c["gold_roots"] += len(gold["roots"])
            c["detected_correct_roots"] += len(root_ids & set(gold["roots"]))
            c["false_roots"] += len(root_ids - set(gold["roots"]))
            c["gold_update_messages"] += len(actual)
            c["recognized_update_messages"] += len(actual.keys() & detected.keys())
            c["false_update_messages"] += len(detected.keys() - actual.keys())
            for event in gold["events"]:
                if event["parent"]:
                    c["resolvable_links"] += 1
                else:
                    c["ambiguous_events"] += 1
                    if event["child"] in detected:
                        p = detected[event["child"]]
                        if p["parent"]:
                            c["ambiguous_forced_links"] += 1
                        else:
                            c["ambiguous_abstentions"] += 1
                        if set(event["possible_parents"]) <= set(p["candidates"]):
                            c["ambiguous_all_candidates_present"] += 1
            for event in prediction["events"]:
                if event["parent"] is None:
                    c["recognized_but_unlinked"] += 1
                    continue
                c["asserted_links"] += 1
                if event["child"] in actual and actual[event["child"]]["parent"] == event["parent"]:
                    c["justified_links"] += 1
                elif event["child"] not in actual:
                    c["links_from_non_updates"] += 1
                elif actual[event["child"]]["parent"] is not None:
                    c["wrong_resolvable_links"] += 1
        fields = ("gold_roots", "detected_correct_roots", "false_roots", "gold_update_messages", "recognized_update_messages",
                  "false_update_messages", "resolvable_links", "asserted_links", "justified_links", "wrong_resolvable_links",
                  "ambiguous_events", "ambiguous_forced_links", "ambiguous_abstentions", "ambiguous_all_candidates_present",
                  "recognized_but_unlinked", "links_from_non_updates")
        result = {key: c[key] for key in fields}
        result["justified_link_precision"] = c["justified_links"] / c["asserted_links"] if c["asserted_links"] else None
        result["resolvable_link_recall"] = c["justified_links"] / c["resolvable_links"] if c["resolvable_links"] else None
        extraction[method] = result
    selection = {}
    for policy in POLICIES:
        full_bytes = sum(row["full_bytes"] for row in rows)
        chosen_bytes = sum(row["selections"][policy]["bytes"] for row in rows)
        failures = sum(row["selections"][policy]["failed"] for row in rows)
        selection[policy] = {"cases": len(rows), "failures": failures, "byte_reduction": 1 - chosen_bytes / full_bytes,
                             "families": {family: {"n": sum(r["family"] == family for r in rows),
                                                    "failures": sum(r["selections"][policy]["failed"] for r in rows if r["family"] == family)}
                                          for family in fixtures.FAMILIES}}
    return {"extraction": extraction, "selection": selection}


def validate(cases, rows):
    assert len(cases) == len({c["id"] for c in cases})
    for case, row in zip(cases, rows):
        public = case["public"]
        assert set(public) == {"history", "query"}
        assert all(set(m) == {"id", "text"} for m in public["history"])
        positions = {m["id"]: i for i, m in enumerate(public["history"])}
        assert len(positions) == len(public["history"])
        assert not row["selections"]["all"]["failed"]
        assert set(row["selections"]["selective"]["ids"]) <= set(row["selections"]["selective_with_candidates"]["ids"])
        for method in METHODS:
            for e in row["predictions"][method]["events"]:
                assert all(positions[c] < positions[e["child"]] for c in e["candidates"])
                assert e["parent"] is None or e["parent"] in e["candidates"]
        for event in case["gold"]["events"]:
            assert event["child"] in positions
            assert event["parent"] is None or positions[event["parent"]] < positions[event["child"]]
    # IDs carry no usable target identity: permuting them must preserve decisions.
    for case in cases[::max(1, len(cases) // 18)]:
        history = case["public"]["history"]
        rename = {m["id"]: f"opaque_{i}" for i, m in enumerate(reversed(history))}
        renamed = [{"id": rename[m["id"]], "text": m["text"]} for m in history]
        for method in METHODS:
            a, b = extractor.extract(history, method), extractor.extract(renamed, method)
            assert b["roots"] == [rename[i] for i in a["roots"]]
            mapped = [{"child": rename[e["child"]], "parent": rename[e["parent"]] if e["parent"] else None,
                       "candidates": [rename[c] for c in e["candidates"]], "decision": e["decision"]} for e in a["events"]]
            assert mapped == b["events"]


def run_split(split):
    cases = fixtures.cases(split)
    rows = [evaluate_case(case) for case in cases]
    validate(cases, rows)
    return cases, {"summary": summarize(cases, rows), "rows": rows}


def freeze():
    target = ROOT / "frozen_protocol.json"
    if target.exists():
        raise RuntimeError("Protocol already frozen; preserve it and create a new research phase for changed methods.")
    if not (ROOT / "development.json").exists():
        raise RuntimeError("Run --dev first.")
    dump("frozen_protocol.json", {
        "scope": "synthetic text-only relation extraction; no operational changes",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "source_hashes": source_hashes(),
        "development_cases": 72, "evaluation_cases_per_split": 288,
        "methods": list(METHODS), "selection_policies": list(POLICIES),
        "test_splits": ["heldout", "stress"],
        "limitations": ["same author wrote algorithm and all templates", "balanced template variants are not IID observations",
                        "not an LLM or embedding evaluation", "no target quality threshold or deployment eligibility claim"],
    })
    print("Frozen source hashes and evaluation protocol before running heldout/stress splits.")


def test():
    protocol = json.loads((ROOT / "frozen_protocol.json").read_text(encoding="utf-8"))
    assert protocol["source_hashes"] == source_hashes(), "Frozen source changed."
    started = time.perf_counter()
    all_cases, results = {}, {}
    for split in ("heldout", "stress"):
        all_cases[split], results[split] = run_split(split)
    # Exact duplicate text check across splits, independently of opaque IDs.
    dev_cases = fixtures.cases("dev")
    signatures = []
    for cs in (dev_cases, all_cases["heldout"], all_cases["stress"]):
        current = {json.dumps([c["public"]["query"], [m["text"] for m in c["public"]["history"]]], ensure_ascii=False) for c in cs}
        assert len(current) == len(cs)
        assert all(not current & previous for previous in signatures)
        signatures.append(current)
    worlds = fixtures.indistinguishable_worlds()
    worlds["predictions"] = {m: extractor.extract(worlds["public"]["history"], m) for m in METHODS}
    dump("evaluation_fixtures.json", all_cases)
    result = {"scope": "frozen rules on synthetic text; no models called", "source_hashes": source_hashes(),
              "python": platform.python_version(), "results": results, "indistinguishable_worlds": worlds,
              "validation": {"passed": True, "exact_cross_split_duplicates": 0, "ids_permuted_without_changed_decisions": True,
                             "extractor_input_keys": ["id", "text"], "gold_supplied_to_extractor": False},
              "elapsed_seconds": time.perf_counter() - started}
    dump("results.json", result)
    assert protocol["source_hashes"] == source_hashes()
    print(json.dumps({split: result["results"][split]["summary"] for split in results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dev", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.dev:
        cs, result = run_split("dev")
        dump("development.json", {"cases": cs, **result})
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    elif args.freeze:
        freeze()
    else:
        test()
