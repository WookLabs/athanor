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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts/hooks/stop_verify_claims.py"
HOOK_STATE_DIR = REPO_ROOT / ".athanor" / "sessions" / "active" / ".hook-state"


@pytest.fixture(autouse=True)
def _clean_hook_state():
    """v0.7.9: reset stop-hook state before each test to prevent counter
    or nonce leakage across tests when they run against REPO_ROOT cwd.

    Tests that pass an explicit `cwd=tmp_path` are isolated by construction;
    this fixture handles the default-cwd case (REPO_ROOT)."""
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)
    yield
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)


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


def _emit_v2_sentinel(body: str) -> str:
    """v0.7.9: invoke sentinel_helper.py to get a valid v=2 sentinel for `body`.

    Returns the full response (sentinel + body) the verification skill would
    emit. The helper writes nonce state alongside.
    """
    helper = REPO_ROOT / "scripts/hooks/sentinel_helper.py"
    result = subprocess.run(
        [sys.executable, str(helper), "emit"],
        input=body, text=True, capture_output=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"sentinel_helper failed: {result.stderr}"
    sentinel = result.stdout.strip()
    return sentinel + "\n" + body


def test_v2_sentinel_at_response_start_exits_0():
    """v=2 nonce-bound sentinel with matching body hash → exit 0."""
    body = "Verified pytest run: 81 passed, 0 failed. Build succeeded."
    response = _emit_v2_sentinel(body)
    rc, _, _ = _run({"last_assistant_message": response})
    assert rc == 0, f"v=2 sentinel-prefixed response should exit 0, got {rc}"


def test_v2_sentinel_with_body_tampering_falls_through():
    """If body emitted doesn't match what was piped to helper, hash mismatch
    causes the sentinel to be rejected and material claim takes over."""
    body_piped = "Some non-material text"
    body_emitted = "But actually tests pass and build succeeded"  # different + material
    helper = REPO_ROOT / "scripts/hooks/sentinel_helper.py"
    result = subprocess.run(
        [sys.executable, str(helper), "emit"],
        input=body_piped, text=True, capture_output=True, cwd=str(REPO_ROOT),
    )
    sentinel = result.stdout.strip()
    response = sentinel + "\n" + body_emitted
    rc, _, _ = _run({"last_assistant_message": response})
    assert rc == 2, (
        f"v=2 sentinel with tampered body should fall through to material check "
        f"(exit 2); got rc={rc}"
    )


def test_v2_sentinel_one_shot_after_validation():
    """After first successful v=2 validation, the state file is deleted.
    A replay of the same response should fall through (no state to validate)."""
    body = "Ran pytest, 81 tests pass."
    response = _emit_v2_sentinel(body)
    rc1, _, _ = _run({"last_assistant_message": response})
    assert rc1 == 0
    # Second invocation with same response — state was atomic-deleted
    rc2, _, _ = _run({"last_assistant_message": response})
    assert rc2 == 2, (
        f"Replay of valid v=2 sentinel should fail (state deleted); got rc={rc2}"
    )


def test_v1_legacy_sentinel_rejected():
    """v=1 bare-string sentinel was forgeable; v0.7.9 rejects it."""
    rc, _, err = _run({
        "last_assistant_message": (
            "<!-- athanor:verification-emission v=1 -->\nBuild succeeded"
        )
    })
    assert rc == 2, f"v=1 legacy sentinel should fall through to material check; got rc={rc}"
    assert "legacy v=1" in err.lower() or "v=1" in err.lower(), (
        f"stderr should warn about legacy v=1 rejection; got: {err!r}"
    )


def test_v2_sentinel_missing_state_falls_through():
    """v=2 sentinel with no corresponding state file → forgery attempt → reject."""
    fake_sentinel = "<!-- athanor:verification-emission v=2 nonce=" + "a" * 32 + " -->"
    rc, _, _ = _run({
        "last_assistant_message": fake_sentinel + "\nBuild succeeded"
    })
    assert rc == 2, (
        f"Forged v=2 sentinel without matching state should fall through; got rc={rc}"
    )


def test_sentinel_with_leading_whitespace_still_recognized():
    """Leading whitespace before sentinel is allowed (regex pattern \\s*)."""
    body = "files changed"
    response = _emit_v2_sentinel(body)
    # Add leading whitespace
    response_padded = "  \n" + response
    rc, _, _ = _run({"last_assistant_message": response_padded})
    assert rc == 0


def test_sentinel_on_line_2_does_not_count():
    """Sentinel must be at start; greeting before it → falls through."""
    body = "tests pass"
    response = _emit_v2_sentinel(body)
    # Wrap with a greeting BEFORE the sentinel
    response_wrapped = "Sure thing!\n" + response
    rc, _, _ = _run({"last_assistant_message": response_wrapped})
    assert rc == 2, (
        f"Sentinel on line 2 should NOT prevent material-claim detection; got rc={rc}"
    )


def test_v2_sentinel_unbound_format_rejected():
    """v=2 sentinel WITHOUT nonce= field (malformed) → falls through."""
    rc, _, _ = _run({
        "last_assistant_message": (
            "<!-- athanor:verification-emission v=2 -->\n"
            "tests pass"
        )
    })
    assert rc == 2, (
        f"v=2 sentinel missing nonce= should fail validation; got rc={rc}"
    )


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


# --- v0.7.9 U4: config resolution priority ($CLAUDE_PROJECT_DIR, git-root, walk-stops-at-git)


def test_claude_project_dir_env_var_honored(tmp_path):
    """When $CLAUDE_PROJECT_DIR points at a directory with athanor.json,
    that config is used (priority 1)."""
    project = tmp_path / "claude_project"
    project.mkdir()
    (project / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off"}}), encoding="utf-8"
    )
    # Run from a different cwd so only the env var resolves the config
    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)
    rc, _, err = _run(
        {"last_assistant_message": "tests pass"},
        cwd=str(other_dir),
        env=env,
    )
    assert rc == 0, f"profile=off via $CLAUDE_PROJECT_DIR should disable gate; got rc={rc}"
    assert "CLAUDE_PROJECT_DIR" in err, (
        f"stderr should announce resolution via $CLAUDE_PROJECT_DIR; got: {err!r}"
    )


def test_parent_dir_hijack_blocked_by_git_boundary(tmp_path):
    """v0.7.9 closes PR #16 sec-002: ancestor athanor.json with profile=off
    must NOT silently disable the gate when called from inside a git repo
    whose root has no athanor.json. Walk-up stops at .git boundary."""
    # Set up: /tmp/X/athanor.json (profile=off) is a hostile ancestor.
    # /tmp/X/myrepo/ is a git repo with no athanor.json.
    # Run from /tmp/X/myrepo/subdir/ — the hostile athanor.json must NOT apply.
    ancestor = tmp_path / "hostile_ancestor"
    ancestor.mkdir()
    (ancestor / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off"}}), encoding="utf-8"
    )
    repo = ancestor / "myrepo"
    repo.mkdir()
    (repo / ".git").mkdir()  # simulate git repo (just need the dir to exist)
    subdir = repo / "subdir"
    subdir.mkdir()
    rc, _, _ = _run({"last_assistant_message": "tests pass"}, cwd=str(subdir))
    assert rc == 2, (
        f"v0.7.9 must NOT honor ancestor athanor.json above a .git boundary; got rc={rc} "
        f"(if 0, the parent-dir hijack from PR #16 sec-002 is still exploitable)"
    )


def test_athanor_json_at_git_root_resolved_via_git_root(tmp_path):
    """When athanor.json is at the git repo root, mechanism is 'git-root'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off"}}), encoding="utf-8"
    )
    subdir = repo / "src"
    subdir.mkdir()
    rc, _, err = _run({"last_assistant_message": "tests pass"}, cwd=str(subdir))
    assert rc == 0, f"profile=off at git root should disable gate; got rc={rc}"
    assert "git-root" in err, (
        f"stderr should announce resolution via 'git-root'; got: {err!r}"
    )


# --- Integration: re-entry prevention -------------------------------------


def test_two_turn_reentry_prevention_v2():
    """v0.7.9 contract: first Stop fires on material claim (exit 2),
    next turn the verification skill emits v=2 nonce-bound evidence, that
    triggers a second Stop event which exits 0 silently (no infinite loop)."""
    # Turn 1: material claim, no sentinel → exit 2
    rc1, _, _ = _run({"last_assistant_message": "build succeeded"})
    assert rc1 == 2
    # Turn 2: verification skill response with v=2 sentinel → exit 0
    body = "Ran `pytest`, exit 0, 81 tests passed."
    response = _emit_v2_sentinel(body)
    rc2, _, _ = _run({"last_assistant_message": response})
    assert rc2 == 0, (
        f"Re-entry prevention failed: sentinel-prefixed response triggered exit {rc2}"
    )
