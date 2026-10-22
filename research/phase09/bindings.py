"""Read-only Phase08 bindings. Imports and source verification are outside timing."""
import hashlib
import importlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_COMMIT = "efba3224dd09d5c5e2bf9d9be11734fa10b32502"
sys.path.insert(0, str(ROOT / "research/phase08"))
try:
    P8R = importlib.import_module("runtime")
    P8E = importlib.import_module("evaluation")
finally:
    sys.path.pop(0)
P6 = P8R.P6
S7 = P8E.S7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_sources():
    import frozen
    frozen.verify_sources()

