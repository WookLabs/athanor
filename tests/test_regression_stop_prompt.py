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


def test_current_hooks_contains_narrowed_gating_markers():
    """Stop prompt must contain the narrowed-gating markers shipped in S4.

    Guards against silent re-broadening of the completion-claim gate. Any
    valid narrowed prompt (however worded) must mention both ``material``
    (the claim-type qualifier) and ``Explicitly skip`` (the non-claim
    carve-out). If a future edit drops either, this test fails.
    """
    with open(REPO_ROOT / "hooks/hooks.json", encoding="utf-8") as f:
        d = json.load(f)
    prompt = d["hooks"]["Stop"][0]["hooks"][0]["prompt"]
    assert "material" in prompt, "Stop prompt missing 'material' gating keyword"
    assert "Explicitly skip" in prompt, (
        "Stop prompt missing 'Explicitly skip' non-claim carve-out"
    )
