"""Read-only semantic binding. No evaluator, gold, data, or network imports."""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "6da051c0132811184ecf39975d7ff647a1f47842"
SOURCE_HASHES = {
    "research/phase06/scoped.py": "1b443560f5899a6ae2eecd2b16aee2493d303dff945a07354b8e831ce10872b4",
    "research/phase05/revision02/engine.py": "67163a9f83b11364ffa82be824925d96b8d62a828fd18d18cb3812f869f9d993",
}
SEMANTIC_FINGERPRINT = hashlib.sha256("|".join(SOURCE_HASHES.values()).encode()).hexdigest()


def verify_sources():
    for name, digest in SOURCE_HASHES.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


spec = importlib.util.spec_from_file_location("phase08_frozen_scope", ROOT / "research/phase06/scoped.py")
P6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P6)
