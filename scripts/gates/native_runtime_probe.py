#!/usr/bin/env python3
"""Read-only native runtime capability probe for Athanor."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SURFACES = ("goal", "loop", "worktree", "dynamic_workflow", "agent_team")
SURFACE_STATUSES = {"available", "documented", "manual", "unavailable", "unknown"}
BACKENDS = {"solo", "subagent-wave", "manual-worktree", "dynamic-workflow", "agent-team"}
BACKEND_SURFACE = {
    "manual-worktree": "worktree",
    "dynamic-workflow": "dynamic_workflow",
    "agent-team": "agent_team",
}


class NativeRuntimeProbeInputError(Exception):
    """Raised when profile or fixture input cannot be evaluated."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise NativeRuntimeProbeInputError(f"{label} not found: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NativeRuntimeProbeInputError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise NativeRuntimeProbeInputError(f"{label} must be a JSON object")
    return parsed


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise NativeRuntimeProbeInputError(f"{field} must be a list of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise NativeRuntimeProbeInputError(f"{field}[{index}] must be a string")
        if item.strip():
            result.append(item)
    return result


def _bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise NativeRuntimeProbeInputError(f"{field} must be a boolean")


def _surface(name: str, raw: Any) -> dict[str, Any]:
    if raw is None:
        return {
            "name": name,
            "status": "unknown",
            "evidence_refs": [],
            "auto_launch_requested": False,
        }
    if not isinstance(raw, dict):
        raise NativeRuntimeProbeInputError(f"surface {name!r} must be an object")
    status = raw.get("status", "unknown")
    if not isinstance(status, str) or status not in SURFACE_STATUSES:
        raise NativeRuntimeProbeInputError(f"unsupported surface status for {name}: {status!r}")
    return {
        "name": name,
        "status": status,
        "evidence_refs": _string_list(raw.get("evidence_refs"), f"{name}.evidence_refs"),
        "auto_launch_requested": _bool(
            raw.get("auto_launch_allowed", False),
            f"{name}.auto_launch_allowed",
        ),
    }


def _requested_backends(raw: Any) -> list[str]:
    if raw is None:
        return ["solo", "manual-worktree", "dynamic-workflow", "agent-team"]
    if not isinstance(raw, list):
        raise NativeRuntimeProbeInputError("requested_backends must be a list of strings")
    result: list[str] = []
    for index, backend in enumerate(raw):
        if not isinstance(backend, str) or backend not in BACKENDS:
            raise NativeRuntimeProbeInputError(
                f"unsupported requested_backends[{index}]: {backend!r}"
            )
        if backend not in result:
            result.append(backend)
    return result


def _normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    profile_id = raw.get("id", "profile")
    if not isinstance(profile_id, str) or not profile_id.strip():
        raise NativeRuntimeProbeInputError("profile id must be a non-empty string")
    raw_surfaces = raw.get("surfaces", {})
    if raw_surfaces is None:
        raw_surfaces = {}
    if not isinstance(raw_surfaces, dict):
        raise NativeRuntimeProbeInputError("surfaces must be an object")
    return {
        "id": profile_id,
        "surfaces": {
            surface_name: _surface(surface_name, raw_surfaces.get(surface_name))
            for surface_name in SURFACES
        },
        "requested_backends": _requested_backends(raw.get("requested_backends")),
    }


def _warning(
    warnings: list[dict[str, Any]],
    code: str,
    message: str,
    *,
    backend: str | None = None,
    surface: str | None = None,
) -> None:
    item: dict[str, Any] = {"code": code, "message": message}
    if backend is not None:
        item["backend"] = backend
    if surface is not None:
        item["surface"] = surface
    warnings.append(item)


def _error(
    errors: list[dict[str, Any]],
    code: str,
    message: str,
    *,
    surface: str | None = None,
) -> None:
    item: dict[str, Any] = {"code": code, "message": message}
    if surface is not None:
        item["surface"] = surface
    errors.append(item)


def _launch_plan(
    backend: str,
    surfaces: dict[str, dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    surface_name = BACKEND_SURFACE.get(backend)
    if surface_name is None:
        return {
            "backend": backend,
            "surface": None,
            "surface_status": "available",
            "mode": "current-session",
            "auto_launch_allowed": False,
            "operator_approval_required": False,
            "cleanup_required": False,
        }

    surface = surfaces[surface_name]
    status = surface["status"]
    if status in {"unknown", "unavailable"}:
        code = "capability-unconfirmed" if status == "unknown" else "capability-unavailable"
        _warning(
            warnings,
            code,
            f"{backend} surface is {status}; emitting dry-run plan only.",
            backend=backend,
            surface=surface_name,
        )

    return {
        "backend": backend,
        "surface": surface_name,
        "surface_status": status,
        "mode": "dry-run-only",
        "auto_launch_allowed": False,
        "operator_approval_required": True,
        "cleanup_required": backend in {"manual-worktree", "dynamic-workflow", "agent-team"},
        "evidence_refs": surface["evidence_refs"],
    }


def build_probe(raw_profile: dict[str, Any]) -> dict[str, Any]:
    """Build a native runtime probe report from a profile object."""
    profile = _normalize_profile(raw_profile)
    surfaces = profile["surfaces"]
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for surface in surfaces.values():
        if surface["auto_launch_requested"]:
            _error(
                errors,
                "auto_launch_not_allowed",
                "native runtime surfaces must not be auto-launched by default",
                surface=surface["name"],
            )
        if surface["status"] in {"available", "documented", "manual"} and not surface[
            "evidence_refs"
        ]:
            _warning(
                warnings,
                "missing-evidence-ref",
                "non-unknown surface should include evidence_refs",
                surface=surface["name"],
            )

    launch_plans = [
        _launch_plan(backend, surfaces, warnings)
        for backend in profile["requested_backends"]
    ]
    executable = sum(
        1
        for plan in launch_plans
        if plan["surface"] is not None and plan["surface_status"] == "available"
    )
    return {
        "schema_version": 1,
        "profile_id": profile["id"],
        "status": "fail" if errors else "pass",
        "summary": {
            "surfaces": len(surfaces),
            "requested_backends": len(profile["requested_backends"]),
            "available_native_surfaces": sum(
                1 for surface in surfaces.values() if surface["status"] == "available"
            ),
            "dry_run_plans": sum(
                1 for plan in launch_plans if plan["mode"] == "dry-run-only"
            ),
            "executable_native_plans": executable,
            "warnings": len(warnings),
            "errors": len(errors),
        },
        "surfaces": list(surfaces.values()),
        "launch_plans": launch_plans,
        "warnings": warnings,
        "errors": errors,
    }


def _expectation_failures(probe: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if not isinstance(expect, dict):
        return [{"field": "expect", "message": "expect must be an object"}]

    expected_status = expect.get("report_status")
    if expected_status is not None and probe["status"] != expected_status:
        failures.append(
            {
                "field": "report_status",
                "expected": expected_status,
                "actual": probe["status"],
            }
        )

    by_surface = {surface["name"]: surface for surface in probe["surfaces"]}
    for name, expected in expect.get("surface_statuses", {}).items():
        actual = by_surface.get(name, {}).get("status")
        if actual != expected:
            failures.append(
                {
                    "field": "surface_statuses",
                    "surface": name,
                    "expected": expected,
                    "actual": actual,
                }
            )

    by_backend = {plan["backend"]: plan for plan in probe["launch_plans"]}
    for backend, expected in expect.get("launch_plan_modes", {}).items():
        actual = by_backend.get(backend, {}).get("mode")
        if actual != expected:
            failures.append(
                {
                    "field": "launch_plan_modes",
                    "backend": backend,
                    "expected": expected,
                    "actual": actual,
                }
            )

    actual_codes = sorted(error["code"] for error in probe["errors"])
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
        probe = build_probe(fixture["profile"])
        failures = _expectation_failures(probe, fixture["expect"])
        item: dict[str, Any] = {
            "id": fixture_id,
            "path": path.as_posix(),
            "status": "pass" if not failures else "fail",
            "probe": probe,
        }
        if failures:
            item["failures"] = failures
        items.append(item)

    failed = sum(1 for item in items if item["status"] == "fail")
    return {
        "schema_version": 1,
        "status": "fail" if failed else "pass",
        "summary": {
            "fixtures": len(items),
            "passed": len(items) - failed,
            "failed": failed,
        },
        "generated_at": generated_at or _iso_now(),
        "fixtures": items,
    }


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def build_live_profile() -> dict[str, Any]:
    """Return a conservative local profile without launching Claude surfaces."""
    surfaces: dict[str, dict[str, Any]] = {
        surface: {"status": "unknown", "evidence_refs": []} for surface in SURFACES
    }

    try:
        claude = _run_command(["claude", "--version"])
    except (OSError, subprocess.TimeoutExpired):
        claude = None
    if claude is not None and claude.returncode == 0:
        evidence = [f"claude --version: {claude.stdout.strip() or claude.stderr.strip()}"]
        for surface in ("goal", "loop", "dynamic_workflow", "agent_team"):
            surfaces[surface] = {"status": "documented", "evidence_refs": evidence}

    try:
        worktree = _run_command(["git", "worktree", "list", "--porcelain"])
    except (OSError, subprocess.TimeoutExpired):
        worktree = None
    if worktree is not None and worktree.returncode == 0:
        surfaces["worktree"] = {
            "status": "manual",
            "evidence_refs": ["git worktree list --porcelain"],
        }

    return {
        "id": "local-live-profile",
        "surfaces": surfaces,
        "requested_backends": ["solo", "manual-worktree", "dynamic-workflow", "agent-team"],
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe Athanor native runtime readiness.")
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
                    "native-runtime-probe "
                    f"status={report['status']} "
                    f"fixtures={report['summary']['fixtures']} "
                    f"failed={report['summary']['failed']}"
                )
            return 0 if report["status"] == "pass" else 1

        profile = _read_json(args.profile, "native runtime profile") if args.profile else build_live_profile()
        probe = build_probe(profile)
    except (OSError, NativeRuntimeProbeInputError) as exc:
        print(f"native runtime probe: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(probe, indent=2, sort_keys=True))
    else:
        print(
            "native-runtime-probe "
            f"status={probe['status']} "
            f"dry_run_plans={probe['summary']['dry_run_plans']} "
            f"errors={probe['summary']['errors']}"
        )
    return 0 if probe["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

