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


def _current_stop_prompt() -> str:
    with open(REPO_ROOT / "hooks/hooks.json", encoding="utf-8") as f:
        d = json.load(f)
    return d["hooks"]["Stop"][0]["hooks"][0]["prompt"]


# --- v0.7.5 semantic fixture (Codex hook review TOP 5 #1 + #2 + #3) ---
# Locks the v0.7.5 changes that close the false-negative vector identified
# by the 2026-05-02 cross-model hook audit (`.athanor/sessions/2026-05-02-001/
# codex-hook-review.md`). Each assertion below maps to a specific finding:
#
#   - whitelist parity (Codex #2): hook prompt must list the same material
#     categories as agents/cleaner.md / verification skill body / CLAUDE.md
#     (builds, files, lint/typecheck, bug fixed, requirements met).
#   - Korean parity (Codex #2): the prompt must explicitly mark Korean
#     equivalents of the success verbs as material — otherwise generic
#     Korean responses ("수정했습니다", "통과", "배포") slip past gating.
#   - tool-output summary disambiguation (Codex #1): the prompt must
#     distinguish "describes what the tool printed" (skippable) from
#     "asserts work status from the tool output" (material). The "evidence
#     already present" rationalization must be foreclosed.
#   - fresh-evidence requirement (Codex #1): the prompt must require
#     evidence IN THIS RESPONSE, not from prior turns / earlier in same turn.

def test_prompt_lists_expanded_material_categories():
    """Codex #2: whitelist must include builds, files, lint, bug fixed, requirements."""
    prompt = _current_stop_prompt()
    expected = [
        "files created",
        "lint",
        "builds succeeding",
        "bug fixed",
        "requirements met",
    ]
    missing = [c for c in expected if c not in prompt]
    assert not missing, f"Stop prompt missing expanded material categories: {missing}"


def test_prompt_marks_korean_success_verbs_as_material():
    """Codex #2: Korean equivalents of success verbs must be flagged material."""
    prompt = _current_stop_prompt()
    # Sample of must-cover Korean verbs from the audit.
    expected_korean = ["수정", "통과", "성공", "배포", "완료"]
    missing = [v for v in expected_korean if v not in prompt]
    assert not missing, f"Stop prompt missing Korean material verbs: {missing}"


def test_prompt_disambiguates_tool_output_summary_from_status_claim():
    """Codex #1: tool-output summary skip must NOT cover status-claim summaries."""
    prompt = _current_stop_prompt()
    # The disambiguation phrase distinguishes "describes what the tool
    # printed" from claims like "tests pass". The exact wording can drift,
    # so we check for both halves of the contract.
    assert "tests pass" in prompt or "build succeeded" in prompt, (
        "Stop prompt must spell out at least one status-claim form that "
        "remains material despite being a tool-output summary"
    )
    assert "remain material" in prompt or "still require" in prompt or "are material" in prompt, (
        "Stop prompt must explicitly state that status-claim tool-output "
        "summaries are material (closes 'evidence already present' rationalization)"
    )


def test_prompt_requires_fresh_evidence_in_this_response():
    """Codex #1: prior-turn evidence must NOT satisfy the gate."""
    prompt = _current_stop_prompt()
    # Word-stem flexible check: prompt must indicate evidence comes from
    # the current response, not prior turns or earlier in same turn.
    assert "IN THIS RESPONSE" in prompt or "in this response" in prompt or (
        "fresh" in prompt and "earlier" in prompt
    ), (
        "Stop prompt must require fresh evidence IN THIS RESPONSE — the "
        "'evidence already present in same turn' rationalization is the "
        "documented false-negative vector (Codex review §2)."
    )


def test_prompt_length_within_cognitive_budget():
    """Smoke check that the expanded prompt did not blow past a sane size.

    Cognitive-load budget: ~2000 chars. If we cross 2500 we should split
    the gate into a command-type hook + transcript parser (Codex #4),
    not keep growing the prompt.
    """
    prompt = _current_stop_prompt()
    assert len(prompt) < 2500, (
        f"Stop prompt is {len(prompt)} chars — exceeded cognitive budget. "
        "Migrate to type=command + transcript-parser (Codex #4) instead of "
        "growing the prompt further."
    )
