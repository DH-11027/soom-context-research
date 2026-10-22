"""Read-only access to the exact Phase09 implementations; no policy fork."""
from pathlib import Path
import gzip
import hashlib
import importlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_COMMIT = "0c08785fcee9ab146f33fa8a7d94a4b7700833aa"
P9 = ROOT / "research/phase09"
sys.path.insert(0, str(P9))
try:
    E9 = importlib.import_module("execution")
    B9 = importlib.import_module("bindings")
finally:
    sys.path.pop(0)

METHODS = ("fresh_uninstrumented", "selective_uninstrumented")

def evaluator():
    sys.path.insert(0, str(P9))
    try:
        return importlib.import_module("evaluator")
    finally:
        sys.path.pop(0)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

def save_gzip(path, value):
    path = Path(path)
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    with path.open("xb") as handle:
        with gzip.GzipFile(filename="", fileobj=handle, mode="wb", mtime=0, compresslevel=9) as target:
            target.write(raw)

def prepare(streams):
    return tuple(tuple(({k: step["public"][k] for k in ("records", "entities", "snapshot", "query")},
                        step["parser_namespace"]) for step in stream["steps"]) for stream in streams)

def verify_base():
    freeze = load(P9 / "freeze.json")
    for name, digest in freeze["hashes"].items():
        assert sha(P9 / name) == digest, name
    for name, digest in freeze["baseline_hashes"].items():
        assert sha(ROOT / name) == digest, name
    B9.verify_sources()

