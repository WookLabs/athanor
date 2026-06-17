"""Regression tests for workflow trace/eval documentation."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "workflow-trace-evals.md"


def test_workflow_trace_eval_doc_names_runner_schema_and_events() -> None:
    body = DOC.read_text(encoding="utf-8")
    for token in (
        "scripts/evals/run_workflow_scenarios.py",
        "schemas/workflow-trace.schema.json",
        "workflow.started",
        "verifier.result",
        "escalation.required",
        "deterministic graders",
        "require_order",
        "require_reference",
    ):
        assert token in body
