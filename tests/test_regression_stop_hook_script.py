"""Regression test for scripts/hooks/stop_verify_claims.py decision flow.

The script is invoked by Claude Code on every Stop event (v0.7.8 contract,
see tests/test_regression_stop_command_hook.py for the registration test).
This file unit-tests the script's decision logic with synthetic stdin
payloads — same shape Claude Code would inject at runtime.

Decision flow under test:
  1. Empty / unparseable stdin → exit 0 (fail-open).
  2. profile=off in athanor.json → exit 0 (user opted out).
  3. Response starts with `<!-- athanor:verification-emission v=N -->` →
     exit 0 (re-entry skip; the verification skill's own output).
  4. Response contains a material-claim phrase from the v0.7.7-derived
     whitelist (English + Korean) → exit 2 + stderr directs the model
     to invoke verification-before-completion.
  5. Response contains no material-claim phrase → exit 0.

The whitelist itself is asserted by sampling — we test a handful of
English + Korean variants, not the full list. If the script's whitelist
needs to be expanded later, add a sample for the new phrase here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts/hooks/stop_verify_claims.py"


def _run(payload, *, cwd=None, env=None) -> tuple[int, str, str]:
    """Invoke the script with `payload` (dict or string) as stdin.

    Returns (returncode, stdout, stderr).
    """
    if isinstance(payload, dict):
        stdin_data = json.dumps(payload)
    else:
        stdin_data = payload
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin_data,
        text=True,
        capture_output=True,
        cwd=cwd or str(REPO_ROOT),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


# --- Smoke: script exists + is executable --------------------------------


def test_script_file_exists():
    assert SCRIPT.is_file(), f"Script not at {SCRIPT}"


# --- Decision flow: stdin variations --------------------------------------


def test_empty_payload_fails_open():
    """No payload → fail-open (exit 0) with stderr warning."""
    rc, _, err = _run({})
    assert rc == 0, f"Expected exit 0 for empty payload, got {rc}"


def test_unparseable_json_fails_open():
    rc, _, err = _run("this is not json")
    assert rc == 0, f"Expected exit 0 for non-JSON stdin, got {rc}"


def test_missing_last_assistant_message_fails_open():
    """Payload without `last_assistant_message` key → fail-open."""
    rc, _, _ = _run({"hook_event_name": "Stop", "session_id": "test"})
    assert rc == 0, f"Expected exit 0 when last_assistant_message absent, got {rc}"


# --- Decision flow: material claim detection ------------------------------


def test_material_claim_english_triggers_exit_2():
    """English material claim → exit 2 + stderr cites verification skill."""
    rc, _, err = _run({"last_assistant_message": "tests pass on my machine"})
    assert rc == 2, f"Expected exit 2 for material claim, got {rc}"
    assert "verification-before-completion" in err.lower(), (
        f"stderr should direct user to verification skill; got: {err!r}"
    )


def test_material_claim_korean_triggers_exit_2():
    """Korean material claim → exit 2."""
    rc, _, _ = _run({"last_assistant_message": "테스트 통과 확인했습니다"})
    assert rc == 2, f"Expected exit 2 for Korean material claim, got {rc}"


def test_material_claim_variant_build_succeeded():
    rc, _, _ = _run({"last_assistant_message": "Build succeeded, ready to deploy."})
    assert rc == 2


def test_material_claim_variant_files_changed():
    rc, _, _ = _run({"last_assistant_message": "I modified 3 files; files changed."})
    assert rc == 2


def test_material_claim_variant_deployed():
    rc, _, _ = _run({"last_assistant_message": "Deployed to production successfully."})
    assert rc == 2


def test_non_material_claim_exits_0():
    """Analytical content with no claim phrases → exit 0."""
    rc, _, _ = _run({
        "last_assistant_message": "Let me think about how to approach this problem. "
        "The key consideration is the architecture trade-off."
    })
    assert rc == 0, f"Non-material claim should exit 0, got {rc}"


def test_empty_last_assistant_message_exits_0():
    rc, _, _ = _run({"last_assistant_message": ""})
    assert rc == 0


# --- Decision flow: sentinel anchoring ------------------------------------


def test_sentinel_at_response_start_exits_0():
    """Sentinel as first non-whitespace line → skip even if response contains
    material-claim phrases (this is the re-entry prevention contract)."""
    rc, _, _ = _run({
        "last_assistant_message": (
            "<!-- athanor:verification-emission v=1 -->\n"
            "Verified pytest run: 81 passed, 0 failed. Build succeeded."
        )
    })
    assert rc == 0, f"Sentinel-prefixed response should exit 0, got {rc}"


def test_sentinel_with_leading_whitespace_still_recognized():
    """Leading whitespace before sentinel is allowed (regex pattern \\s*)."""
    rc, _, _ = _run({
        "last_assistant_message": "  \n<!-- athanor:verification-emission v=1 -->\nfiles changed"
    })
    assert rc == 0


def test_sentinel_on_line_2_does_not_count():
    """Sentinel must be at start; greeting before it → exit 2 (claim seen)."""
    rc, _, _ = _run({
        "last_assistant_message": (
            "Sure thing!\n"
            "<!-- athanor:verification-emission v=1 -->\n"
            "tests pass"
        )
    })
    assert rc == 2, (
        f"Sentinel on line 2 should NOT prevent material-claim detection; got rc={rc}"
    )


def test_sentinel_version_forward_compat():
    """v=2 (or any version number) is accepted — version tag is forward-compat."""
    rc, _, _ = _run({
        "last_assistant_message": (
            "<!-- athanor:verification-emission v=2 -->\n"
            "tests pass"
        )
    })
    assert rc == 0


# --- Decision flow: profile=off opt-out -----------------------------------


def test_profile_off_disables_gate(tmp_path):
    """When athanor.json `hooks.profile == "off"`, exit 0 even for material claims."""
    # Build a minimal config dir with profile=off
    cfg_dir = tmp_path / "project"
    cfg_dir.mkdir()
    (cfg_dir / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off"}}), encoding="utf-8"
    )
    rc, _, _ = _run({"last_assistant_message": "tests pass"}, cwd=str(cfg_dir))
    assert rc == 0, f"profile=off should disable gate even for material claim, got {rc}"


def test_profile_standard_engages_gate(tmp_path):
    cfg_dir = tmp_path / "project"
    cfg_dir.mkdir()
    (cfg_dir / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "standard"}}), encoding="utf-8"
    )
    rc, _, _ = _run({"last_assistant_message": "tests pass"}, cwd=str(cfg_dir))
    assert rc == 2, f"profile=standard should engage gate, got {rc}"


def test_profile_missing_defaults_to_standard(tmp_path):
    """No `hooks.profile` field → defaults to standard."""
    cfg_dir = tmp_path / "project"
    cfg_dir.mkdir()
    (cfg_dir / "athanor.json").write_text(
        json.dumps({"hooks": {}}), encoding="utf-8"
    )
    rc, _, _ = _run({"last_assistant_message": "tests pass"}, cwd=str(cfg_dir))
    assert rc == 2


def test_unknown_profile_falls_back_to_standard(tmp_path):
    """profile=lenient or =strict is not yet supported → falls back to standard
    with a stderr warning."""
    cfg_dir = tmp_path / "project"
    cfg_dir.mkdir()
    (cfg_dir / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "lenient"}}), encoding="utf-8"
    )
    rc, _, err = _run({"last_assistant_message": "tests pass"}, cwd=str(cfg_dir))
    assert rc == 2, f"Unknown profile should fall back to standard (exit 2), got {rc}"
    assert "unknown" in err.lower() and "lenient" in err.lower(), (
        f"stderr should warn about unknown profile; got: {err!r}"
    )


def test_missing_athanor_json_defaults_to_standard(tmp_path):
    """No athanor.json in tree → defaults to standard."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    rc, _, _ = _run({"last_assistant_message": "tests pass"}, cwd=str(empty_dir))
    assert rc == 2


# --- Integration: re-entry prevention -------------------------------------


def test_two_turn_reentry_prevention():
    """Simulate the v0.7.8 contract: first Stop fires on material claim (exit 2),
    next turn the verification skill emits sentinel-prefixed evidence, that
    triggers a second Stop event which exits 0 silently (no infinite loop)."""
    # Turn 1: material claim, no sentinel → exit 2
    rc1, _, _ = _run({"last_assistant_message": "build succeeded"})
    assert rc1 == 2
    # Turn 2: verification skill response with sentinel → exit 0
    rc2, _, _ = _run({
        "last_assistant_message": (
            "<!-- athanor:verification-emission v=1 -->\n"
            "Ran `pytest`, exit 0, 81 tests passed."
        )
    })
    assert rc2 == 0, (
        f"Re-entry prevention failed: sentinel-prefixed response triggered exit {rc2}"
    )
