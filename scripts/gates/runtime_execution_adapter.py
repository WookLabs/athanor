#!/usr/bin/env python3
"""Read-only runtime execution backend recommendation gate for Athanor."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKENDS = {
    "solo",
    "subagent-wave",
    "dynamic-workflow",
    "agent-team",
    "manual-worktree",
}
ISOLATION = {"current-checkout", "worktree-recommended", "worktree-required"}
RISK = {"low", "medium", "high"}
CAPABILITY = {"available", "unavailable", "unknown"}
WORKTREE_CAPABILITY = {"available", "unavailable", "manual", "unknown"}

DEFAULT_CAPABILITIES = {
    "subagent_wave": "available",
    "dynamic_workflow": "unknown",
    "agent_team": "unknown",
    "worktree": "manual",
}


class AdapterInputError(Exception):
    """Raised when an adapter request or fixture is invalid."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterInputError(f"{label} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterInputError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AdapterInputError(f"{label} must be a JSON object")
    return data


def _bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise AdapterInputError(f"{field} must be a boolean")


def _int(value: Any, field: str) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    raise AdapterInputError(f"{field} must be a non-negative integer")


def _enum(value: Any, field: str, allowed: set[str]) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    raise AdapterInputError(f"unsupported {field}: {value!r}")


def _capabilities(raw: Any) -> dict[str, str]:
    result = dict(DEFAULT_CAPABILITIES)
    if raw is None:
        return result
    if not isinstance(raw, dict):
        raise AdapterInputError("capabilities must be an object")
    for key, value in raw.items():
        if key not in DEFAULT_CAPABILITIES:
            raise AdapterInputError(f"unsupported capability: {key}")
        allowed = WORKTREE_CAPABILITY if key == "worktree" else CAPABILITY
        result[key] = _enum(value, key, allowed)
    return result


def _normalize_request(raw: dict[str, Any]) -> dict[str, Any]:
    task = raw.get("task", "")
    if not isinstance(task, str) or not task.strip():
        raise AdapterInputError("task must be a non-empty string")
    request_id = raw.get("id", "request")
    if not isinstance(request_id, str) or not request_id.strip():
        raise AdapterInputError("id must be a non-empty string when provided")
    return {
        "id": request_id,
        "task": task,
        "risk": _enum(raw.get("risk", "medium"), "risk", RISK),
        "estimated_files": _int(raw.get("estimated_files", 0), "estimated_files"),
        "parallel_workers": _int(raw.get("parallel_workers", 0), "parallel_workers"),
        "same_file_risk": _enum(raw.get("same_file_risk", "low"), "same_file_risk", RISK),
        "long_running": _bool(raw.get("long_running", False), "long_running"),
        "requires_isolation": _bool(
            raw.get("requires_isolation", False), "requires_isolation"
        ),
        "requires_peer_coordination": _bool(
            raw.get("requires_peer_coordination", False),
            "requires_peer_coordination",
        ),
        "requires_rerunnable_script": _bool(
            raw.get("requires_rerunnable_script", False),
            "requires_rerunnable_script",
        ),
        "requires_human_review": _bool(
            raw.get("requires_human_review", False), "requires_human_review"
        ),
        "capabilities": _capabilities(raw.get("capabilities")),
    }


def _reason(items: list[dict[str, str]], reason_id: str, message: str) -> None:
    items.append({"id": reason_id, "message": message})


def _warning(items: list[dict[str, str]], warning_id: str, message: str) -> None:
    items.append({"id": warning_id, "message": message})


def _dynamic_shape(request: dict[str, Any]) -> bool:
    return (
        request["parallel_workers"] >= 4
        or request["estimated_files"] >= 20
        or request["long_running"]
        or request["requires_rerunnable_script"]
    )


def _isolation(request: dict[str, Any]) -> str:
    if request["requires_isolation"] or request["same_file_risk"] == "high":
        return "worktree-required"
    if request["risk"] == "high" or request["same_file_risk"] == "medium":
        return "worktree-recommended"
    return "current-checkout"


def _base_result(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "request_id": request["id"],
        "recommended_backend": "solo",
        "isolation": _isolation(request),
        "risk_level": request["risk"],
        "confidence": "medium",
        "reasons": [],
        "warnings": [],
        "required_capabilities": [],
        "blocked_capabilities": [],
        "notes": [],
    }


def recommend_backend(raw_request: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic runtime backend recommendation for task shape."""
    request = _normalize_request(raw_request)
    caps = request["capabilities"]
    result = _base_result(request)
    reasons = result["reasons"]
    warnings = result["warnings"]
    required = result["required_capabilities"]
    blocked = result["blocked_capabilities"]

    if request["estimated_files"] <= 2 and request["parallel_workers"] <= 1:
        _reason(reasons, "small-task", "Task is small enough for one focused session.")
    if request["same_file_risk"] == "low":
        _reason(reasons, "low-conflict", "Same-file conflict risk is low.")
    if request["requires_isolation"] or request["same_file_risk"] == "high":
        _reason(
            reasons,
            "isolation-required",
            "Task shape requires isolated filesystem changes.",
        )
    if request["same_file_risk"] == "high":
        _reason(
            reasons,
            "same-file-conflict",
            "High same-file risk should not be handled by generic parallel workers.",
        )

    if (
        result["isolation"] == "worktree-required"
        and caps["worktree"] in {"manual", "unknown", "unavailable"}
    ):
        result["recommended_backend"] = "manual-worktree"
        result["confidence"] = "high" if caps["worktree"] == "manual" else "medium"
        if caps["worktree"] == "unavailable":
            _warning(
                warnings,
                "worktree-unavailable",
                "Worktree isolation is required but unavailable.",
            )
            blocked.append("worktree")
        return result

    if request["requires_peer_coordination"]:
        _reason(
            reasons,
            "peer-coordination",
            "Workers need peer coordination, not only summarized reports.",
        )
        if caps["agent_team"] == "available":
            result["recommended_backend"] = "agent-team"
            result["confidence"] = "high"
            required.append("agent_team")
            return result
        result["recommended_backend"] = (
            "subagent-wave" if caps["subagent_wave"] == "available" else "solo"
        )
        result["fallback_backend"] = "agent-team"
        result["confidence"] = "medium"
        _warning(
            warnings,
            "agent-team-unknown",
            "Agent team capability is not confirmed; using a conservative fallback.",
        )
        blocked.append("agent_team")
        return result

    if _dynamic_shape(request):
        if request["parallel_workers"] >= 4:
            _reason(
                reasons,
                "large-fanout",
                "Task shape needs more fanout than a small worker wave.",
            )
        if request["requires_rerunnable_script"]:
            _reason(reasons, "rerunnable-script", "Task asks for reusable orchestration.")
        if caps["dynamic_workflow"] == "available":
            result["recommended_backend"] = "dynamic-workflow"
            result["confidence"] = "high"
            required.append("dynamic_workflow")
            return result
        result["recommended_backend"] = (
            "subagent-wave" if caps["subagent_wave"] == "available" else "solo"
        )
        result["fallback_backend"] = "dynamic-workflow"
        result["confidence"] = "medium"
        _warning(
            warnings,
            "dynamic-workflow-unknown",
            "Dynamic workflow capability is not confirmed; using a conservative fallback.",
        )
        blocked.append("dynamic_workflow")
        return result

    if request["parallel_workers"] >= 2:
        _reason(
            reasons,
            "bounded-parallelism",
            "Task can be split into a bounded worker wave.",
        )
        if caps["subagent_wave"] == "available":
            result["recommended_backend"] = "subagent-wave"
            result["confidence"] = "high"
            required.append("subagent_wave")
            return result
        _warning(
            warnings,
            "subagent-wave-unavailable",
            "Subagent wave capability is unavailable; using solo execution.",
        )
        blocked.append("subagent_wave")

    result["recommended_backend"] = "solo"
    result["confidence"] = "high" if result["isolation"] == "current-checkout" else "medium"
    return result


def _expectation_failures(
    recommendation: dict[str, Any], expect: dict[str, Any]
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    reason_ids = {item["id"] for item in recommendation["reasons"]}
    warning_ids = {item["id"] for item in recommendation["warnings"]}
    for key in ("recommended_backend", "fallback_backend", "isolation"):
        if key in expect and recommendation.get(key) != expect[key]:
            failures.append(
                {
                    "field": key,
                    "expected": expect[key],
                    "actual": recommendation.get(key),
                }
            )
    for key in ("required_capabilities", "blocked_capabilities"):
        if key in expect and sorted(recommendation.get(key, [])) != sorted(expect[key]):
            failures.append(
                {
                    "field": key,
                    "expected": sorted(expect[key]),
                    "actual": sorted(recommendation.get(key, [])),
                }
            )
    for key, values, actual in (
        ("reason_ids", expect.get("reason_ids", []), reason_ids),
        ("warning_ids", expect.get("warning_ids", []), warning_ids),
    ):
        missing = [value for value in values if value not in actual]
        if missing:
            failures.append({"field": key, "missing": missing, "actual": sorted(actual)})
    return failures


def evaluate_fixture_root(
    fixture_root: Path, generated_at: str | None = None
) -> dict[str, Any]:
    files = sorted(fixture_root.glob("*.json"))
    if not files:
        raise AdapterInputError(f"no runtime execution fixtures found: {fixture_root}")
    items: list[dict[str, Any]] = []
    for path in files:
        fixture = _read_json(path, "runtime execution fixture")
        if "request" not in fixture or "expect" not in fixture:
            raise AdapterInputError(f"fixture must contain request and expect: {path}")
        fixture_id = str(fixture.get("id", path.stem))
        recommendation = recommend_backend(fixture["request"])
        failures = _expectation_failures(recommendation, fixture["expect"])
        item = {
            "id": fixture_id,
            "path": path.as_posix(),
            "status": "pass" if not failures else "fail",
            "recommendation": recommendation,
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


def _request_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "id": args.id,
        "task": args.task,
        "risk": args.risk,
        "estimated_files": args.estimated_files,
        "parallel_workers": args.parallel_workers,
        "same_file_risk": args.same_file_risk,
        "long_running": args.long_running,
        "requires_isolation": args.requires_isolation,
        "requires_peer_coordination": args.requires_peer_coordination,
        "requires_rerunnable_script": args.requires_rerunnable_script,
        "requires_human_review": args.requires_human_review,
        "capabilities": {
            "subagent_wave": args.subagent_wave,
            "dynamic_workflow": args.dynamic_workflow,
            "agent_team": args.agent_team,
            "worktree": args.worktree,
        },
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recommend an Athanor runtime execution backend."
    )
    parser.add_argument("--fixture-root", type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--id", default="request")
    parser.add_argument("--task", default="Ad hoc Athanor task")
    parser.add_argument("--risk", default="medium")
    parser.add_argument("--estimated-files", type=int, default=0)
    parser.add_argument("--parallel-workers", type=int, default=0)
    parser.add_argument("--same-file-risk", default="low")
    parser.add_argument("--long-running", action="store_true")
    parser.add_argument("--requires-isolation", action="store_true")
    parser.add_argument("--requires-peer-coordination", action="store_true")
    parser.add_argument("--requires-rerunnable-script", action="store_true")
    parser.add_argument("--requires-human-review", action="store_true")
    parser.add_argument("--subagent-wave", default="available")
    parser.add_argument("--dynamic-workflow", default="unknown")
    parser.add_argument("--agent-team", default="unknown")
    parser.add_argument("--worktree", default="manual")
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
                    "runtime-adapter "
                    f"status={report['status']} "
                    f"fixtures={report['summary']['fixtures']} "
                    f"failed={report['summary']['failed']}"
                )
            return 0 if report["status"] == "pass" else 1

        request = (
            _read_json(args.request, "runtime adapter request")
            if args.request
            else _request_from_args(args)
        )
        recommendation = recommend_backend(request)
    except AdapterInputError as exc:
        print(f"runtime execution adapter: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(recommendation, indent=2, sort_keys=True))
    else:
        print(
            "runtime-adapter "
            f"backend={recommendation['recommended_backend']} "
            f"isolation={recommendation['isolation']} "
            f"confidence={recommendation['confidence']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
