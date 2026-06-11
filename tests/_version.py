"""Shared test helper: the single source of truth for the live plugin version.

Release-line regression tests historically hard-pinned the version literal
(e.g. ``"0.18.7"``) in four files, forcing every version bump to edit them all
and leaving stale docstrings naming older versions above current asserts
(P18 finding). This module centralizes the literal: tests import
``_plugin_version()`` and assert against the derived value instead.

The version is read from ``.claude-plugin/plugin.json``'s top-level
``version`` field — the canonical release pin. The read is fail-loud: a
missing file, malformed JSON, or absent ``version`` raises rather than
silently substituting a default (per athanor's fail-loud-over-silent-fallback
principle), so a broken manifest surfaces as a test error, not a false pass.
"""
from __future__ import annotations

import json
from pathlib import Path

# tests/_version.py -> repo root is two levels up (parent of tests/).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_JSON = _REPO_ROOT / ".claude-plugin" / "plugin.json"


def _plugin_version() -> str:
    """Return the live plugin version from ``.claude-plugin/plugin.json``.

    Fail-loud: raises ``FileNotFoundError`` if the manifest is missing,
    ``json.JSONDecodeError`` if it is malformed, and ``ValueError`` if the
    top-level ``version`` field is absent or empty. No silent fallback.
    """
    if not _PLUGIN_JSON.is_file():
        raise FileNotFoundError(
            f"plugin manifest not found at {_PLUGIN_JSON}; "
            f"cannot derive the live plugin version"
        )
    data = json.loads(_PLUGIN_JSON.read_text(encoding="utf-8"))
    version = data.get("version")
    if not version:
        raise ValueError(
            f"{_PLUGIN_JSON} has no top-level 'version' field "
            f"(got {version!r}); cannot derive the live plugin version"
        )
    return version
