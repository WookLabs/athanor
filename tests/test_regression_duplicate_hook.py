"""Regression test for the v0.6.2 "Duplicate hooks file detected" plugin load failure.

Mirrors the `Duplicate hooks path check` step in
`.github/workflows/validate-plugin.yml`. Verifies both:
  - the broken fixture (plugin.json with explicit `hooks` -> hooks/hooks.json)
    fails the check.
  - the current repo manifest (`.claude-plugin/plugin.json`) passes.
"""

from __future__ import annotations

from pathlib import Path

from scripts.gates.manifest_checks import duplicate_hooks_path_check

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_fixture_triggers_failure():
    fixture = REPO_ROOT / "tests" / "fixtures" / "fixture_duplicate_hook.json"
    ok, reason = duplicate_hooks_path_check(fixture, REPO_ROOT)
    assert not ok, f"Fixture should have failed but passed. reason={reason!r}"
    assert "auto-discovered" in reason


def test_current_manifest_passes():
    manifest = REPO_ROOT / ".claude-plugin" / "plugin.json"
    ok, reason = duplicate_hooks_path_check(manifest, REPO_ROOT)
    assert ok, f"Current manifest should pass but failed: {reason}"
