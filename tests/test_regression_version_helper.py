"""Regression tests for tests/_version.py — fail-loud version resolver.

Review finding R2 (B): the module's whole purpose is
fail-loud-over-silent-fallback — a missing manifest, malformed JSON, or an
absent/empty top-level ``version`` field must RAISE, never silently
substitute a default (the regression to guard against is a refactor
restoring ``.get("version", "0.0.0")``). The three documented raises had
ZERO coverage.

Mechanism: ``_version._PLUGIN_JSON`` is a module-level ``Path`` constant and
parsing happens at CALL time inside ``_plugin_version()`` — so each test
monkeypatches that constant to point at a tmp_path fixture. The real
``.claude-plugin/plugin.json`` is NEVER mutated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import _version  # noqa: E402


def test_plugin_version_happy_path(tmp_path, monkeypatch):
    """Sanity control: a well-formed manifest returns its version string
    (confirms the tests below isolate the FAILURE branches, not a broken
    monkeypatch)."""
    manifest = tmp_path / "plugin.json"
    manifest.write_text(json.dumps({"version": "9.9.9"}), encoding="utf-8")
    monkeypatch.setattr(_version, "_PLUGIN_JSON", manifest)
    assert _version._plugin_version() == "9.9.9"


def test_plugin_version_missing_file_raises(tmp_path, monkeypatch):
    """Missing manifest → FileNotFoundError (no silent fallback)."""
    missing = tmp_path / "does-not-exist.json"
    monkeypatch.setattr(_version, "_PLUGIN_JSON", missing)
    with pytest.raises(FileNotFoundError):
        _version._plugin_version()


def test_plugin_version_malformed_json_raises(tmp_path, monkeypatch):
    """Malformed JSON → json.JSONDecodeError (no silent fallback)."""
    manifest = tmp_path / "plugin.json"
    manifest.write_text("{ bad json", encoding="utf-8")
    monkeypatch.setattr(_version, "_PLUGIN_JSON", manifest)
    with pytest.raises(json.JSONDecodeError):
        _version._plugin_version()


def test_plugin_version_absent_version_field_raises(tmp_path, monkeypatch):
    """Manifest with no 'version' key → ValueError (no silent fallback)."""
    manifest = tmp_path / "plugin.json"
    manifest.write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setattr(_version, "_PLUGIN_JSON", manifest)
    with pytest.raises(ValueError):
        _version._plugin_version()


def test_plugin_version_empty_version_field_raises(tmp_path, monkeypatch):
    """Manifest with an empty 'version' value → ValueError (no silent
    fallback; ``not version`` catches "")."""
    manifest = tmp_path / "plugin.json"
    manifest.write_text(json.dumps({"version": ""}), encoding="utf-8")
    monkeypatch.setattr(_version, "_PLUGIN_JSON", manifest)
    with pytest.raises(ValueError):
        _version._plugin_version()
