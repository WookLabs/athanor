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
        # Exit-code contract (BLOCKER 2): the block/refuse actions that exit 1
        # must be enumerated in the "Exit codes" section.
        "block_failed_eval",
        "run_scope_drift",
        "require_assessment_evidence",
        "require_receipt_validation",
        "does not invoke Claude Code",
    ):
        assert token in body
