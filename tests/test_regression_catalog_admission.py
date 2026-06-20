"""Regression tests for ref catalog admission governance."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "catalog_admission.py"
SCHEMA = REPO_ROOT / "schemas" / "catalog-entry.schema.json"
DOC = REPO_ROOT / "docs" / "catalog-admission-policy.md"
REF_ROOT = REPO_ROOT / "ref"

REQUIRED_FIELDS = {
    "id",
    "category",
    "url",
    "local_ref",
    "why_included",
    "license",
    "last_reviewed",
    "adoption_status",
    "runtime_surface_delta",
    "sunset_condition",
}


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _entry_by_id(report: dict, entry_id: str) -> dict:
    for entry in report["entries"]:
        if entry["id"] == entry_id:
            return entry
    raise AssertionError(f"missing catalog entry {entry_id!r}")


def test_catalog_admission_reports_all_current_refs_with_schema_valid_entries() -> None:
    assert SCRIPT.is_file(), "catalog admission gate must exist"
    assert SCHEMA.is_file(), "catalog entry schema must exist"
    assert DOC.is_file(), "catalog admission policy doc must exist"

    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    expected_ref_count = len([path for path in REF_ROOT.iterdir() if path.is_dir()])
    assert report["schema_version"] == 1
    assert report["status"] in {"pass", "warn"}
    assert report["summary"]["local_refs"] == expected_ref_count
    assert report["summary"]["entries"] == expected_ref_count
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["summary"]["irreversible_actions"] == 0
    for entry in report["entries"]:
        assert REQUIRED_FIELDS <= set(entry)
        jsonschema.validate(entry, schema)


def test_surface_growth_refs_are_capped_below_adopt() -> None:
    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    compound = _entry_by_id(report, "compound-engineering-plugin")
    assert compound["adoption_status"] in {"adapt", "observe", "reject", "sunset"}
    assert compound["adoption_status"] != "adopt"
    assert compound["runtime_surface_delta"]["skills"] > 0
    assert compound["runtime_surface_delta"]["cap"] is True
    assert "runtime surface" in compound["cap_reason"].lower()


def test_known_low_surface_principle_ref_can_be_adopted() -> None:
    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    principle = _entry_by_id(report, "boshu2-12-factor-agentops")
    assert principle["category"] in {"principles", "agentops"}
    assert principle["adoption_status"] in {"adopt", "adapt"}
    assert principle["runtime_surface_delta"]["cap"] is False


def test_runtime_surface_growth_without_evidence_is_not_adopted(tmp_path: Path) -> None:
    ref_root = tmp_path / "ref"
    candidate = ref_root / "surface-heavy"
    (candidate / ".claude-plugin").mkdir(parents=True)
    (candidate / "skills" / "one").mkdir(parents=True)
    (candidate / "agents").mkdir()
    (candidate / ".claude-plugin" / "plugin.json").write_text(
        '{"name":"surface-heavy","version":"0.1.0"}\n',
        encoding="utf-8",
    )
    (candidate / "skills" / "one" / "SKILL.md").write_text(
        "---\nname: one\n---\n# Skill\n",
        encoding="utf-8",
    )
    (candidate / "agents" / "worker.md").write_text(
        "---\nname: worker\n---\n# Worker\n",
        encoding="utf-8",
    )
    (candidate / "README.md").write_text("Adds skills and agents.\n", encoding="utf-8")

    proc = _run_cli("--ref-root", str(ref_root), "--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    entry = _entry_by_id(report, "surface-heavy")
    assert entry["adoption_status"] in {"observe", "reject", "sunset"}
    assert entry["adoption_status"] != "adopt"
    assert entry["runtime_surface_delta"]["cap"] is True
    assert entry["score"]["overall"] == min(entry["score"]["dimensions"].values())


def test_policy_doc_names_fail_cap_and_allowed_recommendations() -> None:
    body = DOC.read_text(encoding="utf-8")

    assert "fail-cap" in body.lower()
    for status in ("adopt", "adapt", "observe", "reject", "sunset"):
        assert status in body
    assert "no external telemetry" in body.lower()
    assert "11 commands" in body
    assert "4 registered agents" in body
