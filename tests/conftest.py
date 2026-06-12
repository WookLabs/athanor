"""pytest conftest — pins sys.path so tests can `from scripts.gates...` import."""
import sys
from pathlib import Path

# tests/ is intentionally NOT a package: this conftest sys.path injection is the
# deliberate import mechanism. Adding tests/__init__.py risks an INTERNALERROR via
# ref/ collection (see lesson 2026-06-11-003 / plan.md hard constraint).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
