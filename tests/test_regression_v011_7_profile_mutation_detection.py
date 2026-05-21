"""Regression tests for v0.11.7 — B1 minimal mid-session hooks.profile mutation detection.

## Bug being addressed (B1 — Residual #6)

A model with file-system access can write athanor.json mid-session to flip
`hooks.profile` from "standard" to "off", bypassing the Stop hook gate for
the next Stop event in the same session. The full architectural mitigation
(file-lock vs. cached-checksum-key vs. opt-in cross-session edit block) is
deferred to v0.11.8+. v0.11.7 ships **minimal detection only**:

- On the first Stop event of a session, the script computes a SHA-256 of
  the `hooks` block (canonical JSON serialization) and persists it via
  `hook_state.write_profile_snapshot()`.
- On every subsequent Stop event within the same session, the script
  re-computes the hash and compares against the stored value via
  `hook_state.read_profile_snapshot()`. On mismatch, an explicit stderr
  warning fires.
- Detection is informational — it does NOT block the gate, does NOT
  override the off-profile bypass, and does NOT auto-revert. Cross-session
  edits re-snapshot cleanly (new session = new snapshot).

## Acceptance criteria (RED-first)

- 6.1 First Stop event with profile="standard" → snapshot file created, no warning.
- 6.2 Second Stop with profile unchanged → no warning.
- 6.3 Second Stop with profile flipped "standard" → "off" → stderr warning fires.
- 6.4 Mutation detection does NOT block the gate — exit code semantics preserved.
- 6.5 Cross-session — snapshot in session A doesn't affect session B (per-session isolation).

Plan: .athanor/sessions/2026-05-21-004/plan.md (Phase 5)
Companion-fix arc layer 5 of 5: v0.11.3 → v0.11.4 → v0.11.5 → v0.11.6 →
v0.11.7 (security extension / 5th layer).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_HOOKS_DIR = REPO_ROOT / "scripts" / "hooks"
STOP_VERIFY_CLAIMS = SCRIPTS_HOOKS_DIR / "stop_verify_claims.py"
HOOK_STATE_DIR = REPO_ROOT / ".athanor" / "sessions" / "active" / ".hook-state"

MUTATION_WARNING_PHRASE = "mid-session hooks.profile mutation detected"


@pytest.fixture(autouse=True)
def _clean_hook_state():
    """Clean REPO_ROOT .athanor/sessions/active/.hook-state/ before+after each test.

    Tests use cwd=tmp_path for all subprocess invocations, so REPO_ROOT state
    should not be polluted — but this autouse fixture preempts fragility if
    any future test forgets `cwd=` and silently writes into REPO_ROOT. Pattern
    mirrors tests/test_regression_v011_6_sentinel_body_normalization.py.
    """
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)
    yield
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)


def _setup_project(tmp_path: Path, profile: str = "standard") -> Path:
    """Create a minimal project dir with athanor.json + sessions/active/."""
    (tmp_path / ".athanor" / "sessions" / "active" / ".hook-state").mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": profile, "stopLoopThreshold": 3}}),
        encoding="utf-8",
    )
    return tmp_path


def _write_transcript_with_response(tmp_path: Path, response_text: str) -> Path:
    """Write a single-line transcript JSONL containing a main-session
    assistant turn with one text block = `response_text`."""
    tpath = tmp_path / "transcript.jsonl"
    entry = {
        "type": "assistant",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": response_text}],
        },
    }
    tpath.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return tpath


def _run_stop_hook(payload: dict, cwd: Path) -> tuple[int, str]:
    """Invoke stop_verify_claims.py with payload; return (exit_code, stderr)."""
    result = subprocess.run(
        [sys.executable, str(STOP_VERIFY_CLAIMS)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
    )
    return result.returncode, result.stderr


def _stop_payload(transcript: Path) -> dict:
    return {
        "session_id": "test",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }


# ---- Test 6.1: First Stop snapshots, no warning ---------------------------


def test_first_stop_creates_snapshot_no_warning(tmp_path: Path):
    """First Stop event of a session: snapshot file is created, no warning is emitted."""
    project = _setup_project(tmp_path, profile="standard")
    response = "Just a benign analysis with no material claim."  # no gate fire
    transcript = _write_transcript_with_response(project, response)

    exit_code, stderr = _run_stop_hook(_stop_payload(transcript), project)

    # No material claim → exit 0
    assert exit_code == 0, f"expected exit 0 on benign response, got {exit_code}; stderr={stderr!r}"
    # No mutation warning on first Stop (nothing to compare against)
    assert MUTATION_WARNING_PHRASE not in (stderr or ""), (
        f"first Stop should not emit mutation warning; stderr={stderr!r}"
    )
    # Snapshot file must exist at expected location
    snapshot_path = project / ".athanor" / "sessions" / "active" / ".hook-state" / "profile-snapshot.json"
    assert snapshot_path.exists(), (
        f"expected profile-snapshot.json at {snapshot_path}; not found"
    )


# ---- Test 6.2: Second Stop, unchanged → no warning -----------------------


def test_second_stop_unchanged_profile_no_warning(tmp_path: Path):
    """Second Stop with profile unchanged: snapshot matches, no warning."""
    project = _setup_project(tmp_path, profile="standard")
    response = "Just a benign analysis with no material claim."
    transcript = _write_transcript_with_response(project, response)

    # First Stop
    exit_code_1, stderr_1 = _run_stop_hook(_stop_payload(transcript), project)
    assert exit_code_1 == 0, f"first Stop unexpected exit={exit_code_1}; stderr={stderr_1!r}"

    # Second Stop with unchanged config
    exit_code_2, stderr_2 = _run_stop_hook(_stop_payload(transcript), project)
    assert exit_code_2 == 0, f"second Stop unexpected exit={exit_code_2}; stderr={stderr_2!r}"
    assert MUTATION_WARNING_PHRASE not in (stderr_2 or ""), (
        f"unchanged profile should not emit mutation warning; stderr={stderr_2!r}"
    )


# ---- Test 6.3: Second Stop, mutated → warning ---------------------------


def test_second_stop_mutated_profile_emits_warning(tmp_path: Path):
    """Second Stop with profile flipped standard→off: mutation warning fires on stderr."""
    project = _setup_project(tmp_path, profile="standard")
    response = "Just a benign analysis with no material claim."
    transcript = _write_transcript_with_response(project, response)

    # First Stop with profile=standard → snapshot taken
    exit_code_1, stderr_1 = _run_stop_hook(_stop_payload(transcript), project)
    assert exit_code_1 == 0, f"first Stop unexpected exit={exit_code_1}; stderr={stderr_1!r}"

    # Mutate athanor.json: flip profile standard → off
    (project / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off", "stopLoopThreshold": 3}}),
        encoding="utf-8",
    )

    # Second Stop
    exit_code_2, stderr_2 = _run_stop_hook(_stop_payload(transcript), project)

    # Mutation warning MUST appear on stderr
    assert MUTATION_WARNING_PHRASE in (stderr_2 or ""), (
        f"mutation warning {MUTATION_WARNING_PHRASE!r} should fire on stderr; "
        f"got stderr={stderr_2!r}"
    )


# ---- Test 6.4: Mutation detection does NOT block the gate -----------------


def test_mutation_warning_does_not_change_exit_code(tmp_path: Path):
    """Mutation detection is warning-only: exit code semantics preserved.

    - First Stop with material claim + profile=standard → exit 2 (gate fires)
    - Mutate profile standard → off
    - Second Stop with same material claim → exit 0 (off-profile bypass) +
      mutation warning on stderr (detection doesn't change exit code)
    """
    project = _setup_project(tmp_path, profile="standard")
    # Material claim → gate would normally fire with profile=standard
    response = "All tests pass on my machine."
    transcript = _write_transcript_with_response(project, response)

    # First Stop with profile=standard → gate fires (exit 2) AND snapshot taken
    exit_code_1, _ = _run_stop_hook(_stop_payload(transcript), project)
    assert exit_code_1 == 2, f"first Stop should fire gate (exit 2), got {exit_code_1}"

    # Mutate athanor.json: flip profile standard → off (the attempted bypass)
    (project / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off", "stopLoopThreshold": 3}}),
        encoding="utf-8",
    )

    # Second Stop: off-profile bypass remains in effect (exit 0) — detection
    # ONLY warns; it does NOT override the opt-out (honesty: opt-out remains opt-out).
    exit_code_2, stderr_2 = _run_stop_hook(_stop_payload(transcript), project)
    assert exit_code_2 == 0, (
        f"profile=off bypass MUST remain in effect — detection is warning-only. "
        f"Got exit={exit_code_2}; stderr={stderr_2!r}"
    )
    # The mutation warning still fires
    assert MUTATION_WARNING_PHRASE in (stderr_2 or ""), (
        f"mutation warning should still fire alongside the off-profile bypass; "
        f"stderr={stderr_2!r}"
    )


# ---- Test 6.5: Cross-session isolation -----------------------------------


def test_cross_session_snapshot_isolation(tmp_path: Path):
    """Snapshot in session A doesn't affect a different session B.

    Each session's snapshot lives under `.athanor/sessions/<id>/.hook-state/`,
    so two separate project trees (= two separate cwd) get independent
    snapshots. First Stop in session B sees no prior snapshot → no warning
    even if session A had a "standard" profile and session B has "off".
    """
    # Session A: profile=standard, first Stop creates snapshot
    session_a = tmp_path / "session_a"
    session_a.mkdir()
    _setup_project(session_a, profile="standard")
    response = "Just a benign analysis with no material claim."
    transcript_a = _write_transcript_with_response(session_a, response)
    exit_code_a, stderr_a = _run_stop_hook(_stop_payload(transcript_a), session_a)
    assert exit_code_a == 0, f"session A unexpected exit={exit_code_a}; stderr={stderr_a!r}"

    # Session B: profile=off (different value), separate cwd → separate state
    session_b = tmp_path / "session_b"
    session_b.mkdir()
    _setup_project(session_b, profile="off")
    transcript_b = _write_transcript_with_response(session_b, response)
    exit_code_b, stderr_b = _run_stop_hook(_stop_payload(transcript_b), session_b)

    # No warning in session B — it's a fresh session, no prior snapshot to compare against
    assert exit_code_b == 0, f"session B unexpected exit={exit_code_b}; stderr={stderr_b!r}"
    assert MUTATION_WARNING_PHRASE not in (stderr_b or ""), (
        f"session B is fresh; no mutation warning expected. stderr={stderr_b!r}"
    )
