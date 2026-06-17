"""Regression tests for the P12 runtime execution adapter."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "runtime_execution_adapter.py"
SCHEMA = REPO_ROOT / "schemas" / "runtime-execution-adapter-report.schema.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "runtime_execution"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location("runtime_execution_adapter", SCRIPT)
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


def test_fixture_gate_emits_schema_valid_pass_report() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["fixtures"] >= 6


def test_small_low_risk_patch_recommends_solo_current_checkout() -> None:
    module = _load_module()

    recommendation = module.recommend_backend(
        {
            "id": "unit-solo",
            "task": "Adjust one docs typo",
            "risk": "low",
            "estimated_files": 1,
            "parallel_workers": 0,
            "same_file_risk": "low",
            "long_running": False,
            "requires_isolation": False,
            "requires_peer_coordination": False,
            "requires_rerunnable_script": False,
            "requires_human_review": False,
        }
    )

    assert recommendation["recommended_backend"] == "solo"
    assert recommendation["isolation"] == "current-checkout"
    assert recommendation["confidence"] == "high"
    assert {reason["id"] for reason in recommendation["reasons"]} >= {
        "small-task",
        "low-conflict",
    }


def test_agent_team_unknown_falls_back_to_subagent_wave_with_warning() -> None:
    module = _load_module()

    recommendation = module.recommend_backend(
        {
            "id": "unit-agent-team-fallback",
            "task": "Have reviewers compare competing hypotheses",
            "risk": "medium",
            "estimated_files": 4,
            "parallel_workers": 3,
            "same_file_risk": "low",
            "long_running": False,
            "requires_isolation": False,
            "requires_peer_coordination": True,
            "requires_rerunnable_script": False,
            "requires_human_review": True,
            "capabilities": {"agent_team": "unknown", "subagent_wave": "available"},
        }
    )

    assert recommendation["recommended_backend"] == "subagent-wave"
    assert recommendation["fallback_backend"] == "agent-team"
    assert "agent-team-unknown" in {
        warning["id"] for warning in recommendation["warnings"]
    }
    assert "agent_team" in recommendation["blocked_capabilities"]


def test_fixture_mismatch_exits_one(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    (fixture_root / "bad.json").write_text(
        json.dumps(
            {
                "id": "bad",
                "request": {
                    "task": "Small patch",
                    "risk": "low",
                    "estimated_files": 1,
                    "parallel_workers": 0,
                    "same_file_risk": "low",
                    "long_running": False,
                    "requires_isolation": False,
                    "requires_peer_coordination": False,
                    "requires_rerunnable_script": False,
                    "requires_human_review": False,
                },
                "expect": {"recommended_backend": "agent-team"},
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


def test_invalid_request_exits_two(tmp_path: Path) -> None:
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "task": "Invalid risk",
                "risk": "severe",
                "estimated_files": 1,
                "parallel_workers": 0,
                "same_file_risk": "low",
                "long_running": False,
                "requires_isolation": False,
                "requires_peer_coordination": False,
                "requires_rerunnable_script": False,
                "requires_human_review": False,
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--request", str(request), "--json")

    assert proc.returncode == 2
    assert "unsupported risk" in proc.stderr
