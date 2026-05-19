"""Regression test for v0.10.1 U1 invariant — `scripts/check_vendor_drift.py`
exists, is invocable, and produces sensible exit codes.

Exit code contract:
  0 — no drift detected (vendored tree matches upstream caches)
  1 — drift detected
  2 — upstream cache unreachable

Plan reference: docs/plans/2026-05-19-004-feat-v0.10.1-vendor-hygiene-plan.md
§U1.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_vendor_drift.py"


def _run_drift(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        **kwargs,
    )


def test_script_exists_and_is_executable_python():
    """MUST: script file exists and starts with a Python shebang."""
    assert SCRIPT.exists(), f"Drift script missing: {SCRIPT}"
    first_line = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!") and "python" in first_line, (
        f"Drift script shebang must invoke python; first line: {first_line!r}"
    )


def test_script_help_works():
    """MUST: --help exits 0 and prints a usage banner."""
    result = _run_drift(["--help"])
    assert result.returncode == 0
    assert "drift" in result.stdout.lower() or "vendor" in result.stdout.lower()


def test_unreachable_cache_yields_exit_2():
    """MUST: pointing the script at a non-existent cache root returns
    exit code 2 (upstream unreachable)."""
    result = _run_drift(["--cache-root", "/tmp/__athanor_nonexistent_cache__"])
    assert result.returncode == 2, (
        f"Expected exit 2 for missing cache; got {result.returncode}. "
        f"stderr: {result.stderr[:200]}"
    )


def test_single_skill_filter_works():
    """MUST: --skill filter limits the diff to one skill."""
    result = _run_drift(["--skill", "ce-plan", "--ci"])
    # exit code may be 0/1/2 depending on local state; we only assert the
    # summary mentions `total=1` (the filter restricted to one skill).
    assert "total=1" in result.stdout, (
        f"--skill filter must restrict to total=1. stdout: {result.stdout!r}"
    )


def test_ci_mode_suppresses_per_skill_output():
    """MUST: --ci mode prints only the one-line summary (per-skill drift
    bodies suppressed)."""
    result = _run_drift(["--ci"])
    # Either pass (no drift) or fail (drift) is fine; we just assert the
    # bulk diff body is NOT in the output in CI mode.
    assert "@@" not in result.stdout, (
        "--ci mode must not emit unified-diff bodies"
    )
    assert "check_vendor_drift:" in result.stdout, (
        "--ci mode must still print the summary line"
    )
