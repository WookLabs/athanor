"""Regression tests for v0.19.0 Freeze change evidence concern gate."""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_WORK = REPO_ROOT / "scripts" / "work"
GATE_SCRIPT = SCRIPTS_WORK / "freeze_evidence_gate.py"

if str(SCRIPTS_WORK) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_WORK))


def _gate():
    sys.modules.pop("freeze_evidence_gate", None)
    return importlib.import_module("freeze_evidence_gate")


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def test_missing_evidence_file_returns_pass(tmp_path):
    report = _gate().evaluate_freeze_evidence(tmp_path / "missing.jsonl")

    assert report["status"] == "pass"
    assert report["concerns"] == []
    assert report["observed_paths"] == 0


def test_in_allowlist_evidence_returns_pass(tmp_path):
    evidence = _write_jsonl(
        tmp_path / "freeze-change-evidence.jsonl",
        [
            {
                "schema_version": 1,
                "paths": [
                    {
                        "path": "src/foo.py",
                        "source": "tool_input.file_path",
                        "allowlist_status": "in_allowlist",
                    }
                ],
            }
        ],
    )

    report = _gate().evaluate_freeze_evidence(evidence)

    assert report["status"] == "pass"
    assert report["concerns"] == []
    assert report["observed_paths"] == 1


def test_out_of_allowlist_evidence_returns_concern(tmp_path):
    evidence = _write_jsonl(
        tmp_path / "freeze-change-evidence.jsonl",
        [
            {
                "schema_version": 1,
                "tool_name": "Bash",
                "paths": [
                    {
                        "path": "src/secret.py",
                        "source": "tool_response.files_changed",
                        "allowlist_status": "out_of_allowlist",
                    }
                ],
            }
        ],
    )

    report = _gate().evaluate_freeze_evidence(evidence)

    assert report["status"] == "concern"
    assert report["observed_paths"] == 1
    assert report["concerns"] == [
        "line 1: src/secret.py is out_of_allowlist via tool_response.files_changed"
    ]


def test_unknown_allowlist_evidence_returns_concern(tmp_path):
    evidence = _write_jsonl(
        tmp_path / "freeze-change-evidence.jsonl",
        [
            {
                "schema_version": 1,
                "paths": [
                    {
                        "path": "src/secret.py",
                        "source": "tool_input.file_path",
                        "allowlist_status": "unknown_allowlist",
                    }
                ],
            }
        ],
    )

    report = _gate().evaluate_freeze_evidence(evidence)

    assert report["status"] == "concern"
    assert report["concerns"] == [
        "line 1: src/secret.py is unknown_allowlist via tool_input.file_path"
    ]


def test_cli_returns_zero_for_concern_and_outputs_json(tmp_path):
    evidence = _write_jsonl(
        tmp_path / "freeze-change-evidence.jsonl",
        [
            {
                "schema_version": 1,
                "paths": [
                    {
                        "path": "src/secret.py",
                        "source": "tool_response.files_changed",
                        "allowlist_status": "out_of_allowlist",
                    }
                ],
            }
        ],
    )

    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--evidence", str(evidence)],
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["status"] == "concern"
    assert report["observed_paths"] == 1


def test_cli_returns_two_for_malformed_jsonl(tmp_path):
    evidence = tmp_path / "freeze-change-evidence.jsonl"
    evidence.write_text("{not json}\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--evidence", str(evidence)],
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 2
    assert "malformed JSONL line 1" in proc.stderr

