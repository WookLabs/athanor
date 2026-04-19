"""
Regression test for hook-uniqueness contract (v0.7.1 follow-up fix #1).

Replaces the v0.7.0 substring-grep Check #9 with a structural call to
hook_uniqueness_check(). Verifies:
  - fixture with 2 Stop entries FAILS
  - current hooks/hooks.json (1 Stop entry) PASSES
  - malformed JSON FAILS with a clean violation line (no traceback)
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.gates.manifest_checks import hook_uniqueness_check

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DUPLICATE = REPO_ROOT / "tests" / "fixtures" / "fixture_duplicate_stop_entries.json"
CURRENT_HOOKS = REPO_ROOT / "hooks" / "hooks.json"


def test_fixture_with_duplicate_stop_entries_fails():
    ok, violations = hook_uniqueness_check(FIXTURE_DUPLICATE)
    assert ok is False
    assert len(violations) == 1
    assert "hook-uniqueness violation" in violations[0]
    assert "Stop" in violations[0]
    assert "2 times" in violations[0]


def test_current_hooks_json_passes():
    ok, violations = hook_uniqueness_check(CURRENT_HOOKS)
    assert ok is True
    assert violations == []


def test_malformed_json_fails_clean():
    # Use stdlib tempfile instead of pytest's tmp_path to avoid a
    # Windows-11 / pytest teardown bug where pytest creates a
    # "<testname>current" directory junction and sessionfinish's
    # resolve() raises WinError 448 (untrusted reparse point),
    # turning an all-green run into exit 1. Assertions unchanged.
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.json"
        bad.write_text("{ this is not valid json", encoding="utf-8")
        ok, violations = hook_uniqueness_check(bad)
        assert ok is False
        assert len(violations) == 1
        assert "not valid JSON" in violations[0]
        assert "Traceback" not in violations[0]


def test_missing_file_fails_clean():
    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "nonexistent.json"
        ok, violations = hook_uniqueness_check(missing)
        assert ok is False
        assert len(violations) == 1
        assert "not found" in violations[0]
