"""Regression tests for durable lfg-loop loop state handling."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.loops.lfg_loop_controller import (
    LoopState,
    LoopStateError,
    is_terminal_state,
    load_loop_state,
    write_loop_state_atomic,
)


def _valid_state() -> dict:
    return {
        "schema_version": 1,
        "loop_id": "36470e54",
        "cycle_state": "cycle_n_in_progress",
        "cycle_phase": "receipt_validated",
        "current_cycle": 2,
        "max_iterations": 5,
        "no_progress_threshold": 2,
        "last_receipt_path": ".athanor/loops/36470e54/receipts/C002-lfg-receipt.md",
        "last_validator_status": "all_valid",
        "tier2_last_verdict": None,
        "aborted_reason": None,
        "no_progress_count": 0,
        "stop_reason": None,
        "updated_at": "2026-06-17T08:30:00Z",
    }


def test_loop_state_round_trips_with_atomic_writer(tmp_path: Path) -> None:
    path = tmp_path / ".athanor" / "goals" / "36470e54" / "state.json"
    state = LoopState.from_dict(_valid_state())

    write_loop_state_atomic(path, state)

    loaded = load_loop_state(path)
    assert loaded.loop_id == "36470e54"
    assert loaded.cycle_phase == "receipt_validated"
    assert loaded.to_dict() == state.to_dict()
    assert not list(path.parent.glob("*.tmp"))


def test_loop_state_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(LoopStateError, match="malformed state JSON"):
        load_loop_state(path)


def test_loop_state_rejects_missing_required_field() -> None:
    data = _valid_state()
    data.pop("current_cycle")

    with pytest.raises(LoopStateError, match="missing required fields"):
        LoopState.from_dict(data)


def test_loop_state_rejects_unsupported_enum_value() -> None:
    data = _valid_state()
    data["cycle_state"] = "spinning"

    with pytest.raises(LoopStateError, match="unsupported cycle_state"):
        LoopState.from_dict(data)


def test_loop_state_accepts_legacy_missing_cycle_phase_with_warning() -> None:
    data = _valid_state()
    data.pop("schema_version")
    data.pop("cycle_phase")

    loaded = LoopState.from_dict(data)

    assert loaded.schema_version == 1
    assert loaded.cycle_phase is None
    assert "legacy_missing_schema_version" in loaded.warnings
    assert "legacy_missing_phase" in loaded.warnings


@pytest.mark.parametrize("cycle_state", ["loop_complete", "aborted"])
def test_terminal_loop_states_are_detected(cycle_state: str) -> None:
    data = _valid_state()
    data["cycle_state"] = cycle_state
    data["cycle_phase"] = None
    data["aborted_reason"] = "max iterations reached" if cycle_state == "aborted" else None

    state = LoopState.from_dict(data)

    assert is_terminal_state(state)


def test_loop_state_schema_defines_required_contract() -> None:
    schema = json.loads(
        Path("schemas/durable-loop-state.schema.json").read_text(encoding="utf-8")
    )

    assert schema["properties"]["schema_version"]["const"] == 1
    for field in [
        "loop_id",
        "cycle_state",
        "current_cycle",
        "max_iterations",
        "no_progress_threshold",
        "last_validator_status",
    ]:
        assert field in schema["required"]
