#!/usr/bin/env python3
"""Durable state helpers for Athanor lfg-goal loops."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CYCLE_STATES = {
    "aborted",
    "bootstrapping",
    "cycle_n_complete",
    "cycle_n_in_progress",
    "goal_complete",
    "scope_change_pending",
}
CYCLE_PHASES = {
    "lfg_done_seen",
    "not_started",
    "receipt_validated",
    "tier1_checked",
    "tier2_checked",
    "tier3_pending",
    "tier3_ratified",
}
TERMINAL_CYCLE_STATES = {"aborted", "goal_complete"}
VALIDATOR_STATUSES = {
    "all_valid",
    "completed_with_residuals",
    "invalid_steps_present",
    "not_yet_run",
}

REQUIRED_FIELDS = {
    "schema_version",
    "goal_id",
    "cycle_state",
    "cycle_phase",
    "current_cycle",
    "max_iterations",
    "no_progress_threshold",
    "last_receipt_path",
    "last_validator_status",
    "tier2_last_verdict",
    "aborted_reason",
    "no_progress_count",
    "stop_reason",
    "updated_at",
}
LEGACY_OPTIONAL_FIELDS = {"schema_version", "cycle_phase"}
GOAL_ID_RE = re.compile(r"^[0-9a-f]{8}$")


class LoopStateError(ValueError):
    """Raised when durable loop state is malformed or contradictory."""


def _require_object(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise LoopStateError("state root must be an object")
    return data


def _require_int(value: Any, field_name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LoopStateError(f"{field_name} must be an integer")
    if minimum is not None and value < minimum:
        raise LoopStateError(f"{field_name} must be >= {minimum}")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise LoopStateError(f"{field_name} must be a non-empty string or null")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise LoopStateError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class LoopState:
    """Validated durable lfg-goal loop state."""

    schema_version: int
    goal_id: str
    cycle_state: str
    cycle_phase: str | None
    current_cycle: int
    max_iterations: int
    no_progress_threshold: int
    last_receipt_path: str | None
    last_validator_status: str
    tier2_last_verdict: dict[str, Any] | None
    aborted_reason: str | None
    no_progress_count: int
    stop_reason: str | None
    updated_at: str
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, raw_data: Any) -> "LoopState":
        data = dict(_require_object(raw_data))
        warnings: list[str] = []

        legacy_missing_schema = "schema_version" not in data
        if legacy_missing_schema:
            warnings.append("legacy_missing_schema_version")
            data["schema_version"] = 1
        elif data.get("schema_version") != 1:
            raise LoopStateError("schema_version must be 1")

        if "cycle_phase" not in data and legacy_missing_schema:
            warnings.append("legacy_missing_phase")
            data["cycle_phase"] = None

        missing = sorted(REQUIRED_FIELDS - set(data))
        if missing:
            raise LoopStateError(f"missing required fields: {missing}")

        goal_id = _require_string(data["goal_id"], "goal_id")
        if not GOAL_ID_RE.match(goal_id):
            raise LoopStateError("goal_id must be 8 lowercase hex characters")

        cycle_state = _require_string(data["cycle_state"], "cycle_state")
        if cycle_state not in CYCLE_STATES:
            raise LoopStateError(f"unsupported cycle_state: {cycle_state}")

        cycle_phase = data["cycle_phase"]
        if cycle_phase is not None:
            cycle_phase = _require_string(cycle_phase, "cycle_phase")
            if cycle_phase not in CYCLE_PHASES:
                raise LoopStateError(f"unsupported cycle_phase: {cycle_phase}")

        if cycle_state == "cycle_n_in_progress" and cycle_phase is None and not warnings:
            raise LoopStateError("cycle_phase is required for cycle_n_in_progress")
        if cycle_state != "cycle_n_in_progress" and cycle_phase is not None:
            raise LoopStateError("cycle_phase must be null outside cycle_n_in_progress")

        max_iterations = _require_int(data["max_iterations"], "max_iterations", minimum=1)
        current_cycle = _require_int(data["current_cycle"], "current_cycle", minimum=0)
        if current_cycle > max_iterations:
            raise LoopStateError("current_cycle must be <= max_iterations")

        no_progress_threshold = _require_int(
            data["no_progress_threshold"], "no_progress_threshold", minimum=1
        )
        no_progress_count = _require_int(
            data["no_progress_count"], "no_progress_count", minimum=0
        )
        if no_progress_count > no_progress_threshold:
            raise LoopStateError("no_progress_count must be <= no_progress_threshold")

        last_validator_status = _require_string(
            data["last_validator_status"], "last_validator_status"
        )
        if last_validator_status not in VALIDATOR_STATUSES:
            raise LoopStateError(
                f"unsupported last_validator_status: {last_validator_status}"
            )

        tier2_last_verdict = data["tier2_last_verdict"]
        if tier2_last_verdict is not None and not isinstance(tier2_last_verdict, dict):
            raise LoopStateError("tier2_last_verdict must be an object or null")

        return cls(
            schema_version=1,
            goal_id=goal_id,
            cycle_state=cycle_state,
            cycle_phase=cycle_phase,
            current_cycle=current_cycle,
            max_iterations=max_iterations,
            no_progress_threshold=no_progress_threshold,
            last_receipt_path=_require_optional_string(
                data["last_receipt_path"], "last_receipt_path"
            ),
            last_validator_status=last_validator_status,
            tier2_last_verdict=tier2_last_verdict,
            aborted_reason=_require_optional_string(
                data["aborted_reason"], "aborted_reason"
            ),
            no_progress_count=no_progress_count,
            stop_reason=_require_optional_string(data["stop_reason"], "stop_reason"),
            updated_at=_require_string(data["updated_at"], "updated_at"),
            warnings=tuple(warnings),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "goal_id": self.goal_id,
            "cycle_state": self.cycle_state,
            "cycle_phase": self.cycle_phase,
            "current_cycle": self.current_cycle,
            "max_iterations": self.max_iterations,
            "no_progress_threshold": self.no_progress_threshold,
            "last_receipt_path": self.last_receipt_path,
            "last_validator_status": self.last_validator_status,
            "tier2_last_verdict": self.tier2_last_verdict,
            "aborted_reason": self.aborted_reason,
            "no_progress_count": self.no_progress_count,
            "stop_reason": self.stop_reason,
            "updated_at": self.updated_at,
        }


def is_terminal_state(state: LoopState) -> bool:
    return state.cycle_state in TERMINAL_CYCLE_STATES


def load_loop_state(path: Path | str) -> LoopState:
    state_path = Path(path)
    try:
        parsed = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoopStateError(f"malformed state JSON: {exc.msg}") from exc
    except OSError as exc:
        raise LoopStateError(f"could not read state file: {state_path}") from exc
    return LoopState.from_dict(parsed)


def write_loop_state_atomic(path: Path | str, state: LoopState) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_name(f"{state_path.name}.tmp")
    temp_path.write_text(
        json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(state_path)
