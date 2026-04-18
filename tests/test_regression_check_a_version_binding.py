"""
Regression test for structured version-anchor check (v0.7.1 follow-up fix #3).

Imports `_work_log_has_version_anchor` from scripts.check_release_ready.
Covers:
  - positive: `## v0.7.1\n` header matches
  - positive: `## 0.7.1\n` (no v prefix) also matches (spec)
  - negative: substring `v10.7.1` does NOT match (word-boundary)
  - negative: `0.7.10` does NOT match (word-boundary)
  - negative: pure-prose mention of v0.7.1 does NOT satisfy the gate
  - negative: missing file returns False (no exception)
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.check_release_ready import _work_log_has_version_anchor

REPO_ROOT = Path(__file__).resolve().parent.parent
NO_ANCHOR_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "work-log-no-anchor.md"


def _write_tmp(content: str) -> Path:
    """Windows-safe tmp file via tempfile (avoid pytest tmp_path junction issue)."""
    d = tempfile.mkdtemp()
    p = Path(d) / "work-log.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_positive_header_matches():
    p = _write_tmp("some body\n\n## v0.7.1\n\ncontent\n")
    assert _work_log_has_version_anchor(p, "0.7.1") is True


def test_positive_no_v_prefix():
    p = _write_tmp("some body\n\n## 0.7.1\n\ncontent\n")
    assert _work_log_has_version_anchor(p, "0.7.1") is True


def test_negative_substring_does_not_match():
    p = _write_tmp("Released v10.7.1 earlier in the day.\n")
    assert _work_log_has_version_anchor(p, "0.7.1") is False


def test_negative_dot_extension_does_not_match():
    p = _write_tmp("## See 0.7.10 for details\n")
    assert _work_log_has_version_anchor(p, "0.7.1") is False


def test_negative_prose_mention_does_not_match():
    # Load the pre-existing fixture from the repo
    assert _work_log_has_version_anchor(NO_ANCHOR_FIXTURE, "0.7.1") is False


def test_negative_missing_file():
    assert _work_log_has_version_anchor(Path("/definitely/does/not/exist.md"), "0.7.1") is False


def test_session_missing_gives_clean_error():
    """--session <nonexistent> should exit non-zero with clean stderr, no traceback."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_release_ready.py"),
         "--session", "does-not-exist-0000-00-00-999",
         "--skip-evidence"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, f"Expected non-zero exit; got {result.returncode}"
    assert "session directory not found" in result.stderr, f"Expected 'session directory not found' in stderr; got: {result.stderr!r}"
    assert "Traceback" not in combined, f"Expected no traceback in output; got: {combined!r}"
