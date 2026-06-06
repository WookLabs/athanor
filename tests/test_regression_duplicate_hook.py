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


def test_non_string_hooks_field_does_not_crash(tmp_path):
    """R2 (v0.18.6) — a non-string `hooks` field (object/array/number) must
    yield a clean (False, reason), NOT an uncaught TypeError that crashes the
    release gate.

    Found by the deep bug hunt: `repo_root / explicit` raised TypeError when
    `explicit` was a dict, and the `except` clause only caught OSError, so the
    (bool, str) contract was violated and the gate exited with a traceback.
    """
    manifest = tmp_path / "plugin.json"
    manifest.write_text('{"hooks": {"PreToolUse": []}}', encoding="utf-8")
    # REPO_ROOT/hooks/hooks.json exists, so the check reaches the path-resolve
    # line that previously crashed on the dict value.
    ok, reason = duplicate_hooks_path_check(manifest, REPO_ROOT)
    assert ok is False, f"non-string hooks must fail cleanly; got ok={ok}"
    assert "string" in reason.lower() or "hooks" in reason.lower(), (
        f"reason must explain the non-string hooks field; got {reason!r}"
    )
