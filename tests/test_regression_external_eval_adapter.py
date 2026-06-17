"""Regression tests for external eval/sandbox adapter export."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "scripts" / "evals" / "package_workflow_episode.py"
EXPORTER = REPO_ROOT / "scripts" / "evals" / "export_external_eval_adapter.py"
RUNNER = REPO_ROOT / "scripts" / "evals" / "run_workflow_scenarios.py"
SCENARIO_ROOT = REPO_ROOT / "tests" / "fixtures" / "workflow_evals"
SCHEMA = REPO_ROOT / "schemas" / "external-eval-adapter.schema.json"
DOC = REPO_ROOT / "docs" / "external-eval-adapter.md"


def _package_episode(output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(PACKAGE),
            "--scenario-root",
            str(SCENARIO_ROOT),
            "--output-dir",
            str(output_dir),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def _export_adapter(episode_dir: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(EXPORTER),
            "--episode-root",
            str(episode_dir),
            "--output-dir",
            str(output_dir),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def test_exporter_creates_external_eval_layout_from_episode(tmp_path: Path) -> None:
    episode_dir = tmp_path / "episode"
    adapter_dir = tmp_path / "external"
    package_proc = _package_episode(episode_dir)
    assert package_proc.returncode == 0, package_proc.stderr

    proc = _export_adapter(episode_dir, adapter_dir)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["adapter_root"] == str(adapter_dir)
    assert report["episode_root"] == str(episode_dir)
    assert report["summary"] == {
        "compatibility_profiles": 2,
        "external_execution_default_enabled": False,
        "external_telemetry": False,
        "network_access": False,
        "setup_commands": 0,
    }

    manifest_path = adapter_dir / "external-eval.json"
    task_path = adapter_dir / "tasks" / "workflow-evals.json"
    scorer_path = adapter_dir / "scorers" / "deterministic-workflow.json"
    sandbox_path = adapter_dir / "sandbox" / "manifest.json"
    readme_path = adapter_dir / "README.md"
    for path in (manifest_path, task_path, scorer_path, sandbox_path, readme_path):
        assert path.is_file(), path

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["adapter"] == "athanor-external-eval-adapter"
    assert manifest["compatibility_profiles"] == ["inspect-like", "harbor-like"]
    assert manifest["episode"]["manifest"] == "../episode/episode.json"
    assert manifest["external_execution"] == {
        "default_enabled": False,
        "dependencies": [],
        "install_commands": [],
        "runner_command": [
            "python",
            "scripts/evals/run_workflow_scenarios.py",
            "--episode-root",
            "<episode-root>",
            "--json",
        ],
    }

    task = json.loads(task_path.read_text(encoding="utf-8"))
    assert task["task_id"] == "workflow-evals"
    assert task["dataset"]["path"] == "../episode/scenarios"
    assert task["scorer"] == "../scorers/deterministic-workflow.json"
    assert task["sandbox"] == "../sandbox/manifest.json"

    scorer = json.loads(scorer_path.read_text(encoding="utf-8"))
    assert scorer["type"] == "deterministic-workflow-trace"
    assert set(scorer["grader_kinds"]) == {
        "forbid_event",
        "require_event",
        "require_order",
        "require_reference",
    }

    sandbox = json.loads(sandbox_path.read_text(encoding="utf-8"))
    assert sandbox["type"] == "local-readonly"
    assert sandbox["network_access"] is False
    assert sandbox["setup_commands"] == []
    assert sandbox["external_telemetry"] is False
    assert sandbox["filesystem"] == {
        "read_only_paths": ["../episode"],
        "write_paths": ["stdout"],
    }


def test_exported_episode_still_runs_with_local_runner(tmp_path: Path) -> None:
    episode_dir = tmp_path / "episode"
    adapter_dir = tmp_path / "external"
    assert _package_episode(episode_dir).returncode == 0
    assert _export_adapter(episode_dir, adapter_dir).returncode == 0

    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--episode-root",
            str(episode_dir),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert all(item["score"] == 1.0 for item in report["scenarios"])


def test_exporter_removes_stale_generated_files(tmp_path: Path) -> None:
    episode_dir = tmp_path / "episode"
    adapter_dir = tmp_path / "external"
    assert _package_episode(episode_dir).returncode == 0
    stale = adapter_dir / "tasks" / "old.json"
    stale.parent.mkdir(parents=True)
    stale.write_text("{}\n", encoding="utf-8")

    proc = _export_adapter(episode_dir, adapter_dir)

    assert proc.returncode == 0, proc.stderr
    assert not stale.exists()
    assert (adapter_dir / "tasks" / "workflow-evals.json").is_file()


def test_exporter_rejects_episode_that_requires_network(tmp_path: Path) -> None:
    episode_dir = tmp_path / "episode"
    package_proc = _package_episode(episode_dir)
    assert package_proc.returncode == 0, package_proc.stderr
    manifest_path = episode_dir / "episode.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sandbox"]["network_access"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    proc = _export_adapter(episode_dir, tmp_path / "external")

    assert proc.returncode == 2
    assert "network_access must be false" in proc.stderr


def test_external_adapter_schema_and_docs_are_tracked() -> None:
    assert SCHEMA.is_file()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["adapter"]["const"] == "athanor-external-eval-adapter"
    assert (
        schema["properties"]["external_execution"]["properties"]["default_enabled"]["const"]
        is False
    )

    body = DOC.read_text(encoding="utf-8")
    for token in (
        "scripts/evals/export_external_eval_adapter.py",
        "external-eval.json",
        "inspect-like",
        "harbor-like",
        "sandbox/manifest.json",
        "network_access",
        "external_telemetry",
    ):
        assert token in body
