"""Regression — Critic axis (D) Simplicity & fail-loud + review lens (v0.18.4).

The user's §Core Principle ("Engineering quality": low complexity, fail-loud
over silent fallback) is wired into the advisory review/plan surfaces:

- plan Critic gains a 4th axis (D) — flags unjustified complexity/scope and
  fallback designs that swallow should-be-fixed errors.
- the axis is synced into the inline Critic dispatch injections
  (critic-variants.md, "three-axis" → "four-axis").
- the review maintainability persona names fail-loud explicitly and calls
  out indiscriminate fallbacks (not just empty catch blocks).

These stay ADVISORY (athanor's Critic/review are leader-dispatched, not
merge gates) — the tests lock presence/sync, not enforcement. Static reads.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CRITIC_RUBRIC = REPO_ROOT / "skills" / "plan" / "references" / "critic-rubric.md"
CRITIC_VARIANTS = REPO_ROOT / "skills" / "plan" / "references" / "critic-variants.md"
REVIEW_SECTIONS = REPO_ROOT / "skills" / "review" / "references" / "review-sections.md"
REVIEW_SKILL = REPO_ROOT / "skills" / "review" / "SKILL.md"
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"


def test_critic_rubric_has_axis_d_simplicity_failloud() -> None:
    """MUST — critic-rubric adds axis (D) covering simplicity + fail-loud."""
    body = CRITIC_RUBRIC.read_text(encoding="utf-8")
    assert re.search(r"##\s*\(D\)", body), (
        "critic-rubric.md must add a '## (D)' axis (Simplicity & fail-loud)."
    )
    low = body.lower()
    assert "fail-loud" in low and "fallback" in low, (
        "axis (D) must cover fail-loud over silent fallback."
    )
    assert "복잡도" in body or "complexity" in low or "simplicity" in low, (
        "axis (D) must cover unjustified complexity / scope."
    )


def test_critic_variants_inject_axis_d_four_axis() -> None:
    """MUST — inline Critic injections reference axis (D) as four-axis."""
    body = CRITIC_VARIANTS.read_text(encoding="utf-8")
    assert "(D)" in body, (
        "critic-variants.md injection must reference axis (D) so dispatched "
        "Critics evaluate it alongside (A)/(B)/(C)."
    )
    low = body.lower()
    assert "four-axis" in low or "four axes" in low, (
        "critic-variants.md must say four-axis (was three) now that (D) exists."
    )
    assert "three-axis" not in low and "three axes" not in low, (
        "no stale 'three-axis' wording may remain after the (D) sync."
    )


def test_review_maintainability_failloud_explicit() -> None:
    """MUST — review maintainability persona names fail-loud + indiscriminate fallback."""
    low = REVIEW_SECTIONS.read_text(encoding="utf-8").lower()
    assert "fail-loud" in low, (
        "maintainability silent-failure heuristic must name fail-loud explicitly."
    )
    assert "indiscriminate" in low or "should-be-fixed" in low, (
        "must call out indiscriminate fallbacks routing a should-be-fixed "
        "error into a default path (the user's core concern)."
    )


def test_plan_skill_axis_count_synced_to_four() -> None:
    """MUST — plan SKILL.md (descriptor + operative dispatch) lists four axes incl (D).

    Closes the coverage hole the adversarial review found: the three→four
    sync was guarded only on critic-variants.md, so the stale 'three axes
    A/B/C' in the SKILL.md router + dispatch instruction slipped through.
    """
    low = PLAN_SKILL.read_text(encoding="utf-8").lower()
    assert "three axes" not in low and "three-axis" not in low, (
        "skills/plan/SKILL.md must not say 'three axes' after axis (D) — the "
        "operative Critic dispatch enumeration (line ~258) and the rubric "
        "descriptor must list four axes A/B/C/D."
    )
    assert "four axes" in low or "four-axis" in low, (
        "skills/plan/SKILL.md must name the v0.8.0 Critic Rubric as four axes."
    )
    assert "(d)" in low, (
        "the SKILL.md dispatch enumeration must include axis (D) "
        "(simplicity & fail-loud), matching critic-rubric/variants."
    )


def test_review_surface_carries_advisory_not_merge_gate_label() -> None:
    """MUST (HL1, v0.18.5) — the /athanor:review surface carries an explicit
    advisory / not-a-merge-gate honesty label, mirroring critic-rubric.md:3.

    §Core Principle pairs Critic AND review as advisory-on-user-code. The Critic
    surface labels itself ('This rubric is advisory — there is no runtime gate');
    review had NO such label while emitting 'must fix before merge' severity
    prose — an under-label the v0.18.5 enforcement audit flagged. A reader could
    mistake review for a CI gate, which is itself a fail-loud honesty violation
    (a false enforcement impression hides the real advisory boundary).
    """
    body = (
        REVIEW_SKILL.read_text(encoding="utf-8")
        + "\n"
        + REVIEW_SECTIONS.read_text(encoding="utf-8")
    ).lower()
    assert "advisory" in body, (
        "the /athanor:review surface must carry an 'advisory' label "
        "(mirror critic-rubric.md line 3)."
    )
    assert "not a merge gate" in body, (
        "the /athanor:review surface must state it is NOT a merge gate / does "
        "not block CI (CLAUDE.md §Core Principle: review is advisory on user "
        "code — athanor is not the user's CI)."
    )
