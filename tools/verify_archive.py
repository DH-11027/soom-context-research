"""Check archived bytes, original freezes, syntax and local documentation links.

Read-only. No imports from the experiments, network, models or database access.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in {"a", "img", "script", "link"}:
            self.links.extend(v for k, v in attrs if k in {"href", "src"} and v)


def verify():
    manifest = read_json(ROOT / "archive-manifest.json")
    listed = {entry["path"] for entry in manifest["files"]}
    require(len(listed) == len(manifest["files"]), "Duplicate manifest paths")
    for entry in manifest["files"]:
        p = ROOT / entry["path"]
        require(p.is_file(), f"Missing archive file: {entry['path']}")
        require(p.stat().st_size == entry["bytes"], f"Size changed: {entry['path']}")
        require(sha(p) == entry["sha256"], f"SHA-256 changed: {entry['path']}")

    frozen_checks = 0
    protocols = [
        ("phase03/frozen_protocol.json", "source_hashes"),
        ("phase04/protocol.json", "hashes"),
        ("phase05/protocol.json", "hashes"),
        ("phase05/reduction_protocol.json", "hashes"),
        ("phase05/revision02/reduction_protocol.json", "hashes"),
    ]
    for rel, key in protocols:
        p = ROOT / "research" / rel
        for name, expected in read_json(p)[key].items():
            require(sha(p.parent / name) == expected, f"Original freeze mismatch: {rel}: {name}")
            frozen_checks += 1
    for folder, script in [("", "experiment.py"), ("phase02", "study.py")]:
        p = ROOT / "research" / folder
        require(read_json(p / "results.json")["script_sha256"] == sha(p / script), f"Study source mismatch: {folder}")
    for folder in ["phase04", "phase05"]:
        p = ROOT / "research" / folder
        require(read_json(p / "results.json")["protocol_sha256"] == sha(p / "protocol.json"), f"Protocol binding mismatch: {folder}")
    p = ROOT / "research" / "phase04"
    require(read_json(p / "audit.json")["results_sha256"] == sha(p / "results.json"), "Phase 04 audit binding mismatch")

    sources = [ROOT / name for name in listed]
    sources += sorted((ROOT / "tools").glob("*.py"))
    sources += sorted((ROOT / "docs").glob("*.md"))
    sources += [ROOT / "README.md", ROOT / "HANDOFF.md"]
    json_count = python_count = notebook_count = link_count = 0
    for p in sources:
        text = p.read_text(encoding="utf-8")
        if p.suffix == ".py":
            ast.parse(text, filename=str(p))
            python_count += 1
        if p.suffix in {".json", ".ipynb"}:
            data = json.loads(text)
            json_count += 1
            if p.suffix == ".ipynb":
                require(data["nbformat"] == 4, f"Unexpected notebook version: {p.name}")
                require(isinstance(data["cells"], list), f"Notebook cells missing: {p.name}")
                notebook_count += 1
        links = []
        if p.suffix == ".html":
            parser = Links()
            parser.feed(text)
            links = parser.links
        elif p.suffix == ".md":
            without_code = re.sub(r"```.*?```", "", text, flags=re.S)
            links = re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", without_code)
        for link in links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            target = p.parent / unquote(parts.path)
            require(target.exists(), f"Broken local link: {p.relative_to(ROOT)} -> {link}")
            link_count += 1
    return {
        "archive_files": len(listed), "archive_bytes": sum(x["bytes"] for x in manifest["files"]),
        "original_frozen_source_bindings": frozen_checks,
        "parsed_json_and_notebooks": json_count, "python_syntax_files": python_count,
        "notebooks_basic_structure": notebook_count, "resolved_local_links": link_count,
        "status": "passed", "boundary": "Integrity and packaging only; does not rerun experiments or prove scientific claims.",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
