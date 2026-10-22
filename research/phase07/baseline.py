"""Read-only bindings to the frozen Phase06 implementation and evaluator."""
import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P6DIR = ROOT / "research/phase06"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

P6 = load("phase07_frozen_scope", P6DIR / "scoped.py")
# The frozen evaluator imports scoped by name. Bind that exact frozen module.
sys.modules["scoped"] = P6
E6 = load("phase07_frozen_evaluator", P6DIR / "evaluate.py")
SOURCE_HASHES = {
    "research/phase06/scoped.py": "1b443560f5899a6ae2eecd2b16aee2493d303dff945a07354b8e831ce10872b4",
    "research/phase05/revision02/engine.py": "67163a9f83b11364ffa82be824925d96b8d62a828fd18d18cb3812f869f9d993",
}
SEMANTIC_FINGERPRINT = hashlib.sha256("|".join(SOURCE_HASHES.values()).encode()).hexdigest()

def verify_sources():
    for relative, expected in SOURCE_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
