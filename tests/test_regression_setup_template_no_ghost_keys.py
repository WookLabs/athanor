"""Regression: templates/athanor.json must NOT contain the ghost
``models.debugger`` / ``models.debugger-tracer`` keys whose unreviewed
addition caused the v0.7.6 C4 finding.

Closes plan §4 C4 — the template extraction must purge the old shape.
The embedded fallback inside ``skills/setup/SKILL.md`` MAY still carry
the old shape (per Wave 1A worker's preservation note) — this test
intentionally inspects ONLY the canonical template file, not the
fallback string.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_CONFIG = REPO_ROOT / "athanor.json"
TEMPLATE_CONFIG = REPO_ROOT / "templates" / "athanor.json"

GHOST_KEYS = ("debugger", "debugger-tracer")


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_template_no_debugger_key():
    """templates/athanor.json models block must NOT contain 'debugger'."""
    template = _load_json(TEMPLATE_CONFIG)
    models = template.get("models", {})
    assert "debugger" not in models, (
        "templates/athanor.json models block contains ghost 'debugger' key — "
        "this is the v0.7.6 C4 regression. /athanor:debug uses a hardcoded "
        "model in the skill dispatch; this key has no consumer."
    )


def test_template_no_debugger_tracer_key():
    """templates/athanor.json models block must NOT contain 'debugger-tracer'."""
    template = _load_json(TEMPLATE_CONFIG)
    models = template.get("models", {})
    assert "debugger-tracer" not in models, (
        "templates/athanor.json models block contains ghost 'debugger-tracer' key — "
        "this is the v0.7.6 C4 regression. No skill/agent reads this name."
    )


def test_root_config_no_ghost_keys():
    """Paranoia: same invariant applied to root athanor.json."""
    root = _load_json(ROOT_CONFIG)
    models = root.get("models", {})
    for ghost in GHOST_KEYS:
        assert ghost not in models, (
            f"athanor.json models block contains ghost {ghost!r} key — "
            f"either the v0.7.6 drift was reintroduced or this key now has "
            f"a real consumer (in which case wire it explicitly and remove "
            f"from this test)."
        )
