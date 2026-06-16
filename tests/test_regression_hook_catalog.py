"""Regression tests for the hook catalog contract.

The catalog is the safety boundary between currently registered runtime hooks
and future opt-in or capture-only hook expansion.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_PATH = REPO_ROOT / "hooks" / "hooks.json"
CATALOG_PATH = REPO_ROOT / "hooks" / "catalog.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "hook-catalog.schema.json"
DOC_PATH = REPO_ROOT / "docs" / "hook-catalog.md"


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _registered_runtime_hooks() -> dict[tuple[str, str], str]:
    hooks = _load_json(HOOKS_PATH)["hooks"]
    registered: dict[tuple[str, str], str] = {}
    for event, matcher_entries in hooks.items():
        for matcher_entry in matcher_entries:
            matcher = matcher_entry.get("matcher", "")
            for hook in matcher_entry.get("hooks", []):
                command = hook["command"]
                registered[(event, command)] = matcher
    return registered


def _catalog_entries() -> list[dict[str, object]]:
    catalog = _load_json(CATALOG_PATH)
    return catalog["hooks"]


def test_hook_catalog_validates_against_schema():
    schema = _load_json(SCHEMA_PATH)
    catalog = _load_json(CATALOG_PATH)
    jsonschema.validate(instance=catalog, schema=schema)


def test_registered_runtime_hooks_are_cataloged_as_enabled():
    registered = _registered_runtime_hooks()
    cataloged = {
        (entry["event"], entry["command"]): entry
        for entry in _catalog_entries()
        if entry["runtime_default"] == "enabled"
    }

    assert set(registered) == set(cataloged)

    for key, matcher in registered.items():
        entry = cataloged[key]
        assert entry["matcher"] == matcher
        assert entry["evidence_level"] in {"live-redacted", "replay-gated"}
        assert entry["performance_budget_ms"] <= 500


def test_non_enabled_catalog_entries_are_explicitly_non_runtime():
    registered_commands = {command for (_event, command) in _registered_runtime_hooks()}

    for entry in _catalog_entries():
        if entry["runtime_default"] == "enabled":
            continue
        assert entry["runtime_default"] in {"disabled", "capture-only"}
        assert entry.get("command", "") not in registered_commands
        assert entry["policy_mode"] in {"observe", "warn"}
        assert entry["evidence_level"] in {"none", "synthetic", "live-redacted"}


def test_catalog_documentation_names_every_catalog_entry():
    doc = DOC_PATH.read_text(encoding="utf-8")
    for entry in _catalog_entries():
        assert f"`{entry['id']}`" in doc


def test_safety_corpus_catalog_entry_is_disabled_or_observe_only():
    entries = {entry["id"]: entry for entry in _catalog_entries()}
    entry = entries["pretool-safety-pattern-corpus"]
    assert entry["event"] == "PreToolUse"
    assert entry["runtime_default"] == "disabled"
    assert entry["policy_mode"] == "observe"
    assert entry["command"] == ""


def test_capture_first_lifecycle_events_are_cataloged_as_capture_only():
    by_event = {
        entry["event"]: entry
        for entry in _catalog_entries()
        if entry["runtime_default"] == "capture-only"
    }
    for event in (
        "SessionStart",
        "UserPromptSubmit",
        "PreCompact",
        "PermissionRequest",
        "PostToolUseFailure",
        "SubagentStop",
    ):
        entry = by_event[event]
        assert entry["policy_mode"] == "observe"
        assert entry["evidence_level"] == "synthetic"
        if event == "UserPromptSubmit":
            assert "user_prompt_submit_spike.py" in entry["command"]
        else:
            assert "hook_payload_capture.py" in entry["command"]
            assert f"--event {event}" in entry["command"]
