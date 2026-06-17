"""Regression tests for cross-runtime conformance.

P9 turns the Claude/Codex companion relationship into an executable contract:
the gate should catch drift without generating manifests or installing hooks.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_CONTRACT = REPO_ROOT / "docs" / "runtime-surface-contract.json"
RUNTIME_DOC = REPO_ROOT / "docs" / "runtime-conformance.md"
RUNTIME_SCHEMA = REPO_ROOT / "schemas" / "runtime-conformance-report.schema.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_report() -> dict:
    result = subprocess.run(
        [sys.executable, "scripts/gates/runtime_conformance.py", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_runtime_surface_contract_exists_and_names_expected_surfaces():
    contract = _load_json(RUNTIME_CONTRACT)

    assert contract["schema_version"] == 1
    assert contract["claude_plugin"]["name"] == "athanor"
    assert contract["codex_companion"]["name"] == "athanor-codex"
    assert "analyze" in contract["claude_plugin"]["native_skills"]
    assert "athanor-analyze" in contract["codex_companion"]["skills"]
    assert "ce-test-browser" in contract["claude_plugin"]["vendored_claude_only_skills"]
    assert "athanor-ce-test-browser" not in contract["codex_companion"]["skills"]


def test_runtime_conformance_docs_state_non_generator_boundary():
    body = RUNTIME_DOC.read_text(encoding="utf-8")

    for token in (
        "read-only verifier",
        "not a generator",
        "hooks/catalog.json",
        "plugins/athanor-codex",
        "ce-test-browser",
        "Cross-runtime conformance gate",
    ):
        assert token in body


def test_runtime_conformance_cli_reports_pass_on_current_repo():
    report = _run_report()

    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["errors"] == 0
    assert report["surfaces"]["claude"]["plugin_name"] == "athanor"
    assert report["surfaces"]["codex"]["plugin_name"] == "athanor-codex"
    assert report["surfaces"]["hooks"]["enabled_events"] == [
        "PostToolUse",
        "PreToolUse",
        "Stop",
    ]


def test_runtime_conformance_schema_validates_report():
    report = _run_report()
    schema = _load_json(RUNTIME_SCHEMA)

    jsonschema.validate(report, schema)
