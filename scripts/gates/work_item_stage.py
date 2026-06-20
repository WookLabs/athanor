#!/usr/bin/env python3
"""Validate file-local work-item stage transitions and audit logs."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "work_items" / "valid"

STAGES = ("queued", "work", "review", "done", "blocked")
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"work", "blocked"},
    "work": {"review", "blocked"},
    "review": {"done", "work", "blocked"},
    "blocked": {"work"},
    "done": set(),
}
APPROVAL_STATES = {"not_required", "requested", "approved", "denied"}
INTERVENTION_STATES = {"none", "proceed", "deny", "guide", "interrupt", "transform"}


class WorkItemStageInputError(Exception):
    """Raised when work-item stage inputs are malformed."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _profile() -> dict[str, Any]:
    return {
        "id": "work-item-stage-transition",
        "description": "Read-only validator for file-local work-item stage transitions and append-only audit logs.",
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "auto_runtime_launch": False,
        "irreversible_actions": 0,
    }


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise WorkItemStageInputError(f"missing JSON input: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkItemStageInputError(f"{path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise WorkItemStageInputError(f"{path}: JSON root must be an object")
    return parsed


def _load_items(path: Path) -> dict[str, dict[str, Any]]:
    data = _load_json(path)
    if data.get("schema_version") != 1:
        raise WorkItemStageInputError("work-items.json schema_version must be 1")
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise WorkItemStageInputError("work-items.json must contain items[]")
    items: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise WorkItemStageInputError(f"work item at index {index} must be an object")
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            raise WorkItemStageInputError(f"work item at index {index} is missing id")
        if item_id in items:
            raise WorkItemStageInputError(f"duplicate work item id: {item_id}")
        items[item_id] = item
    return items


def _load_transitions(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise WorkItemStageInputError(f"missing JSONL input: {path}")
    records: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkItemStageInputError(f"{path}:{index}: invalid JSON: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise WorkItemStageInputError(f"{path}:{index}: JSONL records must be objects")
        parsed["_line"] = index
        records.append(parsed)
    return records


def _error(
    errors: list[dict[str, Any]],
    code: str,
    message: str,
    *,
    path: str,
    work_item_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    item: dict[str, Any] = {"code": code, "message": message, "path": path}
    if work_item_id is not None:
        item["work_item_id"] = work_item_id
    if extra:
        item.update(extra)
    errors.append(item)


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    message: str,
    *,
    expected: Any = None,
    actual: Any = None,
) -> None:
    item: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if expected is not None:
        item["expected"] = expected
    if actual is not None:
        item["actual"] = actual
    checks.append(item)


def _safe_rel(ref: Any, *, fixture_root: Path) -> tuple[str, bool]:
    if not _non_empty_string(ref):
        return "", False
    ref_text = str(ref).strip()
    path = Path(ref_text)
    if path.is_absolute() or ".." in path.parts:
        return ref_text, False
    return ref_text, (fixture_root / ref_text).is_file()


def _validate_item_shape(
    item: dict[str, Any],
    *,
    item_id: str,
    fixture_root: Path,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    for field in ("id", "title", "owner", "stage", "approval_state", "intervention_state", "created_at", "updated_at"):
        if not _non_empty_string(item.get(field)):
            _error(
                errors,
                "blank_required_field",
                f"work item field {field!r} must be non-empty",
                path="work-items.json",
                work_item_id=item_id,
                extra={"field": field},
            )
    stage = str(item.get("stage", "")).strip()
    if stage not in STAGES:
        _error(
            errors,
            "invalid_stage",
            f"work item stage must be one of {list(STAGES)}",
            path="work-items.json",
            work_item_id=item_id,
            extra={"stage": stage},
        )
    approval_state = str(item.get("approval_state", "")).strip()
    if approval_state not in APPROVAL_STATES:
        _error(
            errors,
            "invalid_approval_state",
            f"approval_state must be one of {sorted(APPROVAL_STATES)}",
            path="work-items.json",
            work_item_id=item_id,
            extra={"approval_state": approval_state},
        )
    intervention_state = str(item.get("intervention_state", "")).strip()
    if intervention_state not in INTERVENTION_STATES:
        _error(
            errors,
            "invalid_intervention_state",
            f"intervention_state must be one of {sorted(INTERVENTION_STATES)}",
            path="work-items.json",
            work_item_id=item_id,
            extra={"intervention_state": intervention_state},
        )

    evidence_reports: list[dict[str, Any]] = []
    required_evidence = item.get("required_evidence")
    if not isinstance(required_evidence, list):
        _error(
            errors,
            "invalid_required_evidence",
            "required_evidence must be a list",
            path="work-items.json",
            work_item_id=item_id,
        )
        required_evidence = []
    for ref in required_evidence:
        ref_text, exists = _safe_rel(ref, fixture_root=fixture_root)
        evidence_reports.append({"path": ref_text, "exists": exists, "status": "pass" if exists else "fail"})
        if not exists:
            _error(
                errors,
                "missing_required_evidence",
                "required evidence path must resolve inside the fixture root",
                path="work-items.json",
                work_item_id=item_id,
                extra={"ref": ref_text},
            )

    dependencies = item.get("dependencies")
    if not isinstance(dependencies, list):
        _error(
            errors,
            "invalid_dependencies",
            "dependencies must be a list",
            path="work-items.json",
            work_item_id=item_id,
        )
        dependencies = []

    return {
        "id": item_id,
        "title": str(item.get("title", "")),
        "owner": str(item.get("owner", "")),
        "stage": stage,
        "dependencies": dependencies,
        "dependency_status": "unknown",
        "required_evidence": evidence_reports,
        "evidence_status": "pass" if all(report["exists"] for report in evidence_reports) else "fail",
        "approval_state": approval_state,
        "intervention_state": intervention_state,
        "created_at": str(item.get("created_at", "")),
        "updated_at": str(item.get("updated_at", "")),
    }


def _validate_dependencies(
    reports: dict[str, dict[str, Any]],
    raw_items: dict[str, dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    for item_id, report in reports.items():
        deps = report["dependencies"]
        dep_reports: list[dict[str, Any]] = []
        for dep_id in deps:
            dep_text = str(dep_id).strip()
            dep = raw_items.get(dep_text)
            if dep is None:
                _error(
                    errors,
                    "unknown_dependency",
                    "dependency id must exist in work-items.json",
                    path="work-items.json",
                    work_item_id=item_id,
                    extra={"dependency": dep_text},
                )
                dep_reports.append({"id": dep_text, "stage": "", "status": "fail"})
                continue
            dep_stage = str(dep.get("stage", "")).strip()
            if dep_stage != "done":
                _error(
                    errors,
                    "dependency_not_done",
                    "dependency must be in done stage before dependent work advances",
                    path="work-items.json",
                    work_item_id=item_id,
                    extra={"dependency": dep_text, "dependency_stage": dep_stage},
                )
            dep_reports.append(
                {
                    "id": dep_text,
                    "stage": dep_stage,
                    "status": "pass" if dep_stage == "done" else "fail",
                }
            )
        report["dependencies"] = dep_reports
        report["dependency_status"] = "pass" if all(dep["status"] == "pass" for dep in dep_reports) else "fail"


def _validate_transition(
    transition: dict[str, Any],
    *,
    expected_sequence: int,
    states: dict[str, str],
    fixture_root: Path,
    raw_items: dict[str, dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    line = int(transition.get("_line", expected_sequence))
    path = f"transitions.jsonl:{line}"
    work_item_id = str(transition.get("work_item_id", "")).strip()
    from_stage = str(transition.get("from_stage", "")).strip()
    to_stage = str(transition.get("to_stage", "")).strip()
    actor = str(transition.get("actor", "")).strip()
    decision = str(transition.get("decision", "")).strip()
    reason = str(transition.get("reason", "")).strip()
    approval_state = str(transition.get("approval_state", "")).strip()
    intervention_state = str(transition.get("intervention_state", "")).strip()
    sequence = transition.get("sequence")

    if sequence != expected_sequence:
        _error(
            errors,
            "audit_sequence_gap",
            "transition audit sequence must be gap-free and monotonic",
            path=path,
            work_item_id=work_item_id or None,
            extra={"expected": expected_sequence, "actual": sequence},
        )
    if transition.get("schema_version") != 1:
        _error(errors, "invalid_schema_version", "transition schema_version must be 1", path=path, work_item_id=work_item_id)
    if work_item_id not in raw_items:
        _error(errors, "unknown_work_item", "transition work_item_id must exist", path=path, work_item_id=work_item_id)
    for field, value in {
        "actor": actor,
        "decision": decision,
        "reason": reason,
        "from_stage": from_stage,
        "to_stage": to_stage,
    }.items():
        if not value:
            _error(
                errors,
                "blank_transition_field",
                f"transition field {field!r} must be non-empty",
                path=path,
                work_item_id=work_item_id,
                extra={"field": field},
            )
    if from_stage not in STAGES:
        _error(errors, "invalid_stage", "from_stage must be valid", path=path, work_item_id=work_item_id, extra={"stage": from_stage})
    if to_stage not in STAGES:
        _error(errors, "invalid_stage", "to_stage must be valid", path=path, work_item_id=work_item_id, extra={"stage": to_stage})
    if to_stage not in ALLOWED_TRANSITIONS.get(from_stage, set()):
        _error(
            errors,
            "invalid_transition",
            "stage transition is not allowed",
            path=path,
            work_item_id=work_item_id,
            extra={"from_stage": from_stage, "to_stage": to_stage},
        )

    expected_from = states.get(work_item_id, "queued")
    if work_item_id in raw_items and from_stage != expected_from:
        _error(
            errors,
            "transition_from_mismatch",
            "transition from_stage must match the current reconstructed stage",
            path=path,
            work_item_id=work_item_id,
            extra={"expected": expected_from, "actual": from_stage},
        )

    if approval_state not in APPROVAL_STATES:
        _error(
            errors,
            "invalid_approval_state",
            "transition approval_state is invalid",
            path=path,
            work_item_id=work_item_id,
            extra={"approval_state": approval_state},
        )
    if intervention_state not in INTERVENTION_STATES:
        _error(
            errors,
            "invalid_intervention_state",
            "transition intervention_state is invalid",
            path=path,
            work_item_id=work_item_id,
            extra={"intervention_state": intervention_state},
        )
    if to_stage == "done" and approval_state != "approved":
        _error(
            errors,
            "approval_required",
            "review -> done requires approved approval_state",
            path=path,
            work_item_id=work_item_id,
            extra={"approval_state": approval_state},
        )
    if approval_state == "denied" and to_stage != "blocked":
        _error(
            errors,
            "approval_denied_transition",
            "denied approval cannot advance work except to blocked",
            path=path,
            work_item_id=work_item_id,
            extra={"to_stage": to_stage},
        )
    if intervention_state in {"deny", "interrupt"} and to_stage != "blocked":
        _error(
            errors,
            "intervention_blocks_transition",
            "deny or interrupt interventions must route the item to blocked",
            path=path,
            work_item_id=work_item_id,
            extra={"intervention_state": intervention_state, "to_stage": to_stage},
        )

    evidence_refs = transition.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        evidence_refs = []
        _error(errors, "invalid_evidence_refs", "evidence_refs must be a list", path=path, work_item_id=work_item_id)
    if to_stage in {"review", "done"} and not evidence_refs:
        _error(
            errors,
            "transition_missing_evidence",
            "transitions into review or done require evidence_refs",
            path=path,
            work_item_id=work_item_id,
        )
    evidence_reports: list[dict[str, Any]] = []
    for ref in evidence_refs:
        ref_text, exists = _safe_rel(ref, fixture_root=fixture_root)
        evidence_reports.append({"path": ref_text, "exists": exists, "status": "pass" if exists else "fail"})
        if not exists:
            _error(
                errors,
                "missing_transition_evidence",
                "transition evidence_ref path must resolve inside the fixture root",
                path=path,
                work_item_id=work_item_id,
                extra={"ref": ref_text},
            )

    if work_item_id in raw_items and to_stage in STAGES:
        states[work_item_id] = to_stage

    return {
        "sequence": sequence,
        "line": line,
        "work_item_id": work_item_id,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "actor": actor,
        "decision": decision,
        "reason": reason,
        "approval_state": approval_state,
        "intervention_state": intervention_state,
        "evidence_refs": evidence_reports,
        "created_at": str(transition.get("created_at", "")),
    }


def build_report(*, fixture_root: Path) -> dict[str, Any]:
    fixture_root = fixture_root.resolve()
    raw_items = _load_items(fixture_root / "work-items.json")
    transitions_raw = _load_transitions(fixture_root / "transitions.jsonl")
    errors: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    item_reports = {
        item_id: _validate_item_shape(
            item,
            item_id=item_id,
            fixture_root=fixture_root,
            errors=errors,
        )
        for item_id, item in raw_items.items()
    }
    _validate_dependencies(item_reports, raw_items, errors)

    states = {item_id: "queued" for item_id in raw_items}
    transitions = [
        _validate_transition(
            transition,
            expected_sequence=index,
            states=states,
            fixture_root=fixture_root,
            raw_items=raw_items,
            errors=errors,
        )
        for index, transition in enumerate(transitions_raw, start=1)
    ]

    for item_id, item in raw_items.items():
        expected_stage = str(item.get("stage", "")).strip()
        actual_stage = states.get(item_id, "queued")
        if expected_stage != actual_stage:
            _error(
                errors,
                "current_stage_mismatch",
                "work item stage must match the final stage reconstructed from transition audit",
                path="work-items.json",
                work_item_id=item_id,
                extra={"expected": expected_stage, "actual": actual_stage},
            )

    _check(
        checks,
        "work_item_stage.inputs_present",
        "pass",
        "work item and transition audit inputs were loaded",
        actual={"items": len(raw_items), "transitions": len(transitions_raw)},
    )
    _check(
        checks,
        "work_item_stage.transitions_valid",
        "pass" if not errors else "fail",
        "work item transitions satisfy allowed stage, evidence, dependency, approval, and intervention contracts",
        actual=len(errors),
    )
    _check(
        checks,
        "work_item_stage.read_only",
        "pass",
        "work item stage gate is read-only",
        expected={"mutates_files_by_default": False, "irreversible_actions": 0},
        actual={"mutates_files_by_default": False, "irreversible_actions": 0},
    )

    status = "fail" if errors else "pass"
    return {
        "schema_version": 1,
        "status": status,
        "generated_at": _iso_now(),
        "profile": _profile(),
        "summary": {
            "checks": len(checks),
            "errors": len(errors),
            "warnings": 0,
            "items": len(raw_items),
            "transitions": len(transitions),
            "irreversible_actions": 0,
        },
        "source": {
            "fixture_root": str(fixture_root),
            "work_items": str(fixture_root / "work-items.json"),
            "transitions": str(fixture_root / "transitions.jsonl"),
        },
        "allowed_transitions": {stage: sorted(targets) for stage, targets in ALLOWED_TRANSITIONS.items()},
        "approval_states": sorted(APPROVAL_STATES),
        "intervention_states": sorted(INTERVENTION_STATES),
        "work_items": list(item_reports.values()),
        "transitions": transitions,
        "checks": checks,
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor work-item stage transition checks.")
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = build_report(fixture_root=args.fixture_root)
    except (OSError, json.JSONDecodeError, WorkItemStageInputError) as exc:
        print(f"work item stage: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "work-item-stage "
            f"status={report['status']} "
            f"items={report['summary']['items']} "
            f"transitions={report['summary']['transitions']} "
            f"errors={report['summary']['errors']}"
        )
        for check in report["checks"]:
            print(f"- {check['id']}: {check['status']}")
        for error in report["errors"]:
            print(f"  - {error['code']}: {error['message']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
