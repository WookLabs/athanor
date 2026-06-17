"""Portable workflow eval episode packaging helpers."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

CREATED_BY = "athanor-workflow-episode-packager"
EPISODE_SCHEMA_VERSION = 1
DEFAULT_LIMITS = {
    "timeout_seconds": 120,
    "max_retries": 0,
    "max_parallelism": 1,
    "max_scenarios": 100,
    "max_trace_records": 1000,
}


class EpisodeSuiteFailed(Exception):
    """Raised when source scenarios evaluate but do not pass their thresholds."""

    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report
        super().__init__("workflow episode source scenarios did not pass")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load episode JSON {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"episode JSON root must be an object: {path}")
    return parsed


def _scenario_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise ValueError(f"scenario root does not exist: {root}")
    files = sorted(path for path in root.glob("*.json") if path.is_file())
    if not files:
        raise ValueError(f"scenario root contains no JSON scenario files: {root}")
    return files


def _scenario_summary(scenario_dir: Path) -> dict[str, Any]:
    scenario_ids: list[str] = []
    grader_kinds: set[str] = set()
    scenario_files: list[str] = []
    trace_records = 0
    for path in _scenario_files(scenario_dir):
        scenario_files.append(path.name)
        parsed = _load_json(path)
        raw_scenarios = parsed.get("scenarios")
        if not isinstance(raw_scenarios, list):
            raise ValueError(f"scenario file must contain scenarios[]: {path}")
        for scenario in raw_scenarios:
            if not isinstance(scenario, dict):
                raise ValueError(f"scenario entry must be an object: {path}")
            scenario_id = scenario.get("id")
            if isinstance(scenario_id, str):
                scenario_ids.append(scenario_id)
            trace = scenario.get("trace", [])
            if isinstance(trace, list):
                trace_records += len(trace)
            graders = scenario.get("graders", [])
            if isinstance(graders, list):
                for grader in graders:
                    if isinstance(grader, dict) and isinstance(grader.get("kind"), str):
                        grader_kinds.add(grader["kind"])
    return {
        "scenario_ids": sorted(scenario_ids),
        "scenario_files": sorted(scenario_files),
        "grader_kinds": sorted(grader_kinds),
        "trace_records": trace_records,
    }


def _manifest(
    *,
    source_root: Path,
    episode_id: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": EPISODE_SCHEMA_VERSION,
        "episode_id": episode_id,
        "title": "Athanor Workflow Eval Episode",
        "description": "Portable local package for deterministic Athanor workflow trace scenarios.",
        "created_by": CREATED_BY,
        "source": {
            "scenario_root": str(source_root),
            "scenario_files": summary["scenario_files"],
            "scenario_ids": summary["scenario_ids"],
        },
        "runtime": {
            "runner": "scripts/evals/run_workflow_scenarios.py",
            "command": [
                "python",
                "scripts/evals/run_workflow_scenarios.py",
                "--episode-root",
                ".",
                "--json",
            ],
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
            "deterministic_grader_kinds": summary["grader_kinds"],
        },
        "sandbox": {
            "network_access": False,
            "setup_commands_executed": False,
            "read_only_inputs": ["scenarios"],
            "filesystem_writes": ["episode report stdout"],
        },
        "limits": dict(DEFAULT_LIMITS),
        "privacy": {
            "raw_trace_content": "synthetic_fixture",
            "external_upload": False,
        },
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _readme(manifest: dict[str, Any]) -> str:
    command = " ".join(manifest["runtime"]["command"])
    return (
        "# Athanor Workflow Eval Episode\n\n"
        f"Episode id: `{manifest['episode_id']}`\n\n"
        "This directory is a portable local package for deterministic Athanor "
        "workflow trace scenarios.\n\n"
        "## Run\n\n"
        "```bash\n"
        f"{command}\n"
        "```\n\n"
        "The episode is local-first. It requires no network access, performs no "
        "setup command execution, and uses deterministic trace graders only.\n\n"
        "## Files\n\n"
        "- `episode.json`: episode manifest\n"
        "- `scenarios/`: packaged workflow scenario JSON files\n"
    )


def create_episode(
    source_root: Path,
    output_dir: Path,
    *,
    episode_id: str | None = None,
) -> dict[str, Any]:
    """Create a portable episode directory from workflow scenario files."""
    from scripts.evals.run_workflow_scenarios import evaluate_root

    source_root = Path(source_root)
    output_dir = Path(output_dir)
    source_files = _scenario_files(source_root)
    scenario_dir = output_dir / "scenarios"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    for stale in scenario_dir.glob("*.json"):
        stale.unlink()
    for source in source_files:
        shutil.copyfile(source, scenario_dir / source.name)

    evaluation = evaluate_root(scenario_dir)
    summary = _scenario_summary(scenario_dir)
    if evaluation["status"] != "pass":
        raise EpisodeSuiteFailed(evaluation)

    manifest = _manifest(
        source_root=source_root,
        episode_id=episode_id or output_dir.name or "workflow-evals",
        summary=summary,
    )
    _write_json(output_dir / "episode.json", manifest)
    (output_dir / "README.md").write_text(_readme(manifest), encoding="utf-8")
    load_episode(output_dir)
    return {
        "schema_version": 1,
        "status": "pass",
        "episode_root": str(output_dir),
        "manifest": str(output_dir / "episode.json"),
        "scenario_count": len(summary["scenario_ids"]),
        "scenario_ids": summary["scenario_ids"],
        "source_status": evaluation["status"],
    }


def _require_object(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"episode manifest {key} must be an object")
    return value


def _require_list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise ValueError(f"episode manifest {key} must be a list")
    return value


def _require_string(parent: dict[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"episode manifest {key} must be a non-empty string")
    return value


def load_episode(root: Path) -> dict[str, Any]:
    """Load and validate an episode manifest."""
    root = Path(root)
    manifest_path = root / "episode.json"
    if not manifest_path.is_file():
        raise ValueError(f"episode manifest not found: {manifest_path}")
    manifest = _load_json(manifest_path)
    required = {
        "schema_version",
        "episode_id",
        "title",
        "description",
        "created_by",
        "source",
        "runtime",
        "artifacts",
        "scorers",
        "sandbox",
        "limits",
        "privacy",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(f"episode manifest missing required fields: {missing}")
    if manifest.get("schema_version") != EPISODE_SCHEMA_VERSION:
        raise ValueError("episode manifest schema_version must be 1")
    if manifest.get("created_by") != CREATED_BY:
        raise ValueError(f"episode manifest created_by must be {CREATED_BY!r}")
    for key in ("episode_id", "title", "description"):
        _require_string(manifest, key)

    _require_object(manifest, "source")
    runtime = _require_object(manifest, "runtime")
    artifacts = _require_object(manifest, "artifacts")
    scorers = _require_object(manifest, "scorers")
    sandbox = _require_object(manifest, "sandbox")
    limits = _require_object(manifest, "limits")
    privacy = _require_object(manifest, "privacy")

    _require_string(runtime, "runner")
    command = _require_list(runtime, "command")
    if not all(isinstance(item, str) and item for item in command):
        raise ValueError("episode manifest runtime.command must be a list of strings")
    _require_string(runtime, "requires_python")
    _require_list(runtime, "dependencies")

    scenario_root = _require_string(artifacts, "scenario_root")
    _require_string(artifacts, "scenario_schema")
    _require_string(artifacts, "trace_schema")

    if scorers.get("type") != "deterministic":
        raise ValueError("episode manifest scorers.type must be deterministic")
    _require_list(scorers, "deterministic_grader_kinds")

    if sandbox.get("network_access") is not False:
        raise ValueError("episode manifest sandbox.network_access must be false")
    if sandbox.get("setup_commands_executed") is not False:
        raise ValueError("episode manifest sandbox.setup_commands_executed must be false")
    _require_list(sandbox, "filesystem_writes")

    for key in ("timeout_seconds", "max_retries", "max_parallelism", "max_scenarios", "max_trace_records"):
        value = limits.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"episode manifest limits.{key} must be a non-negative integer")

    _require_string(privacy, "raw_trace_content")
    if privacy.get("external_upload") is not False:
        raise ValueError("episode manifest privacy.external_upload must be false")

    root_resolved = root.resolve()
    scenario_path = (root / scenario_root).resolve()
    if not scenario_path.is_relative_to(root_resolved):
        raise ValueError("episode scenario_root must stay inside episode root")
    if not scenario_path.is_dir():
        raise ValueError(f"episode scenario root does not exist: {scenario_path}")
    summary = _scenario_summary(scenario_path)
    if len(summary["scenario_ids"]) > limits["max_scenarios"]:
        raise ValueError("episode scenario count exceeds limits.max_scenarios")
    if summary["trace_records"] > limits["max_trace_records"]:
        raise ValueError("episode trace record count exceeds limits.max_trace_records")
    return manifest


def resolve_episode_scenario_root(root: Path) -> Path:
    """Return the scenario root declared by a validated episode manifest."""
    manifest = load_episode(root)
    return Path(root) / manifest["artifacts"]["scenario_root"]
