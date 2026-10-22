"""Reproduce v2-versus-v1 corpus regression without modifying either archive."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(research: Path):
    phase = research / "phase05"
    engine_file = phase / "revision02" / "engine.py"
    spec = importlib.util.spec_from_file_location("research05_revision02_engine", engine_file)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    corpus = json.loads((phase / "corpus.json").read_text(encoding="utf-8"))
    baseline = json.loads((phase / "results.json").read_text(encoding="utf-8"))
    rows = {(r["case_id"], r["query"], r["mode"]): r for r in baseline["rows"]}
    comparisons = 0
    for case in corpus:
        for query in case["queries"]:
            for mode in ("drop_unknown", "cheap", "eager", "lazy"):
                public = {**case["public"], "query": query}
                actual = json.loads(json.dumps(engine.run(public, mode), ensure_ascii=False))
                expected = rows[(case["id"], query, mode)]
                for key, value in actual.items():
                    if expected[key] != value:
                        raise RuntimeError(f"Revision regression: {case['id']}, {mode}, {key}")
                comparisons += 1
    recorded = json.loads((phase / "revision02" / "corpus_regression.json").read_text(encoding="utf-8"))
    if comparisons != recorded["mode_query_comparisons"]:
        raise RuntimeError("Revision comparison count changed")
    digest = hashlib.sha256(engine_file.read_bytes()).hexdigest()
    if digest != recorded["engine_sha256"]:
        raise RuntimeError("Revision source digest changed")
    return {"mode_query_comparisons": comparisons, "all_existing_corpus_outputs_unchanged": True,
            "engine_sha256": digest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", type=Path, default=ROOT / "research")
    args = parser.parse_args()
    print(json.dumps(check(args.research_root), indent=2))
