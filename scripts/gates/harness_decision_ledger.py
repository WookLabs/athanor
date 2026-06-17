#!/usr/bin/env python3
"""Validate committed Athanor harness decision ledger files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER_ROOT = REPO_ROOT / "docs" / "harness-decisions"
VALID_DECISION_STATUSES = {"planned", "observed", "follow_up", "rolled_back"}
VALID_DIRECTIONS = {
    "increase",
    "decrease",
    "stay",
    "stay_or_increase",
    "stay_or_decrease",
}
REQUIRED_STRINGS = (
    "id",
    "date",
    "status",
    "change_type",
    "summary",
    "decision",
    "rollback_or_follow_up",
)


class HarnessDecisionInputError(Exception):
    """Raised when ledger inputs cannot be loaded."""


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _error(
    errors: list[dict[str, Any]],
    code: str,
    message: str,
    path: str,
    *,
    decision_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    item: dict[str, Any] = {
        "code": code,
        "message": message,
        "path": path,
    }
    if decision_id is not None:
        item["decision_id"] = decision_id
    if extra:
        item.update(extra)
    errors.append(item)


def _json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise HarnessDecisionInputError(f"ledger root is not a directory: {root}")
    return sorted(path for path in root.glob("*.json") if path.is_file())


def _load_file(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HarnessDecisionInputError(f"{path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise HarnessDecisionInputError(f"{path}: ledger root must be an object")
    return parsed


def _validate_expected_metrics(
    decision: dict[str, Any],
    *,
    path: str,
    decision_id: str,
    errors: list[dict[str, Any]],
) -> None:
    metrics = decision.get("expected_metrics")
    if not isinstance(metrics, list) or not metrics:
        _error(
            errors,
            "missing_expected_metrics",
            "decision must contain expected_metrics[]",
            path,
            decision_id=decision_id,
        )
        return
    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            _error(
                errors,
                "invalid_expected_metric",
                "expected metric entries must be objects",
                path,
                decision_id=decision_id,
                extra={"index": index},
            )
            continue
        for field in ("metric", "direction", "target"):
            if not _non_empty_string(metric.get(field)):
                _error(
                    errors,
                    "blank_expected_metric_field",
                    f"expected metric field {field!r} must be non-empty",
                    path,
                    decision_id=decision_id,
                    extra={"index": index, "field": field},
                )
        direction = metric.get("direction")
        if _non_empty_string(direction) and direction not in VALID_DIRECTIONS:
            _error(
                errors,
                "invalid_metric_direction",
                f"metric direction must be one of {sorted(VALID_DIRECTIONS)}",
                path,
                decision_id=decision_id,
                extra={"index": index, "direction": direction},
            )


def _validate_verification_commands(
    decision: dict[str, Any],
    *,
    path: str,
    decision_id: str,
    errors: list[dict[str, Any]],
) -> None:
    commands = decision.get("verification_commands")
    if not isinstance(commands, list) or not commands:
        _error(
            errors,
            "missing_verification_commands",
            "decision must contain verification_commands[]",
            path,
            decision_id=decision_id,
        )
        return
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            _error(
                errors,
                "invalid_verification_command",
                "verification command entries must be objects",
                path,
                decision_id=decision_id,
                extra={"index": index},
            )
            continue
        if not _non_empty_string(command.get("command")):
            _error(
                errors,
                "blank_verification_command",
                "verification command must be non-empty",
                path,
                decision_id=decision_id,
                extra={"index": index},
            )
        if not _non_empty_string(command.get("expected")):
            _error(
                errors,
                "blank_verification_expected",
                "verification expected result must be non-empty",
                path,
                decision_id=decision_id,
                extra={"index": index},
            )


def _validate_observed_results(
    decision: dict[str, Any],
    *,
    path: str,
    decision_id: str,
    errors: list[dict[str, Any]],
) -> None:
    observed_results = decision.get("observed_results")
    if decision.get("status") == "observed" and (
        not isinstance(observed_results, list) or not observed_results
    ):
        _error(
            errors,
            "missing_observed_results",
            "observed decisions must contain observed_results[]",
            path,
            decision_id=decision_id,
        )
        return
    if observed_results is None:
        return
    if not isinstance(observed_results, list):
        _error(
            errors,
            "invalid_observed_results",
            "observed_results must be a list",
            path,
            decision_id=decision_id,
        )
        return
    for index, result in enumerate(observed_results):
        if not isinstance(result, dict):
            _error(
                errors,
                "invalid_observed_result",
                "observed result entries must be objects",
                path,
                decision_id=decision_id,
                extra={"index": index},
            )
            continue
        for field in ("status", "summary"):
            if not _non_empty_string(result.get(field)):
                _error(
                    errors,
                    "blank_observed_result_field",
                    f"observed result field {field!r} must be non-empty",
                    path,
                    decision_id=decision_id,
                    extra={"index": index, "field": field},
                )
        refs = result.get("evidence_refs")
        if not isinstance(refs, list) or not any(_non_empty_string(item) for item in refs):
            _error(
                errors,
                "missing_evidence_refs",
                "observed results must include evidence_refs[]",
                path,
                decision_id=decision_id,
                extra={"index": index},
            )


def _validate_decision(
    decision: dict[str, Any],
    *,
    path: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_id = decision.get("id")
    decision_id = raw_id.strip() if isinstance(raw_id, str) and raw_id.strip() else "<missing-id>"
    for field in REQUIRED_STRINGS:
        if not _non_empty_string(decision.get(field)):
            _error(
                errors,
                "blank_required_field",
                f"required field {field!r} must be non-empty",
                path,
                decision_id=decision_id,
                extra={"field": field},
            )
    status = decision.get("status")
    if _non_empty_string(status) and status not in VALID_DECISION_STATUSES:
        _error(
            errors,
            "invalid_decision_status",
            f"decision status must be one of {sorted(VALID_DECISION_STATUSES)}",
            path,
            decision_id=decision_id,
            extra={"status": status},
        )
    _validate_expected_metrics(decision, path=path, decision_id=decision_id, errors=errors)
    _validate_verification_commands(decision, path=path, decision_id=decision_id, errors=errors)
    _validate_observed_results(decision, path=path, decision_id=decision_id, errors=errors)
    return {
        "id": decision_id,
        "path": path,
        "date": str(decision.get("date", "")),
        "status": str(decision.get("status", "")),
        "change_type": str(decision.get("change_type", "")),
    }


def build_report(ledger_root: Path, *, allow_empty: bool = False) -> dict[str, Any]:
    files = _json_files(ledger_root)
    decisions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: dict[str, str] = {}

    for path in files:
        rel_path = _rel(ledger_root, path)
        parsed = _load_file(path)
        if parsed.get("schema_version") != 1:
            _error(
                errors,
                "invalid_schema_version",
                "ledger file schema_version must be 1",
                rel_path,
            )
            continue
        raw_decisions = parsed.get("decisions")
        if not isinstance(raw_decisions, list):
            _error(errors, "invalid_decisions", "ledger file must contain decisions[]", rel_path)
            continue
        for raw in raw_decisions:
            if not isinstance(raw, dict):
                _error(errors, "invalid_decision", "decision entries must be objects", rel_path)
                continue
            summary = _validate_decision(raw, path=rel_path, errors=errors)
            decision_id = summary["id"]
            if decision_id in seen:
                _error(
                    errors,
                    "duplicate_id",
                    "decision ids must be unique across ledger files",
                    rel_path,
                    decision_id=decision_id,
                    extra={"first_path": seen[decision_id]},
                )
            else:
                seen[decision_id] = rel_path
            decisions.append(summary)

    if not decisions and not allow_empty:
        _error(
            errors,
            "empty_ledger",
            "ledger must contain at least one decision unless --allow-empty is set",
            str(ledger_root),
        )

    return {
        "schema_version": 1,
        "status": "fail" if errors else "pass",
        "ledger_root": str(ledger_root),
        "summary": {
            "files": len(files),
            "decisions": len(decisions),
            "errors": len(errors),
        },
        "decisions": decisions,
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Athanor harness decision ledgers.")
    parser.add_argument("--ledger-root", type=Path, default=DEFAULT_LEDGER_ROOT)
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = build_report(args.ledger_root, allow_empty=args.allow_empty)
    except (OSError, json.JSONDecodeError, HarnessDecisionInputError) as exc:
        print(f"harness decision ledger: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"{report['status']}: decisions={report['summary']['decisions']} "
            f"errors={report['summary']['errors']}"
        )
        for error in report["errors"]:
            decision = f" ({error['decision_id']})" if "decision_id" in error else ""
            print(f"  - {error['code']}{decision}: {error['message']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
