"""Regression tests for S07 depth dispatch after explicit wrapper restoration.

S07 originally collapsed `/athanor:deep-plan` and `/athanor:lite-plan` into
`/athanor:plan --depth=<value>`. The current surface restores those names as
thin, user-invocable wrappers while keeping `/athanor:plan` as the canonical
owner of the planning protocol and session artifacts.

Acceptance criteria:
- `/athanor:deep-plan` and `/athanor:lite-plan` exist as thin wrappers.
- Wrappers force their tier, reject contradictory `--depth=` flags, and do not
  create `deep-plan.md` / `lite-plan.md` artifacts.
- `/athanor:plan` still documents `--depth={standard|deep|lite}` +
  `--no-review` compatibility.
- Identity-surface tuples include the restored wrappers.
- The v0.17.0 migration doc remains as historical flag-mapping context and
  explains that wrappers have since been restored.
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


def _skill_body(name: str) -> str:
    skill_md = SKILLS_DIR / name / "SKILL.md"
    assert skill_md.is_file(), f"skills/{name}/SKILL.md must exist"
    return skill_md.read_text(encoding="utf-8")


def _frontmatter(body: str) -> str:
    front_end = body.find("\n---\n", 4)
    assert front_end != -1, "SKILL.md missing YAML frontmatter"
    return body[:front_end]


def test_deep_plan_skill_dir_exists_as_thin_wrapper():
    body = _skill_body("deep-plan")
    front = _frontmatter(body)

    assert "name: deep-plan" in front
    assert "user-invocable: true" in front
    assert "/athanor:plan" in body
    assert "tier=deep" in body
    assert "--depth=standard" in body
    assert "--depth=lite" in body
    assert "contradictory" in body.lower()
    assert "deep-plan.md" in body
    assert "Do not create `deep-plan.md`" in body


def test_lite_plan_skill_dir_exists_as_thin_wrapper():
    body = _skill_body("lite-plan")
    front = _frontmatter(body)

    assert "name: lite-plan" in front
    assert "user-invocable: true" in front
    assert "/athanor:plan" in body
    assert "tier=lite" in body
    assert "--depth=standard" in body
    assert "--depth=deep" in body
    assert "contradictory" in body.lower()
    assert "lite-plan.md" in body
    assert "Do not create `lite-plan.md`" in body


def test_depth_flag_documented_in_plan_skill_or_references():
    bodies = []
    if PLAN_SKILL.exists():
        bodies.append(PLAN_SKILL.read_text(encoding="utf-8"))
    if DEPTH_STUB.exists():
        bodies.append(DEPTH_STUB.read_text(encoding="utf-8"))
    combined = "\n".join(bodies)
    for needle in ("--depth=standard", "--depth=deep", "--depth=lite", "--no-review"):
        assert needle in combined, (
            f"--depth/--no-review flag handling must document {needle!r} "
            f"in skills/plan/SKILL.md or references/depth-flag-dispatch.md."
        )


def test_depth_stub_marks_handler_as_active_not_stub():
    assert DEPTH_STUB.exists(), f"{DEPTH_STUB} required by S02."
    body = DEPTH_STUB.read_text(encoding="utf-8")
    assert "forward-compat stub" not in body.lower() or "active" in body.lower(), (
        "depth-flag-dispatch.md MUST signal the handler is active, "
        "not only a forward-compat stub."
    )
    assert "thin wrapper" in body.lower()
    assert "skills/deep-plan/SKILL.md" in body
    assert "skills/lite-plan/SKILL.md" in body


def test_v012_identity_surface_tuple_contains_restored_wrappers():
    target = REPO_ROOT / "tests" / "test_regression_v012_native_identity_surface.py"
    body = target.read_text(encoding="utf-8")
    start = body.find("NATIVE_THIN_LEADER_SKILLS = (")
    assert start != -1, f"NATIVE_THIN_LEADER_SKILLS tuple not found in {target}"
    end = body.find(")", start)
    tuple_body = body[start:end]
    for skill in ('"deep-plan"', '"lite-plan"'):
        assert skill in tuple_body, (
            "v0.12.0 identity surface tuple must include restored "
            f"thin wrapper {skill}."
        )


def test_v011_1_boundary_tuple_contains_restored_wrappers():
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
    for skill in ('"deep-plan"', '"lite-plan"'):
        assert skill in tuple_body, (
            "v0.11.1 boundary tuple must include restored "
            f"thin wrapper {skill}."
        )


def test_v017_0_migration_doc_documents_flag_mapping_and_wrapper_restore():
    assert MIGRATION_DOC.exists()
    body = MIGRATION_DOC.read_text(encoding="utf-8")
    for needle in (
        "/athanor:deep-plan",
        "/athanor:lite-plan",
        "--depth=deep",
        "--depth=lite",
        "thin wrapper",
        "restored",
    ):
        assert needle in body, (
            f"docs/v0.17.0-migration.md must document {needle!r} as part "
            "of the historical collapse and current wrapper restoration."
        )


def test_plan_frontmatter_preserves_deep_tier_muscle_memory():
    front = _frontmatter(PLAN_SKILL.read_text(encoding="utf-8"))
    for needle in ("딥 플랜", "deep plan", "심층"):
        assert needle in front, (
            f"/athanor:plan frontmatter must preserve deep-tier trigger "
            f"keyword {needle!r} for depth compatibility."
        )


def test_plan_frontmatter_preserves_lite_tier_muscle_memory():
    front = _frontmatter(PLAN_SKILL.read_text(encoding="utf-8"))
    for needle in ("라이트 플랜", "lite plan", "간단한 계획", "빠른"):
        assert needle in front, (
            f"/athanor:plan frontmatter must preserve lite-tier trigger "
            f"keyword {needle!r} for depth compatibility."
        )


def test_claude_md_commands_table_lists_wrappers_and_plan_depth_flag():
    body = CLAUDE_MD.read_text(encoding="utf-8")
    for command in (
        "| `/athanor:plan` |",
        "| `/athanor:deep-plan` |",
        "| `/athanor:lite-plan` |",
    ):
        assert command in body, f"CLAUDE.md Commands table missing {command}"

    plan_row = next(
        (line for line in body.splitlines() if line.startswith("| `/athanor:plan`")),
        None,
    )
    assert plan_row is not None
    assert "--depth=" in plan_row, (
        f"/athanor:plan row must mention --depth= compatibility. Row: {plan_row!r}"
    )
