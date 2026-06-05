"""Regression — /athanor:plan carries the approach-altitude gate (A-1).

Adopted concept from compound-engineering v3.11.1 /ce-plan Phase 0.1a:
before committing to a deliverable plan, recognize "plan the approach"
requests and hold at the methodology level. Explicit triggers are ungated;
proactive offers are conservative (high method-uncertainty only). The gate
detail lives in skills/plan/references/approach-altitude.md with a Step 1
pointer + companion registration in the skill router. Static reads only.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"
APPROACH_REF = REPO_ROOT / "skills" / "plan" / "references" / "approach-altitude.md"


def test_plan_skill_references_approach_altitude() -> None:
    """MUST — the plan skill router wires the approach-altitude gate."""
    body = PLAN_SKILL.read_text(encoding="utf-8").lower()
    assert "approach-altitude" in body, (
        "skills/plan/SKILL.md must wire the approach-altitude gate (Step 1 "
        "pointer + companion-file registration)."
    )


def test_approach_altitude_reference_populated() -> None:
    """MUST — the reference covers the gate's load-bearing parts."""
    assert APPROACH_REF.is_file(), (
        "skills/plan/references/approach-altitude.md must exist."
    )
    low = APPROACH_REF.read_text(encoding="utf-8").lower()
    for kw in ("explicit", "proactive", "deliverable", "re-anchor"):
        assert kw in low, (
            f"approach-altitude.md must cover '{kw}' (explicit vs proactive "
            f"entry, what it produces, and how it re-anchors to the "
            f"deliverable plan)."
        )


def test_plan_skill_stays_thin_router() -> None:
    """MUST — plan SKILL.md stays within its <=300-line router budget."""
    lines = PLAN_SKILL.read_text(encoding="utf-8").count("\n")
    assert lines <= 300, (
        f"skills/plan/SKILL.md is {lines} lines; the router contract is "
        f"<=300 (push detail into references/)."
    )
