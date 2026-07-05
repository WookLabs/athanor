"""Regression locks for the current `/athanor:lfg-loop` skill surface."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "lfg-loop" / "SKILL.md"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_lfg_loop_skill_file_and_frontmatter() -> None:
    assert SKILL_PATH.is_file()
    text = _skill_text()
    assert "name: lfg-loop" in text
    assert "user-invocable: true" in text
    assert "allowed-tools: Bash, Read, Write, Task, AskUserQuestion, Skill" in text


def test_lfg_loop_accepts_objective_and_runs_full_flow() -> None:
    text = _skill_text().lower()
    required = [
        "natural-language objective",
        "deep research/discovery",
        "planning",
        "architecture/design",
        "implementation cycle",
        "assessment and review",
        "verification gate",
        "persistence and next-loop",
    ]
    missing = [needle for needle in required if needle not in text]
    assert not missing


def test_lfg_loop_has_explicit_evidence_gates_without_stop_hook_identity() -> None:
    text = _skill_text()
    lower = text.lower()
    assert "per-cycle receipts" in lower
    assert "assessment/review gates" in lower
    assert "controller decision" in lower
    assert "human escalation" in lower
    assert "no hidden completion hook" in lower
    assert "Stop hook runtime gate" not in text
    assert "stop_verify_claims.py" not in text


def test_lfg_loop_documents_controller_and_terminal_artifacts() -> None:
    text = _skill_text()
    assert "scripts/loops/run_lfg_loop_controller.py" in text
    assert "`complete_loop`" in text
    assert "loop-completion.md" in text
    assert "loop-residual-exit.md" in text


def test_lfg_loop_references_are_current() -> None:
    text = _skill_text()
    for reference in [
        "state-shape.md",
        "receipt-validator.md",
        "judge-rubric.md",
        "scope-change-critic.md",
        "loop-md-template.md",
        "lfg-vs-lfg-loop.md",
        "release-strategy.md",
        "enforcement-scope.md",
    ]:
        assert (REPO_ROOT / "skills" / "lfg-loop" / "references" / reference).is_file()
        assert reference in text
