"""Regression tests for S02 — split `skills/plan/SKILL.md` into a thin router
(<=300 lines) plus a `references/` companion directory.

Context
-------
Through v0.16.x, `skills/plan/SKILL.md` had grown to ~1255 lines: it carried
Identity + boundaries + tier dispatch table + Step 0 Codex matrix + Step 1
brief + every Planner/Reviewer/Critic prompt body + the v0.8.0 Critic Rubric
+ presentation template + dispatch sequence summary, all in one file. The
S02 refactor splits these out into a thin router (the SKILL.md itself, kept
under 300 lines for fast scanning by the Leader) plus 7 reference docs
under `skills/plan/references/` that hold the bulky prompt bodies, rubric
text, codex availability state-machine, presentation templates, and the new
v0.17.0 depth-flag dispatch stub.

This test pins:

1. `skills/plan/SKILL.md` is <= 300 lines.
2. The 7 reference files exist:
     - references/planner-dispatch.md
     - references/reviewer-dispatch.md
     - references/critic-variants.md
     - references/codex-availability.md
     - references/critic-rubric.md
     - references/presentation.md
     - references/depth-flag-dispatch.md
3. The depth-flag-dispatch.md stub mentions `--depth=standard`,
   `--depth=deep`, `--depth=lite` so S07 (Wave 2) has a forward-compat anchor.
4. SKILL.md cross-references the references/ directory so the Leader can
   navigate into the deeper prompt detail when needed.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"
PLAN_REFERENCES = REPO_ROOT / "skills" / "plan" / "references"


def _count_lines(p: Path) -> int:
    return len(p.read_text(encoding="utf-8").splitlines())


# ---- Acceptance Criterion 1 — SKILL.md line cap ----


def test_plan_skill_md_is_at_most_300_lines():
    """MUST — skills/plan/SKILL.md is the thin router, <= 300 lines."""
    n = _count_lines(PLAN_SKILL)
    assert n <= 300, (
        f"skills/plan/SKILL.md must stay <= 300 lines for the router role; "
        f"current line count = {n}. Spill the overflow into "
        f"skills/plan/references/*.md."
    )


# ---- Acceptance Criterion 2 — 7 reference files exist ----


REQUIRED_REFERENCES = [
    "planner-dispatch.md",
    "reviewer-dispatch.md",
    "critic-variants.md",
    "codex-availability.md",
    "critic-rubric.md",
    "presentation.md",
    "depth-flag-dispatch.md",
]


def test_references_directory_exists():
    """MUST — references/ directory exists under skills/plan/."""
    assert PLAN_REFERENCES.is_dir(), (
        f"Expected directory {PLAN_REFERENCES} to exist."
    )


def test_all_seven_reference_files_exist():
    """MUST — each of the 7 reference files exists."""
    missing = [name for name in REQUIRED_REFERENCES
               if not (PLAN_REFERENCES / name).exists()]
    assert not missing, (
        f"Missing reference files in {PLAN_REFERENCES}: {missing}. "
        f"S02 acceptance criterion: all 7 reference files must be created."
    )


def test_reference_files_are_non_trivial():
    """SHOULD — each reference file has > 5 lines (non-stub-of-stub).

    The depth-flag-dispatch.md is allowed to be a small stub but should
    still contain at least a few lines documenting --depth=<value>.
    """
    too_small = []
    for name in REQUIRED_REFERENCES:
        p = PLAN_REFERENCES / name
        if not p.exists():
            continue
        n = _count_lines(p)
        if n < 5:
            too_small.append(f"{name}={n}")
    assert not too_small, (
        f"Reference files too small (<5 lines), likely stub-of-stub: "
        f"{too_small}"
    )


# ---- Acceptance Criterion 3 — depth-flag-dispatch.md stub content ----


def test_depth_flag_dispatch_stub_documents_three_depths():
    """MUST — depth-flag-dispatch.md stub references each of standard /
    deep / lite depths so S07 (Wave 2 — collapse of /athanor:deep-plan
    and /athanor:lite-plan) has a forward-compat anchor."""
    p = PLAN_REFERENCES / "depth-flag-dispatch.md"
    assert p.exists(), f"{p} missing — required by S07 forward compat."
    body = p.read_text(encoding="utf-8").lower()
    for needle in ["--depth=standard", "--depth=deep", "--depth=lite"]:
        assert needle in body, (
            f"depth-flag-dispatch.md must mention {needle!r} as a forward-"
            f"compat anchor for S07. Body did not contain it."
        )


# ---- Acceptance Criterion 4 — SKILL.md cross-references references/ ----


def test_skill_md_cross_references_references_dir():
    """MUST — SKILL.md mentions the references/ companion path so a Leader
    reading SKILL.md alone can navigate to deeper prompt detail."""
    body = PLAN_SKILL.read_text(encoding="utf-8")
    assert "references/" in body, (
        "skills/plan/SKILL.md must cross-reference references/ companion "
        "files so the Leader can navigate to dispatch prompts, rubric, etc."
    )
