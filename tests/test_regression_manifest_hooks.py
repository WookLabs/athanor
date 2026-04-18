"""Regression test for the v0.6.3 "plugin.json hooks field" regression class.

Mirrors a CI grep-assert that forbids any top-level ``"hooks":`` field inside
`.claude-plugin/plugin.json`. The presence of that field (regardless of value)
is the regression pattern — auto-discovery of `hooks/hooks.json` is the
sanctioned path.

Verifies both:
  - the broken fixture (plugin.json with a ``hooks`` field) FAILS the check.
  - the current repo manifest (`.claude-plugin/plugin.json`) PASSES.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r'"hooks"\s*:')


def manifest_hooks_field_check(manifest_path) -> tuple[bool, str]:
    """Fail if plugin.json has any top-level 'hooks': field.

    Mirrors CI grep-assert. Returns (ok, reason).
    """
    text = Path(manifest_path).read_text(encoding="utf-8")
    if PATTERN.search(text):
        return False, "plugin.json contains 'hooks:' field (v0.6.3 regression class)"
    return True, "OK"


def test_fixture_fails():
    fixture = REPO_ROOT / "tests" / "fixtures" / "fixture_manifest_hooks_field.json"
    ok, reason = manifest_hooks_field_check(fixture)
    assert not ok, f"Fixture should have failed but passed. reason={reason!r}"
    assert "regression" in reason


def test_current_manifest_passes():
    manifest = REPO_ROOT / ".claude-plugin" / "plugin.json"
    ok, reason = manifest_hooks_field_check(manifest)
    assert ok, f"Current manifest should pass but failed: {reason}"
