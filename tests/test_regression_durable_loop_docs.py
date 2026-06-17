"""Regression tests for durable loop controller documentation."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "durable-loop-controller.md"


def test_durable_loop_doc_names_cli_fixture_state_and_boundary() -> None:
    body = DOC.read_text(encoding="utf-8")
    for token in (
        "scripts/loops/run_goal_loop_controller.py",
        "scripts/loops/run_goal_loop_fixtures.py",
        ".athanor/goals/<goal_id>/state.json",
        "loop.decision",
        "stop_no_progress",
        "stop_max_iterations",
        "require_eval_evidence",
        "does not invoke Claude Code",
    ):
        assert token in body
