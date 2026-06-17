#!/usr/bin/env python3
"""Read-only operator playbook builder for native runtime surfaces."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gates.native_runtime_probe import (  # noqa: E402
    NativeRuntimeProbeInputError,
    _read_json,
    build_live_profile,
    build_probe,
)


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safety() -> dict[str, Any]:
    return {
        "read_only_report": True,
        "executes_commands": False,
        "writes_runtime_state": False,
        "auto_launch_allowed": False,
        "external_telemetry": False,
        "irreversible_actions": 0,
    }


def _approval_prompt(backend: str, profile_id: str, required: bool) -> str:
    if not required:
        return ""
    return (
        "Type `I approve "
        f"{backend} execution for {profile_id}` before running any manual command "
        "from this recipe."
    )


def _manual_worktree_recipe(profile_id: str) -> dict[str, list[str]]:
    worktree = f"../athanor-{profile_id}-worktree"
    return {
        "preflight_commands": [
            "git status --short",
            "git worktree list --porcelain",
        ],
        "manual_commands": [
            f"git worktree add {worktree} HEAD",
            f"cd {worktree}",
            "python scripts/gates/native_runtime_probe.py --json",
        ],
        "evidence_required": [
            "Record `git worktree list --porcelain` before and after worktree creation.",
            "Record the worktree path, branch/ref, and validation commands run.",
            "Attach the cleanup result before treating the lifecycle as closed.",
        ],
        "cleanup_commands": [
            f"git worktree remove {worktree}",
            "git worktree prune",
            "git status --short",
        ],
    }


def _dynamic_workflow_recipe(profile_id: str) -> dict[str, list[str]]:
    return {
        "preflight_commands": [
            "claude --version",
            "git status --short",
            "python scripts/gates/native_runtime_probe.py --json",
        ],
        "manual_commands": [
            (
                "claude \"Run the approved Athanor dynamic-workflow plan for "
                f"{profile_id}; keep all spawned work read-only until explicit "
                "operator approval.\""
            ),
            "python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json",
        ],
        "evidence_required": [
            "Record the dynamic workflow prompt, spawned worker count, and stop condition.",
            "Capture each worker summary and the validation command output.",
            "Record any escalation back to the operator.",
        ],
        "cleanup_commands": [
            "Stop or close all spawned dynamic workflow sessions.",
            "git status --short",
        ],
    }


def _agent_team_recipe(profile_id: str) -> dict[str, list[str]]:
    return {
        "preflight_commands": [
            "claude --version",
            "git status --short",
            "python scripts/gates/native_runtime_probe.py --json",
        ],
        "manual_commands": [
            (
                "claude \"Start the approved Athanor agent-team lifecycle for "
                f"{profile_id}; assign roles, require evidence, and do not merge "
                "without operator approval.\""
            ),
            "python scripts/gates/harness_decision_ledger.py --json",
        ],
        "evidence_required": [
            "Record team roles, task split, and the owner for final integration.",
            "Capture each agent result and unresolved question.",
            "Run the relevant focused tests before accepting team output.",
        ],
        "cleanup_commands": [
            "Stop or close each agent-team session.",
            "Archive or delete temporary handoff notes after required evidence is committed.",
            "git status --short",
        ],
    }


def _current_session_recipe() -> dict[str, list[str]]:
    return {
        "preflight_commands": ["git status --short"],
        "manual_commands": ["Continue in the current session; do not launch native surfaces."],
        "evidence_required": [
            "Record the validation command output before claiming completion."
        ],
        "cleanup_commands": [],
    }


def _recipe_details(backend: str, profile_id: str) -> dict[str, list[str]]:
    if backend == "manual-worktree":
        return _manual_worktree_recipe(profile_id)
    if backend == "dynamic-workflow":
        return _dynamic_workflow_recipe(profile_id)
    if backend == "agent-team":
        return _agent_team_recipe(profile_id)
    return _current_session_recipe()


def _recipe(plan: dict[str, Any], profile_id: str) -> dict[str, Any]:
    backend = plan["backend"]
    details = _recipe_details(backend, profile_id)
    approval_required = bool(plan["operator_approval_required"])
    return {
        "backend": backend,
        "surface": plan.get("surface"),
        "surface_status": plan["surface_status"],
        "dry_run_source_mode": plan["mode"],
        "auto_execute": False,
        "operator_approval_required": approval_required,
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "cleanup_required": bool(plan["cleanup_required"]),
        "approval_prompt": _approval_prompt(backend, profile_id, approval_required),
        "preflight_commands": details["preflight_commands"],
        "manual_commands": details["manual_commands"],
        "evidence_required": details["evidence_required"],
        "cleanup_commands": details["cleanup_commands"],
        "evidence_refs": plan.get("evidence_refs", []),
    }


def _summary(recipes: list[dict[str, Any]], warnings: list[Any], errors: list[Any]) -> dict[str, Any]:
    return {
        "recipes": len(recipes),
        "native_recipes": sum(1 for recipe in recipes if recipe["surface"] is not None),
        "operator_approval_required": sum(
            1 for recipe in recipes if recipe["operator_approval_required"]
        ),
        "auto_executable_recipes": sum(1 for recipe in recipes if recipe["auto_execute"]),
        "irreversible_actions": 0,
        "warnings": len(warnings),
        "errors": len(errors),
    }


def build_playbook(raw_profile: dict[str, Any]) -> dict[str, Any]:
    """Build a native runtime operator playbook from a probe profile."""
    probe = build_probe(raw_profile)
    warnings = probe["warnings"]
    errors = probe["errors"]
    recipes = [] if probe["status"] != "pass" else [
        _recipe(plan, probe["profile_id"]) for plan in probe["launch_plans"]
    ]
    return {
        "schema_version": 1,
        "profile_id": probe["profile_id"],
        "status": probe["status"],
        "probe_status": probe["status"],
        "summary": _summary(recipes, warnings, errors),
        "safety": _safety(),
        "recipes": recipes,
        "warnings": warnings,
        "errors": errors,
    }


def _expectation_failures(playbook: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    expected_status = expect.get("report_status")
    if expected_status is not None and playbook["status"] != expected_status:
        failures.append(
            {
                "field": "report_status",
                "expected": expected_status,
                "actual": playbook["status"],
            }
        )
    actual_codes = sorted(error["code"] for error in playbook["errors"])
    expected_codes = sorted(expect.get("error_codes", []))
    if actual_codes != expected_codes:
        failures.append(
            {
                "field": "error_codes",
                "expected": expected_codes,
                "actual": actual_codes,
            }
        )
    return failures


def evaluate_fixture_root(
    fixture_root: Path, generated_at: str | None = None
) -> dict[str, Any]:
    if not fixture_root.is_dir():
        raise NativeRuntimeProbeInputError(f"fixture root is not a directory: {fixture_root}")
    files = sorted(path for path in fixture_root.glob("*.json") if path.is_file())
    if not files:
        raise NativeRuntimeProbeInputError(f"no native runtime probe fixtures found: {fixture_root}")

    items: list[dict[str, Any]] = []
    for path in files:
        fixture = _read_json(path, "native runtime probe fixture")
        if "profile" not in fixture or "expect" not in fixture:
            raise NativeRuntimeProbeInputError(f"fixture must contain profile and expect: {path}")
        fixture_id = str(fixture.get("id", path.stem))
        playbook = build_playbook(fixture["profile"])
        failures = _expectation_failures(playbook, fixture["expect"])
        item: dict[str, Any] = {
            "id": fixture_id,
            "path": path.as_posix(),
            "status": "pass" if not failures else "fail",
            "playbook": playbook,
        }
        if failures:
            item["failures"] = failures
        items.append(item)

    failed = sum(1 for item in items if item["status"] == "fail")
    playbooks = [item["playbook"] for item in items]
    return {
        "schema_version": 1,
        "status": "fail" if failed else "pass",
        "summary": {
            "fixtures": len(items),
            "passed": len(items) - failed,
            "failed": failed,
            "playbooks": len(playbooks),
            "recipes": sum(playbook["summary"]["recipes"] for playbook in playbooks),
            "auto_executable_recipes": sum(
                playbook["summary"]["auto_executable_recipes"]
                for playbook in playbooks
            ),
            "irreversible_actions": 0,
        },
        "generated_at": generated_at or _iso_now(),
        "fixtures": items,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build read-only native runtime operator playbooks."
    )
    parser.add_argument("--fixture-root", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        if args.fixture_root:
            report = evaluate_fixture_root(args.fixture_root)
            if args.json:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(
                    "native-runtime-playbook "
                    f"status={report['status']} "
                    f"fixtures={report['summary']['fixtures']} "
                    f"failed={report['summary']['failed']} "
                    f"recipes={report['summary']['recipes']}"
                )
            return 0 if report["status"] == "pass" else 1

        profile = _read_json(args.profile, "native runtime profile") if args.profile else build_live_profile()
        playbook = build_playbook(profile)
    except (OSError, NativeRuntimeProbeInputError) as exc:
        print(f"native runtime playbook: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(playbook, indent=2, sort_keys=True))
    else:
        print(
            "native-runtime-playbook "
            f"status={playbook['status']} "
            f"recipes={playbook['summary']['recipes']} "
            f"errors={playbook['summary']['errors']}"
        )
    return 0 if playbook["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
