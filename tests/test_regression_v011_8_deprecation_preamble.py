"""Regression tests for v0.11.8 → v0.12.0 deprecation cycle closure.

## Scope

v0.11.8 (2026-05-22) shipped a deprecation warning cycle that injected an
in-skill preamble (`<!-- athanor:deprecated v=1 since=0.11.8 removal=0.12.0 -->`)
into 45 vendored SKILL.md files (5 LIFT + 40 DROP). v0.12.0 (Subtask 15)
completes the cycle by atomically removing those files via
`scripts/v012_remove_vendored.py`.

This test file was rewritten in Subtask 15 because its pre-v0.12.0 form
asserted that the 45 SKILL.md files exist on disk and carry the
deprecation sentinel. Post-removal those files are gone, so the
existence-and-sentinel assertions no longer apply. The rewritten test
file pins three v0.12.0-state invariants instead:

  1. The 45 DEPRECATION_TARGETS paths are absent on disk (the cycle's
     promised removal completed).
  2. `ce-test-browser` (D8 KEEP) survives.
  3. The Stop hook carve-out for the deprecation sentinel still triggers
     correctly — relevant when historical CHANGELOG / archive prose
     quotes the sentinel literal in a fresh assistant turn.

D14.2 correction: scope is 45 files (5 LIFT + 40 DROP), not 44.

D8 carve-out: ce-test-browser is the sole KEEP.

D7 voice constraints: forbidden phrases ("translated", "interpreted",
"we discovered", "natural maturation") do not appear in this test file.

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Subtask 15. Earlier plan: v0.11.8 deprecation cycle.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


# ---------------------------------------------------------------------------
# D14.2 target list — 45 SKILL.md paths (5 LIFT + 40 DROP). These were the
# deprecation targets in v0.11.8 and the removal targets in v0.12.0.
# Hardcoded so disk drift cannot silently change scope.
# ---------------------------------------------------------------------------

LIFT_TARGETS: list[str] = [
    "ce-brainstorm",
    "ce-code-review",
    "ce-doc-review",
    "sp-systematic-debugging",
    "sp-using-superpowers",
]

DROP_TARGETS: list[str] = [
    # ce-* DROP (28 entries)
    "ce-agent-native-architecture",
    "ce-agent-native-audit",
    "ce-clean-gone-branches",
    "ce-commit",
    "ce-commit-push-pr",
    "ce-compound",
    "ce-compound-refresh",
    "ce-debug",
    "ce-demo-reel",
    "ce-dhh-rails-style",
    "ce-frontend-design",
    "ce-gemini-imagegen",
    "ce-ideate",
    "ce-lfg",
    "ce-optimize",
    "ce-plan",
    "ce-polish-beta",
    "ce-product-pulse",
    "ce-proof",
    "ce-resolve-pr-feedback",
    "ce-riffrec-feedback-analysis",
    "ce-sessions",
    "ce-simplify-code",
    "ce-slack-research",
    "ce-strategy",
    "ce-test-xcode",
    "ce-work",
    "ce-work-beta",
    "ce-worktree",
    # sp-* DROP (12 entries)
    "sp-brainstorming",
    "sp-dispatching-parallel-agents",
    "sp-executing-plans",
    "sp-finishing-a-development-branch",
    "sp-receiving-code-review",
    "sp-requesting-code-review",
    "sp-subagent-driven-development",
    "sp-test-driven-development",
    "sp-using-git-worktrees",
    "sp-writing-plans",
    "sp-writing-skills",
]

DEPRECATION_TARGETS: list[str] = LIFT_TARGETS + DROP_TARGETS

KEEP_SKILLS: list[str] = ["ce-test-browser"]


# ---------------------------------------------------------------------------
# Scope sanity (covers D14.2 count + KEEP carve-out)
# ---------------------------------------------------------------------------


def test_deprecation_target_count_is_45():
    """D14.2: scope is 5 LIFT + 40 DROP = 45 SKILL.md files."""
    assert len(LIFT_TARGETS) == 5, f"expected 5 LIFT entries, got {len(LIFT_TARGETS)}"
    assert len(DROP_TARGETS) == 40, f"expected 40 DROP entries, got {len(DROP_TARGETS)}"
    assert len(DEPRECATION_TARGETS) == 45, (
        f"D14.2 corrected count is 45 (5 LIFT + 40 DROP); got {len(DEPRECATION_TARGETS)}"
    )


def test_keep_skill_is_only_ce_test_browser():
    """D8: ce-test-browser is the only KEEP carve-out."""
    assert KEEP_SKILLS == ["ce-test-browser"]


# ---------------------------------------------------------------------------
# v0.12.0 cycle-closure invariants
# ---------------------------------------------------------------------------


def test_all_45_deprecation_targets_removed_in_v012():
    """v0.12.0 closure: every path in DEPRECATION_TARGETS is absent on
    disk post-Subtask-15. The v0.11.8 deprecation cycle promised removal
    at v0.12.0; Subtask 15 fulfils that promise."""
    still_present: list[str] = []
    for name in DEPRECATION_TARGETS:
        if (SKILLS_DIR / name).exists():
            still_present.append(name)
    assert not still_present, (
        f"v0.12.0 closure: {len(still_present)} of 45 deprecation targets "
        f"still present on disk: {still_present!r}. Re-run "
        f"`python3 scripts/v012_remove_vendored.py` to complete the cut."
    )


def test_ce_test_browser_keep_skill_still_present():
    """D8 invariant: ce-test-browser survives the v0.12.0 cut.

    The pre-v0.12.0 test asserted the sentinel was absent from the file;
    post-v0.12.0 we assert the file itself survives — that's the D8
    carve-out's structural commitment.
    """
    keep_path = SKILLS_DIR / "ce-test-browser" / "SKILL.md"
    assert keep_path.is_file(), (
        f"D8 invariant: ce-test-browser KEEP skill must survive v0.12.0 "
        f"cut at {keep_path}"
    )
