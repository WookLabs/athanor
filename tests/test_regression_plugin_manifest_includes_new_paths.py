"""Regression: marketplace packaging guards (plan §5).

v0.7.7 adds two new top-level directories that must ship in the plugin
package: ``schemas/`` and ``templates/``. v0.7.8 adds ``scripts/hooks/``
(the spike-PASS command-hook script). If the plugin manifest acquires
an explicit include/files/globs list, those paths must be present.

Both Claude Code plugin manifests today (.claude-plugin/plugin.json,
.claude-plugin/marketplace.json) follow a ship-everything-by-default
contract — no include list. The test handles both states:

  * No include list present → trivially PASS (default ships everything).
  * Include list present → MUST contain the new paths.

This sentinel design future-proofs against a manifest schema change
introducing an opt-in include array.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = REPO_ROOT / ".claude-plugin" / "marketplace.json"

# Field names a future manifest schema might use to opt-in explicit shipping.
_INCLUDE_FIELDS = ("include", "files", "globs", "ship")

# Paths that MUST ship in v0.7.7+ (schemas/, templates/) and v0.7.8+
# (scripts/hooks/ for the command-hook Stop script).
_REQUIRED_PATHS = ("schemas/", "templates/", "scripts/hooks/")


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _collect_include_entries(manifest: dict) -> list[str] | None:
    """Return the flat list of include-glob strings if any include-style
    field is present, else None (ship-everything-by-default semantics)."""
    for field in _INCLUDE_FIELDS:
        if field in manifest:
            value = manifest[field]
            if isinstance(value, list):
                return [str(v) for v in value]
            if isinstance(value, str):
                return [value]
    # marketplace.json wraps plugins in a "plugins":[{...}] envelope; check
    # the first plugin entry too.
    for entry in manifest.get("plugins", []) or []:
        if isinstance(entry, dict):
            for field in _INCLUDE_FIELDS:
                if field in entry:
                    value = entry[field]
                    if isinstance(value, list):
                        return [str(v) for v in value]
                    if isinstance(value, str):
                        return [value]
    return None


def _path_satisfied(required: str, include_entries: list[str]) -> bool:
    """A required path is satisfied iff ANY include entry contains it
    as a prefix-style match (e.g. 'schemas/' is matched by 'schemas/**',
    'schemas/', or the bare 'schemas')."""
    stripped = required.rstrip("/")
    for entry in include_entries:
        normalized = entry.replace("\\", "/")
        if normalized.startswith(stripped):
            return True
        # Also accept '**/schemas/**' style globs:
        if f"/{stripped}/" in f"/{normalized}/":
            return True
    return False


@pytest.fixture(scope="module")
def plugin_manifest():
    assert PLUGIN_MANIFEST.is_file(), f"{PLUGIN_MANIFEST} not found"
    return _load_json(PLUGIN_MANIFEST)


@pytest.fixture(scope="module")
def marketplace_manifest():
    assert MARKETPLACE_MANIFEST.is_file(), f"{MARKETPLACE_MANIFEST} not found"
    return _load_json(MARKETPLACE_MANIFEST)


def _assert_path_shipped(manifest: dict, required_path: str, manifest_name: str) -> None:
    """Sentinel check: if no include list, trivially pass; else require path."""
    includes = _collect_include_entries(manifest)
    if includes is None:
        # ship-everything-by-default — current state per Wave 1A.
        return
    assert _path_satisfied(required_path, includes), (
        f"{manifest_name} declares an include list {includes!r} but it does "
        f"not cover {required_path!r}. New v0.7.7+ paths must ship in the "
        f"plugin package (plan §5)."
    )


def test_plugin_json_schemas_path(plugin_manifest):
    """schemas/ must ship via plugin.json (either by-default or explicit)."""
    _assert_path_shipped(plugin_manifest, "schemas/", "plugin.json")


def test_plugin_json_templates_path(plugin_manifest):
    """templates/ must ship via plugin.json (either by-default or explicit)."""
    _assert_path_shipped(plugin_manifest, "templates/", "plugin.json")


def test_plugin_json_scripts_hooks_path(plugin_manifest):
    """scripts/hooks/ must ship via plugin.json (v0.7.8 prep)."""
    _assert_path_shipped(plugin_manifest, "scripts/hooks/", "plugin.json")


def test_marketplace_json_same_invariants(marketplace_manifest):
    """marketplace.json must not override the include semantics either."""
    for required in _REQUIRED_PATHS:
        _assert_path_shipped(marketplace_manifest, required, "marketplace.json")


def test_no_unexpected_include_field_today(plugin_manifest, marketplace_manifest):
    """Documentation sentinel: today, both manifests use ship-everything-by-
    default semantics. If this test starts failing, a contributor opted into
    an include list — they MUST add the v0.7.7 paths and update this test's
    documentation to remove the 'today' assertion."""
    assert _collect_include_entries(plugin_manifest) is None, (
        "plugin.json acquired an include/files/globs field; ensure the new "
        "v0.7.7 paths (schemas/, templates/, scripts/hooks/) are listed and "
        "remove this 'today' sentinel test."
    )
    assert _collect_include_entries(marketplace_manifest) is None, (
        "marketplace.json acquired an include/files/globs field; ensure the "
        "new v0.7.7 paths (schemas/, templates/, scripts/hooks/) are listed "
        "and remove this 'today' sentinel test."
    )
