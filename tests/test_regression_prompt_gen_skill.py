"""Regression tests for the Athanor prompt-gen skill surface."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_PROMPT_GEN = REPO_ROOT / "skills" / "prompt-gen" / "SKILL.md"
CODEX_PROMPT_GEN = (
    REPO_ROOT
    / "plugins"
    / "athanor-codex"
    / "skills"
    / "athanor-prompt-gen"
    / "SKILL.md"
)
CLAUDE_PLAN = REPO_ROOT / "skills" / "plan" / "SKILL.md"
CODEX_PLAN = REPO_ROOT / "plugins" / "athanor-codex" / "skills" / "athanor-plan" / "SKILL.md"
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


def test_claude_prompt_gen_skill_exists_with_trigger_surface() -> None:
    body = _read(CLAUDE_PROMPT_GEN)
    front = _frontmatter(body)

    assert "name: prompt-gen" in front
    assert "user-invocable: true" in front
    for token in (
        "프롬프트 젠",
        "프롬프트 만들어줘",
        "요청 명확화",
        "다음 스킬 추천",
        "prompt generation",
        "plan prompt prep",
    ):
        assert token in front
    for tool in ("Bash", "Read", "Write", "Glob", "Grep", "AskUserQuestion", "Skill"):
        assert tool in front


def test_claude_prompt_gen_protocol_has_prompt_and_routing_contract() -> None:
    body = _read(CLAUDE_PROMPT_GEN)

    for token in (
        "/athanor:prompt-gen",
        ".athanor/sessions/{session-id}/prompt-gen.md",
        "Generated Prompt",
        "Recommended Next Skill",
        "Success Criteria",
        "Open Questions",
        "/athanor:plan --depth=lite",
        "/athanor:plan --depth=standard",
        "/athanor:plan --depth=deep",
        "/athanor:lfg-goal",
        "Do not implement",
        "Do not silently call the recommended next skill",
    ):
        assert token in body


def test_claude_prompt_gen_has_thin_leader_boundary_pointer() -> None:
    body = _read(CLAUDE_PROMPT_GEN)
    assert "You are the Athanor prompt-gen leader" in body
    assert "### using-superpowers boundary" in body
    assert "CLAUDE.md" in body


def test_codex_prompt_gen_companion_exists_and_states_runtime_limits() -> None:
    body = _read(CODEX_PROMPT_GEN)
    front = _frontmatter(body)

    assert "name: athanor-prompt-gen" in front
    for token in (
        "Generated Prompt",
        "Recommended Next Skill",
        "athanor-plan",
        "athanor-lfg-goal",
        "Do not claim Claude hooks",
        "Do not silently call the recommended skill",
    ):
        assert token in body


def test_runtime_contract_and_docs_list_prompt_gen_surface() -> None:
    contract = json.loads(RUNTIME_CONTRACT.read_text(encoding="utf-8"))
    assert "prompt-gen" in contract["claude_plugin"]["native_skills"]
    assert "athanor-prompt-gen" in contract["codex_companion"]["skills"]

    readme = README.read_text(encoding="utf-8")
    assert "/athanor:prompt-gen" in readme
    assert "Ships 15 skills" in readme
    assert "athanor-prompt-gen" in readme

    claude = CLAUDE_MD.read_text(encoding="utf-8")
    assert "11 user-invocable" in claude
    assert "| `/athanor:prompt-gen` |" in claude
    assert "11 native Thin Leader skills" in claude
    assert "prompt-gen" in claude


def test_plan_skill_uses_prompt_gen_for_vague_request_preflight() -> None:
    claude_plan = CLAUDE_PLAN.read_text(encoding="utf-8")
    codex_plan = CODEX_PLAN.read_text(encoding="utf-8")
    codex_plan_norm = " ".join(codex_plan.split())

    for token in (
        "prompt-gen.md",
        "Prompt-gen preflight",
        "/athanor:prompt-gen",
        "Do not invent product behavior",
    ):
        assert token in claude_plan
    for token in (
        "prompt-gen.md",
        "athanor-prompt-gen",
    ):
        assert token in codex_plan
    assert "instead of inventing product behavior" in codex_plan_norm


def test_unreleased_documents_prompt_gen_skill() -> None:
    body = CHANGELOG.read_text(encoding="utf-8")
    assert "Prompt generation skill" in body
    for token in (
        "/athanor:prompt-gen",
        "athanor-prompt-gen",
        "structured prompts",
        "recommend the next Athanor skill",
        "/athanor:plan",
    ):
        assert token in body
