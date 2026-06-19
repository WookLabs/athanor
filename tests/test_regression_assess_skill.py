"""Regression tests for the Athanor assess skill surface.

The assess skill is a goal-aligned assessment workflow: it turns a user goal
into weighted dimensions, scores the target on a 100-point scale, separates
confidence from score, and returns improvement priorities without executing
the plan.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_ASSESS = REPO_ROOT / "skills" / "assess" / "SKILL.md"
CODEX_ASSESS = (
    REPO_ROOT
    / "plugins"
    / "athanor-codex"
    / "skills"
    / "athanor-assess"
    / "SKILL.md"
)
RUNTIME_CONTRACT = REPO_ROOT / "docs" / "runtime-surface-contract.json"
README = REPO_ROOT / "README.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing file: {path}"
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = text.find("\n---\n", 4)
    assert end != -1, "SKILL.md must close YAML frontmatter"
    return text[:end]


def test_claude_assess_skill_exists_with_trigger_surface() -> None:
    body = _read(CLAUDE_ASSESS)
    front = _frontmatter(body)

    assert "name: assess" in front
    assert "user-invocable: true" in front
    for token in (
        "평가",
        "점수",
        "100점",
        "다각도",
        "성숙도",
        "팀 구성",
        "overbuilt",
        "underbuilt",
    ):
        assert token in front
    assert "allowed-tools:" in front
    for tool in ("Bash", "Read", "Write", "Glob", "Grep", "Task"):
        assert tool in front


def test_claude_assess_protocol_has_team_and_scoring_contract() -> None:
    body = _read(CLAUDE_ASSESS)

    for role in (
        "Goal Framer",
        "Structure Analyst",
        "Workflow Analyst",
        "Evidence Analyst",
        "Risk & Safety Analyst",
        "Operator Analyst",
        "Scoring Critic",
    ):
        assert role in body

    for token in (
        "/athanor:assess",
        "100-point",
        "Confidence",
        "weighted dimensions",
        "Overbuilt",
        "Underbuilt",
        "Add",
        "Remove / Simplify",
        "Priority Plan",
        "Final Score: {score} / 100",
        ".athanor/sessions/{session-id}/assess.md",
        "Do not implement",
        "Do not modify project source",
    ):
        assert token in body


def test_codex_assess_companion_exists_and_states_runtime_limits() -> None:
    body = _read(CODEX_ASSESS)
    front = _frontmatter(body)

    assert "name: athanor-assess" in front
    for token in (
        "goal-aligned",
        "100-point",
        "overbuilt",
        "underbuilt",
        "team",
    ):
        assert token in front or token in body
    for token in (
        "Goal Interpretation",
        "Score Summary",
        "Scoring Table",
        "Overbuilt",
        "Underbuilt",
        "Priority Plan",
        "Do not fabricate parallel worker output",
        "Do not modify files",
    ):
        assert token in body


def test_runtime_contract_and_docs_list_assess_surface() -> None:
    contract = json.loads(RUNTIME_CONTRACT.read_text(encoding="utf-8"))
    assert "assess" in contract["claude_plugin"]["native_skills"]
    assert "athanor-assess" in contract["codex_companion"]["skills"]

    readme = README.read_text(encoding="utf-8")
    assert "/athanor:assess" in readme
    assert "Ships 15 skills" in readme
    assert "athanor-assess" in readme

    claude = CLAUDE_MD.read_text(encoding="utf-8")
    assert "11 user-invocable" in claude
    assert "| `/athanor:assess` |" in claude
    assert "11 native Thin Leader skills" in claude
    assert "assess, analyze" in claude


def test_unreleased_documents_assess_skill() -> None:
    body = CHANGELOG.read_text(encoding="utf-8")
    assert "Assessment skill" in body
    for token in (
        "skills/assess/SKILL.md",
        "plugins/athanor-codex/skills/athanor-assess/SKILL.md",
        "100-point",
        "weighted dimensions",
        "overbuilt",
        "underbuilt",
        "Priority Plan",
    ):
        assert token in body
