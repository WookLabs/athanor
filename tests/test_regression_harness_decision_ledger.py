"""Regression tests for the P18 harness decision ledger gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "gates" / "harness_decision_ledger.py"
SCHEMA = REPO_ROOT / "schemas" / "harness-decision-ledger-report.schema.json"
LEDGER_ROOT = REPO_ROOT / "docs" / "harness-decisions"


def _run_report(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_ledger(root: Path, name: str, decisions: list[dict]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(
        json.dumps({"schema_version": 1, "decisions": decisions}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _decision(**overrides: object) -> dict:
    item = {
        "id": "decision-a",
        "date": "2026-06-17",
        "status": "observed",
        "change_type": "gate",
        "summary": "Fixture decision.",
        "expected_metrics": [
            {
                "metric": "fixture.metric",
                "direction": "increase",
                "target": "higher is better",
            }
        ],
        "verification_commands": [
            {"command": "python fixture.py --json", "expected": "status pass"}
        ],
        "observed_results": [
            {
                "status": "pass",
                "summary": "Observed pass.",
                "evidence_refs": ["tests/fixture.py"],
            }
        ],
        "decision": "keep",
        "rollback_or_follow_up": "Revert fixture gate if it becomes noisy.",
    }
    item.update(overrides)
    return item


def test_committed_harness_decision_ledger_passes() -> None:
    result = _run_report("--ledger-root", str(LEDGER_ROOT))

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["decisions"] >= 1
    assert report["summary"]["errors"] == 0
    assert "p17-trace-memory-quality" in {item["id"] for item in report["decisions"]}


def test_harness_decision_ledger_report_matches_schema() -> None:
    result = _run_report("--ledger-root", str(LEDGER_ROOT))

    assert result.returncode == 0, result.stdout + result.stderr
    jsonschema.validate(
        json.loads(result.stdout),
        json.loads(SCHEMA.read_text(encoding="utf-8")),
    )


def test_duplicate_decision_ids_fail(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "a.json", [_decision(id="dupe")])
    _write_ledger(tmp_path, "b.json", [_decision(id="dupe")])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "duplicate_id" for error in report["errors"])


def test_observed_decision_without_observed_results_fails(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "a.json", [_decision(observed_results=[])])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(error["code"] == "missing_observed_results" for error in report["errors"])


def test_observed_result_without_evidence_refs_fails(tmp_path: Path) -> None:
    item = _decision(
        observed_results=[
            {"status": "pass", "summary": "Observed pass.", "evidence_refs": []}
        ]
    )
    _write_ledger(tmp_path, "a.json", [item])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(error["code"] == "missing_evidence_refs" for error in report["errors"])


def test_invalid_metric_direction_fails(tmp_path: Path) -> None:
    item = _decision(
        expected_metrics=[
            {"metric": "fixture.metric", "direction": "sideways", "target": "invalid"}
        ]
    )
    _write_ledger(tmp_path, "a.json", [item])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(error["code"] == "invalid_metric_direction" for error in report["errors"])


def test_blank_verification_command_fails(tmp_path: Path) -> None:
    item = _decision(verification_commands=[{"command": " ", "expected": "status pass"}])
    _write_ledger(tmp_path, "a.json", [item])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(error["code"] == "blank_verification_command" for error in report["errors"])
