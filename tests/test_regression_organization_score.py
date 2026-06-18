"""Regression tests for the P30 organization score gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "organization_score.py"
SCHEMA = REPO_ROOT / "schemas" / "organization-score-report.schema.json"
DOC = REPO_ROOT / "docs" / "organization-score.md"

REQUIRED_INPUTS = {
    "organization-operating-model",
    "organization-work-item-registry",
    "organization-stage-receipt",
    "policy-promotion-ledger",
    "harness-decision-ledger",
    "package-facing-knowledge-index",
    "package-footprint-policy",
    "ci-gate-coverage",
    "safety-profile",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_emits_schema_valid_read_only_score_report() -> None:
    assert SCRIPT.is_file(), "P30 organization score gate must exist"
    assert SCHEMA.is_file(), "P30 report schema must exist"
    assert DOC.is_file(), "P30 organization score doc must exist"

    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["profile"]["auto_runtime_launch"] is False
    assert report["summary"]["irreversible_actions"] == 0
    assert report["summary"]["target_score"] == 9.8
    assert report["summary"]["current_score"] >= 9.8


def test_score_is_computed_from_current_evidence_inputs() -> None:
    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    inputs = {item["id"]: item for item in report["inputs"]}
    dimensions = {item["id"]: item for item in report["dimensions"]}

    assert REQUIRED_INPUTS <= set(inputs)
    assert all(inputs[input_id]["status"] in {"pass", "warn"} for input_id in REQUIRED_INPUTS)
    assert set(dimensions) >= {
        "organization-structure",
        "work-item-state",
        "stage-receipts",
        "policy-learning",
        "decision-evidence",
        "package-boundary",
        "ci-coverage",
        "safety",
    }
    assert abs(sum(item["weight"] for item in report["dimensions"]) - 1.0) < 0.0001
    assert report["score"]["target"] == 9.8
    assert report["score"]["current"] == report["summary"]["current_score"]
    assert report["score"]["current"] >= report["score"]["target"]


def test_score_report_tracks_bounded_residual_gaps() -> None:
    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    gap_ids = {gap["id"] for gap in report["residual_gaps"]}

    assert "external-sandboxed-benchmark-profile" in gap_ids
    assert "runtime-integration-hardening" in gap_ids
    assert "package-footprint-warning-reduction" in gap_ids
    assert all(gap["blocking_9_8"] is False for gap in report["residual_gaps"])


def test_missing_input_fails_below_target(tmp_path: Path) -> None:
    root = tmp_path / "empty-plugin"
    root.mkdir()

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert report["summary"]["current_score"] < report["summary"]["target_score"]
    assert any(error["code"] == "input_error" for error in report["errors"])
