"""Regression tests for ship-profile reduction decisions."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "package_footprint_policy.py"
SCHEMA = REPO_ROOT / "schemas" / "package-footprint-policy-report.schema.json"
DOC = REPO_ROOT / "docs" / "package-footprint-reduction.md"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_gate_reports_explicit_ship_profile_decisions_for_reduction_buckets() -> None:
    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(report, schema)

    decisions = {item["path_prefix"]: item for item in report["ship_profile_decisions"]}
    for prefix in ("docs/plans/", "docs/archive/", "tests/", "docs/architecture/", "ref/"):
        assert prefix in decisions
        assert decisions[prefix]["ship_profile_action"] == "exclude"
        assert decisions[prefix]["repo_local_retention"] == "keep"
        assert decisions[prefix]["deletion_allowed_by_policy"] is False
        assert decisions[prefix]["evidence_gate"] == "scripts/gates/package_footprint_policy.py --json"

    assert report["summary"]["ship_profile_exclusions"] >= 5
    assert any(
        check["id"] == "footprint.ship_profile_decisions" and check["status"] == "pass"
        for check in report["checks"]
    )


def test_reduction_doc_records_action_for_each_dev_only_bucket() -> None:
    assert DOC.is_file(), "ship-profile reduction doc must exist"
    body = DOC.read_text(encoding="utf-8")

    for token in (
        "docs/plans/",
        "docs/archive/",
        "tests/",
        "docs/architecture/",
        "ref/",
        "exclude from default ship profile",
        "keep repo-local",
        "do not delete",
        "python scripts/gates/package_footprint_policy.py --json",
        "python scripts/gates/catalog_admission.py --json",
    ):
        assert token in body
