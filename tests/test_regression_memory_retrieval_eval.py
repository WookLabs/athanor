"""Regression tests for memory-index retrieval quality evaluation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "memory_retrieval_eval.py"
SCHEMA = REPO_ROOT / "schemas" / "memory-retrieval-eval-report.schema.json"
DOC = REPO_ROOT / "docs" / "memory-retrieval-eval.md"
MEMORY_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "memory_index"
QUERIES = REPO_ROOT / "tests" / "fixtures" / "memory_retrieval_eval" / "queries.json"


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


def test_memory_retrieval_eval_fixture_report_passes_and_matches_schema() -> None:
    assert SCRIPT.is_file(), "memory retrieval eval gate must exist"
    assert SCHEMA.is_file(), "memory retrieval eval schema must exist"
    assert DOC.is_file(), "memory retrieval eval doc must exist"

    report = _report(
        "--fixture-root",
        str(MEMORY_FIXTURES),
        "--queries",
        str(QUERIES),
    )

    jsonschema.validate(report, json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["summary"]["queries"] == 2
    assert report["summary"]["failures"] == 0
    assert report["summary"]["hit_rate"] == 1.0
    assert report["summary"]["average_recall_at_k"] == 1.0
    assert report["summary"]["irreversible_actions"] == 0

    first = report["queries"][0]
    assert first["id"] == "release-evidence"
    assert first["retrieved_ids"][0] == "lesson:release-evidence"
    assert first["precision_at_k"] > 0
    assert first["recall_at_k"] == 1.0


def test_memory_retrieval_eval_fails_when_gold_id_is_missing(tmp_path: Path) -> None:
    query_file = tmp_path / "queries.json"
    query_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "queries": [
                    {
                        "id": "missing",
                        "query": "release evidence",
                        "gold_ids": ["lesson:not-present"],
                        "top_k": 2,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = _run_cli(
        "--fixture-root",
        str(MEMORY_FIXTURES),
        "--queries",
        str(query_file),
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert report["summary"]["failures"] == 1
    assert report["queries"][0]["missing_gold_ids"] == ["lesson:not-present"]
