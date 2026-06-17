"""External eval/sandbox adapter export helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.evals.workflow_episode import load_episode

ADAPTER_ID = "athanor-external-eval-adapter"
SCHEMA_VERSION = 1
COMPATIBILITY_PROFILES = ["inspect-like", "harbor-like"]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _relpath(target: Path, start: Path) -> str:
    return Path(target).resolve().relative_to(Path(start).resolve()).as_posix()


def _portable_relpath(target: Path, start: Path) -> str:
    try:
        return _relpath(target, start)
    except ValueError:
        import os

        return Path(os.path.relpath(target.resolve(), start.resolve())).as_posix()


def _remove_stale_json(root: Path) -> None:
    if not root.exists():
        return
    for path in root.glob("*.json"):
        if path.is_file():
            path.unlink()


def _clean_generated_dirs(output_dir: Path) -> None:
    for name in ("tasks", "scorers", "sandbox"):
        _remove_stale_json(output_dir / name)


def _runner_command() -> list[str]:
    return [
        "python",
        "scripts/evals/run_workflow_scenarios.py",
        "--episode-root",
        "<episode-root>",
        "--json",
    ]


def _manifest(episode_root: Path, output_dir: Path, episode: dict[str, Any]) -> dict[str, Any]:
    episode_manifest = _portable_relpath(episode_root / "episode.json", output_dir)
    scenario_root = _portable_relpath(
        episode_root / episode["artifacts"]["scenario_root"],
        output_dir,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "adapter": ADAPTER_ID,
        "compatibility_profiles": list(COMPATIBILITY_PROFILES),
        "episode": {
            "id": episode["episode_id"],
            "manifest": episode_manifest,
            "scenario_root": scenario_root,
            "scenario_ids": episode["source"]["scenario_ids"],
        },
        "artifacts": {
            "task": "tasks/workflow-evals.json",
            "scorer": "scorers/deterministic-workflow.json",
            "sandbox": "sandbox/manifest.json",
        },
        "external_execution": {
            "default_enabled": False,
            "dependencies": [],
            "install_commands": [],
            "runner_command": _runner_command(),
        },
        "privacy": {
            "external_telemetry": False,
            "external_upload": False,
            "raw_trace_content": episode["privacy"]["raw_trace_content"],
        },
    }


def _task(episode_root: Path, output_dir: Path, episode: dict[str, Any]) -> dict[str, Any]:
    scenario_root = _portable_relpath(
        episode_root / episode["artifacts"]["scenario_root"],
        output_dir,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "workflow-evals",
        "title": episode["title"],
        "description": episode["description"],
        "dataset": {
            "format": "athanor-workflow-eval-scenarios",
            "path": scenario_root,
            "scenario_schema": episode["artifacts"]["scenario_schema"],
            "trace_schema": episode["artifacts"]["trace_schema"],
            "scenario_ids": episode["source"]["scenario_ids"],
        },
        "runner": {
            "command": _runner_command(),
            "requires_python": episode["runtime"]["requires_python"],
            "dependencies": [],
        },
        "scorer": "../scorers/deterministic-workflow.json",
        "sandbox": "../sandbox/manifest.json",
        "limits": episode["limits"],
    }


def _scorer(episode: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "scorer_id": "deterministic-workflow",
        "type": "deterministic-workflow-trace",
        "grader_kinds": episode["scorers"]["deterministic_grader_kinds"],
        "score_range": {"min": 0.0, "max": 1.0},
        "pass_condition": "scenario score >= scenario min_score",
        "external_model_required": False,
    }


def _sandbox(episode_root: Path, output_dir: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "local-readonly",
        "network_access": False,
        "setup_commands": [],
        "external_telemetry": False,
        "filesystem": {
            "read_only_paths": [_portable_relpath(episode_root, output_dir)],
            "write_paths": ["stdout"],
        },
        "docker_required": False,
        "harbor_required": False,
        "inspect_required": False,
    }


def _readme() -> str:
    return (
        "# Athanor External Eval Adapter\n\n"
        "This directory exports a packaged Athanor workflow eval episode into an "
        "Inspect/Harbor-like metadata layout.\n\n"
        "## Files\n\n"
        "- `external-eval.json`: top-level adapter manifest\n"
        "- `tasks/workflow-evals.json`: task metadata\n"
        "- `scorers/deterministic-workflow.json`: deterministic scorer metadata\n"
        "- `sandbox/manifest.json`: local-only sandbox policy\n\n"
        "External execution is disabled by default. The adapter installs no "
        "dependencies, runs no setup commands, uses no network access, and emits "
        "no external telemetry.\n"
    )


def export_adapter(episode_root: Path, output_dir: Path) -> dict[str, Any]:
    """Export a packaged workflow episode into an external eval layout."""
    episode_root = Path(episode_root)
    output_dir = Path(output_dir)
    episode = load_episode(episode_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    _clean_generated_dirs(output_dir)

    manifest = _manifest(episode_root, output_dir, episode)
    task = _task(episode_root, output_dir, episode)
    scorer = _scorer(episode)
    sandbox = _sandbox(episode_root, output_dir)

    _write_json(output_dir / "external-eval.json", manifest)
    _write_json(output_dir / "tasks" / "workflow-evals.json", task)
    _write_json(output_dir / "scorers" / "deterministic-workflow.json", scorer)
    _write_json(output_dir / "sandbox" / "manifest.json", sandbox)
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "adapter": ADAPTER_ID,
        "adapter_root": str(output_dir),
        "episode_root": str(episode_root),
        "manifest": str(output_dir / "external-eval.json"),
        "files": {
            "task": str(output_dir / "tasks" / "workflow-evals.json"),
            "scorer": str(output_dir / "scorers" / "deterministic-workflow.json"),
            "sandbox": str(output_dir / "sandbox" / "manifest.json"),
        },
        "summary": {
            "compatibility_profiles": len(COMPATIBILITY_PROFILES),
            "external_execution_default_enabled": False,
            "external_telemetry": False,
            "network_access": False,
            "setup_commands": 0,
        },
    }
