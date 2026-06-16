"""Regression tests for v0.19.0 evidence-bound Spec-then-TDD gate.

The gate consumes PostToolUse pytest evidence JSONL and a normalized
ATHANOR_RESULT JSON object. It is hybrid in v1:

- evidence mismatch => failure
- evidence missing => concern
- evidence match => pass
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_WORK = REPO_ROOT / "scripts" / "work"
GATE_SCRIPT = SCRIPTS_WORK / "evidence_gate.py"

if str(SCRIPTS_WORK) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_WORK))


@pytest.fixture
def gate():
    sys.modules.pop("evidence_gate", None)
    return importlib.import_module("evidence_gate")


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n",
        encoding="utf-8",
    )
    return path


def _result(
    *,
    red_exit: int = 1,
    full_suite_passed: bool = True,
    command: str = "python -m pytest tests/test_demo.py::test_red -v",
) -> dict:
    return {
        "execution_note": "spec-then-tdd",
        "red_evidence": [
            {
                "criterion": "MUST prove red",
                "command": command,
                "test_node_id": "tests/test_demo.py::test_red",
                "exit_code": red_exit,
                "output_tail": "FAILED tests/test_demo.py::test_red",
            }
        ],
        "full_suite_passed": full_suite_passed,
        "verification": "pytest tests/ -> pass",
    }


def test_script_exists_and_has_python_shebang():
    assert GATE_SCRIPT.is_file(), f"missing {GATE_SCRIPT}"
    first = GATE_SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("#!") and "python" in first


def test_evaluate_result_is_importable(gate):
    assert hasattr(gate, "evaluate_result_against_evidence")
    assert callable(gate.evaluate_result_against_evidence)


def test_matching_red_and_full_suite_evidence_passes(gate, tmp_path):
    evidence = _write_jsonl(
        tmp_path / "test-evidence.jsonl",
        [
            {
                "schema_version": 1,
                "command": "python -m pytest tests/test_demo.py::test_red -v",
                "test_targets": ["tests/test_demo.py::test_red"],
                "scope": "targeted",
                "exit_code": 1,
                "output_tail": "FAILED tests/test_demo.py::test_red",
                "timestamp": "2026-06-14T00:00:00+00:00",
                "session_id": "2026-06-14-001",
            },
            {
                "schema_version": 1,
                "command": "pytest tests/ -q",
                "test_targets": ["tests/"],
                "scope": "full_suite",
                "exit_code": 0,
                "output_tail": "980 passed",
                "timestamp": "2026-06-14T00:01:00+00:00",
                "session_id": "2026-06-14-001",
            },
        ],
    )

    report = gate.evaluate_result_against_evidence(_result(), evidence)

    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["concerns"] == []
    assert {m["kind"] for m in report["matches"]} == {"red_evidence", "full_suite"}


def test_red_evidence_exit_code_mismatch_fails(gate, tmp_path):
    evidence = _write_jsonl(
        tmp_path / "test-evidence.jsonl",
        [
            {
                "command": "python -m pytest tests/test_demo.py::test_red -v",
                "test_targets": ["tests/test_demo.py::test_red"],
                "scope": "targeted",
                "exit_code": 0,
            }
        ],
    )

    report = gate.evaluate_result_against_evidence(_result(red_exit=1), evidence)

    assert report["status"] == "failure"
    assert any("exit code mismatch" in item for item in report["failures"])


def test_missing_red_evidence_is_concern_not_failure(gate, tmp_path):
    evidence = _write_jsonl(
        tmp_path / "test-evidence.jsonl",
        [
            {
                "command": "pytest tests/ -q",
                "test_targets": ["tests/"],
                "scope": "full_suite",
                "exit_code": 0,
            }
        ],
    )

    report = gate.evaluate_result_against_evidence(_result(), evidence)

    assert report["status"] == "concern"
    assert report["failures"] == []
    assert any("missing evidence" in item for item in report["concerns"])


def test_observe_mode_reports_missing_evidence_without_gate_status(gate, tmp_path):
    report = gate.evaluate_result_against_evidence(
        _result(),
        tmp_path / "missing.jsonl",
        mode="observe",
    )

    assert report["mode"] == "observe"
    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["concerns"] == []
    assert any("missing evidence" in item for item in report["observations"])


def test_strict_mode_promotes_missing_evidence_to_failure(gate, tmp_path):
    report = gate.evaluate_result_against_evidence(
        _result(),
        tmp_path / "missing.jsonl",
        mode="strict",
    )

    assert report["mode"] == "strict"
    assert report["status"] == "failure"
    assert report["concerns"] == []
    assert any("missing evidence" in item for item in report["failures"])


def test_observe_mode_demotes_mismatch_to_observation(gate, tmp_path):
    evidence = _write_jsonl(
        tmp_path / "test-evidence.jsonl",
        [
            {
                "command": "python -m pytest tests/test_demo.py::test_red -v",
                "test_targets": ["tests/test_demo.py::test_red"],
                "scope": "targeted",
                "exit_code": 0,
            }
        ],
    )

    report = gate.evaluate_result_against_evidence(
        _result(red_exit=1),
        evidence,
        mode="observe",
    )

    assert report["status"] == "pass"
    assert report["failures"] == []
    assert any("exit code mismatch" in item for item in report["observations"])


def test_full_suite_true_with_nonzero_latest_full_suite_fails(gate, tmp_path):
    evidence = _write_jsonl(
        tmp_path / "test-evidence.jsonl",
        [
            {
                "command": "pytest tests/ -q",
                "test_targets": ["tests/"],
                "scope": "full_suite",
                "exit_code": 0,
            },
            {
                "command": "python -m pytest tests",
                "test_targets": ["tests"],
                "scope": "full_suite",
                "exit_code": 1,
            },
        ],
    )

    report = gate.evaluate_result_against_evidence(
        {"full_suite_passed": True, "red_evidence": []},
        evidence,
    )

    assert report["status"] == "failure"
    assert any("full_suite_passed=true" in item for item in report["failures"])


def test_missing_evidence_file_is_concern(gate, tmp_path):
    report = gate.evaluate_result_against_evidence(_result(), tmp_path / "missing.jsonl")

    assert report["status"] == "concern"
    assert report["failures"] == []
    assert any("evidence file missing" in item for item in report["concerns"])


def test_malformed_jsonl_lines_are_concerns_but_valid_lines_still_used(gate, tmp_path):
    path = tmp_path / "test-evidence.jsonl"
    path.write_text(
        '{"command":"pytest tests/ -q","scope":"full_suite","exit_code":0}\n'
        'not valid json\n',
        encoding="utf-8",
    )

    report = gate.evaluate_result_against_evidence(
        {"full_suite_passed": True, "red_evidence": []},
        path,
    )

    assert report["status"] == "concern"
    assert any("malformed JSONL" in item for item in report["concerns"])
    assert any(m["kind"] == "full_suite" for m in report["matches"])


def test_cli_reads_result_from_stdin_and_writes_json(gate, tmp_path):
    evidence = _write_jsonl(
        tmp_path / "test-evidence.jsonl",
        [
            {
                "command": "python -m pytest tests/test_demo.py::test_red -v",
                "test_targets": ["tests/test_demo.py::test_red"],
                "scope": "targeted",
                "exit_code": 1,
            },
            {
                "command": "pytest tests/ -q",
                "test_targets": ["tests/"],
                "scope": "full_suite",
                "exit_code": 0,
            },
        ],
    )

    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--evidence", str(evidence), "--result-json", "-"],
        input=json.dumps(_result()),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0
    parsed = json.loads(proc.stdout)
    assert parsed["status"] == "pass"
    assert proc.stderr == ""


def test_cli_strict_mode_returns_one_on_missing_evidence(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--evidence",
            str(tmp_path / "missing.jsonl"),
            "--result-json",
            "-",
            "--mode",
            "strict",
        ],
        input=json.dumps(_result()),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 1
    parsed = json.loads(proc.stdout)
    assert parsed["status"] == "failure"
    assert parsed["mode"] == "strict"


def test_cli_returns_one_on_failure(tmp_path):
    evidence = _write_jsonl(
        tmp_path / "test-evidence.jsonl",
        [
            {
                "command": "python -m pytest tests/test_demo.py::test_red -v",
                "test_targets": ["tests/test_demo.py::test_red"],
                "scope": "targeted",
                "exit_code": 0,
            }
        ],
    )

    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--evidence", str(evidence), "--result-json", "-"],
        input=json.dumps(_result(red_exit=1)),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 1
    parsed = json.loads(proc.stdout)
    assert parsed["status"] == "failure"


def test_cli_returns_two_on_invalid_result_json(tmp_path):
    evidence = _write_jsonl(tmp_path / "test-evidence.jsonl", [])

    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--evidence", str(evidence), "--result-json", "-"],
        input="not json",
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 2
    assert "invalid result json" in proc.stderr.lower()
