#!/usr/bin/env python3
"""Validate Athanor policy promotion ledger files."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER_ROOT = Path("docs/policy-promotions")

STATE_ORDER = [
    "incident",
    "lesson",
    "candidate_policy",
    "policy",
    "gate_candidate",
    "gate",
    "retired",
]
STATE_INDEX = {state: index for index, state in enumerate(STATE_ORDER)}
VALID_HISTORY_STATUSES = {"completed", "current", "skipped"}


class PolicyPromotionInputError(Exception):
    """Raised when policy promotion inputs cannot be loaded."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_list(value: Any) -> bool:
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
    promotion_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    item: dict[str, Any] = {"code": code, "message": message, "path": path}
    if promotion_id is not None:
        item["promotion_id"] = promotion_id
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
        raise PolicyPromotionInputError(f"{path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise PolicyPromotionInputError(f"{path}: JSON root must be an object")
    return parsed


def _ledger_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise PolicyPromotionInputError(f"ledger root is not a directory: {root}")
    return sorted(path for path in root.glob("*.json") if path.is_file())


def _resolve_repo_ref(
    ref: Any,
    *,
    repo_root: Path,
    path: str,
    promotion_id: str,
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
                promotion_id=promotion_id,
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
            promotion_id=promotion_id,
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
            promotion_id=promotion_id,
            extra={"field": field, "ref": ref_text},
        )
    return {"path": ref_text, "exists": exists, "status": "pass" if exists else "fail"}


def _resolve_ref_list(
    value: Any,
    *,
    repo_root: Path,
    path: str,
    promotion_id: str,
    field: str,
    errors: list[dict[str, Any]],
    required: bool = True,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        if required:
            _error(
                errors,
                "missing_ref_list",
                f"{field} must contain at least one repository-relative path",
                path,
                promotion_id=promotion_id,
                extra={"field": field},
            )
        return []
    return [
        _resolve_repo_ref(
            ref,
            repo_root=repo_root,
            path=path,
            promotion_id=promotion_id,
            field=field,
            errors=errors,
        )
        for ref in value
    ]


def _validate_history(
    promotion: dict[str, Any],
    *,
    repo_root: Path,
    path: str,
    promotion_id: str,
    current_state: str,
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    history = promotion.get("state_history")
    reports: list[dict[str, Any]] = []
    if not isinstance(history, list) or not history:
        _error(errors, "missing_state_history", "promotion must contain state_history[]", path, promotion_id=promotion_id)
        return reports

    indices: list[int] = []
    seen: set[str] = set()
    current_entries: list[str] = []
    for index, entry in enumerate(history):
        if not isinstance(entry, dict):
            _error(
                errors,
                "invalid_state_history",
                "state_history entries must be objects",
                path,
                promotion_id=promotion_id,
                extra={"index": index},
            )
            continue
        state = str(entry.get("state", "")).strip()
        status = str(entry.get("status", "")).strip()
        owner_role = str(entry.get("owner_role", "")).strip()
        if state not in STATE_INDEX:
            _error(errors, "unknown_state", "state_history state must be in the promotion lifecycle", path, promotion_id=promotion_id, extra={"state": state})
            state_index = -1
        else:
            state_index = STATE_INDEX[state]
            indices.append(state_index)
        if state in seen:
            _error(errors, "duplicate_state_history", "state_history cannot repeat a state", path, promotion_id=promotion_id, extra={"state": state})
        seen.add(state)
        if status not in VALID_HISTORY_STATUSES:
            _error(
                errors,
                "invalid_state_history_status",
                f"state_history status must be one of {sorted(VALID_HISTORY_STATUSES)}",
                path,
                promotion_id=promotion_id,
                extra={"status": status},
            )
        if status == "current":
            current_entries.append(state)
        if not owner_role:
            _error(errors, "blank_state_owner", "state_history owner_role must be non-empty", path, promotion_id=promotion_id)
        evidence = _resolve_ref_list(
            entry.get("evidence_refs"),
            repo_root=repo_root,
            path=path,
            promotion_id=promotion_id,
            field="state_history.evidence_refs",
            errors=errors,
        )
        reports.append(
            {
                "state": state,
                "order": state_index + 1 if state_index >= 0 else None,
                "status": status,
                "owner_role": owner_role,
                "evidence_refs": evidence,
                "decided_at": str(entry.get("decided_at", "")),
            }
        )

    if indices != sorted(indices):
        _error(errors, "state_history_order", "state_history must follow the policy promotion lifecycle", path, promotion_id=promotion_id, extra={"actual": indices})
    if indices:
        expected = list(range(indices[0], indices[-1] + 1))
        if indices != expected:
            _error(
                errors,
                "state_history_gap",
                "state_history must be gap-free from first recorded state to current state",
                path,
                promotion_id=promotion_id,
                extra={"expected": expected, "actual": indices},
            )
    if current_state not in current_entries:
        _error(
            errors,
            "current_state_missing",
            "state_history must contain one current entry matching current_state",
            path,
            promotion_id=promotion_id,
            extra={"current_state": current_state, "current_entries": current_entries},
        )
    if len(current_entries) != 1:
        _error(
            errors,
            "invalid_current_state_count",
            "state_history must contain exactly one current entry",
            path,
            promotion_id=promotion_id,
            extra={"current_entries": current_entries},
        )
    return reports


def _validate_promotion(
    promotion: dict[str, Any],
    *,
    repo_root: Path,
    path: Path,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    rel_path = _repo_relative(path, repo_root) or path.as_posix()
    start_errors = len(errors)
    promotion_id = str(promotion.get("id", "")).strip() or "<missing-id>"

    if promotion.get("schema_version") != 1:
        _error(errors, "invalid_schema_version", "policy promotion schema_version must be 1", rel_path, promotion_id=promotion_id)
    for field in ("id", "title", "current_state", "owner_office", "owner_role", "created_at", "updated_at"):
        if not _non_empty_string(promotion.get(field)):
            _error(
                errors,
                "blank_required_field",
                f"policy promotion field {field!r} must be non-empty",
                rel_path,
                promotion_id=promotion_id,
                extra={"field": field},
            )

    current_state = str(promotion.get("current_state", "")).strip()
    if current_state not in STATE_INDEX:
        _error(errors, "unknown_state", "current_state must be in the policy promotion lifecycle", rel_path, promotion_id=promotion_id, extra={"current_state": current_state})
    owner_office = str(promotion.get("owner_office", "")).strip()
    owner_role = str(promotion.get("owner_role", "")).strip()
    if owner_office != "learning-governance":
        _error(
            errors,
            "owner_office_mismatch",
            "policy promotions must be owned by learning-governance",
            rel_path,
            promotion_id=promotion_id,
            extra={"actual": owner_office},
        )
    if owner_role != "policy-steward":
        _error(
            errors,
            "owner_role_mismatch",
            "policy promotions must be owned by policy-steward",
            rel_path,
            promotion_id=promotion_id,
            extra={"actual": owner_role},
        )

    source_refs = _resolve_ref_list(
        promotion.get("source_refs"),
        repo_root=repo_root,
        path=rel_path,
        promotion_id=promotion_id,
        field="source_refs",
        errors=errors,
    )
    evidence_refs = _resolve_ref_list(
        promotion.get("evidence_refs"),
        repo_root=repo_root,
        path=rel_path,
        promotion_id=promotion_id,
        field="evidence_refs",
        errors=errors,
    )
    if not _non_empty_list(promotion.get("acceptance_criteria")):
        _error(errors, "missing_acceptance_criteria", "policy promotions must have acceptance_criteria[]", rel_path, promotion_id=promotion_id)

    if current_state in {"candidate_policy", "policy", "gate_candidate", "gate", "retired"} and not _non_empty_string(promotion.get("policy_text")):
        _error(errors, "missing_policy_text", "candidate policies and later states must contain policy_text", rel_path, promotion_id=promotion_id)
    if current_state in {"policy", "gate_candidate", "gate", "retired"} and not _non_empty_string(promotion.get("rollback_plan")):
        _error(errors, "missing_rollback_plan", "policies and later states must contain rollback_plan", rel_path, promotion_id=promotion_id)

    gate_refs = _resolve_ref_list(
        promotion.get("gate_refs"),
        repo_root=repo_root,
        path=rel_path,
        promotion_id=promotion_id,
        field="gate_refs",
        errors=errors,
        required=current_state in {"gate_candidate", "gate"},
    )
    test_refs = _resolve_ref_list(
        promotion.get("test_refs"),
        repo_root=repo_root,
        path=rel_path,
        promotion_id=promotion_id,
        field="test_refs",
        errors=errors,
        required=False,
    )
    schema_refs = _resolve_ref_list(
        promotion.get("schema_refs"),
        repo_root=repo_root,
        path=rel_path,
        promotion_id=promotion_id,
        field="schema_refs",
        errors=errors,
        required=False,
    )
    if current_state in {"gate_candidate", "gate"}:
        if not test_refs:
            _error(errors, "missing_gate_test_refs", "gate candidates and gates must include test_refs[]", rel_path, promotion_id=promotion_id)
        if not schema_refs:
            _error(errors, "missing_gate_schema_refs", "gate candidates and gates must include schema_refs[]", rel_path, promotion_id=promotion_id)

    replacement_refs = _resolve_ref_list(
        promotion.get("replacement_refs"),
        repo_root=repo_root,
        path=rel_path,
        promotion_id=promotion_id,
        field="replacement_refs",
        errors=errors,
        required=False,
    )
    retired_reason = str(promotion.get("retired_reason", "")).strip()
    if current_state == "retired":
        if not retired_reason:
            _error(errors, "missing_retired_reason", "retired promotions must explain why they were retired", rel_path, promotion_id=promotion_id)
        if not replacement_refs:
            _error(errors, "missing_replacement_refs", "retired promotions must point to replacement_refs[]", rel_path, promotion_id=promotion_id)

    state_history = _validate_history(
        promotion,
        repo_root=repo_root,
        path=rel_path,
        promotion_id=promotion_id,
        current_state=current_state,
        errors=errors,
    )

    safety = promotion.get("safety") if isinstance(promotion.get("safety"), dict) else {}
    for key, expected in {
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "auto_runtime_launch": False,
        "irreversible_actions": 0,
    }.items():
        if safety.get(key) != expected:
            _error(
                errors,
                "unsafe_policy_promotion",
                f"policy promotion safety field {key!r} must be {expected!r}",
                rel_path,
                promotion_id=promotion_id,
                extra={"field": key, "expected": expected, "actual": safety.get(key)},
            )

    return {
        "id": promotion_id,
        "path": rel_path,
        "title": str(promotion.get("title", "")),
        "current_state": current_state,
        "owner_office": owner_office,
        "owner_role": owner_role,
        "created_at": str(promotion.get("created_at", "")),
        "updated_at": str(promotion.get("updated_at", "")),
        "source_refs": source_refs,
        "evidence_refs": evidence_refs,
        "acceptance_criteria": promotion.get("acceptance_criteria") if isinstance(promotion.get("acceptance_criteria"), list) else [],
        "rollback_plan": str(promotion.get("rollback_plan", "")),
        "policy_text": str(promotion.get("policy_text", "")),
        "gate_refs": gate_refs,
        "test_refs": test_refs,
        "schema_refs": schema_refs,
        "replacement_refs": replacement_refs,
        "retired_reason": retired_reason,
        "state_history": state_history,
        "safety": {
            "mutates_files_by_default": safety.get("mutates_files_by_default"),
            "external_telemetry": safety.get("external_telemetry"),
            "auto_runtime_launch": safety.get("auto_runtime_launch"),
            "irreversible_actions": safety.get("irreversible_actions"),
        },
        "status": "pass" if len(errors) == start_errors else "fail",
    }


def build_report(repo_root: Path, ledger_root: Path) -> tuple[dict[str, Any], int]:
    repo_root = repo_root.resolve()
    ledger_root = ledger_root if ledger_root.is_absolute() else repo_root / ledger_root
    errors: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    promotions: list[dict[str, Any]] = []

    try:
        files = _ledger_files(ledger_root)
    except PolicyPromotionInputError as exc:
        report = _base_report(
            status="fail",
            ledger_root=str(ledger_root),
            ledger_files=0,
            promotions=[],
            checks=[],
            errors=[{"code": "input_error", "message": str(exc), "path": "<input>"}],
        )
        return report, 1

    if not files:
        _error(errors, "missing_policy_promotions", "policy promotion ledger must contain at least one JSON file", _repo_relative(ledger_root, repo_root) or str(ledger_root))
    for path in files:
        try:
            promotion = _load_json(path)
        except PolicyPromotionInputError as exc:
            _error(errors, "input_error", str(exc), _repo_relative(path, repo_root) or path.as_posix())
            continue
        promotions.append(_validate_promotion(promotion, repo_root=repo_root, path=path, errors=errors))

    _check(
        checks,
        "policy_promotion_lifecycle_defined",
        "pass",
        "policy promotion lifecycle is fixed and ordered",
        expected=STATE_ORDER,
        actual=STATE_ORDER,
    )
    _check(
        checks,
        "policy_promotion_read_only",
        "pass",
        "policy promotion ledger gate is read-only",
        expected={"mutates_files_by_default": False, "irreversible_actions": 0},
        actual={"mutates_files_by_default": False, "irreversible_actions": 0},
    )
    if any(promotion.get("current_state") == "gate" for promotion in promotions):
        _check(checks, "policy_promotion_gate_present", "pass", "at least one promotion has reached gate state")
    if any(promotion.get("current_state") == "retired" for promotion in promotions):
        _check(checks, "policy_promotion_retirement_present", "pass", "at least one promotion has a retirement path")

    status = "fail" if errors else "pass"
    report = _base_report(
        status=status,
        ledger_root=_repo_relative(ledger_root, repo_root) or str(ledger_root),
        ledger_files=len(files),
        promotions=promotions,
        checks=checks,
        errors=errors,
    )
    return report, 1 if errors else 0


def _base_report(
    *,
    status: str,
    ledger_root: str,
    ledger_files: int,
    promotions: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    state_counts = {state: 0 for state in STATE_ORDER}
    for promotion in promotions:
        state = promotion.get("current_state")
        if state in state_counts:
            state_counts[state] += 1
    return {
        "schema_version": 1,
        "status": status,
        "generated_at": _iso_now(),
        "profile": {
            "id": "policy-promotion-ledger",
            "description": "Read-only gate for learning-governance policy promotion state.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
        },
        "summary": {
            "checks": len(checks),
            "errors": len(errors),
            "warnings": len([check for check in checks if check.get("status") == "warn"]),
            "promotions": len(promotions),
            "gate_promotions": state_counts["gate"],
            "retired_promotions": state_counts["retired"],
            "irreversible_actions": 0,
        },
        "lifecycle": STATE_ORDER,
        "ledger": {"path": ledger_root, "files": ledger_files},
        "state_counts": state_counts,
        "promotions": promotions,
        "checks": checks,
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger-root", type=Path, default=DEFAULT_LEDGER_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    report, exit_code = build_report(args.repo_root, args.ledger_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "policy-promotion-ledger "
            f"status={report['status']} promotions={report['summary']['promotions']} "
            f"errors={report['summary']['errors']}"
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
