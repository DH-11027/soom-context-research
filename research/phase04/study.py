"""Freeze and exhaustively check a finite counterfactual sufficiency model.

Run --freeze once before --run. Re-running --run verifies source/data hashes and
must reproduce the same mathematical result. No random sampling or fitting.
The optimizer has the entire finite world model: all optima are ORACLE results.
"""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from model import (
    HEAD, MODES, PROTECTED, QUESTIONS, SOURCE_COUNT,
    build_worlds, byte_cost, certificate, rendering,
)

HERE = Path(__file__).resolve().parent
FULL = (1 << SOURCE_COUNT) - 1


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def answer(world, query):
    return world["answers"] if query == "joint" else world["answers"][query]


def freeze():
    protocol_path = HERE / "protocol.json"
    if protocol_path.exists():
        raise SystemExit("Protocol exists; do not overwrite the frozen experiment.")
    worlds = build_worlds()
    dump(HERE / "worlds.json", worlds)
    dump(protocol_path, {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Exact finite-model analysis, not an NLP benchmark or deployed selector",
        "world_count": len(worlds),
        "questions": QUESTIONS,
        "semantics": "Absolute assignment, relative +1, irrelevant prose, quoted non-action; all interpreted symbolically",
        "sufficient": "Every world matching the selected literal records, positions and optional truthful index gives the same answer",
        "no_selection_side_channel": "Omitted records, choice of mask and choice of index mode do not themselves assert facts",
        "optimizer": "Exhaustive 32 source subsets x 3 index modes; oracle knows all possible worlds",
        "cost": "UTF-8 bytes of rendered source text, source labels, index text and newlines; fixed protected exchange and query also reported separately",
        "comparisons": ["all records", "minimum sufficient for all three questions", "minimum sufficient for the current question without index", "minimum sufficient for the current question with optional index"],
        "diagnostics": ["latest-state source without index", "latest-state source with truthful last-event index", "one false index counterexample", "snapshot extension counterexample", "query-intent mismatch"],
        "integrity": ["direct compatibility cross-check", "all selected optima sufficient and irredundant", "joint cost lower bound", "index optionality cannot worsen optimum", "minimum-budget infeasibility", "ID permutation invariance", "independent nuisance invariance", "source hash checks"],
        "scope_limit": "Finite modeled alternatives and perfect semantic index only; no measured LLM quality, token saving, production latency or real-language index recall",
        "hashes": {name: digest(HERE / name) for name in ("model.py", "study.py", "worlds.json")},
    })
    print(json.dumps({"frozen_worlds": len(worlds), "protocol": str(protocol_path)}, ensure_ascii=False))


class Checker:
    def __init__(self, worlds):
        self.worlds = worlds
        self.all_bits = (1 << len(worlds)) - 1
        self.record_groups = [defaultdict(int) for _ in range(SOURCE_COUNT)]
        self.cert_groups = {mode: defaultdict(int) for mode in MODES}
        self.answer_groups = {q: defaultdict(int) for q in (*QUESTIONS, "joint")}
        for i, world in enumerate(worlds):
            bit = 1 << i
            for record in world["records"]:
                self.record_groups[record["seq"]][record["text"]] |= bit
            for mode in MODES:
                self.cert_groups[mode][certificate(world, mode)] |= bit
            for query in self.answer_groups:
                self.answer_groups[query][key(answer(world, query))] |= bit

    def compatible(self, world, mode, mask, cert_override=None):
        cert = certificate(world, mode) if cert_override is None else cert_override
        bits = self.cert_groups[mode].get(cert, 0)
        for record in world["records"]:
            if mask & (1 << record["seq"]):
                bits &= self.record_groups[record["seq"]][record["text"]]
        return bits

    def sufficient(self, world, query, bits):
        target = self.answer_groups[query][key(answer(world, query))]
        return bool(bits) and not (bits & (self.all_bits ^ target))

    def possible_answers(self, query, bits):
        return [json.loads(k) for k, group in self.answer_groups[query].items() if group & bits]

    def best(self, world, query, modes=MODES):
        choices = []
        for mode in modes:
            for mask in range(FULL + 1):
                bits = self.compatible(world, mode, mask)
                if self.sufficient(world, query, bits):
                    choices.append((byte_cost(world, mode, mask), MODES.index(mode), mask.bit_count(), mask, bits.bit_count()))
        cost, mode_i, _, mask, compatible_count = min(choices)
        return {"bytes": cost, "mode": MODES[mode_i], "mask": mask,
                "sources": [i for i in range(SOURCE_COUNT) if mask & (1 << i)],
                "compatible_worlds": compatible_count}


def summarize(rows, query):
    subset = [r for r in rows if r["query"] == query]
    total_full = sum(r["full_bytes"] for r in subset)
    result = {"worlds": len(subset), "methods": {}}
    for method in ("joint", "no_index", "adaptive"):
        vals = [r[method]["bytes"] for r in subset]
        result["methods"][method] = {
            "min_bytes": min(vals), "median_bytes": median(vals), "max_bytes": max(vals),
            "mean_bytes": mean(vals), "total_bytes": sum(vals),
            "reduction_from_full_percent": 100 * (1 - sum(vals) / total_full),
            "modes": dict(Counter(r[method]["mode"] for r in subset)),
        }
    result["extra_reduction_vs_joint_percent"] = 100 * (1 - sum(r["adaptive"]["bytes"] for r in subset) / sum(r["joint"]["bytes"] for r in subset))
    result["strictly_smaller_than_joint"] = sum(r["adaptive"]["bytes"] < r["joint"]["bytes"] for r in subset)
    result["index_strictly_helps"] = sum(r["adaptive"]["bytes"] < r["no_index"]["bytes"] for r in subset)
    minimum_budget = result["methods"]["adaptive"]["min_bytes"]
    result["min_budget_fails_worlds"] = sum(r["adaptive"]["bytes"] > minimum_budget for r in subset)
    result["full_mean_bytes"] = total_full / len(subset)
    return result


def run():
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    for name, expected in protocol["hashes"].items():
        assert digest(HERE / name) == expected, f"Frozen input changed: {name}"
    worlds = json.loads((HERE / "worlds.json").read_text(encoding="utf-8"))
    assert worlds == build_worlds() and len(worlds) == 200
    checker = Checker(worlds)
    rows, plans = [], {}
    direct_checks = 0
    for world in worlds:
        joint = checker.best(world, "joint")
        plans[world["id"]] = {}
        for query in QUESTIONS:
            adaptive = checker.best(world, query)
            no_index = checker.best(world, query, ("none",))
            assert adaptive["bytes"] <= no_index["bytes"] <= byte_cost(world, "none", FULL)
            assert adaptive["bytes"] <= joint["bytes"]
            for plan in (adaptive, no_index, joint):
                bits = checker.compatible(world, plan["mode"], plan["mask"])
                direct = [w for w in worlds if certificate(w, plan["mode"]) == certificate(world, plan["mode"]) and all(w["records"][i]["text"] == world["records"][i]["text"] for i in plan["sources"])]
                assert bits.bit_count() == len(direct)
                assert all(answer(w, query) == answer(world, query) for w in direct)
                direct_checks += 1
            # Positive source costs imply no removable source in an optimum.
            for i in adaptive["sources"]:
                bits = checker.compatible(world, adaptive["mode"], adaptive["mask"] ^ (1 << i))
                assert not checker.sufficient(world, query, bits)
            plans[world["id"]][query] = adaptive
            fixed = len((PROTECTED + "현재 질문: " + QUESTIONS[query] + "\n").encode("utf-8"))
            rows.append({"world_id": world["id"], "query": query,
                         "full_bytes": byte_cost(world, "none", FULL), "fixed_exchange_query_bytes": fixed,
                         "joint": joint, "no_index": no_index, "adaptive": adaptive})

    # Metadata-only identifiers cannot influence the optimizer.
    renamed = [{**w, "id": f"opaque-{i * 7919 + 17}"} for i, w in enumerate(worlds)]
    renamed_checker = Checker(renamed)
    for w, renamed_w in zip(worlds, renamed):
        for query in QUESTIONS:
            assert checker.best(w, query) == renamed_checker.best(renamed_w, query)

    nuisance_groups = defaultdict(list)
    for world in worlds:
        p = {k: v for k, v in world["parameters"].items() if k != "nuisance"}
        nuisance_groups[key(p)].append(world)
    for a, b in nuisance_groups.values():
        for query in QUESTIONS:
            assert plans[a["id"]][query] == plans[b["id"]][query]

    latest_diagnostics = []
    for mode in ("none", "last"):
        failures = Counter()
        for world in worlds:
            mask = 1 << world["state_sequences"][-1]
            for query in QUESTIONS:
                bits = checker.compatible(world, mode, mask)
                if not checker.sufficient(world, query, bits):
                    failures[query] += 1
        latest_diagnostics.append({"mode": mode, "insufficient_worlds": dict(failures)})

    intent_matrix = {}
    for selected_for in QUESTIONS:
        intent_matrix[selected_for] = {}
        for actual_query in QUESTIONS:
            count = 0
            for world in worlds:
                plan = plans[world["id"]][selected_for]
                bits = checker.compatible(world, plan["mode"], plan["mask"])
                count += not checker.sufficient(world, actual_query, bits)
            intent_matrix[selected_for][actual_query] = count

    # A single false last-event entry can produce a uniquely wrong answer.
    true_world = next(w for w in worlds if w["parameters"] == {"initial": 10, "wording": 0, "first": "set_a", "second": "set_a", "nuisance": 0})
    stale_world = next(w for w in worlds if w["parameters"] == {"initial": 10, "wording": 0, "first": "set_a", "second": "none", "nuisance": 0})
    false_cert = certificate(stale_world, "last")
    false_bits = checker.compatible(true_world, "last", 1 << 2, cert_override=false_cert)
    inferred = checker.possible_answers("current", false_bits)
    assert inferred == [12] and true_world["answers"]["current"] == 14
    diagnostics = {
        "latest_state_source": latest_diagnostics,
        "intent_mismatch_insufficient_worlds": intent_matrix,
        "false_index": {
            "actual_world": true_world["id"], "actual_answer": 14,
            "supplied_source": true_world["records"][2], "supplied_index": false_cert,
            "compatible_model_answers_if_index_trusted": inferred,
            "note": "The actual world is excluded by a false certificate; logical certainty under a false model is not factual correctness.",
        },
        "snapshot_extension": {
            "archive_head": HEAD, "old_answer": true_world["answers"]["current"],
            "new_event": {"seq": 5, "text": "민들레 모임은 16시로 다시 변경해줘.", "kind": "set", "value": 16},
            "same_old_projection_new_now_answer": 16,
            "note": "A truthful certificate through record 4 proves only an as-of-4 answer, not freshness after record 5.",
        },
    }
    examples = []
    for first, second in (("set_a", "set_a"), ("none", "delta"), ("delta", "delta"), ("set_a", "quote")):
        world = next(w for w in worlds if w["parameters"] == {"initial": 10, "wording": 0, "first": first, "second": second, "nuisance": 0})
        examples.append({"world": world, "plans": {
            q: {**plans[world["id"]][q], "rendered": rendering(world, plans[world["id"]][q]["mode"], plans[world["id"]][q]["mask"])} for q in QUESTIONS
        }})
    classes = {q: len(checker.answer_groups[q]) for q in (*QUESTIONS, "joint")}
    results = {
        "protocol_sha256": digest(HERE / "protocol.json"),
        "nature": "200 exhaustive finite worlds, 600 paired question instances; oracle witness optimization, not learned extraction or LLM QA",
        "summary": {q: summarize(rows, q) for q in QUESTIONS},
        "answer_class_counts": classes,
        "fixed_length_answer_encoding_lower_bound_bits": {q: math.ceil(math.log2(n)) for q, n in classes.items()},
        "diagnostics": diagnostics, "examples": examples, "rows": rows,
        "checks": {"frozen_hashes": True, "reconstructed_worlds_equal": True,
                   "direct_compatibility_checks": direct_checks, "all_optima_sufficient": True,
                   "source_irredundancy": True, "joint_cost_bound": True, "optional_index_bound": True,
                   "id_permutation_invariance": True, "independent_nuisance_invariance": True,
                   "false_index_counterexample": True},
    }
    dump(HERE / "results.json", results)
    print(json.dumps({k: results[k] for k in ("nature", "summary", "answer_class_counts", "diagnostics", "checks")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("--freeze", "--run"))
    # Accept literal command-style verbs without argparse interpreting them as flags.
    import sys
    if sys.argv[1:] == ["--freeze"]:
        freeze()
    elif sys.argv[1:] == ["--run"]:
        run()
    else:
        parser.error("Use --freeze or --run")
