"""Regression tests for portable workflow eval episode packaging."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "scripts" / "evals" / "package_workflow_episode.py"
RUNNER = REPO_ROOT / "scripts" / "evals" / "run_workflow_scenarios.py"
SCENARIO_ROOT = REPO_ROOT / "tests" / "fixtures" / "workflow_evals"
SCHEMA = REPO_ROOT / "schemas" / "workflow-eval-episode.schema.json"
DOC = REPO_ROOT / "docs" / "workflow-eval-episodes.md"

EXPECTED_SCENARIOS = {
    "work-evidence-happy-path",
    "work-missing-evidence-escalates",
    "lfg-goal-receipt-loop",
    "durable-loop-no-progress-escalates",
}


def _run_package(output_dir: Path) -> subprocess.CompletedProcess[str]:
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


def _run_episode(output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--episode-root",
            str(output_dir),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def test_packager_creates_portable_episode_manifest_and_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "workflow-evals"

    proc = _run_package(output_dir)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["episode_root"] == str(output_dir)
    assert report["scenario_count"] == 4
    assert set(report["scenario_ids"]) == EXPECTED_SCENARIOS

    manifest_path = output_dir / "episode.json"
    readme_path = output_dir / "README.md"
    scenario_path = output_dir / "scenarios" / "scenarios.json"
    assert manifest_path.is_file()
    assert readme_path.is_file()
    assert scenario_path.is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["episode_id"] == "workflow-evals"
    assert manifest["created_by"] == "athanor-workflow-episode-packager"
    assert set(manifest["source"]["scenario_ids"]) == EXPECTED_SCENARIOS
    assert manifest["runtime"]["dependencies"] == []
    assert manifest["runtime"]["requires_python"].startswith(">=")
    assert "scripts/evals/run_workflow_scenarios.py" in manifest["runtime"]["runner"]
    assert "--episode-root" in manifest["runtime"]["command"]
    assert manifest["artifacts"]["scenario_root"] == "scenarios"
    assert manifest["artifacts"]["scenario_schema"] == "schemas/workflow-eval-scenario.schema.json"
    assert manifest["artifacts"]["trace_schema"] == "schemas/workflow-trace.schema.json"
    assert manifest["sandbox"]["network_access"] is False
    assert manifest["sandbox"]["setup_commands_executed"] is False
    assert manifest["sandbox"]["filesystem_writes"] == ["episode report stdout"]
    assert manifest["limits"]["max_parallelism"] == 1
    assert manifest["limits"]["max_retries"] == 0
    assert manifest["limits"]["timeout_seconds"] >= 30
    assert manifest["privacy"]["raw_trace_content"] == "synthetic_fixture"
    assert set(manifest["scorers"]["deterministic_grader_kinds"]) == {
        "forbid_event",
        "require_event",
        "require_order",
        "require_reference",
    }


def test_runner_executes_packaged_episode_root(tmp_path: Path) -> None:
    output_dir = tmp_path / "workflow-evals"
    package_proc = _run_package(output_dir)
    assert package_proc.returncode == 0, package_proc.stderr

    proc = _run_episode(output_dir)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["episode_root"] == str(output_dir)
    assert report["scenario_root"] == str(output_dir / "scenarios")
    assert {item["id"] for item in report["scenarios"]} == EXPECTED_SCENARIOS
    assert all(item["score"] == 1.0 for item in report["scenarios"])


def test_runner_rejects_episode_manifest_that_requires_network(tmp_path: Path) -> None:
    episode_root = tmp_path / "bad-episode"
    (episode_root / "scenarios").mkdir(parents=True)
    (episode_root / "episode.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "episode_id": "bad-episode",
                "title": "Bad Episode",
                "description": "Invalid because it requires network.",
                "created_by": "athanor-workflow-episode-packager",
                "source": {"scenario_root": "tests/fixtures/workflow_evals", "scenario_ids": []},
                "runtime": {
                    "runner": "scripts/evals/run_workflow_scenarios.py",
                    "command": ["python", "scripts/evals/run_workflow_scenarios.py"],
                    "requires_python": ">=3.10",
                    "dependencies": [],
                },
                "artifacts": {
                    "scenario_root": "scenarios",
                    "scenario_schema": "schemas/workflow-eval-scenario.schema.json",
                    "trace_schema": "schemas/workflow-trace.schema.json",
                },
                "scorers": {"type": "deterministic", "deterministic_grader_kinds": []},
                "sandbox": {
                    "network_access": True,
                    "setup_commands_executed": False,
                    "filesystem_writes": ["episode report stdout"],
                },
                "limits": {
                    "timeout_seconds": 120,
                    "max_retries": 0,
                    "max_parallelism": 1,
                    "max_scenarios": 100,
                    "max_trace_records": 1000,
                },
                "privacy": {
                    "raw_trace_content": "synthetic_fixture",
                    "external_upload": False,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    proc = _run_episode(episode_root)

    assert proc.returncode == 2
    assert "network_access must be false" in proc.stderr


def test_packager_rejects_invalid_source_scenarios(tmp_path: Path) -> None:
    scenario_root = tmp_path / "bad-scenarios"
    scenario_root.mkdir()
    (scenario_root / "bad.json").write_text(
        json.dumps({"schema_version": 2, "scenarios": []}) + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(PACKAGE),
            "--scenario-root",
            str(scenario_root),
            "--output-dir",
            str(tmp_path / "episode"),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 2
    assert "schema_version" in proc.stderr


def test_runner_rejects_episode_that_exceeds_trace_record_limit(tmp_path: Path) -> None:
    episode_root = tmp_path / "limited-episode"
    scenario_dir = episode_root / "scenarios"
    scenario_dir.mkdir(parents=True)
    shutil.copyfile(SCENARIO_ROOT / "scenarios.json", scenario_dir / "scenarios.json")
    (episode_root / "episode.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "episode_id": "limited-episode",
                "title": "Limited Episode",
                "description": "Invalid because the trace record cap is too low.",
                "created_by": "athanor-workflow-episode-packager",
                "source": {
                    "scenario_root": "tests/fixtures/workflow_evals",
                    "scenario_files": ["scenarios.json"],
                    "scenario_ids": ["work-evidence-happy-path"],
                },
                "runtime": {
                    "runner": "scripts/evals/run_workflow_scenarios.py",
                    "command": ["python", "scripts/evals/run_workflow_scenarios.py"],
                    "requires_python": ">=3.10",
                    "dependencies": [],
                },
                "artifacts": {
                    "scenario_root": "scenarios",
                    "scenario_schema": "schemas/workflow-eval-scenario.schema.json",
                    "trace_schema": "schemas/workflow-trace.schema.json",
                },
                "scorers": {
                    "type": "deterministic",
                    "deterministic_grader_kinds": ["require_event"],
                },
                "sandbox": {
                    "network_access": False,
                    "setup_commands_executed": False,
                    "read_only_inputs": ["scenarios"],
                    "filesystem_writes": ["episode report stdout"],
                },
                "limits": {
                    "timeout_seconds": 120,
                    "max_retries": 0,
                    "max_parallelism": 1,
                    "max_scenarios": 100,
                    "max_trace_records": 1,
                },
                "privacy": {
                    "raw_trace_content": "synthetic_fixture",
                    "external_upload": False,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    proc = _run_episode(episode_root)

    assert proc.returncode == 2
    assert "trace record count exceeds limits.max_trace_records" in proc.stderr


def test_episode_schema_and_docs_are_tracked() -> None:
    assert SCHEMA.is_file()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["created_by"]["const"] == "athanor-workflow-episode-packager"
    assert schema["properties"]["sandbox"]["properties"]["network_access"]["const"] is False

    body = DOC.read_text(encoding="utf-8")
    for token in (
        "scripts/evals/package_workflow_episode.py",
        "scripts/evals/run_workflow_scenarios.py --episode-root",
        "schemas/workflow-eval-episode.schema.json",
        "episode.json",
        "network_access",
        "deterministic_grader_kinds",
    ):
        assert token in body
