"""Regression — STATE.md Previous Phase backlog is bounded (trim applied).

Context
-------
v0.18.2 shipped the releaser bounded-history *rule* (Step 3: keep Current +
5 Previous Phase, move surplus to docs/archive/STATE-history.md) but left
the existing backlog untrimmed — docs/STATE.md had grown to ~1362 lines /
Current + 28 Previous Phase sections. v0.18.3 applies the rule for the
first time: the oldest surplus (v0.15.0 … v0.7.9) is MOVED verbatim to the
archive, leaving Current + the newest 5 Previous Phase in STATE.md.

These tests lock the cap and confirm the move was non-destructive.
Static text reads only.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_MD = REPO_ROOT / "docs" / "STATE.md"
ARCHIVE = REPO_ROOT / "docs" / "archive" / "STATE-history.md"
CAP = 5


def test_previous_phase_count_within_cap() -> None:
    """MUST — STATE.md retains at most CAP Previous Phase sections."""
    body = STATE_MD.read_text(encoding="utf-8")
    count = len(re.findall(r"^## Previous(?:-Previous)? Phase", body, re.MULTILINE))
    assert count <= CAP, (
        f"STATE.md has {count} '## Previous Phase' sections; the releaser "
        f"bounded-history cap is {CAP}. Move the oldest surplus to "
        f"docs/archive/STATE-history.md (verbatim, non-destructive)."
    )


def test_state_history_archive_populated() -> None:
    """MUST — archive exists and retains the moved phases verbatim."""
    assert ARCHIVE.is_file(), (
        "docs/archive/STATE-history.md must exist once the backlog is trimmed."
    )
    hist = ARCHIVE.read_text(encoding="utf-8")
    for v in ("v0.7.9", "v0.10.0", "v0.12.0", "v0.15.0"):
        assert v in hist, (
            f"docs/archive/STATE-history.md must retain {v} — archival is a "
            f"verbatim MOVE, not a drop."
        )


def test_state_md_keeps_recent_phases() -> None:
    """MUST — the newest phases stay live in STATE.md."""
    body = STATE_MD.read_text(encoding="utf-8")
    assert "## Current Phase: v0.21" in body, "STATE.md must keep the Current Phase."
    # The pinned set slides with the trim window: v0.21.0 rotates v0.20.1 into
    # Previous and archives the oldest surplus (v0.18.7), so the live Previous
    # phases are now v0.20.1, v0.20.0, v0.19.3, v0.19.2, v0.18.8.
    for v in ("v0.20.1", "v0.20.0", "v0.18.8"):
        assert v in body, f"STATE.md must keep the recent phase {v}."
