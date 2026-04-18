"""Regression test for the v0.6.2 "Duplicate hooks file detected" plugin load failure.

Mirrors the `Duplicate hooks path check` step in
`.github/workflows/validate-plugin.yml`. Verifies both:
  - the broken fixture (plugin.json with explicit `hooks` -> hooks/hooks.json)
    fails the check.
  - the current repo manifest (`.claude-plugin/plugin.json`) passes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def duplicate_hooks_check(
    manifest_path: str | os.PathLike[str],
    repo_root: str | os.PathLike[str] = REPO_ROOT,
    hooks_file: str = "hooks/hooks.json",
) -> tuple[bool, str]:
    """Mirror of CI's duplicate-hooks-path check.

    Resolves both the auto-discovered hooks path and the manifest's explicit
    ``hooks`` field against ``repo_root`` (the CI runs with CWD at repo root).

    Returns
    -------
    (ok, reason) : tuple[bool, str]
        ``ok`` is True when the manifest does not duplicate the auto-discovered
        hooks path. ``reason`` is an empty string on success, otherwise the
        exact sys.exit message the CI step would emit.
    """
    repo_root = Path(repo_root)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    auto_path = repo_root / hooks_file
    auto = os.path.abspath(auto_path) if auto_path.exists() else None

    if "hooks" in manifest:
        explicit_raw = Path(manifest["hooks"])
        if not explicit_raw.is_absolute():
            explicit_raw = repo_root / explicit_raw
        explicit = os.path.abspath(explicit_raw)
    else:
        explicit = None

    if auto and explicit and auto == explicit:
        return (
            False,
            "plugin.json declares hooks -> hooks/hooks.json which is "
            "auto-discovered; remove the field",
        )
    return True, ""


def test_fixture_triggers_failure():
    fixture = REPO_ROOT / "tests" / "fixtures" / "fixture_duplicate_hook.json"
    ok, reason = duplicate_hooks_check(fixture)
    assert not ok, f"Fixture should have failed but passed. reason={reason!r}"
    assert "auto-discovered" in reason


def test_current_manifest_passes():
    manifest = REPO_ROOT / ".claude-plugin" / "plugin.json"
    ok, reason = duplicate_hooks_check(manifest)
    assert ok, f"Current manifest should pass but failed: {reason}"
