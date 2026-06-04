"""Regression — learner-on-release contract has a wired trigger point.

Context
-------
`agents/learner.md` §On Release defines a release-time invariant: every
git tag must trigger a Learner run that mines the release diff for at
least one lesson. The lfg/lfg-goal doc-lifecycle audit found this contract
dormant — `docs/STATE.md` tracked it as "contract만 있음 / 자동 트리거
없음" (contract-only, no trigger). Nothing in the release ceremony invoked
the Learner.

Wave 2 wires the trigger into the release ceremony: `agents/releaser.md`
gains a Step 6 that makes the leader dispatch the Learner after the
release tag (the releaser worker has no Agent tool, so it surfaces a
pending signal and the leader honors the contract — Thin Leader
preserved). These tests lock the trigger point so it cannot silently
regress back to dormant.

Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASER = REPO_ROOT / "agents" / "releaser.md"
LEARNER = REPO_ROOT / "agents" / "learner.md"


def test_releaser_wires_learner_on_release() -> None:
    """MUST — the release ceremony documents a learner-on-release dispatch."""
    text = RELEASER.read_text(encoding="utf-8")
    low = text.lower()
    assert "learner-on-release" in low, (
        "agents/releaser.md must wire the learner-on-release trigger (a "
        "ceremony step that dispatches the Learner after the release tag) — "
        "otherwise the contract in agents/learner.md §On Release stays "
        "dormant."
    )
    assert "learner" in low and "release" in low and "dispatch" in low, (
        "the learner-on-release step must describe dispatching the Learner "
        "for the release window."
    )


def test_learner_on_release_contract_present() -> None:
    """MUST — the Learner still declares the On Release invariant."""
    text = LEARNER.read_text(encoding="utf-8")
    assert "## On Release" in text and "learner-on-release" in text.lower(), (
        "agents/learner.md must keep the §On Release contract that the "
        "releaser step honors."
    )
