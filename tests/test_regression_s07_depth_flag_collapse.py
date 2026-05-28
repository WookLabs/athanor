"""Regression tests for S07 — collapse /athanor:deep-plan + /athanor:lite-plan
into /athanor:plan --depth=<value>.

Per C4 (clean removal + migration doc, NOT shim files):
1. skills/deep-plan/ and skills/lite-plan/ directories MUST be absent.
2. /athanor:plan SKILL.md (or references/depth-flag-dispatch.md) MUST
   document --depth={standard|deep|lite} + --no-review flag handling.
3. NATIVE_THIN_LEADER_SKILLS tuples in the two pre-existing identity-
   surface regression tests MUST be updated atomically — they MUST NOT
   contain "deep-plan" or "lite-plan" any more (or those tests would fail
   when the directories disappear).
4. docs/v0.17.0-migration.md MUST exist with flag mapping for both
   collapsed commands.
5. /athanor:plan trigger keywords MUST preserve muscle memory — they
   MUST include both the deep-tier shorthand ("딥 플랜", "deep plan",
   "심층") and the lite-tier shorthand ("라이트 플랜", "lite plan",
   "간단한 계획", "빠른").

Acceptance criteria (mirrors the S07 subtask):
- MUST: skills/deep-plan/ and skills/lite-plan/ deleted
- MUST: --depth flag handling documented
- MUST: NATIVE_THIN_LEADER_SKILLS tuple updated atomically
- MUST: docs/v0.17.0-migration.md created with flag mapping
- MUST: Trigger keywords preserved on /athanor:plan
- MUST: All existing tests pass (this test file participates)
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
PLAN_SKILL = SKILLS_DIR / "plan" / "SKILL.md"
PLAN_REFERENCES = SKILLS_DIR / "plan" / "references"
DEPTH_STUB = PLAN_REFERENCES / "depth-flag-dispatch.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
MIGRATION_DOC = REPO_ROOT / "docs" / "v0.17.0-migration.md"


# ---- Acceptance Criterion 1 — directories removed ----


def test_deep_plan_skill_dir_absent():
    """MUST: skills/deep-plan/ must NOT exist post-S07 (C4 clean removal)."""
    p = SKILLS_DIR / "deep-plan"
    assert not p.exists(), (
        f"S07 acceptance: {p} must be deleted (C4 clean removal). "
        f"Users invoke /athanor:plan --depth=deep instead."
    )


def test_lite_plan_skill_dir_absent():
    """MUST: skills/lite-plan/ must NOT exist post-S07 (C4 clean removal)."""
    p = SKILLS_DIR / "lite-plan"
    assert not p.exists(), (
        f"S07 acceptance: {p} must be deleted (C4 clean removal). "
        f"Users invoke /athanor:plan --depth=lite instead."
    )


# ---- Acceptance Criterion 2 — --depth flag documented in plan skill ----


def test_depth_flag_documented_in_plan_skill_or_references():
    """MUST: --depth={standard|deep|lite} handling is documented in
    skills/plan/SKILL.md or its references/depth-flag-dispatch.md, with
    --no-review also documented."""
    bodies = []
    if PLAN_SKILL.exists():
        bodies.append(PLAN_SKILL.read_text(encoding="utf-8"))
    if DEPTH_STUB.exists():
        bodies.append(DEPTH_STUB.read_text(encoding="utf-8"))
    combined = "\n".join(bodies)
    for needle in ("--depth=standard", "--depth=deep", "--depth=lite", "--no-review"):
        assert needle in combined, (
            f"--depth/--no-review flag handling must document {needle!r} "
            f"in skills/plan/SKILL.md or references/depth-flag-dispatch.md "
            f"(S07 acceptance)."
        )


def test_depth_stub_marks_handler_as_active_not_stub():
    """MUST: post-S07, the depth-flag-dispatch.md MUST no longer carry the
    `forward-compat stub` framing — the handler is active in S07."""
    assert DEPTH_STUB.exists(), f"{DEPTH_STUB} required by S02."
    body = DEPTH_STUB.read_text(encoding="utf-8")
    # The stub framing must be retired in favour of an active handler note.
    assert "forward-compat stub" not in body.lower() or "active" in body.lower(), (
        "depth-flag-dispatch.md MUST signal the handler is active in S07, "
        "not a forward-compat stub. Retain provenance but mark live."
    )


# ---- Acceptance Criterion 3 — NATIVE_THIN_LEADER_SKILLS updated ----


def test_v012_identity_surface_tuple_does_not_contain_deep_or_lite():
    """MUST: tests/test_regression_v012_native_identity_surface.py's
    NATIVE_THIN_LEADER_SKILLS tuple does NOT contain `deep-plan` or
    `lite-plan` (else the post-deletion identity test would itself fail —
    atomic update requirement)."""
    target = REPO_ROOT / "tests" / "test_regression_v012_native_identity_surface.py"
    body = target.read_text(encoding="utf-8")
    # Find the tuple body (between `NATIVE_THIN_LEADER_SKILLS = (` and matching `)`).
    start = body.find("NATIVE_THIN_LEADER_SKILLS = (")
    assert start != -1, f"NATIVE_THIN_LEADER_SKILLS tuple not found in {target}"
    end = body.find(")", start)
    tuple_body = body[start:end]
    assert '"deep-plan"' not in tuple_body, (
        "v0.12.0 identity surface tuple must not contain 'deep-plan' "
        "post-S07 — atomic with directory removal."
    )
    assert '"lite-plan"' not in tuple_body, (
        "v0.12.0 identity surface tuple must not contain 'lite-plan' "
        "post-S07 — atomic with directory removal."
    )


def test_v011_1_boundary_tuple_does_not_contain_deep_or_lite():
    """MUST: tests/test_regression_v011_1_using_superpowers_boundary.py's
    NATIVE_THIN_LEADER_SKILLS tuple does NOT contain `deep-plan` or
    `lite-plan` (else the boundary preamble test would fail when the
    SKILL.md files no longer exist)."""
    target = (
        REPO_ROOT
        / "tests"
        / "test_regression_v011_1_using_superpowers_boundary.py"
    )
    body = target.read_text(encoding="utf-8")
    start = body.find("NATIVE_THIN_LEADER_SKILLS = (")
    assert start != -1, f"NATIVE_THIN_LEADER_SKILLS tuple not found in {target}"
    end = body.find(")", start)
    tuple_body = body[start:end]
    assert '"deep-plan"' not in tuple_body, (
        "v0.11.1 boundary tuple must not contain 'deep-plan' post-S07."
    )
    assert '"lite-plan"' not in tuple_body, (
        "v0.11.1 boundary tuple must not contain 'lite-plan' post-S07."
    )


# ---- Acceptance Criterion 4 — v0.17.0 migration doc exists ----


def test_v017_0_migration_doc_exists():
    """MUST: docs/v0.17.0-migration.md exists with flag mapping."""
    assert MIGRATION_DOC.exists(), (
        f"S07 acceptance: {MIGRATION_DOC} must be created with the flag "
        f"mapping for /athanor:deep-plan and /athanor:lite-plan collapse."
    )


def test_v017_0_migration_doc_documents_flag_mapping():
    """MUST: migration doc explains the deep-plan → --depth=deep and
    lite-plan → --depth=lite mapping."""
    assert MIGRATION_DOC.exists()
    body = MIGRATION_DOC.read_text(encoding="utf-8")
    for needle in (
        "/athanor:deep-plan",
        "/athanor:lite-plan",
        "--depth=deep",
        "--depth=lite",
    ):
        assert needle in body, (
            f"docs/v0.17.0-migration.md must document {needle!r} as part "
            f"of the flag-mapping migration table."
        )


# ---- Acceptance Criterion 5 — trigger keywords preserve muscle memory ----


def test_plan_frontmatter_preserves_deep_tier_muscle_memory():
    """MUST: /athanor:plan frontmatter `description:` mentions deep-tier
    shorthand so the existing "딥 플랜" / "deep plan" / "심층" triggers
    continue to surface the plan skill."""
    body = PLAN_SKILL.read_text(encoding="utf-8")
    # The trigger keywords live in the YAML frontmatter description block.
    # Use a generous substring scan; the exact phrasing is open as long as
    # these tokens land somewhere in the frontmatter prose.
    front_end = body.find("\n---\n", 4)  # skip leading `---` then find closing
    assert front_end != -1, "/athanor:plan SKILL.md missing YAML frontmatter"
    front = body[:front_end]
    for needle in ("딥 플랜", "deep plan", "심층"):
        assert needle in front, (
            f"/athanor:plan frontmatter must preserve deep-tier trigger "
            f"keyword {needle!r} for muscle memory (S07 requirement)."
        )


def test_plan_frontmatter_preserves_lite_tier_muscle_memory():
    """MUST: /athanor:plan frontmatter mentions lite-tier shorthand so the
    existing "라이트 플랜" / "lite plan" / "간단한 계획" / "빠른" triggers
    continue to surface the plan skill."""
    body = PLAN_SKILL.read_text(encoding="utf-8")
    front_end = body.find("\n---\n", 4)
    assert front_end != -1, "/athanor:plan SKILL.md missing YAML frontmatter"
    front = body[:front_end]
    for needle in ("라이트 플랜", "lite plan", "간단한 계획", "빠른"):
        assert needle in front, (
            f"/athanor:plan frontmatter must preserve lite-tier trigger "
            f"keyword {needle!r} for muscle memory (S07 requirement)."
        )


# ---- CLAUDE.md Commands table ----


def test_claude_md_commands_table_does_not_list_deep_plan_row():
    """MUST: CLAUDE.md Commands table no longer carries the
    `/athanor:deep-plan` row (collapsed into /athanor:plan --depth=deep)."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    assert "| `/athanor:deep-plan` |" not in body, (
        "CLAUDE.md Commands table must not list /athanor:deep-plan as a "
        "separate row post-S07."
    )


def test_claude_md_commands_table_does_not_list_lite_plan_row():
    """MUST: CLAUDE.md Commands table no longer carries the
    `/athanor:lite-plan` row (collapsed into /athanor:plan --depth=lite)."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    assert "| `/athanor:lite-plan` |" not in body, (
        "CLAUDE.md Commands table must not list /athanor:lite-plan as a "
        "separate row post-S07."
    )


def test_claude_md_plan_row_mentions_depth_flag():
    """MUST: the /athanor:plan row in the Commands table mentions
    `--depth=` (and ideally --no-review) so users see the consolidated
    interface."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    # Find the /athanor:plan row.
    plan_row = next(
        (
            line
            for line in body.splitlines()
            if line.startswith("| `/athanor:plan`")
        ),
        None,
    )
    assert plan_row is not None, (
        "CLAUDE.md Commands table missing /athanor:plan row entirely."
    )
    assert "--depth=" in plan_row, (
        f"/athanor:plan row must mention --depth= flag post-S07. "
        f"Row was: {plan_row!r}"
    )
