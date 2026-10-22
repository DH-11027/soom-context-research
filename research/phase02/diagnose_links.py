"""Post-hoc mechanism diagnostic, NOT a new held-out policy evaluation.

Uses the SAME synthetic fixtures after inspecting the frozen study's failures.
True reference edges are supplied by the generator. Examines what happens when
lookup can follow an edge in either direction and when some edges are missing.
Never adds these diagnostic policies to the original 22-policy calibration.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
fixtures = json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))
study = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))


def close_both_ways(selected, edges):
    selected = set(selected)
    changed = True
    while changed:
        changed = False
        for a, b in edges:
            if (a in selected or b in selected) and not {a, b} <= selected:
                selected.update((a, b))
                changed = True
    return selected


def uniform(case_id, edge):
    digest = hashlib.sha256((case_id + ':' + ':'.join(edge)).encode()).digest()
    return int.from_bytes(digest[:8], 'big') / 2**64


reports = {}
for split in ("test_same_generator", "stress_shifted_generator"):
    lookup = {row["id"]: row for row in study["rows"][split]}
    rows = []
    for missing_rate in (0.0, 0.25, 0.5, 1.0):
        failures = full_bytes = selected_bytes = edge_count = retained_edges = 0
        for case in fixtures["splits"][split]:
            edges = [edge for edge in case["dependencies"] if uniform(case["id"], edge) >= missing_rate]
            selection = close_both_ways(lookup[case["id"]]["policies"]["lexical"]["selected"], edges)
            failures += int(any(not set(choices) & selection for choices in case["required_any_of"]))
            full_bytes += lookup[case["id"]]["full_bytes"]
            selected_bytes += sum(len(item["text"].encode("utf-8")) for item in case["history"] if item["id"] in selection)
            edge_count += len(case["dependencies"])
            retained_edges += len(edges)
        rows.append({"missing_edge_probability": missing_rate, "failures": failures,
                     "cases": len(lookup), "failure_rate": failures / len(lookup),
                     "byte_reduction": 1 - selected_bytes / full_bytes,
                     "available_true_edges": edge_count, "retained_true_edges": retained_edges})
    baseline = next(row for row in study["summaries"][split] if row["policy"] == "lexical")
    assert rows[-1]["failures"] == baseline["failures"]
    assert abs(rows[-1]["byte_reduction"] - baseline["byte_reduction"]) < 1e-12
    reports[split] = rows
result = {
    "scope": "post-hoc oracle-edge ablation on reused synthetic test fixtures; no generalization claim",
    "source_study_sha256": study["script_sha256"],
    "diagnostic_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "reports": reports,
}
(ROOT / "link_diagnostic.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
