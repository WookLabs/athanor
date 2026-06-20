"""Regression tests for the ref-driven local memory index gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "memory_index.py"
SCHEMA = REPO_ROOT / "schemas" / "memory-index-report.schema.json"
DOC = REPO_ROOT / "docs" / "memory-index.md"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "memory_index"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _load_report(*args: str) -> dict:
    result = _run_cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_memory_index_fixture_report_matches_schema() -> None:
    assert SCRIPT.is_file(), "memory index gate script must exist"
    assert SCHEMA.is_file(), "memory index report schema must exist"
    assert DOC.is_file(), "memory index operator doc must exist"

    report = _load_report("--fixture-root", str(FIXTURE_ROOT))

    jsonschema.validate(report, json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["summary"]["irreversible_actions"] == 0
    assert report["summary"]["source_records"] == 5
    assert report["summary"]["records"] == 4
    assert report["summary"]["duplicates"] == 1
    assert {record["kind"] for record in report["records"]} == {
        "lesson",
        "trace",
        "goal",
        "completed_goal",
    }


def test_memory_index_records_are_stable_and_budgeted() -> None:
    report = _load_report("--fixture-root", str(FIXTURE_ROOT))

    records = {record["id"]: record for record in report["records"]}
    lesson = records["lesson:release-evidence"]
    assert lesson["kind"] == "lesson"
    assert lesson["source_path"].endswith("lessons/release-evidence.md")
    assert len(lesson["content_hash"]) == 64
    assert lesson["title"] == "Release evidence discipline"
    assert "verification evidence" in lesson["summary"]
    assert isinstance(lesson["tokens_estimate"], int)
    assert lesson["tokens_estimate"] > 0
    assert "full_content" not in lesson


def test_memory_index_search_returns_summaries_not_full_content() -> None:
    report = _load_report(
        "--fixture-root",
        str(FIXTURE_ROOT),
        "--query",
        "release evidence",
        "--limit",
        "3",
    )

    search = report["search"]
    assert search["query"] == "release evidence"
    assert search["limit"] == 3
    assert search["results"], report
    first = search["results"][0]
    assert first["id"] == "lesson:release-evidence"
    assert "summary" in first
    assert "full_content" not in first
    assert first["score"] > 0


def test_memory_index_detail_returns_full_record_by_id() -> None:
    report = _load_report(
        "--fixture-root",
        str(FIXTURE_ROOT),
        "--detail",
        "trace:workflow-finished",
    )

    detail = report["detail"]
    assert detail["id"] == "trace:workflow-finished"
    assert detail["kind"] == "trace"
    assert "workflow.finished" in detail["full_content"]
    assert detail["source_path"].endswith("traces/workflow.jsonl")


def test_memory_index_context_block_obeys_token_budget() -> None:
    report = _load_report(
        "--fixture-root",
        str(FIXTURE_ROOT),
        "--query",
        "release evidence goal",
        "--context-budget",
        "24",
    )

    context = report["context"]
    assert context["budget_tokens"] == 24
    assert context["tokens_estimate"] <= 24
    assert context["record_ids"]
    assert "release" in context["text"].lower()


def test_memory_index_missing_detail_fails() -> None:
    result = _run_cli(
        "--fixture-root",
        str(FIXTURE_ROOT),
        "--detail",
        "lesson:not-found",
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert report["summary"]["errors"] == 1
    assert "not-found" in report["errors"][0]["message"]
