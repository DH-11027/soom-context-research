"""Read-only bindings to the exact Phase08 instrumented implementations."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "efba3224dd09d5c5e2bf9d9be11734fa10b32502"
sys.path.insert(0, str(ROOT / "research/phase08"))
import frozen as F8
import runtime as R8
import evaluation as E8
sys.path.pop(0)
P6 = R8.P6
SEMANTIC_FINGERPRINT = R8.SEMANTIC_FINGERPRINT


def verify_sources():
    F8.verify_sources()

