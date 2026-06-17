#!/usr/bin/env python3
"""Local-only reactive channel fixture mapper for Athanor."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReactiveChannelInputError(Exception):
    """Raised when a reactive channel fixture cannot be evaluated."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ReactiveChannelInputError(f"{label} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReactiveChannelInputError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ReactiveChannelInputError(f"{label} must be a JSON object")
    return data


def _object(value: Any, field: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise ReactiveChannelInputError(f"{field} must be an object")


def _string(value: Any, field: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ReactiveChannelInputError(f"{field} must be a non-empty string")


def _int(value: Any, field: str) -> int:
    if isinstance(value, int) and value > 0:
        return value
    raise ReactiveChannelInputError(f"{field} must be a positive integer")


def _repository(payload: dict[str, Any]) -> str:
    raw_repository = payload.get("repository")
    if not isinstance(raw_repository, dict):
        raise ReactiveChannelInputError("repository.full_name must be present")
    repository = raw_repository
    return _string(repository.get("full_name"), "repository.full_name")


def _first_pr_number(workflow_run: dict[str, Any]) -> int:
    pull_requests = workflow_run.get("pull_requests")
    if not isinstance(pull_requests, list) or not pull_requests:
        raise ReactiveChannelInputError("workflow_run.pull_requests must include a PR")
    first = _object(pull_requests[0], "workflow_run.pull_requests[0]")
    return _int(first.get("number"), "workflow_run.pull_requests[0].number")


def _listener() -> dict[str, Any]:
    return {
        "default_enabled": False,
        "registered": False,
        "mode": "fixture-only",
    }


def _safety(actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "local_only_fixture": True,
        "auto_listeners": 0,
        "auto_execute_actions": sum(1 for action in actions if action["auto_execute"]),
        "external_network_default": False,
        "external_telemetry": False,
        "irreversible_actions": 0,
    }


def _action(
    *,
    action_id: str,
    kind: str,
    title: str,
    requires_operator_approval: bool,
    command_templates: list[str],
    evidence_required: list[str],
) -> dict[str, Any]:
    return {
        "id": action_id,
        "kind": kind,
        "title": title,
        "requires_operator_approval": requires_operator_approval,
        "auto_execute": False,
        "listener_registered": False,
        "external_network_default": False,
        "external_telemetry": False,
        "irreversible_actions": 0,
        "command_templates": command_templates,
        "evidence_required": evidence_required,
    }


def _ci_failure_action(pr_number: int, conclusion: str, run_url: str) -> dict[str, Any]:
    return _action(
        action_id="dispatch-ci-watcher",
        kind="ci-watch",
        title=f"Dispatch CI watcher for PR #{pr_number}",
        requires_operator_approval=True,
        command_templates=[
            f"@athanor-ci-watcher pr_number={pr_number} max_iterations=3",
            f"gh pr checks {pr_number} --watch",
        ],
        evidence_required=[
            f"Record CI workflow run conclusion: {conclusion}.",
            f"Attach CI run URL before any fix: {run_url}",
            "Capture `gh pr checks` output before dispatching fixes.",
        ],
    )


def _ci_pass_action(pr_number: int, conclusion: str, run_url: str) -> dict[str, Any]:
    return _action(
        action_id="record-ci-pass",
        kind="status-record",
        title=f"Record CI pass for PR #{pr_number}",
        requires_operator_approval=False,
        command_templates=[],
        evidence_required=[
            f"Record workflow run conclusion `{conclusion}` for PR #{pr_number}.",
            f"Keep run URL as evidence: {run_url}",
        ],
    )


def _review_response_action(pr_number: int, review_url: str) -> dict[str, Any]:
    return _action(
        action_id="plan-review-response",
        kind="review-response",
        title=f"Plan review response for PR #{pr_number}",
        requires_operator_approval=True,
        command_templates=[
            f"gh pr view {pr_number} --comments",
            f"/athanor:review PR #{pr_number} review comments and changed files",
        ],
        evidence_required=[
            f"Record review URL before edits: {review_url}",
            "Capture each requested change and the planned response.",
            "Run focused tests before marking review feedback addressed.",
        ],
    )


def _record_review_action(pr_number: int, review_url: str) -> dict[str, Any]:
    return _action(
        action_id="record-review-pass",
        kind="status-record",
        title=f"Record review pass for PR #{pr_number}",
        requires_operator_approval=False,
        command_templates=[],
        evidence_required=[
            f"Record approving review for PR #{pr_number}: {review_url}",
        ],
    )


def _workflow_plan(fixture: dict[str, Any]) -> dict[str, Any]:
    payload = _object(fixture.get("payload"), "payload")
    action = _string(payload.get("action"), "payload.action")
    if action != "completed":
        raise ReactiveChannelInputError("workflow_run payload.action must be completed")
    repository = _repository(payload)
    workflow_run = _object(payload.get("workflow_run"), "workflow_run")
    conclusion = _string(workflow_run.get("conclusion"), "workflow_run.conclusion").lower()
    run_url = _string(workflow_run.get("html_url"), "workflow_run.html_url")
    pr_number = _first_pr_number(workflow_run)
    failure_conclusions = {"failure", "timed_out", "cancelled", "startup_failure"}
    if conclusion in failure_conclusions:
        normalized_type = "ci.failed"
        actions = [_ci_failure_action(pr_number, conclusion, run_url)]
    elif conclusion == "success":
        normalized_type = "ci.passed"
        actions = [_ci_pass_action(pr_number, conclusion, run_url)]
    else:
        normalized_type = "ci.neutral"
        actions = [
            _action(
                action_id="record-ci-neutral",
                kind="status-record",
                title=f"Record neutral CI result for PR #{pr_number}",
                requires_operator_approval=False,
                command_templates=[],
                evidence_required=[
                    f"Record workflow run conclusion `{conclusion}` for PR #{pr_number}.",
                    f"Keep run URL as evidence: {run_url}",
                ],
            )
        ]
    return _plan(
        fixture=fixture,
        source="github",
        event_type="workflow_run.completed",
        normalized_type=normalized_type,
        repository=repository,
        pr_number=pr_number,
        actions=actions,
    )


def _review_plan(fixture: dict[str, Any]) -> dict[str, Any]:
    payload = _object(fixture.get("payload"), "payload")
    action = _string(payload.get("action"), "payload.action")
    if action != "submitted":
        raise ReactiveChannelInputError("pull_request_review payload.action must be submitted")
    repository = _repository(payload)
    pull_request = _object(payload.get("pull_request"), "pull_request")
    pr_number = _int(pull_request.get("number"), "pull_request.number")
    review = _object(payload.get("review"), "review")
    review_state = _string(review.get("state"), "review.state").lower()
    review_url = _string(review.get("html_url"), "review.html_url")
    if review_state == "changes_requested":
        normalized_type = "review.changes_requested"
        actions = [_review_response_action(pr_number, review_url)]
    elif review_state == "approved":
        normalized_type = "review.approved"
        actions = [_record_review_action(pr_number, review_url)]
    else:
        normalized_type = f"review.{review_state}"
        actions = [_record_review_action(pr_number, review_url)]
    return _plan(
        fixture=fixture,
        source="github",
        event_type="pull_request_review.submitted",
        normalized_type=normalized_type,
        repository=repository,
        pr_number=pr_number,
        actions=actions,
    )


def _plan(
    *,
    fixture: dict[str, Any],
    source: str,
    event_type: str,
    normalized_type: str,
    repository: str,
    pr_number: int,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "fixture_id": _string(fixture.get("id", "fixture"), "id"),
        "event": {
            "source": source,
            "channel": _string(fixture.get("channel"), "channel"),
            "event_type": event_type,
            "normalized_type": normalized_type,
            "delivery_id": _string(fixture.get("delivery_id"), "delivery_id"),
            "repository": repository,
            "pr_number": pr_number,
        },
        "listener": _listener(),
        "actions": actions,
        "safety": _safety(actions),
        "warnings": [],
        "errors": [],
    }


def build_plan(fixture: dict[str, Any]) -> dict[str, Any]:
    """Map one local fake channel fixture to a safe reactive action plan."""
    channel = _string(fixture.get("channel"), "channel")
    event_type = _string(fixture.get("event_type"), "event_type")
    if channel == "github-actions" and event_type == "workflow_run":
        return _workflow_plan(fixture)
    if channel == "github-pr-review" and event_type == "pull_request_review":
        return _review_plan(fixture)
    raise ReactiveChannelInputError(f"unsupported channel/event_type: {channel}/{event_type}")


def _expectation_failures(plan: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if not isinstance(expect, dict):
        return [{"field": "expect", "message": "expect must be an object"}]
    event = plan["event"]
    for key in ("normalized_type", "pr_number"):
        if key in expect and event.get(key) != expect[key]:
            failures.append(
                {
                    "field": key,
                    "expected": expect[key],
                    "actual": event.get(key),
                }
            )
    actual_action_ids = [action["id"] for action in plan["actions"]]
    expected_action_ids = expect.get("action_ids", [])
    if expected_action_ids and actual_action_ids != expected_action_ids:
        failures.append(
            {
                "field": "action_ids",
                "expected": expected_action_ids,
                "actual": actual_action_ids,
            }
        )
    command_text = "\n".join(
        command for action in plan["actions"] for command in action["command_templates"]
    )
    for token in expect.get("command_tokens", []):
        if token not in command_text:
            failures.append(
                {
                    "field": "command_tokens",
                    "missing": token,
                    "actual": command_text,
                }
            )
    return failures


def evaluate_fixture_root(
    fixture_root: Path, generated_at: str | None = None
) -> dict[str, Any]:
    if not fixture_root.is_dir():
        raise ReactiveChannelInputError(f"fixture root is not a directory: {fixture_root}")
    files = sorted(path for path in fixture_root.glob("*.json") if path.is_file())
    if not files:
        raise ReactiveChannelInputError(f"no reactive channel fixtures found: {fixture_root}")
    items: list[dict[str, Any]] = []
    for path in files:
        fixture = _read_json(path, "reactive channel fixture")
        if "expect" not in fixture:
            raise ReactiveChannelInputError(f"fixture must contain expect: {path}")
        plan = build_plan(fixture)
        failures = _expectation_failures(plan, fixture["expect"])
        item: dict[str, Any] = {
            "id": _string(fixture.get("id", path.stem), "id"),
            "path": path.as_posix(),
            "status": "pass" if not failures else "fail",
            "plan": plan,
        }
        if failures:
            item["failures"] = failures
        items.append(item)
    failed = sum(1 for item in items if item["status"] == "fail")
    plans = [item["plan"] for item in items]
    return {
        "schema_version": 1,
        "status": "fail" if failed else "pass",
        "summary": {
            "fixtures": len(items),
            "passed": len(items) - failed,
            "failed": failed,
            "auto_listeners": 0,
            "auto_execute_actions": sum(
                plan["safety"]["auto_execute_actions"] for plan in plans
            ),
            "irreversible_actions": 0,
        },
        "generated_at": generated_at or _iso_now(),
        "fixtures": items,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate local-only reactive channel fixtures."
    )
    parser.add_argument("--fixture-root", type=Path)
    parser.add_argument("--fixture", type=Path)
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
                    "reactive-channel-fixture "
                    f"status={report['status']} "
                    f"fixtures={report['summary']['fixtures']} "
                    f"failed={report['summary']['failed']}"
                )
            return 0 if report["status"] == "pass" else 1
        if args.fixture:
            plan = build_plan(_read_json(args.fixture, "reactive channel fixture"))
        else:
            raise ReactiveChannelInputError("--fixture-root or --fixture is required")
    except (OSError, ReactiveChannelInputError) as exc:
        print(f"reactive channel fixture: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(
            "reactive-channel-fixture "
            f"normalized_type={plan['event']['normalized_type']} "
            f"actions={len(plan['actions'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
