"""Regression tests for the Athanor analyze skill surface.

The analyze skill is a Thin-Leader parallel fast-analysis workflow: the leader
dispatches simultaneous analyst workers (structure / dependency / context),
merges their short briefs directly, and writes the result to the session's
`analyze.md` — without reading or analyzing project code itself. These tests
lock the dispatch contract the SKILL.md actually commits to (not invented
behavior), mirroring tests/test_regression_assess_skill.py.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_ANALYZE = REPO_ROOT / "skills" / "analyze" / "SKILL.md"
CODEX_ANALYZE = (
    REPO_ROOT
    / "plugins"
    / "athanor-codex"
    / "skills"
    / "athanor-analyze"
    / "SKILL.md"
)
RUNTIME_CONTRACT = REPO_ROOT / "docs" / "runtime-surface-contract.json"
README = REPO_ROOT / "README.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

SESSION_DIR_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}$"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing file: {path}"
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = text.find("\n---\n", 4)
    assert end != -1, "SKILL.md must close YAML frontmatter"
    return text[:end]


def test_claude_analyze_skill_exists_with_trigger_surface() -> None:
    body = _read(CLAUDE_ANALYZE)
    front = _frontmatter(body)

    assert "name: analyze" in front
    assert "user-invocable: true" in front
    # Korean + English trigger tokens the description commits to.
    for token in ("분석", "코드 분석", "구조 파악", "analyze", "code analysis"):
        assert token in front
    assert "allowed-tools:" in front
    for tool in ("Bash", "Read", "Grep", "Glob", "Task"):
        assert tool in front


def test_claude_analyze_is_thin_leader_with_parallel_dispatch() -> None:
    body = _read(CLAUDE_ANALYZE)

    # Thin Leader marker: leader does NOT do the analysis itself.
    assert "Thin Leader" in body
    assert "you do NOT read files, trace code, or analyze anything yourself" in body
    assert "Parallel Fast Analysis" in body
    assert "Speed is the priority" in body

    # Core dispatch shape: simultaneous analyst workers, leader merges directly.
    for token in (
        "Structure Analyst",
        "Dependency Analyst",
        "Context Analyst",
        "Dispatch Parallel Workers",
        "simultaneous",
        "merges",
    ):
        assert token in body

    # Worker result-packet envelope.
    assert "ATHANOR_RESULT" in body
    assert "END_RESULT" in body


def test_claude_analyze_session_lookup_and_artifact_contract() -> None:
    body = _read(CLAUDE_ANALYZE)

    # Session Lookup Convention: canonical pointer + the exact dir regex.
    assert "Session Lookup Convention" in body
    assert SESSION_DIR_PATTERN in body
    # Read-only / append reuse intent — analyze never creates a new session.
    assert "read-only / append intent" in body
    assert "does NOT" in body and "create a new session" in body

    # Output artifact path under the active session directory.
    assert ".athanor/sessions/{id}/analyze.md" in body

    # Plan-Mode guard: only writes session files, never project source.
    assert "do NOT modify project files" in body
    assert "Only write to `.athanor/sessions/`" in body


def test_claude_analyze_carries_boundary_and_language_pointers() -> None:
    body = _read(CLAUDE_ANALYZE)

    # using-superpowers boundary pointer to the canonical CLAUDE.md declaration.
    assert "### using-superpowers boundary" in body
    assert (
        'using-superpowers boundary (v0.11.1) — canonical declaration' in body
    )

    # output.language handling just before Present-to-User.
    assert "output.language" in body


def test_codex_analyze_companion_states_no_edit_constraint() -> None:
    body = _read(CODEX_ANALYZE)
    front = _frontmatter(body)

    assert "name: athanor-analyze" in front
    for token in (
        "Protocol",
        "Focus areas",
        "Next actions",
        "Codex Constraints",
        "Do not edit files during analysis",
        "Do not invent architecture beyond evidence",
    ):
        assert token in body


def test_runtime_contract_and_docs_list_analyze_surface() -> None:
    contract = json.loads(RUNTIME_CONTRACT.read_text(encoding="utf-8"))
    assert "analyze" in contract["claude_plugin"]["native_skills"]
    assert "athanor-analyze" in contract["codex_companion"]["skills"]

    readme = README.read_text(encoding="utf-8")
    assert "/athanor:analyze" in readme
    assert "athanor-analyze" in readme

    claude = CLAUDE_MD.read_text(encoding="utf-8")
    assert "| `/athanor:analyze` |" in claude
    # analyze is one of the 13 native Thin Leader skills.
    assert "assess, analyze" in claude
