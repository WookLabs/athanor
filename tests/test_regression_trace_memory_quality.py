"""Regression tests for the P17 trace-memory quality gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "gates" / "trace_memory_quality.py"
SCHEMA = REPO_ROOT / "schemas" / "trace-memory-quality-report.schema.json"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "trace_memory_quality"
LESSONS = FIXTURE_ROOT / "lessons"
COMPARISONS = FIXTURE_ROOT / "comparisons.json"


def _run_report(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", "--today", "2026-06-17", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_lesson(root: Path, name: str, frontmatter: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(
        f"---\n{frontmatter.strip()}\n---\n\n## Lesson\nBody.\n",
        encoding="utf-8",
    )
    return path


def test_trace_memory_quality_fixture_report_passes() -> None:
    result = _run_report(
        "--lesson-root",
        str(LESSONS),
        "--comparison-file",
        str(COMPARISONS),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["lessons"] == 4
    assert report["summary"]["violations"] == 0
    actions = {lesson["lesson_id"]: lesson["action"] for lesson in report["lessons"]}
    assert actions["work-2026-06-17-001"] == "promote_candidate"
    assert actions["work-2026-06-01-002"] == "decay"
    assert actions["debug-2026-06-01-003"] == "quarantine"
    assert actions["plan-2026-06-17-004"] == "keep"


def test_trace_memory_quality_report_matches_schema() -> None:
    result = _run_report(
        "--lesson-root",
        str(LESSONS),
        "--comparison-file",
        str(COMPARISONS),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    jsonschema.validate(
        json.loads(result.stdout),
        json.loads(SCHEMA.read_text(encoding="utf-8")),
    )


def test_permanent_lesson_without_evidence_fails(tmp_path: Path) -> None:
    lessons = tmp_path / "lessons"
    _write_lesson(
        lessons,
        "plan-2026-06-17-999.md",
        """
type: lesson
skill: plan
contract-id: missing-evidence
version-at-time-of-lesson: v0.18.8
confidence: high
source: session-p17
access_count: 10
date: 2026-06-17
importance: permanent
""",
    )

    result = _run_report("--lesson-root", str(lessons))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert report["summary"]["violations"] == 1
    assert report["lessons"][0]["action"] == "violation"
    assert "evidence" in report["lessons"][0]["reason"]


def test_promotion_candidate_without_evidence_fails(tmp_path: Path) -> None:
    lessons = tmp_path / "lessons"
    _write_lesson(
        lessons,
        "work-2026-06-01-999.md",
        """
type: lesson
skill: work
contract-id: unbacked-promotion
version-at-time-of-lesson: v0.18.8
confidence: medium
source: session-p17
access_count: 8
date: 2026-06-01
importance: working
""",
    )

    result = _run_report("--lesson-root", str(lessons))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["lessons"][0]["action"] == "violation"
    assert "promotion candidate" in report["lessons"][0]["reason"]


def test_degraded_lesson_without_quarantine_fails(tmp_path: Path) -> None:
    lessons = tmp_path / "lessons"
    _write_lesson(
        lessons,
        "debug-2026-06-17-999.md",
        """
type: lesson
skill: debug
contract-id: degraded-not-quarantined
version-at-time-of-lesson: v0.18.8
confidence: low
source: session-p17
access_count: 1
date: 2026-06-17
importance: working
memory_outcome: degraded
trace_refs:
  - tests/fixtures/workflow_evals/scenarios.json#debug-regression
""",
    )

    result = _run_report("--lesson-root", str(lessons))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["lessons"][0]["action"] == "violation"
    assert "quarantine" in report["lessons"][0]["reason"]


def test_degraded_comparison_fails(tmp_path: Path) -> None:
    comparison = tmp_path / "comparisons.json"
    comparison.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "comparisons": [
                    {
                        "id": "bad-injection",
                        "lesson_id": "work-2026-06-17-001",
                        "scenario_id": "work-happy-path",
                        "baseline_score": 1.0,
                        "injected_score": 0.5,
                        "trace_refs": ["trace.jsonl#workflow.finished"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = _run_report(
        "--lesson-root",
        str(LESSONS),
        "--comparison-file",
        str(comparison),
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert report["comparisons"][0]["status"] == "fail"
    assert "degraded" in report["comparisons"][0]["reason"]
