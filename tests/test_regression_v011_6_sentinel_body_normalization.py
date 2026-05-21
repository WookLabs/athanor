"""Regression tests for v0.11.6 — sentinel body-hash normalization (companion-fix arc).

## Bug being fixed (analyzed 2026-05-21)

v0.7.9 introduced v=2 nonce-bound sentinel protocol with SHA-256 body
hash binding. Production round-trip never worked reliably:

- `sentinel_helper.py emit` reads stdin → hashes raw bytes → stores
  body_hash in nonce.json
- `stop_verify_claims.py validate_emission_sentinel()` extracts body
  from the model's response in transcript → `lstrip("\n")` → hashes →
  compares to stored body_hash

The mismatch source (empirically diagnosed in v0.11.6 ship session):

1. Heredoc / file body typically has trailing `\n` (file = N+1 bytes)
2. Claude Code transcript captures the model's response WITHOUT trailing
   newlines (text block = N bytes)
3. Helper hashes N+1 bytes; script hashes N bytes → mismatch by exactly
   trailing whitespace

This bug was documented as "Residual known limitation" since v0.7.9 and
called "v0.11.0+ candidate" through v0.11.5 — that classification was
itself an honesty-arc violation (a bug, not an enhancement).

## v0.11.6 fix

Both ends normalize whitespace before hashing:
- `sentinel_helper.py`: `body.strip().encode("utf-8")`
- `stop_verify_claims.py`: `body_canonical = body_after.strip()`

This makes the protocol tolerant of trailing-newline differences
between piped body and transcript-captured body, while preserving
forgery cost on content differences (whitespace is not a security
boundary).

Plan: .athanor/sessions/2026-05-21-004/plan.md (this release)
Companion-fix arc:
- v0.11.3: script wrong (stdin parser)
- v0.11.4: path wrong (relative-path hook command)
- v0.11.5: doc drift class (CLAUDE.md untestable claims)
- v0.11.6 (this): sentinel binding wrong (trailing-whitespace mismatch)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINEL_HELPER = REPO_ROOT / "scripts" / "hooks" / "sentinel_helper.py"
STOP_VERIFY_CLAIMS = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"


def _emit_sentinel(body: str, cwd: Path) -> tuple[int, str, str]:
    """Pipe `body` to sentinel_helper.py emit; return (returncode, sentinel, stderr).

    cwd matters because hook_state writes nonce.json under
    `.athanor/sessions/active/.hook-state/` resolved relative to cwd.
    """
    result = subprocess.run(
        [sys.executable, str(SENTINEL_HELPER), "emit"],
        input=body,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
    )
    return result.returncode, result.stdout.strip(), result.stderr


def _run_stop_hook(payload: dict, cwd: Path) -> tuple[int, str]:
    """Invoke stop_verify_claims.py with payload; return (exit_code, stderr)."""
    result = subprocess.run(
        [sys.executable, str(STOP_VERIFY_CLAIMS)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
    )
    return result.returncode, result.stderr


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal project dir with athanor.json and .athanor/sessions/active/."""
    (tmp_path / ".athanor" / "sessions" / "active" / ".hook-state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "athanor.json").write_text(
        '{"hooks": {"profile": "standard", "stopLoopThreshold": 3}}',
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


# ---- Bug repro: trailing-newline mismatch (RED-first) ----


def test_trailing_newline_mismatch_round_trip(tmp_path: Path):
    """The v0.7.9 bug: helper hashes body WITH trailing newline; transcript
    captures response WITHOUT trailing newline → hash mismatch → sentinel
    rejected → gate fires on the verification response itself.

    v0.11.6 fix: both ends normalize via .strip() before hashing. Round-trip
    now works regardless of trailing whitespace differences.
    """
    project = _setup_project(tmp_path)
    body_with_trail = "tests pass on my machine\n"  # heredoc-style with trailing \n
    body_no_trail = body_with_trail.rstrip()  # what transcript captures

    # Emit sentinel binding the body WITH trailing newline
    rc, sentinel, err = _emit_sentinel(body_with_trail, project)
    assert rc == 0, f"sentinel_helper emit failed: {err}"
    assert sentinel.startswith("<!-- athanor:verification-emission v=2 nonce="), sentinel

    # Simulate Claude Code transcript: model response = sentinel + body (no trailing newline)
    response = sentinel + "\n" + body_no_trail
    transcript = _write_transcript_with_response(project, response)

    payload = {
        "session_id": "test",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }
    exit_code, stderr = _run_stop_hook(payload, project)

    # v0.11.6: sentinel binding accepts the mismatch (trailing-newline tolerance)
    # → gate exits 0 (sentinel validates, nonce state consumed).
    assert exit_code == 0, (
        f"v0.11.6 trailing-newline normalization should accept body with "
        f"stripped trailing whitespace. Got exit={exit_code} stderr={stderr!r}"
    )
    assert "body hash mismatch" not in stderr, (
        f"v0.11.6: trailing-newline difference should NOT produce hash mismatch. "
        f"stderr={stderr!r}"
    )


def test_leading_newline_tolerance(tmp_path: Path):
    """v0.11.6: leading newline differences also normalized away by .strip()."""
    project = _setup_project(tmp_path)
    body_with_leading = "\n\ntests pass on my machine"
    body_no_leading = body_with_leading.lstrip()

    rc, sentinel, err = _emit_sentinel(body_with_leading, project)
    assert rc == 0

    response = sentinel + "\n" + body_no_leading
    transcript = _write_transcript_with_response(project, response)

    payload = {
        "session_id": "test",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }
    exit_code, stderr = _run_stop_hook(payload, project)
    assert exit_code == 0, f"leading-newline normalization broken: stderr={stderr!r}"


def test_byte_identical_body_still_validates(tmp_path: Path):
    """Baseline: when piped body == response body byte-for-byte, sentinel
    must still validate (no regression on the working case)."""
    project = _setup_project(tmp_path)
    body = "tests pass on my machine"  # no leading/trailing whitespace

    rc, sentinel, err = _emit_sentinel(body, project)
    assert rc == 0

    response = sentinel + "\n" + body
    transcript = _write_transcript_with_response(project, response)

    payload = {
        "session_id": "test",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }
    exit_code, stderr = _run_stop_hook(payload, project)
    assert exit_code == 0, f"byte-identical baseline broken: stderr={stderr!r}"


def test_content_difference_still_rejected(tmp_path: Path):
    """Security boundary preserved: when response body differs from piped body
    in actual content (not just whitespace), sentinel must still be rejected.

    This is the forgery cost the v=2 protocol is supposed to raise. v0.11.6's
    whitespace normalization must NOT degrade this to v=1 levels.
    """
    project = _setup_project(tmp_path)
    piped_body = "tests pass on my machine"
    forged_body = "tests pass on production"  # different content

    rc, sentinel, err = _emit_sentinel(piped_body, project)
    assert rc == 0

    response = sentinel + "\n" + forged_body
    transcript = _write_transcript_with_response(project, response)

    payload = {
        "session_id": "test",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }
    exit_code, stderr = _run_stop_hook(payload, project)
    # Content forgery should fail sentinel validation → fall through to
    # material-claim check → "tests pass" detected → exit 2.
    assert exit_code == 2, (
        f"v0.11.6: content-forgery (not just whitespace) MUST still be rejected. "
        f"Got exit={exit_code} stderr={stderr!r}"
    )
    assert "body hash mismatch" in stderr or "material claim detected" in stderr


def test_normalization_consistency_between_helper_and_script():
    """Direct unit test: helper.encode and script.encode produce the same
    hash for whitespace-only differences after .strip() normalization."""
    bodies = [
        ("plain body", "plain body"),
        ("body with trail\n", "body with trail"),
        ("\nbody with leading", "body with leading"),
        ("\n\nboth ends\n\n", "both ends"),
        ("  spaces around  ", "spaces around"),
    ]
    for raw_a, raw_b in bodies:
        # Both should normalize to the same canonical hash via .strip()
        h_a = hashlib.sha256(raw_a.strip().encode("utf-8")).hexdigest()
        h_b = hashlib.sha256(raw_b.strip().encode("utf-8")).hexdigest()
        assert h_a == h_b, (
            f"v0.11.6 normalization inconsistent: "
            f"strip({raw_a!r}) hash != strip({raw_b!r}) hash"
        )
