"""Release-level smoke tests for the v0.14.0 release line.

Verifies version consistency across the 5-file manifest convention,
CHANGELOG entry presence, and correct native agent count.

Plan reference: v0.14.0 subtask S8.

The version consistency check asserts against the live plugin version
(``TARGET_VERSION`` derived from ``tests._version._plugin_version()``), so it
tracks every release bump without edits. ``test_v014_changelog_entry_exists``
asserts the historical ``[0.14.0]`` CHANGELOG header is preserved.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests._version import _plugin_version

REPO_ROOT = Path(__file__).resolve().parent.parent

# The 5-file version convention (per releaser.md agent definition).
# plugin.json and marketplace.json live under .claude-plugin/ in this repo.
VERSION_FILES = {
    "plugin.json": REPO_ROOT / ".claude-plugin" / "plugin.json",
    "marketplace.json": REPO_ROOT / ".claude-plugin" / "marketplace.json",
    "athanor.json": REPO_ROOT / "athanor.json",
    "templates/athanor.json": REPO_ROOT / "templates" / "athanor.json",
    "schemas/athanor-config.schema.json": (
        REPO_ROOT / "schemas" / "athanor-config.schema.json"
    ),
}

TARGET_VERSION = _plugin_version()

# Regex to extract version from $schema/$id URLs like .../v0.14.0/schemas/...
_URL_VERSION_RE = re.compile(r"/v?(\d+\.\d+\.\d+)/schemas/")

AGENTS_DIR = REPO_ROOT / "agents"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def _extract_version(label: str, path: Path) -> str:
    """Extract the version string from a manifest file.

    - plugin.json, marketplace.json: top-level "version" field
    - athanor.json, templates/athanor.json: version embedded in "$schema" URL
    - schemas/athanor-config.schema.json: version embedded in "$id" URL
    """
    assert path.exists(), f"{label} not found at {path}"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if label == "plugin.json":
        ver = data.get("version")
        assert ver, f"{label} has no top-level 'version' field"
        return ver

    if label == "marketplace.json":
        # marketplace.json nests version under plugins[0].version
        plugins = data.get("plugins", [])
        assert plugins, f"{label} has no 'plugins' array"
        ver = plugins[0].get("version")
        assert ver, f"{label} plugins[0] has no 'version' field"
        return ver

    if label in ("athanor.json", "templates/athanor.json"):
        url = data.get("$schema", "")
        m = _URL_VERSION_RE.search(url)
        assert m, f"{label} $schema URL has no version segment: {url!r}"
        return m.group(1)

    if label == "schemas/athanor-config.schema.json":
        url = data.get("$id", "")
        m = _URL_VERSION_RE.search(url)
        assert m, f"{label} $id URL has no version segment: {url!r}"
        return m.group(1)

    raise ValueError(f"Unknown manifest label: {label}")


# ---- Version consistency ----


@pytest.mark.parametrize(
    "label,path",
    list(VERSION_FILES.items()),
    ids=list(VERSION_FILES.keys()),
)
def test_v014_version_consistent(label: str, path: Path):
    """All 5 manifest files must agree on the live plugin version (TARGET_VERSION)."""
    actual = _extract_version(label, path)
    assert actual == TARGET_VERSION, (
        f"{label} shows version {actual!r}, expected {TARGET_VERSION!r}. "
        f"Run the releaser agent to bump all 5 files atomically."
    )


# ---- CHANGELOG entry ----


def test_v014_changelog_entry_exists():
    """CHANGELOG.md must contain a ## [0.14.0] section header."""
    assert CHANGELOG.exists(), f"CHANGELOG.md not found at {CHANGELOG}"
    text = CHANGELOG.read_text(encoding="utf-8")
    # Match both "## [0.14.0]" and "## v0.14.0" formats
    assert re.search(
        r"^##\s+(?:\[0\.14\.0\]|v0\.14\.0)", text, re.MULTILINE
    ), (
        "CHANGELOG.md has no ## [0.14.0] or ## v0.14.0 section header. "
        "The CHANGELOG entry must be added before release."
    )


# ---- Native agent count ----


def test_native_agent_count():
    """agents/ directory (excluding vendored/) should contain exactly 11 .md files.

    8 existing (analyst, cleaner, critic, executor, learner, planner,
    researcher, reviewer) + 3 new in v0.14.0 (releaser, codex-dispatcher,
    ci-watcher) = 11 total.
    """
    assert AGENTS_DIR.is_dir(), f"agents/ directory not found at {AGENTS_DIR}"
    agent_files = [
        f
        for f in sorted(AGENTS_DIR.iterdir())
        if f.suffix == ".md" and f.is_file()
    ]
    # Exclude vendored/ subdirectory — those are counted separately
    agent_names = [f.name for f in agent_files]
    assert len(agent_files) == 11, (
        f"Expected 11 native agent .md files in agents/, "
        f"found {len(agent_files)}: {agent_names}"
    )
