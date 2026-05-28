"""Regression test for v0.12.0 vendored-removal script (Subtask 14 + Subtask 15).

Subtask 14 created the script; Subtask 15 ran it on the live tree. The
test is rewritten post-Subtask-15 to reflect that running the script
again on the post-removal disk state surfaces the defense-in-depth count
check (script aborts with exit 1 because the disk shows 1 ce-* + 0 sp-*
instead of the pre-removal 33 + 13).

This test pins:
  - The script file exists (Subtask 14).
  - The dry-run on POST-REMOVAL state surfaces the disk-drift exit-1
    behavior with a clear error message identifying drift from the D14.2
    plan. This is the script behaving correctly — it refuses to run on a
    disk that doesn't match its preconditions.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "v012_remove_vendored.py"


def test_removal_script_exists():
    """Subtask 14 invariant: the script file exists."""
    assert SCRIPT.exists(), (
        f"Subtask 14 must create {SCRIPT}; required by Subtask 15 to run "
        f"the atomic cut"
    )


def test_removal_script_refuses_to_run_on_post_removal_disk():
    """Post-Subtask-15 / post-v0.15.x: re-running the script aborts cleanly
    because the disk no longer matches its pre-removal preconditions.

    With vendored/ fully removed (including the 2 D12 sub-agents removed in
    v0.15.x), the script may exit at the agents-dir guard ("agents dir not
    found") rather than the D14.2 drift check ("drift" / "expected").
    Both indicate the script correctly refuses to proceed — this is the
    intended behavior, not a regression."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    # Script surfaces drift on stderr (SystemExit) with non-zero rc.
    assert result.returncode != 0, (
        f"--dry-run should refuse to run on post-removal disk; got rc=0. "
        f"stdout: {result.stdout[:300]!r}"
    )
    # Error message must identify why the script refused (drift from D14.2
    # plan, or agents/vendored/ce dir no longer present).
    combined = (result.stderr + result.stdout).lower()
    assert (
        "drift" in combined
        or "expected" in combined
        or "not found" in combined
        or "agents dir" in combined
    ), (
        f"Refusal message missing; combined output: "
        f"{(result.stderr + result.stdout)[:500]!r}"
    )
