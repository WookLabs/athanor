"""Regression tests for the P19 native runtime probe."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "native_runtime_probe.py"
SCHEMA = REPO_ROOT / "schemas" / "native-runtime-probe-report.schema.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "native_runtime_probe"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location("native_runtime_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _plans_by_backend(probe: dict) -> dict[str, dict]:
    return {plan["backend"]: plan for plan in probe["launch_plans"]}


def test_fixture_gate_emits_schema_valid_pass_report() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["fixtures"] == 3


def test_native_surfaces_are_dry_run_only_even_when_available() -> None:
    module = _load_module()

    probe = module.build_probe(
        {
            "id": "unit-available",
            "surfaces": {
                "goal": {"status": "available", "evidence_refs": ["unit"]},
                "loop": {"status": "available", "evidence_refs": ["unit"]},
                "worktree": {"status": "available", "evidence_refs": ["unit"]},
                "dynamic_workflow": {
                    "status": "available",
                    "evidence_refs": ["unit"],
                },
                "agent_team": {"status": "available", "evidence_refs": ["unit"]},
            },
            "requested_backends": [
                "manual-worktree",
                "dynamic-workflow",
                "agent-team",
            ],
        }
    )

    assert probe["status"] == "pass"
    plans = _plans_by_backend(probe)
    for backend in ("manual-worktree", "dynamic-workflow", "agent-team"):
        assert plans[backend]["mode"] == "dry-run-only"
        assert plans[backend]["auto_launch_allowed"] is False
        assert plans[backend]["operator_approval_required"] is True


def test_unknown_native_surface_keeps_conservative_warning() -> None:
    module = _load_module()

    probe = module.build_probe(
        {
            "id": "unit-unknown",
            "surfaces": {
                "worktree": {"status": "manual", "evidence_refs": ["git"]}
            },
            "requested_backends": ["dynamic-workflow"],
        }
    )

    plans = _plans_by_backend(probe)
    assert probe["status"] == "pass"
    assert plans["dynamic-workflow"]["surface_status"] == "unknown"
    assert plans["dynamic-workflow"]["mode"] == "dry-run-only"
    assert "capability-unconfirmed" in {
        warning["code"] for warning in probe["warnings"]
    }


def test_autolaunch_attempt_is_policy_failure() -> None:
    module = _load_module()

    probe = module.build_probe(
        {
            "id": "unit-autolaunch",
            "surfaces": {
                "dynamic_workflow": {
                    "status": "available",
                    "auto_launch_allowed": True,
                    "evidence_refs": ["unit"],
                }
            },
            "requested_backends": ["dynamic-workflow"],
        }
    )

    assert probe["status"] == "fail"
    assert "auto_launch_not_allowed" in {error["code"] for error in probe["errors"]}
    assert _plans_by_backend(probe)["dynamic-workflow"]["auto_launch_allowed"] is False


def test_fixture_expectation_mismatch_exits_one(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    (fixture_root / "bad.json").write_text(
        json.dumps(
            {
                "id": "bad",
                "profile": {
                    "id": "bad",
                    "surfaces": {
                        "dynamic_workflow": {
                            "status": "unknown",
                            "evidence_refs": [],
                        }
                    },
                    "requested_backends": ["dynamic-workflow"],
                },
                "expect": {
                    "report_status": "pass",
                    "surface_statuses": {"dynamic_workflow": "available"},
                    "launch_plan_modes": {"dynamic-workflow": "dry-run-only"},
                    "error_codes": [],
                },
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--fixture-root", str(fixture_root), "--json")

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert report["summary"]["failed"] == 1
    assert report["fixtures"][0]["status"] == "fail"


def test_invalid_profile_exits_two(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "id": "invalid",
                "surfaces": {
                    "dynamic_workflow": {
                        "status": "certainly",
                        "evidence_refs": ["bad"],
                    }
                },
                "requested_backends": ["dynamic-workflow"],
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--profile", str(profile), "--json")

    assert proc.returncode == 2
    assert "unsupported surface status" in proc.stderr

