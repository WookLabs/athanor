"""Regression tests for the P29 policy promotion ledger gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "policy_promotion_ledger.py"
SCHEMA = REPO_ROOT / "schemas" / "policy-promotion-ledger-report.schema.json"
DOC = REPO_ROOT / "docs" / "policy-promotion-ledger.md"
LEDGER_ROOT = REPO_ROOT / "docs" / "policy-promotions"

REQUIRED_GATE_PROMOTION = "p29-policy-promotion-gate"
REQUIRED_RETIRED_PROMOTION = "legacy-prose-only-policy-notes"
STATE_ORDER = [
    "incident",
    "lesson",
    "candidate_policy",
    "policy",
    "gate_candidate",
    "gate",
    "retired",
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


def test_cli_emits_schema_valid_read_only_policy_promotion_report() -> None:
    assert SCRIPT.is_file(), "P29 policy promotion ledger gate must exist"
    assert SCHEMA.is_file(), "P29 report schema must exist"
    assert DOC.is_file(), "P29 policy promotion doc must exist"
    assert LEDGER_ROOT.is_dir(), "P29 committed policy promotion root must exist"

    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["profile"]["auto_runtime_launch"] is False
    assert report["summary"]["errors"] == 0
    assert report["summary"]["irreversible_actions"] == 0
    assert report["summary"]["promotions"] >= 2
    assert report["summary"]["gate_promotions"] >= 1
    assert report["summary"]["retired_promotions"] >= 1


def test_committed_promotions_cover_gate_and_retirement_paths() -> None:
    proc = _run_cli()

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    promotions = {promotion["id"]: promotion for promotion in report["promotions"]}

    gate = promotions[REQUIRED_GATE_PROMOTION]
    assert gate["current_state"] == "gate"
    assert gate["owner_office"] == "learning-governance"
    assert gate["owner_role"] == "policy-steward"
    assert gate["acceptance_criteria"]
    assert gate["rollback_plan"]
    assert gate["evidence_refs"]
    assert gate["gate_refs"]
    assert gate["test_refs"]
    assert gate["schema_refs"]
    gate_history = [STATE_ORDER.index(entry["state"]) for entry in gate["state_history"]]
    assert gate_history == sorted(gate_history)

    retired = promotions[REQUIRED_RETIRED_PROMOTION]
    assert retired["current_state"] == "retired"
    assert retired["retired_reason"]
    assert retired["replacement_refs"]


def test_gate_state_requires_tests_and_schema_backed_checks(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    promotion_path = root / "docs" / "policy-promotions" / "fixture-policy.json"
    promotion = _load_json(promotion_path)
    promotion["test_refs"] = []
    promotion["schema_refs"] = []
    promotion_path.write_text(json.dumps(promotion, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    codes = {error["code"] for error in report["errors"]}
    assert "missing_gate_test_refs" in codes
    assert "missing_gate_schema_refs" in codes


def test_policy_state_requires_rollback_plan(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    promotion_path = root / "docs" / "policy-promotions" / "fixture-policy.json"
    promotion = _load_json(promotion_path)
    promotion["current_state"] = "policy"
    promotion["rollback_plan"] = ""
    promotion["state_history"] = promotion["state_history"][:4]
    promotion_path.write_text(json.dumps(promotion, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(error["code"] == "missing_rollback_plan" for error in report["errors"])


def test_state_history_gap_fails_policy_promotion_gate(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    promotion_path = root / "docs" / "policy-promotions" / "fixture-policy.json"
    promotion = _load_json(promotion_path)
    promotion["state_history"] = [
        promotion["state_history"][0],
        promotion["state_history"][3],
        promotion["state_history"][-1],
    ]
    promotion_path.write_text(json.dumps(promotion, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(error["code"] == "state_history_gap" for error in report["errors"])


def test_retired_state_requires_reason_and_replacement(tmp_path: Path) -> None:
    root = _write_fixture_root(tmp_path)
    promotion_path = root / "docs" / "policy-promotions" / "fixture-policy.json"
    promotion = _load_json(promotion_path)
    promotion["current_state"] = "retired"
    promotion["retired_reason"] = ""
    promotion["replacement_refs"] = []
    promotion["state_history"].append(
        {
            "state": "retired",
            "status": "current",
            "owner_role": "policy-steward",
            "evidence_refs": ["docs/evidence.md"],
            "decided_at": "2026-06-18",
        }
    )
    promotion_path.write_text(json.dumps(promotion, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root))

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    codes = {error["code"] for error in report["errors"]}
    assert "missing_retired_reason" in codes
    assert "missing_replacement_refs" in codes


def _write_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    for rel in [
        "docs/evidence.md",
        "docs/policy-promotion-ledger.md",
        "scripts/gates/fixture_policy_gate.py",
        "schemas/fixture-policy.schema.json",
        "tests/test_fixture_policy.py",
    ]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{rel}\n", encoding="utf-8")
    promotion_root = root / "docs" / "policy-promotions"
    promotion_root.mkdir(parents=True, exist_ok=True)
    (promotion_root / "fixture-policy.json").write_text(
        json.dumps(_valid_promotion(), indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def _valid_promotion() -> dict:
    return {
        "schema_version": 1,
        "id": "fixture-policy",
        "title": "Fixture policy promotion",
        "current_state": "gate",
        "owner_office": "learning-governance",
        "owner_role": "policy-steward",
        "created_at": "2026-06-18",
        "updated_at": "2026-06-18",
        "source_refs": ["docs/evidence.md"],
        "evidence_refs": ["docs/evidence.md"],
        "acceptance_criteria": ["the policy is enforceable by a schema-backed gate"],
        "rollback_plan": "remove the gate and return the policy to candidate_policy",
        "policy_text": "Fixture policy text.",
        "gate_refs": ["scripts/gates/fixture_policy_gate.py"],
        "test_refs": ["tests/test_fixture_policy.py"],
        "schema_refs": ["schemas/fixture-policy.schema.json"],
        "replacement_refs": [],
        "retired_reason": "",
        "state_history": [
            {
                "state": "incident",
                "status": "completed",
                "owner_role": "learner",
                "evidence_refs": ["docs/evidence.md"],
                "decided_at": "2026-06-18",
            },
            {
                "state": "lesson",
                "status": "completed",
                "owner_role": "learner",
                "evidence_refs": ["docs/evidence.md"],
                "decided_at": "2026-06-18",
            },
            {
                "state": "candidate_policy",
                "status": "completed",
                "owner_role": "policy-steward",
                "evidence_refs": ["docs/evidence.md"],
                "decided_at": "2026-06-18",
            },
            {
                "state": "policy",
                "status": "completed",
                "owner_role": "policy-steward",
                "evidence_refs": ["docs/evidence.md"],
                "decided_at": "2026-06-18",
            },
            {
                "state": "gate_candidate",
                "status": "completed",
                "owner_role": "policy-steward",
                "evidence_refs": ["tests/test_fixture_policy.py", "schemas/fixture-policy.schema.json"],
                "decided_at": "2026-06-18",
            },
            {
                "state": "gate",
                "status": "current",
                "owner_role": "policy-steward",
                "evidence_refs": ["scripts/gates/fixture_policy_gate.py"],
                "decided_at": "2026-06-18",
            },
        ],
        "safety": {
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
            "irreversible_actions": 0,
        },
    }
