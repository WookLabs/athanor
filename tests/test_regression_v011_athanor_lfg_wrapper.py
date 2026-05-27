"""Regression tests for v0.11.0 invariants — `/athanor:lfg` wrapper skill.

The wrapper exists alongside vendored `/athanor:ce-lfg`. It invokes
athanor-native commands at identity-bearing steps (plan + work + review)
and reuses vendored CE step shape at non-identity-bearing steps (autofix
persist, residual handoff, browser test, commit-push-pr, CI watch, DONE).

Plan reference: docs/plans/2026-05-19-007-feat-v0.11.0-athanor-lfg-wrapper-plan.md
Origin requirements: docs/brainstorms/2026-05-19-003-athanor-standalone-lfg-wrapper-requirements.md
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ATHANOR_LFG_SKILL = REPO_ROOT / "skills" / "lfg" / "SKILL.md"
VENDORED_CE_LFG_SKILL = REPO_ROOT / "skills" / "ce-lfg" / "SKILL.md"


def _load_athanor_lfg() -> str:
    return ATHANOR_LFG_SKILL.read_text(encoding="utf-8")


# v0.12.0: `_load_ce_lfg` removed — vendored skills/ce-lfg/ deleted per D9
# FULL DROP. See `test_vendored_ce_lfg_removed_post_v012` below.


# ---- Structure: file exists at the right path for depth-1 auto-discovery ----


def test_lfg_skill_exists_at_depth_1():
    """MUST: skills/lfg/SKILL.md exists (depth-1 auto-discovery)."""
    assert ATHANOR_LFG_SKILL.exists(), (
        f"v0.11.0: /athanor:lfg wrapper skill must exist at "
        f"skills/lfg/SKILL.md (depth-1 for Claude Code auto-discovery). "
        f"Path checked: {ATHANOR_LFG_SKILL}"
    )


def test_lfg_skill_has_valid_frontmatter():
    """MUST: YAML frontmatter present with name=lfg + non-empty description."""
    body = _load_athanor_lfg()
    lines = body.splitlines()
    assert lines and lines[0].rstrip() == "---", (
        "skills/lfg/SKILL.md must start with YAML frontmatter '---'"
    )
    # Find frontmatter close
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            close_idx = i
            break
    assert close_idx is not None, "Frontmatter must have closing '---'"
    fm = "\n".join(lines[1:close_idx])
    name_match = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
    assert name_match and name_match.group(1) == "lfg", (
        f"Frontmatter `name:` must be 'lfg'; got: {name_match.group(1) if name_match else None!r}"
    )
    assert re.search(r"^description:", fm, re.MULTILINE), (
        "Frontmatter must have `description:` field"
    )


# ---- Identity-bearing steps invoke athanor-native commands ----


def test_step_1_invokes_athanor_plan():
    """MUST: Step 1 dispatches /athanor:plan (cross-model adversarial)."""
    body = _load_athanor_lfg()
    # Locate step 1
    step1_idx = re.search(r"(?im)^\s*(?:#+\s*)?step\s*1\b", body)
    assert step1_idx, "Step 1 anchor must exist in /athanor:lfg body"
    # Look forward from step 1 for /athanor:plan reference within a reasonable window
    window = body[step1_idx.start() : step1_idx.start() + 1500]
    assert "/athanor:plan" in window or "athanor:plan" in window, (
        f"Step 1 must invoke /athanor:plan (cross-model adversarial). "
        f"Window first 200 chars: {window[:200]!r}"
    )


def test_step_2_invokes_athanor_work():
    """MUST: Step 2 dispatches /athanor:work (Spec-then-TDD)."""
    body = _load_athanor_lfg()
    step2_idx = re.search(r"(?im)^\s*(?:#+\s*)?step\s*2\b", body)
    assert step2_idx, "Step 2 anchor must exist"
    window = body[step2_idx.start() : step2_idx.start() + 1500]
    assert "/athanor:work" in window or "athanor:work" in window, (
        f"Step 2 must invoke /athanor:work (Spec-then-TDD). "
        f"Window first 200 chars: {window[:200]!r}"
    )


def test_step_3_invokes_athanor_review():
    """MUST: Step 3 dispatches /athanor:review (parallel multi-lens)."""
    body = _load_athanor_lfg()
    step3_idx = re.search(r"(?im)^\s*(?:#+\s*)?step\s*3\b", body)
    assert step3_idx, "Step 3 anchor must exist"
    window = body[step3_idx.start() : step3_idx.start() + 1500]
    assert "/athanor:review" in window or "athanor:review" in window, (
        f"Step 3 must invoke /athanor:review (parallel multi-lens). "
        f"Window first 200 chars: {window[:200]!r}"
    )


# ---- All 8+ steps present (athanor-native LFG shape) ----


def test_all_pipeline_steps_present():
    """MUST: body has all 8 step anchors plus DONE sentinel."""
    body = _load_athanor_lfg()
    expected_step_anchors = ["1", "2", "3", "4", "5", "6", "7", "8"]
    for n in expected_step_anchors:
        anchor_pattern = rf"(?im)^\s*(?:#+\s*)?step\s*{n}\b"
        assert re.search(anchor_pattern, body), (
            f"Pipeline step {n} anchor missing from /athanor:lfg body"
        )
    assert "<promise>DONE</promise>" in body or "<promise>done</promise>" in body.lower(), (
        "/athanor:lfg must output <promise>DONE</promise> sentinel on completion"
    )


# ---- Voice: no CE-deprecate prose (R4) ----


def test_no_ce_deprecate_phrases_in_lfg_body():
    """MUST: /athanor:lfg body uses positive commitment only — no CE-deprecate
    or supersession framing per origin §R4."""
    body = _load_athanor_lfg().lower()
    forbidden = [
        "ce-lfg deprecated",
        "ce deprecated",
        "supersedes ce-lfg",
        "supersedes compound-engineering",
        "do not use compound-engineering",
        "do not use ce-lfg",
        "replaces ce-lfg",
        "athanor replaces ce",
    ]
    hits = [p for p in forbidden if p in body]
    assert not hits, (
        f"/athanor:lfg body must not deprecate or supersede CE. "
        f"Forbidden phrases found: {hits}"
    )


# ---- Difference-from-ce-lfg section disclosed ----


def test_body_discloses_ce_lfg_historical_note():
    """MUST (post-v0.12.0): body has a historical-note section recording
    that /athanor:ce-lfg was removed in the v0.12.0 atomic cut and
    /athanor:lfg is the sole end-to-end pipeline."""
    body = _load_athanor_lfg().lower()
    signals = [
        "historical note",
        "post-v0.12.0",
        "removed in the v0.12.0",
        "sole end-to-end pipeline",
        "upstream compound-engineering",
    ]
    assert any(s in body for s in signals), (
        f"/athanor:lfg body must disclose ce-lfg historical note (post-v0.12.0). "
        f"Expected one of: {signals}"
    )


# ---- v0.12.0: vendored ce-lfg removed; athanor-native /athanor:lfg survives ----


def test_vendored_ce_lfg_removed_post_v012():
    """MUST (D9): the vendored skills/ce-lfg/ directory is REMOVED in the
    v0.12.0 atomic cut (FULL DROP — no THIN-ADAPTER stub). Users migrate
    to athanor-native /athanor:lfg."""
    assert not VENDORED_CE_LFG_SKILL.exists(), (
        f"v0.12.0 D9 FULL DROP: skills/ce-lfg/SKILL.md must NOT exist "
        f"post-removal; found {VENDORED_CE_LFG_SKILL}"
    )


def test_athanor_native_lfg_survives_post_v012():
    """MUST (R2 post-v0.12.0): athanor-native /athanor:lfg wrapper survives
    the atomic cut (it's identity #3-adjacent — the user-facing pipeline
    surface). The pre-v0.12.0 coexistence with /athanor:ce-lfg collapses
    to native-only."""
    assert ATHANOR_LFG_SKILL.exists(), (
        f"/athanor:lfg native wrapper must survive v0.12.0; missing at "
        f"{ATHANOR_LFG_SKILL}"
    )
