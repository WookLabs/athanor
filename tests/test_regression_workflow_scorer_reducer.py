"""Regression tests for workflow scorer/reducer metadata."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "evals" / "run_workflow_scenarios.py"
SCHEMA = REPO_ROOT / "schemas" / "workflow-eval-scenario.schema.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record(seq: int, event_type: str, status: str) -> dict:
    return {
        "schema_version": 1,
        "trace_id": "trace-scorer-reducer",
        "seq": seq,
        "phase": "work",
        "event_type": event_type,
        "actor": "leader",
        "status": status,
        "message": event_type,
    }


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


def test_runner_emits_scorer_and_reducer_metadata(tmp_path: Path) -> None:
    scenario_root = tmp_path / "scenarios"
    _write_json(
        scenario_root / "scorer-reducer.json",
        {
            "schema_version": 1,
            "scenarios": [
                {
                    "id": "scorer-reducer-profile",
                    "description": "runner exposes deterministic scorer and reducer provenance",
                    "metadata": {
                        "retry_id": "retry-001",
                        "resume_id": "resume-abc",
                    },
                    "min_score": 1.0,
                    "trace": [
                        _record(1, "workflow.started", "started"),
                        _record(2, "workflow.finished", "pass"),
                    ],
                    "graders": [
                        {
                            "id": "started",
                            "kind": "require_event",
                            "scorer_id": "local.require-start",
                            "match": {"event_type": "workflow.started"},
                        },
                        {
                            "id": "finished",
                            "kind": "require_event",
                            "match": {"event_type": "workflow.finished", "status": "pass"},
                        },
                    ],
                }
            ],
        },
    )

    proc = _run_eval(scenario_root)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    scenario = report["scenarios"][0]
    assert scenario["metadata"] == {
        "retry_id": "retry-001",
        "resume_id": "resume-abc",
    }
    assert [grader["scorer_id"] for grader in scenario["graders"]] == [
        "local.require-start",
        "deterministic.require_event",
    ]
    assert scenario["reducer"] == {
        "method": "pass_ratio",
        "sample_limit": 2,
        "score_provenance": [
            {
                "grader_id": "started",
                "scorer_id": "local.require-start",
                "status": "pass",
                "contribution": 1,
            },
            {
                "grader_id": "finished",
                "scorer_id": "deterministic.require_event",
                "status": "pass",
                "contribution": 1,
            },
        ],
    }


def test_committed_scenarios_keep_old_shape_and_add_profile_metadata() -> None:
    proc = _run_eval(REPO_ROOT / "tests" / "fixtures" / "workflow_evals")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    for scenario in report["scenarios"]:
        assert {"id", "status", "score", "passed", "total", "graders"} <= set(scenario)
        assert scenario["reducer"]["method"] == "pass_ratio"
        assert scenario["reducer"]["sample_limit"] == scenario["total"]
        assert len(scenario["reducer"]["score_provenance"]) == scenario["total"]
        assert all(grader["scorer_id"] for grader in scenario["graders"])


def test_schema_accepts_retry_resume_metadata_and_scorer_id() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    scenario_props = schema["properties"]["scenarios"]["items"]["properties"]
    metadata = scenario_props["metadata"]
    grader_props = scenario_props["graders"]["items"]["properties"]

    assert metadata["additionalProperties"] is False
    assert {"retry_id", "resume_id"} <= set(metadata["properties"])
    assert metadata["properties"]["retry_id"]["minLength"] == 1
    assert metadata["properties"]["resume_id"]["minLength"] == 1
    assert grader_props["scorer_id"]["type"] == "string"
    assert grader_props["scorer_id"]["minLength"] == 1


def test_schema_rejects_unknown_grader_fields() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    grader_schema = schema["properties"]["scenarios"]["items"]["properties"]["graders"]["items"]
    jsonschema.validate(
        {
            "id": "started",
            "kind": "require_event",
            "scorer_id": "local.require-start",
            "match": {"event_type": "workflow.started"},
        },
        grader_schema,
    )

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {
                "id": "external-model",
                "kind": "require_event",
                "match": {"event_type": "workflow.started"},
                "model_grader": "not-allowed-in-default-local-profile",
            },
            grader_schema,
        )
