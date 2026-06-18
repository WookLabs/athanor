"""Regression tests for the P27 organization work-item registry gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "organization_work_item_registry.py"
SCHEMA = REPO_ROOT / "schemas" / "organization-work-item-registry-report.schema.json"
DOC = REPO_ROOT / "docs" / "organization-work-item-registry.md"
REGISTRY_ROOT = REPO_ROOT / "docs" / "organization-work-items"

REQUIRED_ITEM = "p27-system-maturity-98"
CANONICAL_STAGE_ORDER = [
    "intake",
    "triage",
    "requirements",
    "research",
    "planning",
    "design-review",
    "execution",
    "verification",
    "release",
    "postmortem",
    "memory-update",
]


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


def test_cli_emits_schema_valid_read_only_registry_report() -> None:
    assert SCRIPT.is_file(), "P27 work-item registry gate must exist"
    assert SCHEMA.is_file(), "P27 report schema must exist"
    assert DOC.is_file(), "P27 registry design doc must exist"
    assert REGISTRY_ROOT.is_dir(), "P27 committed work-item registry must exist"

    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["summary"]["errors"] == 0
    assert report["summary"]["irreversible_actions"] == 0
    assert report["summary"]["items"] >= 1
    assert report["summary"]["active_items"] >= 1


def test_registry_tracks_current_goal_with_ordered_stage_history() -> None:
    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    items = {item["id"]: item for item in report["work_items"]}
    item = items[REQUIRED_ITEM]

    assert item["status"] == "active"
    assert item["target_score"] == 9.8
    assert item["current_stage"] in CANONICAL_STAGE_ORDER
    assert item["owner_office"] in {office["id"] for office in report["offices"]}
    assert item["owner_role"]
    assert item["acceptance_criteria"]
    assert item["artifacts"]

    active_history = [
        history
        for history in item["stage_history"]
        if history["status"] in {"active", "blocked"}
    ]
    assert len(active_history) == 1
    assert active_history[0]["stage"] == item["current_stage"]
    observed_order = [CANONICAL_STAGE_ORDER.index(entry["stage"]) for entry in item["stage_history"]]
    assert observed_order == sorted(observed_order)


def test_completed_stages_require_receipts(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    item_path = root / "docs" / "organization-work-items" / "fixture-item.json"
    item = _load_json(item_path)
    item["stage_history"][0]["receipt_ref"] = ""
    item_path.write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "missing_stage_receipt" for error in report["errors"])


def test_unknown_stage_fails_registry_gate(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    item_path = root / "docs" / "organization-work-items" / "fixture-item.json"
    item = _load_json(item_path)
    item["current_stage"] = "shadow-review"
    item["stage_history"][-1]["stage"] = "shadow-review"
    item_path.write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "unknown_stage" for error in report["errors"])


def test_stage_history_gap_fails_registry_gate(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    item_path = root / "docs" / "organization-work-items" / "fixture-item.json"
    item = _load_json(item_path)
    item["current_stage"] = "execution"
    item["stage_history"] = [
        item["stage_history"][0],
        {
            "stage": "execution",
            "status": "active",
            "owner_role": "executor",
            "artifact_refs": ["docs/organization-work-item-registry.md"],
            "receipt_ref": "",
            "decided_at": "2026-06-18",
        },
    ]
    item_path.write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "stage_history_gap" for error in report["errors"])


def _write_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    model_doc = root / "docs" / "organization-operating-model.md"
    registry_doc = root / "docs" / "organization-work-item-registry.md"
    item_path = root / "docs" / "organization-work-items" / "fixture-item.json"
    model_doc.parent.mkdir(parents=True, exist_ok=True)
    item_path.parent.mkdir(parents=True, exist_ok=True)
    registry_doc.write_text("fixture registry doc\n", encoding="utf-8")

    model = {
        "schema_version": 1,
        "model_id": "athanor-organization-operating-model",
        "last_reviewed": "2026-06-18",
        "safety": {
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
            "default_live_listener": False,
            "registered_agent_additions": 0,
            "irreversible_actions": 0,
        },
        "offices": [
            {"id": "product-intake", "title": "Product", "roles": ["intake-lead", "requirements-steward"]},
            {"id": "research", "title": "Research", "roles": ["research-lead"]},
            {"id": "architecture", "title": "Architecture", "roles": ["planner", "design-reviewer"]},
            {"id": "execution", "title": "Execution", "roles": ["executor"]},
            {"id": "qa-verification", "title": "QA", "roles": ["verification-lead"]},
            {"id": "release", "title": "Release", "roles": ["releaser"]},
            {"id": "learning-governance", "title": "Learning", "roles": ["learner", "policy-steward"]},
        ],
        "stages": [
            {
                "id": stage,
                "order": index + 1,
                "title": stage,
                "office": "product-intake" if index < 3 else "architecture",
                "owner_role": "intake-lead" if stage == "intake" else stage + "-owner",
                "entry_criteria": ["entry"],
                "required_artifacts": ["artifact"],
                "exit_criteria": ["exit"],
                "escalation_conditions": ["escalate"],
                "receipt_required": True,
                "leader_write_scope": "artifact-only",
                "command_mappings": [],
            }
            for index, stage in enumerate(CANONICAL_STAGE_ORDER)
        ],
        "promotion_loop": {
            "states": ["incident", "lesson", "candidate_policy", "policy", "gate_candidate", "gate", "retired"],
            "owner_office": "learning-governance",
        },
        "required_refs": ["docs/organization-work-item-registry.md"],
    }
    model_doc.write_text(
        "# Model\n\n<!-- athanor:organization-operating-model v=1 -->\n\n```json\n"
        + json.dumps(model, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    item_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "fixture-item",
                "title": "Fixture Item",
                "status": "active",
                "created_at": "2026-06-18",
                "updated_at": "2026-06-18",
                "target_score": 9.8,
                "source_refs": ["docs/organization-work-item-registry.md"],
                "acceptance_criteria": ["registry gate passes"],
                "current_stage": "planning",
                "owner_office": "architecture",
                "owner_role": "planning-owner",
                "artifacts": [
                    {
                        "stage": "planning",
                        "path": "docs/organization-work-item-registry.md",
                        "kind": "design",
                        "status": "current",
                    }
                ],
                "stage_history": [
                    {
                        "stage": "intake",
                        "status": "completed",
                        "owner_role": "intake-lead",
                        "artifact_refs": ["docs/organization-work-item-registry.md"],
                        "receipt_ref": "docs/organization-work-item-registry.md",
                        "decided_at": "2026-06-18",
                    },
                    {
                        "stage": "triage",
                        "status": "completed",
                        "owner_role": "triage-owner",
                        "artifact_refs": ["docs/organization-work-item-registry.md"],
                        "receipt_ref": "docs/organization-work-item-registry.md",
                        "decided_at": "2026-06-18",
                    },
                    {
                        "stage": "requirements",
                        "status": "completed",
                        "owner_role": "requirements-owner",
                        "artifact_refs": ["docs/organization-work-item-registry.md"],
                        "receipt_ref": "docs/organization-work-item-registry.md",
                        "decided_at": "2026-06-18",
                    },
                    {
                        "stage": "research",
                        "status": "completed",
                        "owner_role": "research-owner",
                        "artifact_refs": ["docs/organization-work-item-registry.md"],
                        "receipt_ref": "docs/organization-work-item-registry.md",
                        "decided_at": "2026-06-18",
                    },
                    {
                        "stage": "planning",
                        "status": "active",
                        "owner_role": "planning-owner",
                        "artifact_refs": ["docs/organization-work-item-registry.md"],
                        "receipt_ref": "",
                        "decided_at": "2026-06-18",
                    },
                ],
                "safety": {
                    "mutates_files_by_default": False,
                    "external_telemetry": False,
                    "irreversible_actions": 0,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return root
