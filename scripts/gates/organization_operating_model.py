#!/usr/bin/env python3
"""Validate Athanor's company-like organization operating model."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOC = Path("docs/organization-operating-model.md")
MODEL_MARKER = "<!-- athanor:organization-operating-model v=1 -->"

REQUIRED_STAGES = [
    "intake",
    "triage",
    "requirements",
    "research",
    "planning",
    "design-review",
    "execution",
    "verification",
    "release",
    "postmortem",
    "memory-update",
]

REQUIRED_OFFICES = {
    "product-intake",
    "research",
    "architecture",
    "execution",
    "qa-verification",
    "release",
    "learning-governance",
}

REQUIRED_COMMANDS = {
    "/athanor:setup",
    "/athanor:discuss",
    "/athanor:analyze",
    "/athanor:debug",
    "/athanor:plan",
    "/athanor:work",
    "/athanor:review",
    "/athanor:lfg",
    "/athanor:lfg-goal",
}

REQUIRED_PROMOTION_STATES = [
    "incident",
    "lesson",
    "candidate_policy",
    "policy",
    "gate_candidate",
    "gate",
    "retired",
]

ALLOWED_LEADER_WRITE_SCOPES = {
    "none",
    "infrastructure-only",
    "artifact-only",
}


class OrganizationModelInputError(Exception):
    """Raised when the organization model cannot be loaded."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and any(_non_empty_string(item) for item in value)


def _repo_relative(path: Path, repo_root: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None


def _error(
    errors: list[dict[str, Any]],
    code: str,
    message: str,
    path: str,
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    item = {"code": code, "message": message, "path": path}
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
    item: dict[str, Any] = {
        "id": check_id,
        "status": status,
        "message": message,
    }
    if expected is not None:
        item["expected"] = expected
    if actual is not None:
        item["actual"] = actual
    checks.append(item)


def _load_model(doc_path: Path) -> dict[str, Any]:
    if not doc_path.is_file():
        raise OrganizationModelInputError(f"organization model doc does not exist: {doc_path}")
    body = doc_path.read_text(encoding="utf-8")
    marker_index = body.find(MODEL_MARKER)
    if marker_index < 0:
        raise OrganizationModelInputError(f"{doc_path}: missing {MODEL_MARKER}")
    after_marker = body[marker_index + len(MODEL_MARKER) :]
    match = re.search(r"```json\s*(\{.*?\})\s*```", after_marker, re.DOTALL)
    if not match:
        raise OrganizationModelInputError(f"{doc_path}: missing fenced JSON model")
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise OrganizationModelInputError(f"{doc_path}: invalid JSON model: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise OrganizationModelInputError(f"{doc_path}: model must be a JSON object")
    return parsed


def _validate_safety(
    model: dict[str, Any],
    *,
    path: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    safety = model.get("safety")
    if not isinstance(safety, dict):
        _error(errors, "missing_safety", "model must contain safety object", path)
        safety = {}
    expected = {
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "auto_runtime_launch": False,
        "default_live_listener": False,
        "registered_agent_additions": 0,
        "irreversible_actions": 0,
    }
    normalized: dict[str, Any] = {}
    for key, expected_value in expected.items():
        actual = safety.get(key)
        normalized[key] = actual
        if actual != expected_value:
            _error(
                errors,
                "unsafe_default",
                f"safety field {key!r} must be {expected_value!r}",
                path,
                extra={"field": key, "actual": actual, "expected": expected_value},
            )
    return normalized


def _validate_offices(
    model: dict[str, Any],
    *,
    path: str,
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_offices = model.get("offices")
    offices: list[dict[str, Any]] = []
    if not isinstance(raw_offices, list):
        _error(errors, "invalid_offices", "model offices must be a list", path)
        return offices
    seen: set[str] = set()
    for index, office in enumerate(raw_offices):
        if not isinstance(office, dict):
            _error(
                errors,
                "invalid_office",
                "office entries must be objects",
                path,
                extra={"index": index},
            )
            continue
        office_id = str(office.get("id", "")).strip()
        if not office_id:
            _error(errors, "blank_office_id", "office id must be non-empty", path)
            continue
        if office_id in seen:
            _error(
                errors,
                "duplicate_office_id",
                "office ids must be unique",
                path,
                extra={"office_id": office_id},
            )
        seen.add(office_id)
        if not _non_empty_string(office.get("title")):
            _error(
                errors,
                "blank_office_title",
                "office title must be non-empty",
                path,
                extra={"office_id": office_id},
            )
        if not _non_empty_string_list(office.get("roles")):
            _error(
                errors,
                "missing_office_roles",
                "office roles must contain at least one non-empty role",
                path,
                extra={"office_id": office_id},
            )
        offices.append(
            {
                "id": office_id,
                "title": str(office.get("title", "")),
                "roles": office.get("roles") if isinstance(office.get("roles"), list) else [],
                "status": "pass",
            }
        )
    for office_id in sorted(REQUIRED_OFFICES - seen):
        _error(
            errors,
            "missing_office",
            "required office is missing",
            path,
            extra={"office_id": office_id},
        )
    return offices


def _validate_stages(
    model: dict[str, Any],
    *,
    offices: list[dict[str, Any]],
    path: str,
    errors: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str], set[str]]:
    raw_stages = model.get("stages")
    stages: list[dict[str, Any]] = []
    command_to_stage: dict[str, str] = {}
    unknown_commands: set[str] = set()
    office_ids = {office["id"] for office in offices}
    if not isinstance(raw_stages, list):
        _error(errors, "invalid_stages", "model stages must be a list", path)
        return stages, command_to_stage, unknown_commands

    observed_order: list[str] = []
    seen: set[str] = set()
    for index, stage in enumerate(raw_stages):
        if not isinstance(stage, dict):
            _error(
                errors,
                "invalid_stage",
                "stage entries must be objects",
                path,
                extra={"index": index},
            )
            continue
        stage_id = str(stage.get("id", "")).strip()
        observed_order.append(stage_id)
        if not stage_id:
            _error(errors, "blank_stage_id", "stage id must be non-empty", path)
            continue
        if stage_id in seen:
            _error(
                errors,
                "duplicate_stage_id",
                "stage ids must be unique",
                path,
                extra={"stage_id": stage_id},
            )
        seen.add(stage_id)
        office = str(stage.get("office", "")).strip()
        owner_role = str(stage.get("owner_role", "")).strip()
        if office not in office_ids:
            _error(
                errors,
                "unknown_stage_office",
                "stage office must reference a known office",
                path,
                extra={"stage_id": stage_id, "office": office},
            )
        if not owner_role:
            _error(
                errors,
                "blank_stage_owner",
                "stage owner_role must be non-empty",
                path,
                extra={"stage_id": stage_id},
            )
        for field, code in (
            ("entry_criteria", "missing_entry_criteria"),
            ("required_artifacts", "missing_required_artifacts"),
            ("exit_criteria", "missing_exit_criteria"),
            ("escalation_conditions", "missing_escalation_conditions"),
        ):
            if not _non_empty_string_list(stage.get(field)):
                _error(
                    errors,
                    code,
                    f"stage {field} must contain at least one non-empty item",
                    path,
                    extra={"stage_id": stage_id, "field": field},
                )
        if stage.get("receipt_required") is not True:
            _error(
                errors,
                "stage_receipt_not_required",
                "each organization stage must require a receipt",
                path,
                extra={"stage_id": stage_id},
            )
        leader_write_scope = str(stage.get("leader_write_scope", "")).strip()
        if leader_write_scope not in ALLOWED_LEADER_WRITE_SCOPES:
            _error(
                errors,
                "invalid_leader_write_scope",
                f"leader_write_scope must be one of {sorted(ALLOWED_LEADER_WRITE_SCOPES)}",
                path,
                extra={"stage_id": stage_id, "leader_write_scope": leader_write_scope},
            )
        commands = stage.get("command_mappings")
        if not isinstance(commands, list):
            _error(
                errors,
                "invalid_command_mappings",
                "stage command_mappings must be a list",
                path,
                extra={"stage_id": stage_id},
            )
            commands = []
        for command in commands:
            if not _non_empty_string(command):
                _error(
                    errors,
                    "blank_command_mapping",
                    "command mapping must be non-empty",
                    path,
                    extra={"stage_id": stage_id},
                )
                continue
            command_text = str(command)
            if command_text in command_to_stage:
                _error(
                    errors,
                    "duplicate_command_mapping",
                    "command mapping must be unique across stages",
                    path,
                    extra={
                        "command": command_text,
                        "stage_id": stage_id,
                        "first_stage_id": command_to_stage[command_text],
                    },
                )
            command_to_stage[command_text] = stage_id
            if command_text.startswith("/athanor:") and command_text not in REQUIRED_COMMANDS:
                unknown_commands.add(command_text)
                _error(
                    errors,
                    "unknown_command_mapping",
                    "unknown Athanor command mapped into organization model",
                    path,
                    extra={"stage_id": stage_id, "command": command_text},
                )
        stages.append(
            {
                "id": stage_id,
                "order": stage.get("order"),
                "title": str(stage.get("title", "")),
                "office": office,
                "owner_role": owner_role,
                "entry_criteria": stage.get("entry_criteria") if isinstance(stage.get("entry_criteria"), list) else [],
                "required_artifacts": stage.get("required_artifacts") if isinstance(stage.get("required_artifacts"), list) else [],
                "exit_criteria": stage.get("exit_criteria") if isinstance(stage.get("exit_criteria"), list) else [],
                "escalation_conditions": stage.get("escalation_conditions") if isinstance(stage.get("escalation_conditions"), list) else [],
                "receipt_required": stage.get("receipt_required") is True,
                "leader_write_scope": leader_write_scope,
                "command_mappings": [str(command) for command in commands if _non_empty_string(command)],
                "status": "pass",
            }
        )

    if observed_order != REQUIRED_STAGES:
        _error(
            errors,
            "stage_order_mismatch",
            "stage graph must match the canonical organization lifecycle",
            path,
            extra={"expected": REQUIRED_STAGES, "actual": observed_order},
        )
    return stages, command_to_stage, unknown_commands


def _validate_promotion_loop(
    model: dict[str, Any],
    *,
    path: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    loop = model.get("promotion_loop")
    if not isinstance(loop, dict):
        _error(errors, "missing_promotion_loop", "model must contain promotion_loop", path)
        return {"states": [], "owner_office": ""}
    states = loop.get("states")
    owner_office = str(loop.get("owner_office", "")).strip()
    if states != REQUIRED_PROMOTION_STATES:
        _error(
            errors,
            "promotion_states_mismatch",
            "promotion_loop.states must define the canonical policy promotion path",
            path,
            extra={"expected": REQUIRED_PROMOTION_STATES, "actual": states},
        )
    if owner_office != "learning-governance":
        _error(
            errors,
            "promotion_owner_mismatch",
            "promotion_loop.owner_office must be learning-governance",
            path,
            extra={"actual": owner_office},
        )
    return {
        "states": states if isinstance(states, list) else [],
        "owner_office": owner_office,
    }


def _required_ref_reports(
    model: dict[str, Any],
    *,
    repo_root: Path,
    path: str,
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    refs = model.get("required_refs")
    reports: list[dict[str, Any]] = []
    if not isinstance(refs, list) or not refs:
        _error(errors, "missing_required_refs", "model must contain required_refs[]", path)
        return reports
    for ref in refs:
        if not _non_empty_string(ref):
            _error(errors, "blank_required_ref", "required_refs entries must be non-empty", path)
            continue
        ref_text = str(ref).strip()
        if Path(ref_text).is_absolute() or ".." in Path(ref_text).parts:
            exists = False
            status = "fail"
            _error(
                errors,
                "invalid_required_ref",
                "required_refs must be repository-relative paths",
                path,
                extra={"ref": ref_text},
            )
        else:
            exists = (repo_root / ref_text).is_file()
            status = "pass" if exists else "fail"
            if not exists:
                _error(
                    errors,
                    "missing_required_ref",
                    "required reference path does not exist",
                    path,
                    extra={"ref": ref_text},
                )
        reports.append({"path": ref_text, "exists": exists, "status": status})
    return reports


def _command_coverage(command_to_stage: dict[str, str], *, errors: list[dict[str, Any]], path: str) -> list[dict[str, Any]]:
    coverage: list[dict[str, Any]] = []
    for command in sorted(REQUIRED_COMMANDS):
        stage_id = command_to_stage.get(command)
        status = "pass" if stage_id else "fail"
        if status == "fail":
            _error(
                errors,
                "missing_command_mapping",
                "required Athanor command is not mapped to an organization stage",
                path,
                extra={"command": command},
            )
        coverage.append({"command": command, "stage_id": stage_id or "", "status": status})
    return coverage


def build_report(
    *,
    repo_root: Path,
    doc_path: Path = DEFAULT_DOC,
    generated_at: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    doc_abs = (repo_root / doc_path).resolve()
    doc_rel = _repo_relative(doc_abs, repo_root) or doc_path.as_posix()
    model = _load_model(doc_abs)
    errors: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    if model.get("schema_version") != 1:
        _error(errors, "invalid_model_schema_version", "model schema_version must be 1", doc_rel)
    if model.get("model_id") != "athanor-organization-operating-model":
        _error(
            errors,
            "invalid_model_id",
            "model_id must be athanor-organization-operating-model",
            doc_rel,
        )
    if not _non_empty_string(model.get("last_reviewed")):
        _error(errors, "missing_last_reviewed", "model last_reviewed must be non-empty", doc_rel)

    safety = _validate_safety(model, path=doc_rel, errors=errors)
    offices = _validate_offices(model, path=doc_rel, errors=errors)
    stages, command_to_stage, _unknown_commands = _validate_stages(
        model,
        offices=offices,
        path=doc_rel,
        errors=errors,
    )
    promotion_loop = _validate_promotion_loop(model, path=doc_rel, errors=errors)
    required_refs = _required_ref_reports(model, repo_root=repo_root, path=doc_rel, errors=errors)
    command_coverage = _command_coverage(command_to_stage, errors=errors, path=doc_rel)

    _check(
        checks,
        "organization_model.exists",
        "pass" if doc_abs.is_file() else "fail",
        "organization operating model doc exists",
        expected=doc_path.as_posix(),
        actual=doc_rel,
    )
    _check(
        checks,
        "organization_model.stage_graph",
        "pass" if [stage["id"] for stage in stages] == REQUIRED_STAGES else "fail",
        "organization model defines the canonical company-like stage graph",
        expected=REQUIRED_STAGES,
        actual=[stage["id"] for stage in stages],
    )
    _check(
        checks,
        "organization_model.offices",
        "pass" if REQUIRED_OFFICES <= {office["id"] for office in offices} else "fail",
        "organization model defines required offices",
        expected=sorted(REQUIRED_OFFICES),
        actual=sorted(office["id"] for office in offices),
    )
    _check(
        checks,
        "organization_model.command_coverage",
        "pass" if all(item["status"] == "pass" for item in command_coverage) else "fail",
        "existing Athanor commands are mapped into organization stages",
        expected=sorted(REQUIRED_COMMANDS),
        actual=command_coverage,
    )
    _check(
        checks,
        "organization_model.required_refs",
        "pass" if required_refs and all(item["status"] == "pass" for item in required_refs) else "fail",
        "organization model links current runtime refs",
        actual=required_refs,
    )
    _check(
        checks,
        "organization_model.read_only",
        "pass" if safety.get("mutates_files_by_default") is False and safety.get("irreversible_actions") == 0 else "fail",
        "organization model gate is read-only",
        expected={"mutates_files_by_default": False, "irreversible_actions": 0},
        actual={
            "mutates_files_by_default": safety.get("mutates_files_by_default"),
            "irreversible_actions": safety.get("irreversible_actions"),
        },
    )

    for check in checks:
        if check["status"] == "fail":
            _error(
                errors,
                check["id"],
                check["message"],
                doc_rel,
            )

    status = "fail" if errors else "pass"
    return {
        "schema_version": 1,
        "status": status,
        "generated_at": generated_at or _iso_now(),
        "profile": {
            "id": "organization-operating-model",
            "description": "Read-only gate for Athanor's company-like organization operating model.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
        },
        "summary": {
            "checks": len(checks),
            "errors": len(errors),
            "warnings": 0,
            "stages": len(stages),
            "offices": len(offices),
            "commands": len(command_coverage),
            "missing_command_mappings": sum(1 for item in command_coverage if item["status"] == "fail"),
            "required_refs": len(required_refs),
            "missing_required_refs": sum(1 for item in required_refs if item["status"] == "fail"),
            "registered_agent_additions": safety.get("registered_agent_additions", None),
            "irreversible_actions": safety.get("irreversible_actions", None),
        },
        "model": {
            "path": doc_rel,
            "id": str(model.get("model_id", "")),
            "last_reviewed": str(model.get("last_reviewed", "")),
        },
        "safety": safety,
        "offices": offices,
        "stages": stages,
        "command_coverage": command_coverage,
        "promotion_loop": promotion_loop,
        "required_refs": required_refs,
        "checks": checks,
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor organization operating model checks.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = build_report(repo_root=args.repo_root, doc_path=args.doc_path)
    except OrganizationModelInputError as exc:
        print(f"organization operating model: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "organization-operating-model "
            f"status={report['status']} "
            f"stages={summary['stages']} "
            f"offices={summary['offices']} "
            f"errors={summary['errors']}"
        )
        for check in report["checks"]:
            print(f"- {check['id']}: {check['status']}")
        for error in report["errors"]:
            print(f"  - {error['code']}: {error['message']}")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
