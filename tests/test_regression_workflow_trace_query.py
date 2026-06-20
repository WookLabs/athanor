"""Regression tests for local workflow trace replay/search/stats/diff."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "evals" / "workflow_trace_query.py"
DOC = REPO_ROOT / "docs" / "workflow-trace-evals.md"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "workflow_trace_query"
BASE_TRACE = FIXTURE_ROOT / "base.jsonl"
CANDIDATE_TRACE = FIXTURE_ROOT / "candidate.jsonl"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _report(*args: str) -> dict:
    result = _run_cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_workflow_trace_query_timeline_stats_search_and_diff() -> None:
    assert SCRIPT.is_file(), "trace query CLI must exist"
    doc = DOC.read_text(encoding="utf-8")
    for token in ("Trace Query CLI", "timeline", "stats", "search", "diff"):
        assert token in doc

    timeline = _report("--trace-path", str(BASE_TRACE), "--mode", "timeline")
    assert timeline["status"] == "pass"
    assert timeline["profile"]["mutates_files_by_default"] is False
    assert timeline["summary"]["records"] == 4
    assert timeline["timeline"][0]["event_type"] == "workflow.started"
    assert timeline["timeline"][-1]["event_type"] == "workflow.finished"

    stats = _report("--trace-path", str(BASE_TRACE), "--mode", "stats")
    assert stats["stats"]["by_status"] == {"pass": 2, "started": 2}
    assert stats["stats"]["by_phase"] == {"work": 4}
    assert stats["stats"]["by_actor"]["leader"] == 2

    search = _report(
        "--trace-path",
        str(BASE_TRACE),
        "--mode",
        "search",
        "--query",
        "pytest",
    )
    assert search["summary"]["matches"] == 1
    assert search["matches"][0]["seq"] == 3
    assert "full_record" not in search["matches"][0]

    diff = _report(
        "--trace-path",
        str(BASE_TRACE),
        "--compare-path",
        str(CANDIDATE_TRACE),
        "--mode",
        "diff",
    )
    assert diff["summary"]["added"] == 1
    assert diff["summary"]["changed"] == 2
    assert {item["seq"] for item in diff["diff"]["changed"]} == {3, 4}
    assert diff["diff"]["added"][0]["seq"] == 5


def test_workflow_trace_query_requires_compare_path_for_diff() -> None:
    result = _run_cli("--trace-path", str(BASE_TRACE), "--mode", "diff")

    assert result.returncode == 2
    assert "compare-path" in result.stderr
