"""Regression tests for the P28 organization stage receipt adapter."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "organization_stage_receipt.py"
REGISTRY_GATE = REPO_ROOT / "scripts" / "gates" / "organization_work_item_registry.py"
REPORT_SCHEMA = REPO_ROOT / "schemas" / "organization-stage-receipt-report.schema.json"
RECEIPT_SCHEMA = REPO_ROOT / "schemas" / "organization-stage-receipt.schema.json"
DOC = REPO_ROOT / "docs" / "organization-stage-receipts.md"
RECEIPT_ROOT = REPO_ROOT / "docs" / "organization-stage-receipts"

REQUIRED_RECEIPT = "p28-runtime-stage-receipt-adapter-release"

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


def _run_cli(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_registry_gate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REGISTRY_GATE), "--json", "--repo-root", str(root)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_validates_committed_stage_receipts_schema_valid_read_only() -> None:
    assert SCRIPT.is_file(), "P28 organization stage receipt adapter must exist"
    assert REPORT_SCHEMA.is_file(), "P28 report schema must exist"
    assert RECEIPT_SCHEMA.is_file(), "P28 receipt schema must exist"
    assert DOC.is_file(), "P28 receipt design doc must exist"
    assert RECEIPT_ROOT.is_dir(), "P28 committed stage receipt root must exist"

    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(REPORT_SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["profile"]["auto_runtime_launch"] is False
    assert report["profile"]["requires_explicit_emit"] is True
    assert report["profile"]["requires_explicit_work_item_update"] is True
    assert report["summary"]["errors"] == 0
    assert report["summary"]["irreversible_actions"] == 0
    assert report["summary"]["receipts"] >= 1
    assert report["summary"]["emitted_receipts"] == 0
    assert report["summary"]["work_item_updates"] == 0

    receipts = {receipt["id"]: receipt for receipt in report["receipts"]}
    assert REQUIRED_RECEIPT in receipts
    receipt = receipts[REQUIRED_RECEIPT]
    assert receipt["work_item_id"] == "p28-runtime-stage-receipt-adapter"
    assert receipt["stage"] == "release"
    assert receipt["source"] == "lfg-goal"

    receipt_path = REPO_ROOT / receipt["path"]
    jsonschema.validate(_load_json(receipt_path), _load_json(RECEIPT_SCHEMA))


def test_emit_is_explicit_and_does_not_write_by_default(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    output_root = root / ".athanor" / "organization-stage-receipts"

    proc = _run_cli(
        "--repo-root",
        str(root),
        "--work-item-id",
        "fixture-item",
        "--stage",
        "execution",
        "--decision",
        "completed",
        "--summary",
        "Execution completed with fixture evidence.",
        "--source",
        "lfg-goal",
        "--source-receipt",
        "tests/fixtures/lfg_goal/receipt_valid.md",
        "--evidence-ref",
        "docs/evidence.md",
        "--output-root",
        str(output_root.relative_to(root)),
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["summary"]["emitted_receipts"] == 0
    assert report["planned_receipt"]["will_write"] is False
    assert not output_root.exists()


def test_emit_creates_stage_receipt_with_model_owner_and_lfg_source(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    output_root = root / ".athanor" / "organization-stage-receipts"

    proc = _run_cli(
        "--repo-root",
        str(root),
        "--emit",
        "--work-item-id",
        "fixture-item",
        "--stage",
        "execution",
        "--decision",
        "completed",
        "--summary",
        "Execution completed with fixture evidence.",
        "--source",
        "lfg-goal",
        "--source-receipt",
        "tests/fixtures/lfg_goal/receipt_valid.md",
        "--evidence-ref",
        "docs/evidence.md",
        "--output-root",
        str(output_root.relative_to(root)),
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["summary"]["emitted_receipts"] == 1
    emitted = report["emitted_receipts"][0]
    receipt_path = root / emitted["path"]
    assert receipt_path.is_file()

    receipt = _load_json(receipt_path)
    jsonschema.validate(receipt, _load_json(RECEIPT_SCHEMA))
    assert receipt["work_item_id"] == "fixture-item"
    assert receipt["stage"] == "execution"
    assert receipt["owner_office"] == "execution"
    assert receipt["owner_role"] == "executor"
    assert receipt["decision"] == "completed"
    assert receipt["source"] == "lfg-goal"
    assert receipt["source_receipts"] == ["tests/fixtures/lfg_goal/receipt_valid.md"]


def test_apply_work_item_update_advances_registry_when_explicit(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)

    proc = _run_cli(
        "--repo-root",
        str(root),
        "--emit",
        "--apply-work-item-update",
        "--work-item-path",
        "docs/organization-work-items/fixture-item.json",
        "--next-stage",
        "verification",
        "--work-item-id",
        "fixture-item",
        "--stage",
        "execution",
        "--decision",
        "completed",
        "--summary",
        "Execution completed and handed off to verification.",
        "--source",
        "lfg-goal",
        "--source-receipt",
        "tests/fixtures/lfg_goal/receipt_valid.md",
        "--evidence-ref",
        "docs/evidence.md",
        "--output-root",
        "docs/organization-stage-receipts",
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["summary"]["emitted_receipts"] == 1
    assert report["summary"]["work_item_updates"] == 1

    registry_proc = _run_registry_gate(root)
    assert registry_proc.returncode == 0, registry_proc.stderr + registry_proc.stdout

    item = _load_json(root / "docs/organization-work-items/fixture-item.json")
    assert item["current_stage"] == "verification"
    assert item["owner_office"] == "qa-verification"
    assert item["owner_role"] == "verification-lead"
    history = {entry["stage"]: entry for entry in item["stage_history"]}
    assert history["execution"]["status"] == "completed"
    assert history["execution"]["receipt_ref"].startswith("docs/organization-stage-receipts/")
    assert history["verification"]["status"] == "active"


def test_lfg_goal_receipts_must_point_to_validator_output(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    receipt_path = root / "docs" / "organization-stage-receipts" / "bad.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = _valid_stage_receipt(root)
    receipt["source"] = "lfg-goal"
    receipt["source_receipts"] = []
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root), "--receipt-root", "docs/organization-stage-receipts")

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "missing_source_receipt" for error in report["errors"])


def test_unknown_stage_fails_stage_receipt_gate(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    receipt_path = root / "docs" / "organization-stage-receipts" / "bad.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = _valid_stage_receipt(root)
    receipt["stage"] = "shadow-review"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root), "--receipt-root", "docs/organization-stage-receipts")

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "unknown_stage" for error in report["errors"])


def _valid_stage_receipt(root: Path) -> dict:
    return {
        "schema_version": 1,
        "id": "fixture-item-execution-20260618T000000Z",
        "work_item_id": "fixture-item",
        "stage": "execution",
        "owner_office": "execution",
        "owner_role": "executor",
        "decision": "completed",
        "source": "lfg-goal",
        "summary": "Execution completed with fixture evidence.",
        "created_at": "2026-06-18T00:00:00Z",
        "evidence_refs": ["docs/evidence.md"],
        "source_receipts": ["tests/fixtures/lfg_goal/receipt_valid.md"],
        "commands": [
            {
                "command": "python scripts/gates/organization_stage_receipt.py --json",
                "exit_code": 0,
                "evidence": "fixture command passed",
            }
        ],
        "safety": {
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
            "irreversible_actions": 0,
            "requires_explicit_emit": True,
            "requires_explicit_work_item_update": True,
        },
    }


def _write_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    (root / "docs" / "organization-work-items").mkdir(parents=True)
    (root / "tests" / "fixtures" / "lfg_goal").mkdir(parents=True)
    (root / "docs" / "evidence.md").write_text("fixture evidence\n", encoding="utf-8")
    (root / "tests" / "fixtures" / "lfg_goal" / "receipt_valid.md").write_text(
        "# LFG Cycle Receipt C001\n\n## Step Receipts\n\nvalidator_status: all_valid\n",
        encoding="utf-8",
    )
    _write_model(root)
    _write_work_item(root)
    return root


def _write_model(root: Path) -> None:
    offices = [
        {"id": "product-intake", "title": "Product", "roles": ["intake-lead", "requirements-steward"]},
        {"id": "research", "title": "Research", "roles": ["research-lead"]},
        {"id": "architecture", "title": "Architecture", "roles": ["planner", "design-reviewer"]},
        {"id": "execution", "title": "Execution", "roles": ["executor"]},
        {"id": "qa-verification", "title": "QA", "roles": ["verification-lead"]},
        {"id": "release", "title": "Release", "roles": ["releaser"]},
        {"id": "learning-governance", "title": "Learning", "roles": ["learner", "policy-steward"]},
    ]
    stage_meta = {
        "intake": ("product-intake", "intake-lead"),
        "triage": ("product-intake", "requirements-steward"),
        "requirements": ("product-intake", "requirements-steward"),
        "research": ("research", "research-lead"),
        "planning": ("architecture", "planner"),
        "design-review": ("architecture", "design-reviewer"),
        "execution": ("execution", "executor"),
        "verification": ("qa-verification", "verification-lead"),
        "release": ("release", "releaser"),
        "postmortem": ("learning-governance", "learner"),
        "memory-update": ("learning-governance", "policy-steward"),
    }
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
        "offices": offices,
        "stages": [
            {
                "id": stage,
                "order": index + 1,
                "title": stage,
                "office": stage_meta[stage][0],
                "owner_role": stage_meta[stage][1],
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
        "required_refs": ["docs/evidence.md"],
    }
    (root / "docs" / "organization-operating-model.md").write_text(
        "# Model\n\n<!-- athanor:organization-operating-model v=1 -->\n\n```json\n"
        + json.dumps(model, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )


def _write_work_item(root: Path) -> None:
    history = []
    stage_meta = {
        "intake": "intake-lead",
        "triage": "requirements-steward",
        "requirements": "requirements-steward",
        "research": "research-lead",
        "planning": "planner",
        "design-review": "design-reviewer",
        "execution": "executor",
    }
    for stage in CANONICAL_STAGE_ORDER[:7]:
        history.append(
            {
                "stage": stage,
                "status": "active" if stage == "execution" else "completed",
                "owner_role": stage_meta[stage],
                "artifact_refs": ["docs/evidence.md"],
                "receipt_ref": "" if stage == "execution" else "docs/evidence.md",
                "decided_at": "2026-06-18",
            }
        )
    item = {
        "schema_version": 1,
        "id": "fixture-item",
        "title": "Fixture Item",
        "status": "active",
        "created_at": "2026-06-18",
        "updated_at": "2026-06-18",
        "target_score": 9.8,
        "source_refs": ["docs/evidence.md"],
        "acceptance_criteria": ["adapter emits receipts and advances registry explicitly"],
        "current_stage": "execution",
        "owner_office": "execution",
        "owner_role": "executor",
        "artifacts": [
            {
                "stage": "execution",
                "path": "docs/evidence.md",
                "kind": "evidence",
                "status": "current",
            }
        ],
        "stage_history": history,
        "safety": {
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "irreversible_actions": 0,
        },
    }
    (root / "docs" / "organization-work-items" / "fixture-item.json").write_text(
        json.dumps(item, indent=2) + "\n",
        encoding="utf-8",
    )
