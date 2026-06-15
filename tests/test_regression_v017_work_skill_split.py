"""Regression test for v0.17.0 ST-S01 — Split skills/work/SKILL.md.

The legacy skills/work/SKILL.md was 1153 lines — a giant prose surface that
made review, drift detection, and onboarding expensive. ST-S01 splits it
into a thin router (≤250 lines) plus topic references under
``skills/work/references/``.

This test pins:
  1. skills/work/SKILL.md is ≤ 250 lines (router-thin).
  2. skills/work/references/ exists and contains the 4 expected reference
     files (multi-status.md, spec-then-tdd-handler.md, team-mode.md,
     learner-cleaner.md).
  3. spec-then-tdd-handler.md carries the v0.19.0 forward-compat anchor for
     the future PostToolUse test-evidence sniffer.

Plan reference: v0.17.0 SKILL split macro plan (S01).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"
WORK_REFS = REPO_ROOT / "skills" / "work" / "references"


def test_work_skill_router_is_thin():
    """MUST: skills/work/SKILL.md ≤ 250 lines (post-S01)."""
    assert WORK_SKILL.exists(), f"{WORK_SKILL} must exist"
    line_count = len(WORK_SKILL.read_text(encoding="utf-8").splitlines())
    assert line_count <= 250, (
        f"skills/work/SKILL.md is {line_count} lines; ST-S01 requires ≤ 250. "
        f"Move heavy prose blocks to skills/work/references/*.md."
    )


def test_work_references_directory_exists():
    """MUST: skills/work/references/ directory exists."""
    assert WORK_REFS.is_dir(), (
        f"{WORK_REFS} must exist as a directory after ST-S01 split."
    )


def test_work_references_files_exist():
    """MUST: the 4 reference files exist after ST-S01 split."""
    expected = [
        "multi-status.md",
        "spec-then-tdd-handler.md",
        "team-mode.md",
        "learner-cleaner.md",
    ]
    for name in expected:
        path = WORK_REFS / name
        assert path.is_file(), (
            f"skills/work/references/{name} must exist (ST-S01 split target)"
        )
        body = path.read_text(encoding="utf-8")
        assert len(body) > 200, (
            f"skills/work/references/{name} is too small to be substantive "
            f"({len(body)} bytes)"
        )


def test_spec_then_tdd_handler_has_v019_forward_compat_anchor():
    """MUST: spec-then-tdd-handler.md carries the v0.19.0 forward-compat
    anchor marker for the future PostToolUse test-evidence sniffer."""
    path = WORK_REFS / "spec-then-tdd-handler.md"
    assert path.is_file()
    body = path.read_text(encoding="utf-8")
    # The forward-compat anchor must be present so v0.19.0 work can land
    # without re-architecting the section.
    assert "v0.19.0" in body, (
        "spec-then-tdd-handler.md must mention v0.19.0 (forward-compat "
        "anchor for PostToolUse test-evidence sniffer)."
    )
    anchor_signals = [
        "forward-compat anchor",
        "PostToolUse",
        "Evidence-Bound Enforcement",
    ]
    matches = [s for s in anchor_signals if s in body]
    assert len(matches) >= 2, (
        f"spec-then-tdd-handler.md must contain forward-compat anchor markers. "
        f"Expected at least 2 of: {anchor_signals}. Found: {matches}"
    )


def test_spec_then_tdd_handler_declares_canonical_runtime_reference():
    """MUST: runtime behavior detail lives in the split reference, not in
    CLAUDE.md or ROADMAP restatements."""
    path = WORK_REFS / "spec-then-tdd-handler.md"
    assert path.is_file()
    body = path.read_text(encoding="utf-8")
    required = [
        "canonical runtime behavior reference",
        "Evidence-Bound Enforcement",
        "scripts/work/evidence_gate.py",
        "scripts/work/freeze_evidence_gate.py",
    ]
    missing = [needle for needle in required if needle not in body]
    assert not missing, (
        "spec-then-tdd-handler.md must be the canonical runtime behavior "
        f"reference; missing: {missing}"
    )


def test_work_skill_router_points_at_references():
    """MUST: the thin router SKILL.md cross-links the reference files
    (otherwise the references are orphaned)."""
    body = WORK_SKILL.read_text(encoding="utf-8")
    # Each reference must be linked from the router
    expected_links = [
        "references/multi-status.md",
        "references/spec-then-tdd-handler.md",
        "references/team-mode.md",
        "references/learner-cleaner.md",
    ]
    for link in expected_links:
        assert link in body, (
            f"skills/work/SKILL.md must reference '{link}' "
            f"(otherwise the split reference is orphaned)"
        )
