"""Regression — completion archival carries the receipts evidence trail.

Context
-------
`skills/lfg-goal/SKILL.md` §Goal Storage Lifecycle archives a completed
goal by copying `goal.md` + `goal-completion.md` to
`docs/goals-completed/<id>/`. The lfg/lfg-goal doc-lifecycle audit found
the per-cycle validator receipts (`receipts/CNNN-*-receipt.md`) — the
externally-verifiable "load-bearing honesty primitive" — were NOT carried
into the gitted archive. Once the gitignored `.athanor/goals/<id>/` tree is
later aged out, the evidence trail would be lost.

Wave 2 extends the archival to copy the `receipts/` directory too. These
tests lock that the archival names receipts, and that destroying a
completed goal's live tree remains an explicit user action.

Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LFG_GOAL = REPO_ROOT / "skills" / "lfg-goal" / "SKILL.md"


def _goal_storage_section(text: str) -> str:
    """Return the '## Goal Storage Lifecycle' section body (until next H2)."""
    idx = text.find("## Goal Storage Lifecycle")
    if idx == -1:
        return ""
    end = text.find("\n## ", idx + 1)
    return text[idx : end if end != -1 else len(text)]


def test_completion_archival_includes_receipts() -> None:
    """MUST — archival copies receipts alongside goal.md/goal-completion.md."""
    section = _goal_storage_section(LFG_GOAL.read_text(encoding="utf-8"))
    assert section, (
        "skills/lfg-goal/SKILL.md must keep the '## Goal Storage Lifecycle' "
        "section — it is the canonical archival contract."
    )
    low = section.lower()
    assert "goals-completed" in low and "receipts" in low, (
        "completion archival must copy the receipts/ evidence trail into "
        "docs/goals-completed/<id>/ alongside goal.md and goal-completion.md "
        "— receipts are the externally-verifiable completion record and must "
        "survive in the gitted archive."
    )


def test_completed_goal_deletion_remains_user_action() -> None:
    """MUST — deleting a completed goal's live tree stays a user action."""
    low = LFG_GOAL.read_text(encoding="utf-8").lower()
    assert "destructive ops" in low and "user action" in low, (
        "deleting a completed goal's live tree must remain an explicit user "
        "action (athanor convention) — archival is a copy, never an "
        "automatic destructive move."
    )
