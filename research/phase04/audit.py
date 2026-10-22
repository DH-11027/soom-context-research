"""Independent, list-based check of all frozen finite-world optima.

Also tests the counterfactual set-cover reformulation rather than relying on
the study's bitset implementation. This does not validate natural language.
"""

import hashlib
import json
from pathlib import Path

from model import MODES, QUESTIONS, SOURCE_COUNT, byte_cost, certificate

HERE = Path(__file__).resolve().parent


def solve_direct(world, worlds, query, modes):
    candidates = []
    for mode in modes:
        allowed = [w for w in worlds if certificate(w, mode) == certificate(world, mode)]
        wrong = [w for w in allowed if (w["answers"] if query == "joint" else w["answers"][query]) != (world["answers"] if query == "joint" else world["answers"][query])]
        eliminations = [
            {w["id"] for w in wrong if w["records"][i]["text"] != world["records"][i]["text"]}
            for i in range(SOURCE_COUNT)
        ]
        full_wrong = {w["id"] for w in wrong}
        coverages = []
        for mask in range(1 << SOURCE_COUNT):
            selected = [i for i in range(SOURCE_COUNT) if mask & (1 << i)]
            covered = set().union(*(eliminations[i] for i in selected))
            coverages.append(len(covered))
            # Independent direct observation consistency and set cover agree.
            matches = [w for w in wrong if all(w["records"][i]["text"] == world["records"][i]["text"] for i in selected)]
            assert (not matches) == (covered == full_wrong)
            if not matches:
                candidates.append((byte_cost(world, mode, mask), MODES.index(mode), len(selected), mask))
        # Diminishing returns of counterfactual elimination, all A subset B.
        for a in range(1 << SOURCE_COUNT):
            for b in range(1 << SOURCE_COUNT):
                if a & b != a:
                    continue
                assert coverages[a] <= coverages[b]
                for i in range(SOURCE_COUNT):
                    if not b & (1 << i):
                        assert coverages[a | (1 << i)] - coverages[a] >= coverages[b | (1 << i)] - coverages[b]
    return min(candidates)


def run():
    results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    worlds = json.loads((HERE / "worlds.json").read_text(encoding="utf-8"))
    by_id = {w["id"]: w for w in worlds}
    checked = 0
    joint_cache = {}
    for row in results["rows"]:
        world = by_id[row["world_id"]]
        for method, query, modes in (("adaptive", row["query"], MODES), ("no_index", row["query"], ("none",)), ("joint", "joint", MODES)):
            if query == "joint" and world["id"] in joint_cache:
                result = joint_cache[world["id"]]
            else:
                result = solve_direct(world, worlds, query, modes)
                if query == "joint":
                    joint_cache[world["id"]] = result
            plan = row[method]
            assert result == (plan["bytes"], MODES.index(plan["mode"]), len(plan["sources"]), plan["mask"])
            checked += 1
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    for name, expected in protocol["hashes"].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected
    record = {
        "optimum_comparisons": checked,
        "all_match": True,
        "set_cover_equivalence": True,
        "counterfactual_coverage_monotone_submodular": True,
        "source_hashes_match_freeze": True,
        "results_sha256": hashlib.sha256((HERE / "results.json").read_bytes()).hexdigest(),
        "boundary": "Independent implementation, same author and same finite model; not independent empirical validation",
    }
    (HERE / "audit.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
