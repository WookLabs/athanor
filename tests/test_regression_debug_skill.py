"""Regression tests for the Athanor debug skill surface.

The debug skill is a Thin-Leader structured-failure-diagnosis workflow: the
leader dispatches a single triage worker first, then — based on the triage
classification — parallel debug workers (Error Analyst / Git History / Code
Tracer), merges their findings, and writes the result to the session's
`debug.md`. It binds the systematic-debugging Iron Law (no fixes before root
cause). These tests lock the dispatch contract the SKILL.md actually commits
to, mirroring tests/test_regression_assess_skill.py.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DEBUG = REPO_ROOT / "skills" / "debug" / "SKILL.md"
CODEX_DEBUG = (
    REPO_ROOT
    / "plugins"
    / "athanor-codex"
    / "skills"
    / "athanor-debug"
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


def test_claude_debug_skill_exists_with_trigger_surface() -> None:
    body = _read(CLAUDE_DEBUG)
    front = _frontmatter(body)

    assert "name: debug" in front
    assert "user-invocable: true" in front
    # Korean + English trigger tokens the description commits to.
    for token in ("디버그", "에러", "실패 원인", "debug", "root cause", "find the bug"):
        assert token in front
    assert "allowed-tools:" in front
    for tool in ("Bash", "Read", "Grep", "Glob", "Task"):
        assert tool in front


def test_claude_debug_is_thin_leader_triage_then_parallel() -> None:
    body = _read(CLAUDE_DEBUG)

    # Thin Leader marker: leader does NOT debug itself.
    assert "Thin Leader" in body
    assert "you do NOT read files, trace code, or debug anything yourself" in body
    assert "Depth over speed" in body

    # Core dispatch shape: triage-first (single, sequential) → parallel workers.
    assert "Dispatch Triage Worker" in body
    assert "single" in body
    assert "Dispatch Parallel Workers" in body
    for worker in ("Error Analyst", "Git History", "Code Tracer"):
        assert worker in body

    # Triage classification taxonomy committed by the skill.
    for cls in ("error_log", "regression", "logic_bug", "full_debug"):
        assert cls in body

    # Worker result-packet envelope + needs_input branch.
    assert "ATHANOR_RESULT" in body
    assert "END_RESULT" in body
    assert "needs_input" in body


def test_claude_debug_binds_iron_law_systematic_discipline() -> None:
    body = _read(CLAUDE_DEBUG)

    # Iron Law: no fixes without root cause investigation first.
    assert "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST" in body
    assert "Iron Law" in body
    # Four-phase discipline + the 3-fixes architectural escalation.
    assert "Four Phases" in body
    assert "3+ fixes = architectural question" in body
    # pre-existing-issue stop-phrase guard is a debug-specific defense.
    assert "pre-existing issue" in body


def test_claude_debug_session_lookup_and_artifact_contract() -> None:
    body = _read(CLAUDE_DEBUG)

    # Session Lookup Convention: canonical pointer + the exact dir regex.
    assert "Session Lookup Convention" in body
    assert SESSION_DIR_PATTERN in body
    # Read-only / append reuse intent — debug never creates a new session.
    assert "read-only / append intent" in body
    assert "does NOT" in body and "create a new session" in body

    # Output artifact path under the active session directory.
    assert ".athanor/sessions/{id}/debug.md" in body

    # Plan-Mode guard: only writes session files, never project source.
    assert "Plan Mode" in body
    assert ".athanor/sessions/`에만 쓰기" in body


def test_claude_debug_carries_boundary_and_language_pointers() -> None:
    body = _read(CLAUDE_DEBUG)

    # using-superpowers boundary pointer to the canonical CLAUDE.md declaration.
    assert "### using-superpowers boundary" in body
    assert (
        'using-superpowers boundary (v0.11.1) — canonical declaration' in body
    )

    # output.language handling just before Present-to-User.
    assert "output.language" in body


def test_codex_debug_companion_states_diagnose_before_fix() -> None:
    body = _read(CODEX_DEBUG)
    front = _frontmatter(body)

    assert "name: athanor-debug" in front
    for token in (
        "Diagnose before fixing",
        "root cause",
        "Protocol",
        "Codex Constraints",
        "Do not edit files before reproducing",
        "Do not treat unrelated existing failures as solved",
    ):
        assert token in body


def test_runtime_contract_and_docs_list_debug_surface() -> None:
    contract = json.loads(RUNTIME_CONTRACT.read_text(encoding="utf-8"))
    assert "debug" in contract["claude_plugin"]["native_skills"]
    assert "athanor-debug" in contract["codex_companion"]["skills"]

    readme = README.read_text(encoding="utf-8")
    assert "/athanor:debug" in readme
    assert "athanor-debug" in readme

    claude = CLAUDE_MD.read_text(encoding="utf-8")
    assert "| `/athanor:debug` |" in claude
