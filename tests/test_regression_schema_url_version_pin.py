"""Regression: athanor.json and templates/athanor.json $schema URLs must
encode the SAME version as .claude-plugin/plugin.json. Prevents stale-tag
drift on release (plan §4 C3 + §10.4 resolved decision).

Per §10.4, the schema URL is pinned to a release tag (e.g. v0.7.7), not the
mutable ``main`` branch. The URL form is:

    https://raw.githubusercontent.com/<org>/<repo>/v<X.Y.Z>/schemas/athanor-config.schema.json

This test extracts ``X.Y.Z`` and asserts it equals ``plugin.json`` ``version``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_CONFIG = REPO_ROOT / "athanor.json"
TEMPLATE_CONFIG = REPO_ROOT / "templates" / "athanor.json"
PLUGIN_MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"

# Match the version segment in URLs like
# .../<org>/<repo>/v0.7.7/schemas/athanor-config.schema.json
# Accept either /v<X.Y.Z>/ (the §10.4 pinned form) or /<X.Y.Z>/ as fallback.
_VERSION_RE = re.compile(r"/v?(\d+\.\d+\.\d+)/schemas/")


def _extract_schema_url_version(config_path: Path) -> str:
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    schema_url = cfg.get("$schema", "")
    assert schema_url, f"{config_path} missing $schema field"
    m = _VERSION_RE.search(schema_url)
    assert m, (
        f"{config_path} $schema URL does not embed a /vX.Y.Z/schemas/ "
        f"version segment (got: {schema_url!r}); §10.4 requires pinned tag."
    )
    return m.group(1)


def _plugin_version() -> str:
    with open(PLUGIN_MANIFEST, encoding="utf-8") as f:
        return json.load(f)["version"]


def test_root_config_schema_url_pinned_to_plugin_version():
    """athanor.json $schema URL version segment must equal plugin.json version."""
    url_version = _extract_schema_url_version(ROOT_CONFIG)
    pkg_version = _plugin_version()
    assert url_version == pkg_version, (
        f"athanor.json $schema URL pinned to v{url_version} but plugin.json "
        f"version is {pkg_version}. Per CONTRIBUTING.md §Release URL bump, "
        f"every release must update both atomically."
    )


def test_template_schema_url_pinned_to_plugin_version():
    """templates/athanor.json $schema URL version segment must equal plugin.json version."""
    url_version = _extract_schema_url_version(TEMPLATE_CONFIG)
    pkg_version = _plugin_version()
    assert url_version == pkg_version, (
        f"templates/athanor.json $schema URL pinned to v{url_version} but "
        f"plugin.json version is {pkg_version}."
    )


@pytest.mark.parametrize(
    "config_path",
    [ROOT_CONFIG, TEMPLATE_CONFIG],
    ids=["root", "template"],
)
def test_schema_url_not_main_branch(config_path: Path):
    """Per §10.4, $schema URL MUST NOT reference the mutable /main/ branch.

    Pinned-tag policy keeps user installs deterministic: a release tag is
    immutable, so a user editor that fetched the schema once will keep
    seeing the same shape unless they upgrade. /main/ would silently shift
    semantics under their feet.
    """
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    schema_url = cfg.get("$schema", "")
    assert "/main/" not in schema_url, (
        f"{config_path.name} $schema URL references /main/ branch "
        f"(violates §10.4 pinned-tag policy): {schema_url!r}"
    )
