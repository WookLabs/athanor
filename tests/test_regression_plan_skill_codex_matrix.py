"""Regression test for the v0.7.7 M3 finding — codex.enabled + codex.fallback matrix.

Pins that both skills/plan/SKILL.md and skills/discuss/SKILL.md implement the
combined `codex.enabled` × `codex.fallback` availability matrix per plan §4
M3:
  - read `codex.enabled` via `jq` (graceful jq-absence fallback)
  - read `codex.fallback` enum (self-critic / skip / fail)
  - branch dispatch on the resolved state

These prose-level checks ensure that future edits don't silently revert to
the v0.7.6 single-axis check (CLI-presence only, ignoring config).

Plan reference: `.athanor/sessions/2026-05-18-001/plan.md` §4 M3.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"
DISCUSS_SKILL = REPO_ROOT / "skills" / "discuss" / "SKILL.md"


def _load(path: Path) -> str:
    """Load the plan skill body. For PLAN_SKILL, splice in all reference
    companion files under skills/plan/references/ so prose-level checks
    survive the S02 thin-router split (skills/plan/SKILL.md + references/).
    Other paths (e.g., DISCUSS_SKILL) are read as-is."""
    text = path.read_text(encoding="utf-8")
    if path == PLAN_SKILL:
        references_dir = path.parent / "references"
        if references_dir.is_dir():
            for ref in sorted(references_dir.glob("*.md")):
                text += "\n\n" + ref.read_text(encoding="utf-8")
    return text


# ---- plan/SKILL.md tests ----

def test_plan_reads_codex_enabled():
    """plan/SKILL.md must read the `codex.enabled` config key."""
    content = _load(PLAN_SKILL)
    assert "codex.enabled" in content, (
        "plan/SKILL.md must reference `codex.enabled` config key "
        "(v0.7.7 M3 codex availability matrix)."
    )


def test_plan_uses_jq_for_config():
    """plan/SKILL.md must use a concrete `jq -r '.codex.enabled` invocation."""
    content = _load(PLAN_SKILL)
    assert "jq -r '.codex.enabled" in content, (
        "plan/SKILL.md must use the concrete `jq -r '.codex.enabled` "
        "invocation (M3 spec — not just a prose mention)."
    )


def test_plan_handles_jq_absence():
    """plan/SKILL.md must include `command -v jq` graceful-degradation guard."""
    content = _load(PLAN_SKILL)
    assert "command -v jq" in content, (
        "plan/SKILL.md must guard the jq read with `command -v jq` "
        "(M3 graceful-degradation requirement when jq is absent)."
    )


def test_plan_uses_codex_fallback():
    """plan/SKILL.md must consume both `codex.fallback` config + `CODEX_FALLBACK` shell var."""
    content = _load(PLAN_SKILL)
    assert "codex.fallback" in content, (
        "plan/SKILL.md must reference the `codex.fallback` config key "
        "(M3 fallback matrix)."
    )
    assert "CODEX_FALLBACK" in content, (
        "plan/SKILL.md must use the `CODEX_FALLBACK` shell variable "
        "(M3 dispatch branching)."
    )


def test_plan_resolves_review_strategy():
    """plan/SKILL.md must thread `review_strategy` through Step 0 + dispatch sites (>=3 mentions)."""
    content = _load(PLAN_SKILL)
    count = content.count("review_strategy")
    assert count >= 3, (
        f"plan/SKILL.md must reference `review_strategy` at least 3 times "
        f"(Step 0 resolution + Step 3 + Step 4 dispatch branches); "
        f"found {count}. M3 spec requires the resolved variable to thread "
        f"through dispatch sites."
    )


def test_plan_handles_self_critic_fallback():
    """plan/SKILL.md must reference the `self-critic` fallback enum value."""
    content = _load(PLAN_SKILL)
    assert "self-critic" in content, (
        "plan/SKILL.md must reference the `self-critic` fallback value "
        "(default when codex disabled — M3 fallback matrix)."
    )


# ---- discuss/SKILL.md tests ----

def test_discuss_reads_codex_enabled():
    """discuss/SKILL.md must read the `codex.enabled` config key."""
    content = _load(DISCUSS_SKILL)
    assert "codex.enabled" in content, (
        "discuss/SKILL.md must reference `codex.enabled` config key "
        "(M3 requires parity with plan/SKILL.md)."
    )


def test_discuss_uses_jq_with_fallback():
    """discuss/SKILL.md must include `command -v jq` graceful-degradation guard."""
    content = _load(DISCUSS_SKILL)
    assert "command -v jq" in content, (
        "discuss/SKILL.md must guard the jq read with `command -v jq` "
        "(M3 graceful-degradation requirement)."
    )


def test_discuss_uses_codex_fallback():
    """discuss/SKILL.md must consume `codex.fallback` config OR `CODEX_FALLBACK` shell var."""
    content = _load(DISCUSS_SKILL)
    assert ("codex.fallback" in content) or ("CODEX_FALLBACK" in content), (
        "discuss/SKILL.md must reference `codex.fallback` or `CODEX_FALLBACK` "
        "(M3 fallback handling — parity with plan/SKILL.md)."
    )
