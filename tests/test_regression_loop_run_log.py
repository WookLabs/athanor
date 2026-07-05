"""Regression tests for lfg-loop append-only run logs and loop safety gates."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema

from scripts.loops.loop_run_log import (
    append_run_record,
    inspect_loop_dir,
    load_run_log,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = REPO_ROOT / "schemas" / "loop-run-log-record.schema.json"
FIXTURE_GOAL = REPO_ROOT / "tests" / "fixtures" / "loop_run_log" / "loop"
SCRIPT = REPO_ROOT / "scripts" / "loops" / "loop_run_log.py"
STATE_SHAPE = REPO_ROOT / "skills" / "lfg-loop" / "references" / "state-shape.md"
LFG_GOAL = REPO_ROOT / "skills" / "lfg-loop" / "SKILL.md"
DOC = REPO_ROOT / "docs" / "durable-loop-controller.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_goal(tmp_path: Path) -> Path:
    loop_dir = tmp_path / "loop"
    shutil.copytree(FIXTURE_GOAL, loop_dir)
    return loop_dir


def test_loop_run_record_schema_accepts_append_record(tmp_path: Path) -> None:
    loop_dir = _copy_goal(tmp_path)
    record = append_run_record(loop_dir, event="cycle_started")

    jsonschema.validate(record, _load_json(SCHEMA))
    assert record["schema_version"] == 1
    assert record["loop_id"] == "36470e54"
    assert record["sequence"] == 1
    assert record["event"] == "cycle_started"
    assert record["irreversible_actions"] == 0


def test_append_writer_is_jsonl_append_only(tmp_path: Path) -> None:
    loop_dir = _copy_goal(tmp_path)

    first = append_run_record(loop_dir, event="cycle_started")
    second = append_run_record(loop_dir, event="cycle_finished", status="pass")

    records = load_run_log(loop_dir)
    assert [item["sequence"] for item in records] == [1, 2]
    assert records[0] == first
    assert records[1] == second

    raw_lines = (loop_dir / "run-log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 2
    assert json.loads(raw_lines[0])["event"] == "cycle_started"


def test_inspect_reports_lock_conflict_when_acting_on_differs(tmp_path: Path) -> None:
    loop_dir = _copy_goal(tmp_path)

    report = inspect_loop_dir(loop_dir, requested_loop_id="ffffffff")

    assert report["status"] == "warn"
    assert report["lock_status"] == "conflict"
    assert report["lock_conflict"] == {
        "acting_on": "36470e54",
        "requested_loop_id": "ffffffff",
    }
    assert report["summary"]["irreversible_actions"] == 0


def test_inspect_reports_budget_warnings(tmp_path: Path) -> None:
    loop_dir = _copy_goal(tmp_path)

    report = inspect_loop_dir(
        loop_dir,
        current_cycle=3,
        wall_minutes_used=130,
        token_estimate_used=51000,
    )

    assert report["status"] == "warn"
    assert set(report["budget_warnings"]) == {
        "max_cycles_reached",
        "max_wall_minutes_reached",
        "max_token_estimate_reached",
    }


def test_inspect_blocks_risky_or_high_score_target_until_min_attempts(
    tmp_path: Path,
) -> None:
    loop_dir = _copy_goal(tmp_path)

    risky_report = inspect_loop_dir(loop_dir, task_risk="risky", attempts_done=1)
    score_report = inspect_loop_dir(loop_dir, score_target=True, attempts_done=1)

    assert risky_report["min_attempt_gate"]["status"] == "blocked"
    assert score_report["min_attempt_gate"]["status"] == "blocked"
    assert risky_report["min_attempt_gate"]["required"] == 2


def test_cli_append_and_inspect_emit_json(tmp_path: Path) -> None:
    loop_dir = _copy_goal(tmp_path)

    append_result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "append",
            "--loop-dir",
            str(loop_dir),
            "--event",
            "cycle_started",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert append_result.returncode == 0, append_result.stderr
    appended = json.loads(append_result.stdout)
    assert appended["event"] == "cycle_started"

    inspect_result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "inspect",
            "--loop-dir",
            str(loop_dir),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert inspect_result.returncode == 0, inspect_result.stderr
    report = json.loads(inspect_result.stdout)
    assert report["summary"]["records"] == 1
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["summary"]["irreversible_actions"] == 0


def test_docs_and_state_shape_describe_new_loop_run_fields() -> None:
    state_shape = STATE_SHAPE.read_text(encoding="utf-8")
    skill = LFG_GOAL.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    for token in (
        "acting_on",
        "loop_run_log",
        "budget.max_cycles",
        "budget.max_wall_minutes",
        "budget.max_token_estimate",
        "min_attempts",
        "last_evaluator_role",
        "lock_status",
    ):
        assert token in state_shape

    assert "append-only run log" in skill
    assert "min-attempt gate" in skill
    assert "lock conflict" in skill
    assert "loop_run_log.py" in doc
