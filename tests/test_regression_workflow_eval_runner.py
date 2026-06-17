"""Regression tests for deterministic workflow scenario evals."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "evals" / "run_workflow_scenarios.py"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record(seq: int, event_type: str, status: str, *, references: list[str] | None = None) -> dict:
    record = {
        "schema_version": 1,
        "trace_id": "trace-work",
        "seq": seq,
        "phase": "work",
        "event_type": event_type,
        "actor": "gate" if event_type == "verifier.result" else "leader",
        "status": status,
        "message": event_type,
    }
    if references is not None:
        record["references"] = references
    return record


def _run_eval(scenario_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--scenario-root",
            str(scenario_root),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def test_eval_runner_scores_required_event_and_order(tmp_path: Path) -> None:
    scenario_root = tmp_path / "scenarios"
    _write_json(
        scenario_root / "work.json",
        {
            "schema_version": 1,
            "scenarios": [
                {
                    "id": "work-happy",
                    "description": "work emits evidence before finish",
                    "min_score": 1.0,
                    "trace": [
                        _record(1, "workflow.started", "started"),
                        _record(
                            2,
                            "verifier.result",
                            "pass",
                            references=[".hook-state/test-evidence.jsonl"],
                        ),
                        _record(3, "workflow.finished", "pass"),
                    ],
                    "graders": [
                        {
                            "id": "requires-verifier-pass",
                            "kind": "require_event",
                            "match": {
                                "event_type": "verifier.result",
                                "status": "pass",
                            },
                        },
                        {
                            "id": "evidence-before-finish",
                            "kind": "require_order",
                            "before": {"event_type": "verifier.result"},
                            "after": {"event_type": "workflow.finished"},
                        },
                        {
                            "id": "references-test-evidence",
                            "kind": "require_reference",
                            "match": {"event_type": "verifier.result"},
                            "reference": "test-evidence.jsonl",
                        },
                    ],
                }
            ],
        },
    )

    proc = _run_eval(scenario_root)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["scenarios"][0]["score"] == 1.0
    assert all(item["status"] == "pass" for item in report["scenarios"][0]["graders"])


def test_eval_runner_fails_when_required_escalation_is_missing(tmp_path: Path) -> None:
    scenario_root = tmp_path / "scenarios"
    _write_json(
        scenario_root / "missing-escalation.json",
        {
            "schema_version": 1,
            "scenarios": [
                {
                    "id": "work-missing-evidence",
                    "description": "missing evidence must escalate",
                    "min_score": 1.0,
                    "trace": [
                        _record(1, "workflow.started", "started"),
                        _record(2, "verifier.result", "concern"),
                        _record(3, "workflow.finished", "concern"),
                    ],
                    "graders": [
                        {
                            "id": "missing-evidence-escalates",
                            "kind": "require_event",
                            "match": {"event_type": "escalation.required"},
                        }
                    ],
                }
            ],
        },
    )

    proc = _run_eval(scenario_root)

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    scenario = report["scenarios"][0]
    assert scenario["status"] == "fail"
    assert scenario["graders"][0]["status"] == "fail"


def test_committed_workflow_eval_scenarios_pass() -> None:
    proc = _run_eval(REPO_ROOT / "tests" / "fixtures" / "workflow_evals")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert {item["id"] for item in report["scenarios"]} == {
        "work-evidence-happy-path",
        "work-missing-evidence-escalates",
        "lfg-goal-receipt-loop",
    }
    assert all(item["score"] == 1.0 for item in report["scenarios"])
