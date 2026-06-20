"""Regression tests for file-local work-item stage transition governance."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "work_item_stage.py"
SCHEMA = REPO_ROOT / "schemas" / "work-item-stage-report.schema.json"
DOC = REPO_ROOT / "docs" / "work-item-stage-transitions.md"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "work_items"


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


def test_valid_work_item_stage_fixture_passes_and_matches_schema() -> None:
    assert SCRIPT.is_file(), "work-item stage transition gate must exist"
    assert SCHEMA.is_file(), "work-item stage report schema must exist"
    assert DOC.is_file(), "work-item stage transition doc must exist"

    report = _report("--fixture-root", str(FIXTURE_ROOT / "valid"))

    jsonschema.validate(report, json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["summary"]["items"] == 2
    assert report["summary"]["transitions"] == 5
    assert report["summary"]["errors"] == 0
    assert report["summary"]["irreversible_actions"] == 0

    target = next(item for item in report["work_items"] if item["id"] == "wi-stage-valid")
    assert target["stage"] == "review"
    assert target["dependency_status"] == "pass"
    assert target["evidence_status"] == "pass"
    assert target["approval_state"] == "approved"
    assert target["intervention_state"] == "none"


def test_invalid_transition_is_reported_with_actionable_error() -> None:
    result = _run_cli("--fixture-root", str(FIXTURE_ROOT / "invalid_transition"))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "invalid_transition" in {error["code"] for error in report["errors"]}
    invalid = next(error for error in report["errors"] if error["code"] == "invalid_transition")
    assert invalid["work_item_id"] == "wi-invalid-transition"
    assert invalid["from_stage"] == "queued"
    assert invalid["to_stage"] == "done"


def test_missing_dependency_and_required_evidence_are_reported() -> None:
    result = _run_cli("--fixture-root", str(FIXTURE_ROOT / "missing_evidence"))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    codes = {error["code"] for error in report["errors"]}
    assert "dependency_not_done" in codes
    assert "missing_required_evidence" in codes
    assert "transition_missing_evidence" in codes


def test_audit_log_sequence_must_be_gap_free_and_append_only_shaped() -> None:
    result = _run_cli("--fixture-root", str(FIXTURE_ROOT / "bad_audit"))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert "audit_sequence_gap" in {error["code"] for error in report["errors"]}


def test_doc_names_allowed_transitions_and_intervention_states() -> None:
    body = DOC.read_text(encoding="utf-8")

    for transition in ("queued -> work", "work -> review", "review -> done", "work -> blocked", "review -> work"):
        assert transition in body
    for intervention in ("proceed", "deny", "guide", "interrupt", "transform"):
        assert intervention in body
    assert "read-only" in body.lower()
    assert "append-only" in body.lower()
