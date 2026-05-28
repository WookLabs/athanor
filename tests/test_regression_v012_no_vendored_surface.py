"""Regression tests for v0.12.0 atomic vendored-surface removal.

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Subtask 15 (Phase 5 — Execute removal + rewrite/delete stale regression tests).

Post-v0.15.x invariants (D8 / D9 / D14.2):

- Exactly 1 vendored CE skill survives: `ce-test-browser` (D8 KEEP carve-out).
- Zero vendored superpowers skills survive (all 13 sp-* dirs removed).
- No THIN-ADAPTER stubs for `ce-plan` / `ce-work` / `ce-lfg` exist (D9 FULL
  DROP — users migrate to athanor-native `/athanor:plan`, `/athanor:work`,
  `/athanor:lfg`).
- Zero vendored sub-agent files remain: the 2 D12-retained generics
  (`ce-git-history-analyzer.agent.md`, `ce-repo-research-analyst.agent.md`)
  were removed in v0.15.x (no live dispatch references). `agents/vendored/`
  does not exist on disk.
- The 45 removed skill directories enumerated below MUST NOT exist on disk
  (LIFT-source + DROP).

RED-first execution note (Subtask 15 spec-then-tdd): this file was written
BEFORE `scripts/v012_remove_vendored.py` ran. The five assertions show RED
against the pre-removal disk (33 ce-* + 13 sp-* + 49 sub-agents) and GREEN
after the script runs.

Voice constraints (D7): the docstrings here avoid the forbidden phrases
("translated", "interpreted", "we discovered", "natural maturation"). The
framing is direct attribution to the D14.2 corrected counts.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_VENDORED_DIR = REPO_ROOT / "agents" / "vendored"

KEEP_SKILL = "ce-test-browser"

# The 45 skill directories removed by `scripts/v012_remove_vendored.py`
# (5 LIFT-source + 40 DROP). Order: 5 LIFT-source first (sorted),
# then DROP (sorted by namespace then name). Matches the script's
# removal set per D14.2 disk-grounding pass.
REMOVED_SKILL_PATHS = (
    # LIFT-source (5) — concepts migrated into athanor-native skills.
    "skills/ce-brainstorm",
    "skills/ce-code-review",
    "skills/ce-doc-review",
    "skills/sp-systematic-debugging",
    "skills/sp-using-superpowers",
    # ce-* DROP (27 entries after subtracting LIFT-source from 32 ce-*).
    "skills/ce-agent-native-architecture",
    "skills/ce-agent-native-audit",
    "skills/ce-clean-gone-branches",
    "skills/ce-commit",
    "skills/ce-commit-push-pr",
    "skills/ce-compound",
    "skills/ce-compound-refresh",
    "skills/ce-debug",
    "skills/ce-demo-reel",
    "skills/ce-dhh-rails-style",
    "skills/ce-frontend-design",
    "skills/ce-gemini-imagegen",
    "skills/ce-ideate",
    "skills/ce-lfg",
    "skills/ce-optimize",
    "skills/ce-plan",
    "skills/ce-polish-beta",
    "skills/ce-product-pulse",
    "skills/ce-proof",
    "skills/ce-resolve-pr-feedback",
    "skills/ce-riffrec-feedback-analysis",
    "skills/ce-sessions",
    "skills/ce-simplify-code",
    "skills/ce-slack-research",
    "skills/ce-strategy",
    "skills/ce-test-xcode",
    "skills/ce-work",
    "skills/ce-work-beta",
    "skills/ce-worktree",
    # sp-* DROP (12 entries after subtracting 1 LIFT-source from 13 sp-*).
    "skills/sp-brainstorming",
    "skills/sp-dispatching-parallel-agents",
    "skills/sp-executing-plans",
    "skills/sp-finishing-a-development-branch",
    "skills/sp-receiving-code-review",
    "skills/sp-requesting-code-review",
    "skills/sp-subagent-driven-development",
    "skills/sp-test-driven-development",
    "skills/sp-using-git-worktrees",
    "skills/sp-writing-plans",
    "skills/sp-writing-skills",
)


def test_only_one_ce_skill_survives():
    """MUST 1 / D8: glob `skills/ce-*` resolves to exactly `[skills/ce-test-browser]`.

    Pre-removal disk: 33 ce-* dirs (RED).
    Post-removal disk: 1 ce-* dir (GREEN).
    """
    ce_dirs = sorted(p.name for p in SKILLS_DIR.glob("ce-*") if p.is_dir())
    assert ce_dirs == [KEEP_SKILL], (
        f"MUST 1 / D8: exactly one ce-* skill must survive "
        f"({KEEP_SKILL!r}); found {ce_dirs!r}. "
        f"Pre-removal disk had 33 ce-* dirs; D8 carve-out preserves only "
        f"the browser-automation skill (no athanor-native equivalent)."
    )


def test_no_sp_skills_remain():
    """MUST 1 / D14.2: glob `skills/sp-*` is empty post-removal.

    Pre-removal disk: 13 sp-* dirs (RED).
    Post-removal disk: 0 sp-* dirs (GREEN).
    """
    sp_dirs = sorted(p.name for p in SKILLS_DIR.glob("sp-*") if p.is_dir())
    assert sp_dirs == [], (
        f"MUST 1: no sp-* vendored skills should remain; found {sp_dirs!r}. "
        f"All 13 superpowers-vendored skills were removed in v0.12.0."
    )


def test_no_thin_adapter_stubs():
    """MUST 3 / D9: `ce-plan`, `ce-work`, `ce-lfg` directories are absent.

    D9 mandates FULL DROP — no THIN-ADAPTER stubs. Users migrate to
    athanor-native `/athanor:plan`, `/athanor:work`, `/athanor:lfg`.
    """
    forbidden = ("ce-plan", "ce-work", "ce-lfg")
    surviving = [name for name in forbidden if (SKILLS_DIR / name).exists()]
    assert not surviving, (
        f"MUST 3 / D9: FULL DROP requires no THIN-ADAPTER stubs for "
        f"{forbidden!r}; found these still present: {surviving!r}. Users "
        f"migrate to athanor-native /athanor:plan, /athanor:work, "
        f"/athanor:lfg."
    )


def test_no_vendored_sub_agents_remain():
    """MUST: agents/vendored/ does not exist on disk (v0.15.x removal).

    v0.12.0 retained 2 D12 sub-agents (ce-git-history-analyzer,
    ce-repo-research-analyst); v0.15.x confirmed zero live dispatch
    references and removed both. The agents/vendored/ directory must
    not exist.
    """
    assert not AGENTS_VENDORED_DIR.exists(), (
        f"MUST: agents/vendored/ must not exist post-v0.15.x; "
        f"found it at {AGENTS_VENDORED_DIR}. "
        f"All 49 vendored sub-agents are removed (47 at v0.12.0, "
        f"2 D12-retained at v0.15.x)."
    )


def test_removed_skill_directories_absent():
    """MUST: all 45 LIFT-source + DROP skill directories are absent on disk.

    Catches partial-removal regressions (e.g., a single dir reintroduced
    by an accidental restore). The 45-entry hardcoded list pins the
    D14.2 scope.
    """
    still_present = [
        p for p in REMOVED_SKILL_PATHS if (REPO_ROOT / p).exists()
    ]
    assert not still_present, (
        f"MUST: {len(still_present)} of 45 removed skill directories "
        f"still exist on disk: {still_present!r}. Re-run "
        f"`python3 scripts/v012_remove_vendored.py` to complete the "
        f"removal."
    )
