"""Regression tests for the P20 maintenance profile gate."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "maintenance_profile.py"
SCHEMA = REPO_ROOT / "schemas" / "maintenance-profile-report.schema.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location("maintenance_profile", SCRIPT)
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


@pytest.fixture(scope="module")
def current_repo_profile() -> dict:
    module = _load_module()
    return module.build_report(
        repo_root=REPO_ROOT,
        skip_claude=True,
        samples=1,
        ref_warn_days=99999,
    )


def test_cli_emits_schema_valid_read_only_profile() -> None:
    proc = _run_cli(
        "--skip-claude",
        "--ref-warn-days",
        "99999",
        "--samples",
        "1",
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] in {"pass", "warn"}
    assert report["summary"]["failures"] == 0
    assert report["summary"]["irreversible_actions"] == 0


def test_profile_contains_expected_read_only_steps(current_repo_profile: dict) -> None:
    step_ids = {step["id"] for step in current_repo_profile["steps"]}
    assert step_ids >= {
        "entropy-cleanup",
        "distribution-smoke",
        "observability-snapshot",
        "native-runtime-probe",
        "harness-decision-ledger",
    }
    assert all(step["read_only"] is True for step in current_repo_profile["steps"])
    assert current_repo_profile["summary"]["irreversible_actions"] == 0


def test_profile_exposes_loop_prompt_and_ci_command(current_repo_profile: dict) -> None:
    assert "python scripts/gates/maintenance_profile.py" in current_repo_profile["operator"]["ci_command"]
    assert "/loop" in current_repo_profile["operator"]["loop_prompt"]
    assert "--skip-claude" in current_repo_profile["operator"]["ci_command"]
    assert "no irreversible actions" in current_repo_profile["operator"]["loop_prompt"].lower()


def test_invalid_samples_exits_two() -> None:
    proc = _run_cli("--samples", "0", "--json")

    assert proc.returncode == 2
    assert "--samples must be >= 1" in proc.stderr

