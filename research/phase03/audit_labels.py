"""Post-hoc label audit. Frozen policies, public text and predictions stay intact.

The initial rubric always required the original request in three families whose
question asks only current status and whose update explicitly names its object.
That measures request-to-update trace retention, not minimal answering evidence.
Report both rubrics; never replace or silently relabel the frozen experiment.
This audit is by the same author, not independent human adjudication or LLM QA.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
R = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
F = json.loads((ROOT / "evaluation_fixtures.json").read_text(encoding="utf-8"))
P = json.loads((ROOT / "frozen_protocol.json").read_text(encoding="utf-8"))
assert all(hashlib.sha256((ROOT / n).read_bytes()).hexdigest() == h for n, h in P["source_hashes"].items())
REVISED_FAMILIES = {"explicit_task", "novel_expression", "cancelled"}
report = {}
for split, cases in F.items():
    revised = {}
    changes = []
    for case in cases:
        required = case["gold"]["required_any_of"]
        if case["family"] in REVISED_FAMILIES:
            child = case["gold"]["events"][0]["child"]
            required = [[child]]
            changes.append({"id": case["id"], "family": case["family"], "question": case["public"]["query"],
                            "original_required": case["gold"]["required_any_of"], "revised_required": required,
                            "reason": "Current-status question; the update explicitly identifies the project and document. Original request is unnecessary for this answer."})
        revised[case["id"]] = required
    policies = {}
    for policy in R["results"][split]["summary"]["selection"]:
        total = 0
        changed_to_pass = []
        families = {name: {"n": 0, "failures": 0} for name in {case["family"] for case in cases}}
        for row in R["results"][split]["rows"]:
            selection = set(row["selections"][policy]["ids"])
            failed = any(not set(clause) & selection for clause in revised[row["id"]])
            total += int(failed)
            families[row["family"]]["n"] += 1
            families[row["family"]]["failures"] += int(failed)
            if row["selections"][policy]["failed"] and not failed:
                changed_to_pass.append(row["id"])
        original = R["results"][split]["summary"]["selection"][policy]
        assert total <= original["failures"]
        policies[policy] = {"cases": len(cases), "original_trace_failures": original["failures"],
                            "revised_evidence_failures": total, "byte_reduction": original["byte_reduction"],
                            "changed_to_pass": changed_to_pass, "families": families}
    report[split] = {"label_changes": changes, "policies": policies}
result = {"scope": "post-hoc author label audit with paired original and revised metrics; not a new held-out evaluation",
          "source_policy_hashes_unchanged": True, "source_hashes": P["source_hashes"],
          "audit_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "reports": report}
(ROOT / "label_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({split: {p: {k: v for k, v in s.items() if k not in ('families','changed_to_pass')}
                         for p, s in r["policies"].items()} for split, r in report.items()}, ensure_ascii=False, indent=2))
