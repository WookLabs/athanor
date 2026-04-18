"""Regression test for the v0.6.1 missing-Stop-prompt plugin load failure.

Verifies that a Stop-event hook entry of type ``prompt`` carries a non-empty
``prompt`` field. The broken fixture (missing ``prompt``) must fail the check,
and the current repo ``hooks/hooks.json`` must pass.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def stop_prompt_liveness_check(hooks_json_path):
    """Check Stop event has type=prompt + non-empty prompt field."""
    with open(hooks_json_path, encoding="utf-8") as f:
        d = json.load(f)
    stop = d.get("hooks", {}).get("Stop", [])
    for entry in stop:
        for h in entry.get("hooks", []):
            if h.get("type") == "prompt" and h.get("prompt", "").strip():
                return True, "OK"
    return False, "Stop event missing non-empty prompt field"


def test_fixture_fails():
    ok, _ = stop_prompt_liveness_check(
        REPO_ROOT / "tests/fixtures/fixture_wrong_stop_prompt.json"
    )
    assert not ok


def test_current_hooks_passes():
    ok, _ = stop_prompt_liveness_check(REPO_ROOT / "hooks/hooks.json")
    assert ok
