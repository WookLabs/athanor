"""Regression tests for the P24 reactive channel fixture gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "reactive_channel_fixture.py"
SCHEMA = REPO_ROOT / "schemas" / "reactive-channel-fixture-report.schema.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "reactive_channels"
DOC = REPO_ROOT / "docs" / "reactive-channel-fixtures.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _plans_by_fixture(report: dict) -> dict[str, dict]:
    return {fixture["id"]: fixture["plan"] for fixture in report["fixtures"]}


def _actions_by_id(plan: dict) -> dict[str, dict]:
    return {action["id"]: action for action in plan["actions"]}


def test_fixture_gate_emits_schema_valid_local_only_report() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["fixtures"] == 3
    assert report["summary"]["failed"] == 0
    assert report["summary"]["auto_listeners"] == 0
    assert report["summary"]["auto_execute_actions"] == 0
    assert report["summary"]["irreversible_actions"] == 0

    for plan in _plans_by_fixture(report).values():
        assert plan["listener"]["default_enabled"] is False
        assert plan["listener"]["registered"] is False
        assert plan["safety"]["external_network_default"] is False
        assert plan["safety"]["external_telemetry"] is False
        assert plan["safety"]["irreversible_actions"] == 0
        for action in plan["actions"]:
            assert action["auto_execute"] is False
            assert action["listener_registered"] is False
            assert action["external_network_default"] is False
            assert action["external_telemetry"] is False


def test_ci_failure_maps_to_manual_ci_watcher_action() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    plan = _plans_by_fixture(json.loads(proc.stdout))["github-workflow-run-failure"]
    action = _actions_by_id(plan)["dispatch-ci-watcher"]
    commands = "\n".join(action["command_templates"])

    assert plan["event"]["normalized_type"] == "ci.failed"
    assert plan["event"]["pr_number"] == 42
    assert action["requires_operator_approval"] is True
    assert "@athanor-ci-watcher" in commands
    assert "gh pr checks 42 --watch" in commands
    assert any("CI" in item for item in action["evidence_required"])


def test_ci_success_records_pass_without_network_command() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    plan = _plans_by_fixture(json.loads(proc.stdout))["github-workflow-run-success"]
    action = _actions_by_id(plan)["record-ci-pass"]

    assert plan["event"]["normalized_type"] == "ci.passed"
    assert plan["event"]["pr_number"] == 42
    assert action["requires_operator_approval"] is False
    assert action["command_templates"] == []
    assert "workflow run conclusion" in "\n".join(action["evidence_required"])


def test_review_changes_requested_maps_to_review_response_plan() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    plan = _plans_by_fixture(json.loads(proc.stdout))[
        "github-pr-review-changes-requested"
    ]
    action = _actions_by_id(plan)["plan-review-response"]
    commands = "\n".join(action["command_templates"])

    assert plan["event"]["normalized_type"] == "review.changes_requested"
    assert plan["event"]["pr_number"] == 42
    assert action["requires_operator_approval"] is True
    assert "/athanor:review" in commands
    assert "gh pr view 42 --comments" in commands


def test_invalid_fixture_exits_two(tmp_path: Path) -> None:
    fixture = tmp_path / "invalid.json"
    fixture.write_text(
        json.dumps(
            {
                "id": "invalid",
                "channel": "github-actions",
                "event_type": "workflow_run",
                "delivery_id": "evt-invalid",
                "payload": {
                    "action": "completed",
                    "workflow_run": {"conclusion": "failure"},
                },
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--fixture", str(fixture), "--json")

    assert proc.returncode == 2
    assert "repository.full_name" in proc.stderr


def test_schema_docs_and_architecture_are_tracked() -> None:
    assert SCHEMA.is_file()
    assert DOC.is_file()
    assert (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "2026-06-18-p24-reactive-channel-fixture-design.md"
    ).is_file()
    assert (
        REPO_ROOT
        / "docs"
        / "plans"
        / "2026-06-18-p24-reactive-channel-fixture-plan.md"
    ).is_file()
