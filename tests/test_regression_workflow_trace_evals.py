"""Regression tests for workflow trace eval scorer/reducer documentation."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "workflow-trace-evals.md"


def test_workflow_eval_profile_maps_core_terms_and_boundaries() -> None:
    body = DOC.read_text(encoding="utf-8")
    for token in (
        "Eval Profile",
        "Task",
        "Trace Fixture",
        "Scorer",
        "Reducer",
        "scorer_id",
        "score_provenance",
        "model-graded evals are optional",
        "not required for default local gates",
    ):
        assert token in body
