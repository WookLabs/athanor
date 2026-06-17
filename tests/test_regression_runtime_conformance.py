"""Regression tests for cross-runtime conformance.

P9 turns the Claude/Codex companion relationship into an executable contract:
the gate should catch drift without generating manifests or installing hooks.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_CONTRACT = REPO_ROOT / "docs" / "runtime-surface-contract.json"
RUNTIME_DOC = REPO_ROOT / "docs" / "runtime-conformance.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
