#!/usr/bin/env python3
"""Validate and optionally emit Athanor organization stage receipts."""
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
DEFAULT_RECEIPT_ROOT = Path("docs/organization-stage-receipts")
DEFAULT_OUTPUT_ROOT = Path(".athanor/organization-stage-receipts")
MODEL_MARKER = "<!-- athanor:organization-operating-model v=1 -->"

VALID_DECISIONS = {"completed", "blocked", "skipped", "handoff"}
VALID_SOURCES = {"lfg", "lfg-goal", "manual", "gate"}


class StageReceiptInputError(Exception):
    """Raised when stage receipt inputs cannot be loaded."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _error(
    errors: list[dict[str, Any]],
    code: str,
    message: str,
    path: str,
    *,
    receipt_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    item: dict[str, Any] = {"code": code, "message": message, "path": path}
    if receipt_id is not None:
        item["receipt_id"] = receipt_id
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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StageReceiptInputError(f"{path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise StageReceiptInputError(f"{path}: JSON root must be an object")
    return parsed


def _load_model(doc_path: Path) -> dict[str, Any]:
    if not doc_path.is_file():
        raise StageReceiptInputError(f"organization model doc does not exist: {doc_path}")
    body = doc_path.read_text(encoding="utf-8")
    marker_index = body.find(MODEL_MARKER)
    if marker_index < 0:
        raise StageReceiptInputError(f"{doc_path}: missing {MODEL_MARKER}")
    after_marker = body[marker_index + len(MODEL_MARKER) :]
    match = re.search(r"```json\s*(\{.*?\})\s*```", after_marker, re.DOTALL)
    if not match:
        raise StageReceiptInputError(f"{doc_path}: missing fenced JSON model")
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise StageReceiptInputError(f"{doc_path}: invalid JSON model: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise StageReceiptInputError(f"{doc_path}: model must be a JSON object")
    return parsed


def _model_context(model: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    stages = model.get("stages") if isinstance(model.get("stages"), list) else []
    stage_map = {
        str(stage.get("id", "")).strip(): stage
        for stage in stages
        if isinstance(stage, dict) and _non_empty_string(stage.get("id"))
    }
    stage_order = [str(stage.get("id", "")).strip() for stage in stages if isinstance(stage, dict)]
    return stage_order, stage_map


def _repo_relative(path: Path, repo_root: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None


def _inside_repo_path(value: str | Path, repo_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    rel = _repo_relative(path, repo_root)
    if rel is None:
        raise StageReceiptInputError(f"path escapes repository root: {value}")
    return path


def _json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise StageReceiptInputError(f"receipt root is not a directory: {root}")
    return sorted(path for path in root.glob("*.json") if path.is_file())


def _registry_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise StageReceiptInputError(f"registry root is not a directory: {root}")
    return sorted(path for path in root.glob("*.json") if path.is_file())


def _load_work_items(registry_root: Path) -> dict[str, dict[str, Any]]:
    work_items: dict[str, dict[str, Any]] = {}
    for path in _registry_files(registry_root):
        item = _load_json(path)
        item_id = str(item.get("id", "")).strip()
        if item_id:
            work_items[item_id] = {"path": path, "item": item}
    return work_items


def _validate_repo_ref(
    ref: Any,
    *,
    repo_root: Path,
    path: str,
    field: str,
    errors: list[dict[str, Any]],
    receipt_id: str,
    required: bool = True,
) -> dict[str, Any]:
    if not _non_empty_string(ref):
        if required:
            _error(
                errors,
                "blank_ref",
                f"{field} must be a non-empty repository-relative path",
                path,
                receipt_id=receipt_id,
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
            receipt_id=receipt_id,
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
            receipt_id=receipt_id,
            extra={"field": field, "ref": ref_text},
        )
    return {"path": ref_text, "exists": exists, "status": "pass" if exists else "fail"}


def _validate_lfg_goal_source_receipt(
    ref_report: dict[str, Any],
    *,
    repo_root: Path,
    path: str,
    receipt_id: str,
    errors: list[dict[str, Any]],
) -> None:
    if not ref_report.get("exists"):
        return
    body = (repo_root / ref_report["path"]).read_text(encoding="utf-8")
    required_markers = ("## Step Receipts", "validator_status:")
    missing = [marker for marker in required_markers if marker not in body]
    if missing:
        _error(
            errors,
            "invalid_lfg_goal_source_receipt",
            "lfg-goal source receipts must look like validator output",
            path,
            receipt_id=receipt_id,
            extra={"ref": ref_report["path"], "missing": missing},
        )


def _validate_commands(
    value: Any,
    *,
    path: str,
    receipt_id: str,
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    if not isinstance(value, list) or not value:
        _error(errors, "missing_commands", "stage receipt must contain commands[]", path, receipt_id=receipt_id)
        return reports
    for index, command in enumerate(value):
        if not isinstance(command, dict):
            _error(
                errors,
                "invalid_command",
                "command entries must be objects",
                path,
                receipt_id=receipt_id,
                extra={"index": index},
            )
            continue
        if not _non_empty_string(command.get("command")):
            _error(
                errors,
                "blank_command",
                "command must be non-empty",
                path,
                receipt_id=receipt_id,
                extra={"index": index},
            )
        if not isinstance(command.get("exit_code"), int):
            _error(
                errors,
                "invalid_command_exit_code",
                "command exit_code must be an integer",
                path,
                receipt_id=receipt_id,
                extra={"index": index},
            )
        if not _non_empty_string(command.get("evidence")):
            _error(
                errors,
                "blank_command_evidence",
                "command evidence must be non-empty",
                path,
                receipt_id=receipt_id,
                extra={"index": index},
            )
        reports.append(
            {
                "command": str(command.get("command", "")),
                "exit_code": command.get("exit_code"),
                "evidence": str(command.get("evidence", "")),
            }
        )
    return reports


def _validate_receipt(
    receipt: dict[str, Any],
    *,
    repo_root: Path,
    path: Path,
    stage_map: dict[str, dict[str, Any]],
    work_items: dict[str, dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    rel_path = _repo_relative(path, repo_root) or path.as_posix()
    start_errors = len(errors)
    receipt_id = str(receipt.get("id", "")).strip() or "<missing-id>"

    if receipt.get("schema_version") != 1:
        _error(errors, "invalid_schema_version", "stage receipt schema_version must be 1", rel_path, receipt_id=receipt_id)
    for field in ("id", "work_item_id", "stage", "owner_office", "owner_role", "decision", "source", "summary", "created_at"):
        if not _non_empty_string(receipt.get(field)):
            _error(
                errors,
                "blank_required_field",
                f"stage receipt field {field!r} must be non-empty",
                rel_path,
                receipt_id=receipt_id,
                extra={"field": field},
            )

    work_item_id = str(receipt.get("work_item_id", "")).strip()
    stage = str(receipt.get("stage", "")).strip()
    owner_office = str(receipt.get("owner_office", "")).strip()
    owner_role = str(receipt.get("owner_role", "")).strip()
    decision = str(receipt.get("decision", "")).strip()
    source = str(receipt.get("source", "")).strip()

    if work_item_id and work_item_id not in work_items:
        _error(
            errors,
            "unknown_work_item",
            "stage receipt work_item_id must exist in the organization work-item registry",
            rel_path,
            receipt_id=receipt_id,
            extra={"work_item_id": work_item_id},
        )
    if stage not in stage_map:
        _error(errors, "unknown_stage", "stage receipt stage must exist in organization model", rel_path, receipt_id=receipt_id)
    else:
        expected_office = str(stage_map[stage].get("office", "")).strip()
        expected_role = str(stage_map[stage].get("owner_role", "")).strip()
        if owner_office != expected_office:
            _error(
                errors,
                "owner_office_mismatch",
                "owner_office must match the receipt stage office",
                rel_path,
                receipt_id=receipt_id,
                extra={"expected": expected_office, "actual": owner_office},
            )
        if owner_role != expected_role:
            _error(
                errors,
                "owner_role_mismatch",
                "owner_role must match the receipt stage owner_role",
                rel_path,
                receipt_id=receipt_id,
                extra={"expected": expected_role, "actual": owner_role},
            )
    if decision not in VALID_DECISIONS:
        _error(
            errors,
            "invalid_decision",
            f"decision must be one of {sorted(VALID_DECISIONS)}",
            rel_path,
            receipt_id=receipt_id,
            extra={"decision": decision},
        )
    if source not in VALID_SOURCES:
        _error(
            errors,
            "invalid_source",
            f"source must be one of {sorted(VALID_SOURCES)}",
            rel_path,
            receipt_id=receipt_id,
            extra={"source": source},
        )

    evidence_refs = receipt.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        _error(
            errors,
            "missing_evidence_refs",
            "stage receipt must contain evidence_refs[]",
            rel_path,
            receipt_id=receipt_id,
        )
        evidence_ref_reports: list[dict[str, Any]] = []
    else:
        evidence_ref_reports = [
            _validate_repo_ref(
                ref,
                repo_root=repo_root,
                path=rel_path,
                field="evidence_refs",
                errors=errors,
                receipt_id=receipt_id,
            )
            for ref in evidence_refs
        ]

    source_receipts = receipt.get("source_receipts")
    if source in {"lfg", "lfg-goal"} and (not isinstance(source_receipts, list) or not source_receipts):
        _error(
            errors,
            "missing_source_receipt",
            "lfg and lfg-goal stage receipts must point to source receipt artifacts",
            rel_path,
            receipt_id=receipt_id,
        )
        source_receipt_reports: list[dict[str, Any]] = []
    elif source_receipts is None:
        source_receipt_reports = []
    elif not isinstance(source_receipts, list):
        _error(errors, "invalid_source_receipts", "source_receipts must be a list", rel_path, receipt_id=receipt_id)
        source_receipt_reports = []
    else:
        source_receipt_reports = [
            _validate_repo_ref(
                ref,
                repo_root=repo_root,
                path=rel_path,
                field="source_receipts",
                errors=errors,
                receipt_id=receipt_id,
            )
            for ref in source_receipts
        ]
        if source == "lfg-goal":
            for ref_report in source_receipt_reports:
                _validate_lfg_goal_source_receipt(
                    ref_report,
                    repo_root=repo_root,
                    path=rel_path,
                    receipt_id=receipt_id,
                    errors=errors,
                )

    command_reports = _validate_commands(receipt.get("commands"), path=rel_path, receipt_id=receipt_id, errors=errors)

    safety = receipt.get("safety") if isinstance(receipt.get("safety"), dict) else {}
    for key, expected in {
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "auto_runtime_launch": False,
        "irreversible_actions": 0,
        "requires_explicit_emit": True,
        "requires_explicit_work_item_update": True,
    }.items():
        if safety.get(key) != expected:
            _error(
                errors,
                "unsafe_stage_receipt",
                f"stage receipt safety field {key!r} must be {expected!r}",
                rel_path,
                receipt_id=receipt_id,
                extra={"field": key, "expected": expected, "actual": safety.get(key)},
            )

    return {
        "id": receipt_id,
        "path": rel_path,
        "work_item_id": work_item_id,
        "stage": stage,
        "owner_office": owner_office,
        "owner_role": owner_role,
        "decision": decision,
        "source": source,
        "evidence_refs": evidence_ref_reports,
        "source_receipts": source_receipt_reports,
        "commands": command_reports,
        "status": "pass" if len(errors) == start_errors else "fail",
    }


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug or "stage-receipt"


def _build_receipt(
    args: argparse.Namespace,
    *,
    stage_map: dict[str, dict[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    stage = str(args.stage or "").strip()
    stage_def = stage_map.get(stage, {})
    source_receipts = [str(ref).strip() for ref in args.source_receipt if str(ref).strip()]
    evidence_refs = [str(ref).strip() for ref in args.evidence_ref if str(ref).strip()]
    receipt_id = args.receipt_id or _slugify(f"{args.work_item_id}-{stage}-{created_at.replace(':', '').replace('-', '')}")
    return {
        "schema_version": 1,
        "id": receipt_id,
        "work_item_id": str(args.work_item_id or "").strip(),
        "stage": stage,
        "owner_office": str(stage_def.get("office", "")).strip(),
        "owner_role": str(stage_def.get("owner_role", "")).strip(),
        "decision": str(args.decision or "").strip(),
        "source": str(args.source or "").strip(),
        "summary": str(args.summary or "").strip(),
        "created_at": created_at,
        "evidence_refs": evidence_refs,
        "source_receipts": source_receipts,
        "commands": [
            {
                "command": "organization-stage-receipt emit",
                "exit_code": 0,
                "evidence": str(args.summary or "").strip() or "stage receipt emitted",
            }
        ],
        "safety": {
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
            "irreversible_actions": 0,
            "requires_explicit_emit": True,
            "requires_explicit_work_item_update": True,
        },
    }


def _receipt_output_path(args: argparse.Namespace, *, repo_root: Path, receipt: dict[str, Any]) -> Path:
    if args.receipt_path:
        return _inside_repo_path(args.receipt_path, repo_root)
    output_root = _inside_repo_path(args.output_root, repo_root)
    return output_root / f"{receipt['id']}.json"


def _has_emit_inputs(args: argparse.Namespace) -> bool:
    return any(
        (
            args.work_item_id,
            args.stage,
            args.decision,
            args.summary,
            args.source,
            args.source_receipt,
            args.evidence_ref,
        )
    )


def _validate_emit_args(args: argparse.Namespace, *, errors: list[dict[str, Any]]) -> None:
    if not _has_emit_inputs(args):
        return
    missing = [
        name
        for name in ("work_item_id", "stage", "decision", "summary", "source")
        if not _non_empty_string(getattr(args, name))
    ]
    if not args.evidence_ref:
        missing.append("evidence_ref")
    if missing:
        _error(
            errors,
            "missing_emit_argument",
            "stage receipt emission requires all core arguments",
            "<cli>",
            extra={"missing": missing},
        )
    if args.apply_work_item_update and not args.emit:
        _error(
            errors,
            "update_without_emit",
            "--apply-work-item-update requires --emit so the receipt_ref exists",
            "<cli>",
        )
    if args.apply_work_item_update and not _non_empty_string(args.work_item_path):
        _error(
            errors,
            "missing_work_item_path",
            "--apply-work-item-update requires --work-item-path",
            "<cli>",
        )


def _append_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def _apply_work_item_update(
    *,
    repo_root: Path,
    work_item_path: Path,
    receipt_rel: str,
    receipt: dict[str, Any],
    stage_map: dict[str, dict[str, Any]],
    next_stage: str | None,
) -> dict[str, Any]:
    item = _load_json(work_item_path)
    item_id = str(item.get("id", "")).strip()
    if item_id != receipt["work_item_id"]:
        raise StageReceiptInputError(
            f"{work_item_path}: work item id {item_id!r} does not match receipt {receipt['work_item_id']!r}"
        )
    stage = receipt["stage"]
    if stage not in stage_map:
        raise StageReceiptInputError(f"cannot update work item for unknown stage: {stage}")
    history = item.get("stage_history")
    if not isinstance(history, list):
        raise StageReceiptInputError(f"{work_item_path}: stage_history must be a list")
    current_entry = None
    for entry in history:
        if isinstance(entry, dict) and str(entry.get("stage", "")).strip() == stage:
            current_entry = entry
            break
    if current_entry is None:
        raise StageReceiptInputError(f"{work_item_path}: missing stage_history entry for {stage}")
    current_entry["status"] = receipt["decision"]
    current_entry["receipt_ref"] = receipt_rel
    artifact_refs = current_entry.get("artifact_refs")
    if not isinstance(artifact_refs, list):
        artifact_refs = []
        current_entry["artifact_refs"] = artifact_refs
    _append_unique(artifact_refs, receipt_rel)
    for ref in receipt.get("evidence_refs", []):
        _append_unique(artifact_refs, ref)

    artifacts = item.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
        item["artifacts"] = artifacts
    if not any(isinstance(artifact, dict) and artifact.get("path") == receipt_rel for artifact in artifacts):
        artifacts.append(
            {
                "stage": stage,
                "path": receipt_rel,
                "kind": "stage-receipt",
                "status": "current",
            }
        )

    if next_stage:
        if next_stage not in stage_map:
            raise StageReceiptInputError(f"cannot advance to unknown next stage: {next_stage}")
        next_def = stage_map[next_stage]
        item["status"] = "active"
        item["current_stage"] = next_stage
        item["owner_office"] = str(next_def.get("office", "")).strip()
        item["owner_role"] = str(next_def.get("owner_role", "")).strip()
        if not any(isinstance(entry, dict) and entry.get("stage") == next_stage for entry in history):
            history.append(
                {
                    "stage": next_stage,
                    "status": "active",
                    "owner_role": str(next_def.get("owner_role", "")).strip(),
                    "artifact_refs": [receipt_rel],
                    "receipt_ref": "",
                    "decided_at": receipt["created_at"][:10],
                }
            )
    item["updated_at"] = receipt["created_at"][:10]
    work_item_path.write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
    return {
        "path": _repo_relative(work_item_path, repo_root) or work_item_path.as_posix(),
        "work_item_id": item_id,
        "completed_stage": stage,
        "receipt_ref": receipt_rel,
        "next_stage": next_stage or "",
    }


def build_report(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    repo_root = Path(args.repo_root).resolve()
    model_doc = _inside_repo_path(args.model_doc, repo_root)
    registry_root = _inside_repo_path(args.registry_root, repo_root)
    receipt_root = _inside_repo_path(args.receipt_root, repo_root)
    errors: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    emitted_receipts: list[dict[str, Any]] = []
    work_item_updates: list[dict[str, Any]] = []
    planned_receipt: dict[str, Any] | None = None

    try:
        model = _load_model(model_doc)
        stage_order, stage_map = _model_context(model)
        work_items = _load_work_items(registry_root)
        receipt_files = _json_files(receipt_root)
    except StageReceiptInputError as exc:
        report = _base_report(
            status="fail",
            model_path=str(args.model_doc),
            registry_path=str(args.registry_root),
            registry_files=0,
            receipt_root_path=str(args.receipt_root),
            receipt_files=0,
            stage_order=[],
            receipts=[],
            emitted_receipts=[],
            planned_receipt=None,
            work_item_updates=[],
            checks=[],
            errors=[{"code": "input_error", "message": str(exc), "path": "<input>"}],
        )
        return report, 1

    _validate_emit_args(args, errors=errors)

    receipts: list[dict[str, Any]] = []
    for path in receipt_files:
        try:
            receipt = _load_json(path)
        except StageReceiptInputError as exc:
            _error(errors, "input_error", str(exc), _repo_relative(path, repo_root) or path.as_posix())
            continue
        receipts.append(
            _validate_receipt(
                receipt,
                repo_root=repo_root,
                path=path,
                stage_map=stage_map,
                work_items=work_items,
                errors=errors,
            )
        )

    created_at = args.created_at or _iso_now()
    if _has_emit_inputs(args) and not any(error["code"] == "missing_emit_argument" for error in errors):
        receipt = _build_receipt(args, stage_map=stage_map, created_at=created_at)
        try:
            output_path = _receipt_output_path(args, repo_root=repo_root, receipt=receipt)
            output_rel = _repo_relative(output_path, repo_root)
            if output_rel is None:
                raise StageReceiptInputError(f"receipt output path escapes repository root: {output_path}")
            planned_receipt = {
                "path": output_rel,
                "id": receipt["id"],
                "work_item_id": receipt["work_item_id"],
                "stage": receipt["stage"],
                "decision": receipt["decision"],
                "source": receipt["source"],
                "will_write": bool(args.emit),
            }
            temp_errors: list[dict[str, Any]] = []
            _validate_receipt(
                receipt,
                repo_root=repo_root,
                path=output_path,
                stage_map=stage_map,
                work_items=work_items,
                errors=temp_errors,
            )
            if temp_errors:
                errors.extend(temp_errors)
            elif args.emit:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
                emitted_report = _validate_receipt(
                    receipt,
                    repo_root=repo_root,
                    path=output_path,
                    stage_map=stage_map,
                    work_items=work_items,
                    errors=errors,
                )
                emitted_receipts.append(emitted_report)
                if args.apply_work_item_update:
                    update = _apply_work_item_update(
                        repo_root=repo_root,
                        work_item_path=_inside_repo_path(args.work_item_path, repo_root),
                        receipt_rel=output_rel,
                        receipt=receipt,
                        stage_map=stage_map,
                        next_stage=args.next_stage,
                    )
                    work_item_updates.append(update)
        except StageReceiptInputError as exc:
            _error(errors, "input_error", str(exc), "<emit>")

    _check(
        checks,
        "stage-receipt-safety-profile",
        "pass",
        "adapter is read-only by default and writes only through explicit flags",
        expected={"requires_explicit_emit": True, "requires_explicit_work_item_update": True},
        actual={"emit": bool(args.emit), "apply_work_item_update": bool(args.apply_work_item_update)},
    )
    if receipt_files:
        _check(
            checks,
            "stage-receipt-files-present",
            "pass",
            "stage receipt files were found for validation",
            actual=len(receipt_files),
        )

    status = "fail" if errors else "pass"
    report = _base_report(
        status=status,
        model_path=_repo_relative(model_doc, repo_root) or str(args.model_doc),
        registry_path=_repo_relative(registry_root, repo_root) or str(args.registry_root),
        registry_files=len(work_items),
        receipt_root_path=_repo_relative(receipt_root, repo_root) or str(args.receipt_root),
        receipt_files=len(receipt_files),
        stage_order=stage_order,
        receipts=receipts,
        emitted_receipts=emitted_receipts,
        planned_receipt=planned_receipt,
        work_item_updates=work_item_updates,
        checks=checks,
        errors=errors,
    )
    return report, 1 if errors else 0


def _base_report(
    *,
    status: str,
    model_path: str,
    registry_path: str,
    registry_files: int,
    receipt_root_path: str,
    receipt_files: int,
    stage_order: list[str],
    receipts: list[dict[str, Any]],
    emitted_receipts: list[dict[str, Any]],
    planned_receipt: dict[str, Any] | None,
    work_item_updates: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": status,
        "generated_at": _iso_now(),
        "profile": {
            "id": "organization-stage-receipt",
            "description": "Validate or explicitly emit organization stage receipts for work-item handoffs.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
            "requires_explicit_emit": True,
            "requires_explicit_work_item_update": True,
        },
        "summary": {
            "checks": len(checks),
            "errors": len(errors),
            "warnings": len([check for check in checks if check.get("status") == "warn"]),
            "receipts": len(receipts),
            "emitted_receipts": len(emitted_receipts),
            "work_item_updates": len(work_item_updates),
            "irreversible_actions": 0,
        },
        "model": {"path": model_path, "stage_order": stage_order},
        "registry": {"path": registry_path, "files": registry_files},
        "receipt_root": {"path": receipt_root_path, "files": receipt_files},
        "receipts": receipts,
        "emitted_receipts": emitted_receipts,
        "planned_receipt": planned_receipt,
        "work_item_updates": work_item_updates,
        "checks": checks,
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root")
    parser.add_argument("--model-doc", default=str(DEFAULT_MODEL_DOC), help="Organization model document")
    parser.add_argument("--registry-root", default=str(DEFAULT_REGISTRY_ROOT), help="Organization work-item registry root")
    parser.add_argument("--receipt-root", default=str(DEFAULT_RECEIPT_ROOT), help="Committed stage receipt root to validate")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Output root used with --emit")
    parser.add_argument("--receipt-path", default="", help="Explicit output receipt path used with --emit")
    parser.add_argument("--receipt-id", default="", help="Optional explicit receipt id")
    parser.add_argument("--created-at", default="", help="Optional explicit receipt timestamp")
    parser.add_argument("--work-item-id", default="", help="Work item id for a planned or emitted receipt")
    parser.add_argument("--stage", default="", help="Organization stage for a planned or emitted receipt")
    parser.add_argument("--decision", default="", help="Stage decision")
    parser.add_argument("--summary", default="", help="Receipt summary")
    parser.add_argument("--source", default="", help="Receipt evidence source")
    parser.add_argument("--source-receipt", action="append", default=[], help="Source LFG/LFG-goal receipt ref")
    parser.add_argument("--evidence-ref", action="append", default=[], help="Evidence artifact ref")
    parser.add_argument("--emit", action="store_true", help="Write the planned receipt")
    parser.add_argument("--apply-work-item-update", action="store_true", help="Update the selected work item with the emitted receipt")
    parser.add_argument("--work-item-path", default="", help="Work item JSON path for --apply-work-item-update")
    parser.add_argument("--next-stage", default="", help="Next organization stage after a completed handoff")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    report, exit_code = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "organization-stage-receipt "
            f"status={report['status']} receipts={report['summary']['receipts']} "
            f"emitted={report['summary']['emitted_receipts']} errors={report['summary']['errors']}"
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
