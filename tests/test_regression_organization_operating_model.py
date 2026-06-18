"""Regression tests for the P26 organization operating model gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "organization_operating_model.py"
SCHEMA = REPO_ROOT / "schemas" / "organization-operating-model-report.schema.json"
DOC = REPO_ROOT / "docs" / "organization-operating-model.md"

REQUIRED_STAGES = [
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

REQUIRED_OFFICES = {
    "product-intake",
    "research",
    "architecture",
    "execution",
    "qa-verification",
    "release",
    "learning-governance",
}

REQUIRED_COMMANDS = {
    "/athanor:setup",
    "/athanor:discuss",
    "/athanor:analyze",
    "/athanor:debug",
    "/athanor:plan",
    "/athanor:work",
    "/athanor:review",
    "/athanor:lfg",
    "/athanor:lfg-goal",
}

REQUIRED_REFS = {
    "README.md",
    "CLAUDE.md",
    "docs/package-knowledge-index.md",
    "docs/harness-decision-ledger.md",
    "skills/lfg/SKILL.md",
    "skills/lfg-goal/SKILL.md",
    "scripts/gates/organization_operating_model.py",
    "docs/organization-work-item-registry.md",
    "scripts/gates/organization_work_item_registry.py",
    "docs/organization-stage-receipts.md",
    "schemas/organization-stage-receipt.schema.json",
    "schemas/organization-stage-receipt-report.schema.json",
    "scripts/gates/organization_stage_receipt.py",
    "docs/policy-promotion-ledger.md",
    "schemas/policy-promotion-ledger-report.schema.json",
    "scripts/gates/policy_promotion_ledger.py",
    "docs/organization-score.md",
    "schemas/organization-score-report.schema.json",
    "scripts/gates/organization_score.py",
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


def test_cli_emits_schema_valid_read_only_report() -> None:
    assert SCRIPT.is_file(), "P26 organization operating model gate must exist"
    assert SCHEMA.is_file(), "P26 report schema must exist"
    assert DOC.is_file(), "P26 organization operating model doc must exist"

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
    assert report["summary"]["registered_agent_additions"] == 0
    assert report["summary"]["errors"] == 0


def test_model_has_company_like_stage_graph_and_office_ownership() -> None:
    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    stages = {stage["id"]: stage for stage in report["stages"]}
    offices = {office["id"]: office for office in report["offices"]}

    assert list(stages) == REQUIRED_STAGES
    assert REQUIRED_OFFICES <= set(offices)
    for stage_id in REQUIRED_STAGES:
        stage = stages[stage_id]
        assert stage["office"] in offices
        assert stage["owner_role"]
        assert stage["entry_criteria"], stage_id
        assert stage["required_artifacts"], stage_id
        assert stage["exit_criteria"], stage_id
        assert stage["escalation_conditions"], stage_id
        assert stage["receipt_required"] is True


def test_existing_athanor_commands_are_mapped_into_stage_graph() -> None:
    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    command_coverage = {item["command"]: item for item in report["command_coverage"]}

    assert REQUIRED_COMMANDS <= set(command_coverage)
    for command in REQUIRED_COMMANDS:
        item = command_coverage[command]
        assert item["status"] == "pass"
        assert item["stage_id"] in REQUIRED_STAGES


def test_model_links_current_runtime_refs_without_adding_live_surfaces() -> None:
    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    refs = {item["path"]: item for item in report["required_refs"]}

    assert REQUIRED_REFS <= set(refs)
    assert all(refs[path]["status"] == "pass" for path in REQUIRED_REFS)
    assert report["safety"]["auto_runtime_launch"] is False
    assert report["safety"]["default_live_listener"] is False
    assert report["safety"]["registered_agent_additions"] == 0


def test_lfg_skills_reference_organization_operating_model() -> None:
    required = [
        "docs/organization-operating-model.md",
        "office/stage",
        "receipt",
    ]
    for rel in ("skills/lfg/SKILL.md", "skills/lfg-goal/SKILL.md"):
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        missing = [token for token in required if token not in body]
        assert not missing, f"{rel} must route through P26 organization model: {missing}"


def test_missing_stage_owner_fails_gate(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    _write_fixture_root(root)
    doc = root / "docs" / "organization-operating-model.md"
    body = doc.read_text(encoding="utf-8")
    body = body.replace('"owner_role": "intake-lead"', '"owner_role": ""')
    doc.write_text(body, encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "blank_stage_owner" for error in report["errors"])


def test_unknown_command_mapping_fails_gate(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    _write_fixture_root(root)
    doc = root / "docs" / "organization-operating-model.md"
    body = doc.read_text(encoding="utf-8")
    body = body.replace('"/athanor:plan"', '"/athanor:unknown"')
    doc.write_text(body, encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "missing_command_mapping" for error in report["errors"])


def _write_fixture_root(root: Path) -> None:
    for rel in REQUIRED_REFS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{rel}\n", encoding="utf-8")
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
            {"id": office, "title": office, "roles": [office + "-role"]}
            for office in sorted(REQUIRED_OFFICES)
        ],
        "stages": [
            {
                "id": stage,
                "order": index + 1,
                "title": stage,
                "office": sorted(REQUIRED_OFFICES)[index % len(REQUIRED_OFFICES)],
                "owner_role": "intake-lead" if stage == "intake" else stage + "-lead",
                "entry_criteria": ["input exists"],
                "required_artifacts": ["artifact.md"],
                "exit_criteria": ["artifact reviewed"],
                "escalation_conditions": ["missing artifact"],
                "receipt_required": True,
                "leader_write_scope": "infrastructure-only",
                "command_mappings": [],
            }
            for index, stage in enumerate(REQUIRED_STAGES)
        ],
        "promotion_loop": {
            "states": [
                "incident",
                "lesson",
                "candidate_policy",
                "policy",
                "gate_candidate",
                "gate",
                "retired",
            ],
            "owner_office": "learning-governance",
        },
        "required_refs": sorted(REQUIRED_REFS),
    }
    command_pairs = [
        ("/athanor:setup", "intake"),
        ("/athanor:discuss", "requirements"),
        ("/athanor:analyze", "research"),
        ("/athanor:debug", "research"),
        ("/athanor:plan", "planning"),
        ("/athanor:work", "execution"),
        ("/athanor:review", "verification"),
        ("/athanor:lfg", "release"),
        ("/athanor:lfg-goal", "memory-update"),
    ]
    for command, stage_id in command_pairs:
        for stage in model["stages"]:
            if stage["id"] == stage_id:
                stage["command_mappings"].append(command)
                break
    (root / "docs" / "organization-operating-model.md").write_text(
        "# Organization Operating Model\n\n"
        "<!-- athanor:organization-operating-model v=1 -->\n\n"
        "```json\n"
        + json.dumps(model, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
