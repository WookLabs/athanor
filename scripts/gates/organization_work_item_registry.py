#!/usr/bin/env python3
"""Validate Athanor organization work-item registry files."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DOC = Path("docs/organization-operating-model.md")
DEFAULT_REGISTRY_ROOT = Path("docs/organization-work-items")
MODEL_MARKER = "<!-- athanor:organization-operating-model v=1 -->"

VALID_ITEM_STATUSES = {"queued", "active", "blocked", "completed", "retired"}
VALID_HISTORY_STATUSES = {"completed", "active", "blocked", "skipped"}
VALID_ARTIFACT_STATUSES = {"planned", "current", "superseded"}


class RegistryInputError(Exception):
    """Raised when registry inputs cannot be loaded."""


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
    item_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    item: dict[str, Any] = {"code": code, "message": message, "path": path}
    if item_id is not None:
        item["item_id"] = item_id
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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryInputError(f"{path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise RegistryInputError(f"{path}: JSON root must be an object")
    return parsed


def _load_model(doc_path: Path) -> dict[str, Any]:
    if not doc_path.is_file():
        raise RegistryInputError(f"organization model doc does not exist: {doc_path}")
    body = doc_path.read_text(encoding="utf-8")
    marker_index = body.find(MODEL_MARKER)
    if marker_index < 0:
        raise RegistryInputError(f"{doc_path}: missing {MODEL_MARKER}")
    after_marker = body[marker_index + len(MODEL_MARKER) :]
    match = re.search(r"```json\s*(\{.*?\})\s*```", after_marker, re.DOTALL)
    if not match:
        raise RegistryInputError(f"{doc_path}: missing fenced JSON model")
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise RegistryInputError(f"{doc_path}: invalid JSON model: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise RegistryInputError(f"{doc_path}: model must be a JSON object")
    return parsed


def _registry_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise RegistryInputError(f"registry root is not a directory: {root}")
    return sorted(path for path in root.glob("*.json") if path.is_file())


def _resolve_repo_ref(
    ref: Any,
    *,
    repo_root: Path,
    path: str,
    item_id: str,
    field: str,
    errors: list[dict[str, Any]],
    required: bool = True,
) -> dict[str, Any]:
    if not _non_empty_string(ref):
        if required:
            _error(
                errors,
                "blank_ref",
                f"{field} must be a non-empty repository-relative path",
                path,
                item_id=item_id,
                extra={"field": field},
            )
        return {"path": "", "exists": False, "status": "fail"}
    ref_text = str(ref).strip()
    if Path(ref_text).is_absolute() or ".." in Path(ref_text).parts:
        _error(
            errors,
            "invalid_ref",
            f"{field} must stay inside the repository",
            path,
            item_id=item_id,
            extra={"field": field, "ref": ref_text},
        )
        return {"path": ref_text, "exists": False, "status": "fail"}
    exists = (repo_root / ref_text).is_file()
    if not exists:
        _error(
            errors,
            "missing_ref",
            f"{field} path does not exist",
            path,
            item_id=item_id,
            extra={"field": field, "ref": ref_text},
        )
    return {"path": ref_text, "exists": exists, "status": "pass" if exists else "fail"}


def _model_context(model: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    stages = model.get("stages") if isinstance(model.get("stages"), list) else []
    offices = model.get("offices") if isinstance(model.get("offices"), list) else []
    stage_map = {
        str(stage.get("id", "")).strip(): stage
        for stage in stages
        if isinstance(stage, dict) and _non_empty_string(stage.get("id"))
    }
    stage_order = [str(stage.get("id", "")).strip() for stage in stages if isinstance(stage, dict)]
    normalized_offices = [
        {
            "id": str(office.get("id", "")).strip(),
            "title": str(office.get("title", "")),
        }
        for office in offices
        if isinstance(office, dict) and _non_empty_string(office.get("id"))
    ]
    return stage_order, stage_map, normalized_offices


def _validate_artifacts(
    item: dict[str, Any],
    *,
    repo_root: Path,
    path: str,
    item_id: str,
    stage_map: dict[str, dict[str, Any]],
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifacts = item.get("artifacts")
    reports: list[dict[str, Any]] = []
    if not isinstance(artifacts, list) or not artifacts:
        _error(errors, "missing_artifacts", "work item must contain artifacts[]", path, item_id=item_id)
        return reports
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            _error(
                errors,
                "invalid_artifact",
                "artifact entries must be objects",
                path,
                item_id=item_id,
                extra={"index": index},
            )
            continue
        stage = str(artifact.get("stage", "")).strip()
        status = str(artifact.get("status", "")).strip()
        kind = str(artifact.get("kind", "")).strip()
        if stage not in stage_map:
            _error(
                errors,
                "unknown_stage",
                "artifact stage must exist in organization model",
                path,
                item_id=item_id,
                extra={"stage": stage},
            )
        if status not in VALID_ARTIFACT_STATUSES:
            _error(
                errors,
                "invalid_artifact_status",
                f"artifact status must be one of {sorted(VALID_ARTIFACT_STATUSES)}",
                path,
                item_id=item_id,
                extra={"status": status},
            )
        if not kind:
            _error(errors, "blank_artifact_kind", "artifact kind must be non-empty", path, item_id=item_id)
        ref_report = _resolve_repo_ref(
            artifact.get("path"),
            repo_root=repo_root,
            path=path,
            item_id=item_id,
            field="artifact.path",
            errors=errors,
        )
        reports.append(
            {
                "stage": stage,
                "path": ref_report["path"],
                "kind": kind,
                "status": status,
                "exists": ref_report["exists"],
            }
        )
    return reports


def _validate_stage_history(
    item: dict[str, Any],
    *,
    repo_root: Path,
    path: str,
    item_id: str,
    stage_order: list[str],
    stage_map: dict[str, dict[str, Any]],
    current_stage: str,
    item_status: str,
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    history = item.get("stage_history")
    reports: list[dict[str, Any]] = []
    if not isinstance(history, list) or not history:
        _error(errors, "missing_stage_history", "work item must contain stage_history[]", path, item_id=item_id)
        return reports

    indices: list[int] = []
    active_like: list[dict[str, Any]] = []
    seen_stages: set[str] = set()
    for index, entry in enumerate(history):
        if not isinstance(entry, dict):
            _error(
                errors,
                "invalid_stage_history",
                "stage_history entries must be objects",
                path,
                item_id=item_id,
                extra={"index": index},
            )
            continue
        stage = str(entry.get("stage", "")).strip()
        status = str(entry.get("status", "")).strip()
        owner_role = str(entry.get("owner_role", "")).strip()
        receipt_ref = str(entry.get("receipt_ref", "")).strip()
        artifact_refs = entry.get("artifact_refs")
        if stage not in stage_map:
            _error(
                errors,
                "unknown_stage",
                "stage_history stage must exist in organization model",
                path,
                item_id=item_id,
                extra={"stage": stage},
            )
            stage_index = -1
        else:
            stage_index = stage_order.index(stage)
            indices.append(stage_index)
        if stage in seen_stages:
            _error(
                errors,
                "duplicate_stage_history",
                "stage_history cannot repeat a stage",
                path,
                item_id=item_id,
                extra={"stage": stage},
            )
        seen_stages.add(stage)
        if status not in VALID_HISTORY_STATUSES:
            _error(
                errors,
                "invalid_stage_history_status",
                f"stage_history status must be one of {sorted(VALID_HISTORY_STATUSES)}",
                path,
                item_id=item_id,
                extra={"status": status},
            )
        if not owner_role:
            _error(errors, "blank_stage_owner", "stage_history owner_role must be non-empty", path, item_id=item_id)
        if not isinstance(artifact_refs, list) or not artifact_refs:
            _error(
                errors,
                "missing_artifact_refs",
                "stage_history artifact_refs must be non-empty",
                path,
                item_id=item_id,
                extra={"stage": stage},
            )
            artifact_ref_reports: list[dict[str, Any]] = []
        else:
            artifact_ref_reports = [
                _resolve_repo_ref(
                    ref,
                    repo_root=repo_root,
                    path=path,
                    item_id=item_id,
                    field="stage_history.artifact_refs",
                    errors=errors,
                )
                for ref in artifact_refs
            ]
        receipt_report = _resolve_repo_ref(
            receipt_ref,
            repo_root=repo_root,
            path=path,
            item_id=item_id,
            field="stage_history.receipt_ref",
            errors=errors,
            required=status == "completed",
        )
        if status == "completed" and not receipt_ref:
            _error(
                errors,
                "missing_stage_receipt",
                "completed stage_history entries must contain receipt_ref",
                path,
                item_id=item_id,
                extra={"stage": stage},
            )
        if status in {"active", "blocked"}:
            active_like.append({"stage": stage, "status": status})
        reports.append(
            {
                "stage": stage,
                "order": stage_index + 1 if stage_index >= 0 else None,
                "status": status,
                "owner_role": owner_role,
                "artifact_refs": artifact_ref_reports,
                "receipt_ref": receipt_report,
                "decided_at": str(entry.get("decided_at", "")),
            }
        )

    if indices != sorted(indices):
        _error(
            errors,
            "stage_history_order",
            "stage_history must follow organization model order",
            path,
            item_id=item_id,
            extra={"actual": indices},
        )
    if indices:
        expected = list(range(indices[0], indices[-1] + 1))
        if indices != expected:
            _error(
                errors,
                "stage_history_gap",
                "stage_history must be gap-free from first recorded stage to current stage",
                path,
                item_id=item_id,
                extra={"expected": expected, "actual": indices},
            )
    if item_status in {"active", "blocked"}:
        if len(active_like) != 1:
            _error(
                errors,
                "invalid_active_stage_count",
                "active or blocked work items must have exactly one active/blocked stage entry",
                path,
                item_id=item_id,
                extra={"active_like": active_like},
            )
        elif active_like[0]["stage"] != current_stage:
            _error(
                errors,
                "current_stage_mismatch",
                "current_stage must match the active/blocked stage_history entry",
                path,
                item_id=item_id,
                extra={"current_stage": current_stage, "history_stage": active_like[0]["stage"]},
            )
    return reports


def _validate_item(
    item: dict[str, Any],
    *,
    repo_root: Path,
    path: str,
    stage_order: list[str],
    stage_map: dict[str, dict[str, Any]],
    office_ids: set[str],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    item_id = str(item.get("id", "")).strip() or "<missing-id>"
    if item.get("schema_version") != 1:
        _error(errors, "invalid_schema_version", "work item schema_version must be 1", path, item_id=item_id)
    for field in ("id", "title", "created_at", "updated_at", "current_stage", "owner_office", "owner_role"):
        if not _non_empty_string(item.get(field)):
            _error(
                errors,
                "blank_required_field",
                f"work item field {field!r} must be non-empty",
                path,
                item_id=item_id,
                extra={"field": field},
            )
    item_status = str(item.get("status", "")).strip()
    if item_status not in VALID_ITEM_STATUSES:
        _error(
            errors,
            "invalid_item_status",
            f"work item status must be one of {sorted(VALID_ITEM_STATUSES)}",
            path,
            item_id=item_id,
            extra={"status": item_status},
        )
    current_stage = str(item.get("current_stage", "")).strip()
    owner_office = str(item.get("owner_office", "")).strip()
    owner_role = str(item.get("owner_role", "")).strip()
    if current_stage not in stage_map:
        _error(errors, "unknown_stage", "current_stage must exist in organization model", path, item_id=item_id)
    elif owner_office and owner_office != str(stage_map[current_stage].get("office", "")).strip():
        _error(
            errors,
            "owner_office_mismatch",
            "owner_office must match the current stage office",
            path,
            item_id=item_id,
            extra={"current_stage": current_stage, "owner_office": owner_office},
        )
    if owner_office not in office_ids:
        _error(errors, "unknown_office", "owner_office must exist in organization model", path, item_id=item_id)
    if current_stage in stage_map:
        expected_role = str(stage_map[current_stage].get("owner_role", "")).strip()
        if expected_role and owner_role != expected_role:
            _error(
                errors,
                "owner_role_mismatch",
                "owner_role must match the current stage owner_role",
                path,
                item_id=item_id,
                extra={"current_stage": current_stage, "expected": expected_role, "actual": owner_role},
            )
    if not _non_empty_string_list(item.get("source_refs")):
        _error(errors, "missing_source_refs", "work item source_refs must be non-empty", path, item_id=item_id)
    else:
        for ref in item["source_refs"]:
            _resolve_repo_ref(
                ref,
                repo_root=repo_root,
                path=path,
                item_id=item_id,
                field="source_refs",
                errors=errors,
            )
    if not _non_empty_string_list(item.get("acceptance_criteria")):
        _error(
            errors,
            "missing_acceptance_criteria",
            "work item acceptance_criteria must be non-empty",
            path,
            item_id=item_id,
        )
    safety = item.get("safety") if isinstance(item.get("safety"), dict) else {}
    for key, expected in {
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "irreversible_actions": 0,
    }.items():
        if safety.get(key) != expected:
            _error(
                errors,
                "unsafe_work_item",
                f"work item safety field {key!r} must be {expected!r}",
                path,
                item_id=item_id,
                extra={"field": key, "actual": safety.get(key), "expected": expected},
            )
    artifacts = _validate_artifacts(
        item,
        repo_root=repo_root,
        path=path,
        item_id=item_id,
        stage_map=stage_map,
        errors=errors,
    )
    stage_history = _validate_stage_history(
        item,
        repo_root=repo_root,
        path=path,
        item_id=item_id,
        stage_order=stage_order,
        stage_map=stage_map,
        current_stage=current_stage,
        item_status=item_status,
        errors=errors,
    )
    return {
        "id": item_id,
        "path": path,
        "title": str(item.get("title", "")),
        "status": item_status,
        "created_at": str(item.get("created_at", "")),
        "updated_at": str(item.get("updated_at", "")),
        "target_score": item.get("target_score"),
        "current_stage": current_stage,
        "owner_office": owner_office,
        "owner_role": owner_role,
        "source_refs": item.get("source_refs") if isinstance(item.get("source_refs"), list) else [],
        "acceptance_criteria": item.get("acceptance_criteria") if isinstance(item.get("acceptance_criteria"), list) else [],
        "artifacts": artifacts,
        "stage_history": stage_history,
        "safety": {
            "mutates_files_by_default": safety.get("mutates_files_by_default"),
            "external_telemetry": safety.get("external_telemetry"),
            "irreversible_actions": safety.get("irreversible_actions"),
        },
    }


def build_report(
    *,
    repo_root: Path,
    model_doc: Path = DEFAULT_MODEL_DOC,
    registry_root: Path = DEFAULT_REGISTRY_ROOT,
    generated_at: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    model_abs = (repo_root / model_doc).resolve()
    registry_abs = (repo_root / registry_root).resolve()
    registry_rel = _repo_relative(registry_abs, repo_root) or registry_root.as_posix()
    model_rel = _repo_relative(model_abs, repo_root) or model_doc.as_posix()
    model = _load_model(model_abs)
    stage_order, stage_map, offices = _model_context(model)
    office_ids = {office["id"] for office in offices}
    errors: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    seen_ids: dict[str, str] = {}

    files = _registry_files(registry_abs)
    for file_path in files:
        rel_path = _repo_relative(file_path, repo_root) or file_path.as_posix()
        item = _load_json(file_path)
        report_item = _validate_item(
            item,
            repo_root=repo_root,
            path=rel_path,
            stage_order=stage_order,
            stage_map=stage_map,
            office_ids=office_ids,
            errors=errors,
        )
        item_id = report_item["id"]
        if item_id in seen_ids:
            _error(
                errors,
                "duplicate_work_item_id",
                "work item ids must be unique",
                rel_path,
                item_id=item_id,
                extra={"first_path": seen_ids[item_id]},
            )
        seen_ids[item_id] = rel_path
        items.append(report_item)

    _check(
        checks,
        "work_item_registry.exists",
        "pass" if registry_abs.is_dir() else "fail",
        "organization work-item registry root exists",
        expected=registry_root.as_posix(),
        actual=registry_rel,
    )
    _check(
        checks,
        "work_item_registry.items_present",
        "pass" if items else "fail",
        "organization work-item registry contains at least one item",
        actual=len(items),
    )
    _check(
        checks,
        "work_item_registry.items_valid",
        "pass" if not errors else "fail",
        "organization work items satisfy stage, owner, artifact, and receipt contracts",
        actual=len(errors),
    )
    active_items = [item for item in items if item["status"] in {"active", "blocked"}]
    _check(
        checks,
        "work_item_registry.active_items_tracked",
        "pass" if active_items else "warn",
        "registry tracks at least one active or blocked item",
        actual=len(active_items),
    )
    _check(
        checks,
        "work_item_registry.read_only",
        "pass",
        "organization work-item registry gate is read-only",
        expected={"mutates_files_by_default": False, "irreversible_actions": 0},
        actual={"mutates_files_by_default": False, "irreversible_actions": 0},
    )

    for check in checks:
        if check["status"] == "fail":
            _error(errors, check["id"], check["message"], registry_rel)

    status = "fail" if errors else ("warn" if any(check["status"] == "warn" for check in checks) else "pass")
    return {
        "schema_version": 1,
        "status": status,
        "generated_at": generated_at or _iso_now(),
        "profile": {
            "id": "organization-work-item-registry",
            "description": "Read-only gate for organization work-item stage state.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
        },
        "summary": {
            "checks": len(checks),
            "errors": len(errors),
            "warnings": sum(1 for check in checks if check["status"] == "warn"),
            "items": len(items),
            "active_items": len([item for item in items if item["status"] == "active"]),
            "blocked_items": len([item for item in items if item["status"] == "blocked"]),
            "completed_items": len([item for item in items if item["status"] == "completed"]),
            "irreversible_actions": 0,
        },
        "model": {
            "path": model_rel,
            "stage_order": stage_order,
        },
        "registry": {
            "path": registry_rel,
            "files": len(files),
        },
        "offices": offices,
        "work_items": items,
        "checks": checks,
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor organization work-item registry checks.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--model-doc", type=Path, default=DEFAULT_MODEL_DOC)
    parser.add_argument("--registry-root", type=Path, default=DEFAULT_REGISTRY_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = build_report(
            repo_root=args.repo_root,
            model_doc=args.model_doc,
            registry_root=args.registry_root,
        )
    except RegistryInputError as exc:
        print(f"organization work-item registry: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "organization-work-item-registry "
            f"status={report['status']} "
            f"items={summary['items']} "
            f"active={summary['active_items']} "
            f"errors={summary['errors']}"
        )
        for check in report["checks"]:
            print(f"- {check['id']}: {check['status']}")
        for error in report["errors"]:
            print(f"  - {error['code']}: {error['message']}")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
