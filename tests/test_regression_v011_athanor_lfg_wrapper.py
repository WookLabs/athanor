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


def _load_ce_lfg() -> str:
    return VENDORED_CE_LFG_SKILL.read_text(encoding="utf-8")


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


def test_body_discloses_difference_from_ce_lfg():
    """MUST: body has a section explaining how /athanor:lfg differs from
    vendored /athanor:ce-lfg so users can choose by namespace."""
    body = _load_athanor_lfg().lower()
    # The difference disclosure can be a §"Difference from /athanor:ce-lfg"
    # heading or inline prose mentioning the alternative.
    signals = [
        "difference from",
        "vs /athanor:ce-lfg",
        "vs ce-lfg",
        "ce-lfg coexists",
        "ce-lfg as the explicit alternative",
        "compared to /athanor:ce-lfg",
        "vendored /athanor:ce-lfg",
    ]
    assert any(s in body for s in signals), (
        f"/athanor:lfg body must disclose its difference from /athanor:ce-lfg. "
        f"Expected one of: {signals}"
    )


# ---- T2 commitment: vendored ce-lfg body untouched ----


def test_vendored_ce_lfg_body_unchanged():
    """MUST (AE2): vendored skills/ce-lfg/SKILL.md must NOT contain
    /athanor:plan, /athanor:work, /athanor:review references. If those
    appear, the vendored body was edited — T2 provenance violated."""
    ce_lfg_body = _load_ce_lfg()
    # The vendored body should only reference ce-* skills (and built-in
    # tooling). Any /athanor:plan etc. reference indicates accidental edit.
    athanor_native_refs = ["/athanor:plan", "/athanor:work", "/athanor:review",
                           "/athanor:lfg", "/athanor:discuss", "/athanor:debug"]
    leaks = [r for r in athanor_native_refs if r in ce_lfg_body]
    assert not leaks, (
        f"Vendored skills/ce-lfg/SKILL.md was edited — contains "
        f"athanor-native references: {leaks}. T2 provenance violated."
    )


# ---- Coexistence regression: both skills exist ----


def test_both_lfg_skills_coexist():
    """MUST (R2): both skills/lfg/SKILL.md and skills/ce-lfg/SKILL.md
    exist; user chooses by namespace."""
    assert ATHANOR_LFG_SKILL.exists()
    assert VENDORED_CE_LFG_SKILL.exists()
