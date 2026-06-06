"""Regression — pretool_dispatcher surfaces stdin parse failure (fail-loud).

The dispatcher's entry fail-open on missing/unparseable stdin returned 0
**silently** (no stderr) — a guard that no-ops invisibly is exactly the
"error swallowed by a fallback" the §Core Principle ("Engineering quality":
fail-loud over silent fallback) warns against. The kernel_guard and
stop_verify hooks already emit a breadcrumb on this path. v0.18.4 makes the
dispatcher do the same: fail-open is fine, fail-SILENT is not.

This is athanor's OWN code, so it is a real gate (subprocess test), not an
advisory lens.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DISPATCHER = REPO_ROOT / "scripts" / "hooks" / "pretool_dispatcher.py"


def test_dispatcher_emits_breadcrumb_on_unparseable_stdin() -> None:
    """MUST — empty/unparseable stdin → exit 0 (fail-open) WITH a stderr breadcrumb."""
    result = subprocess.run(
        [sys.executable, str(DISPATCHER)],
        input="",  # empty body → read_stdin_payload() returns None
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"dispatcher must fail-OPEN (exit 0) on unparseable stdin, got "
        f"{result.returncode}. stderr={result.stderr!r}"
    )
    assert result.stderr.strip() != "", (
        "dispatcher must emit a stderr breadcrumb on unparseable stdin — a "
        "silently no-op guard hides the failure (fail-loud over silent "
        "fallback, §Core Principle)."
    )
    low = result.stderr.lower()
    assert "stdin" in low or "fail-open" in low, (
        f"breadcrumb should name the cause (stdin / fail-open); got "
        f"{result.stderr!r}"
    )
