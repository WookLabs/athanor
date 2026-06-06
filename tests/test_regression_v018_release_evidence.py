"""v0.18.0 release-evidence regression tests.

Locks the v0.18.0 release ceremony surface:

- CHANGELOG.md has a `## [0.18.0]` section.
- docs/STATE.md `## Current Phase` references v0.18.0 literal.
- docs/v0.18.0-migration.md exists.
- All 5 version-pinned files agree on `0.18.0`.
- capability_probe.py produces a fresh `.athanor/hook-capability.json`
  when invoked.

Plan reference: v0.18.0 plan §Subtask 4.2.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Five-file version parity tracks the live release. Bumped to 0.18.5 by the
# v0.18.5 self-dogfood ceremony (fail-loud fixes the adversarial enforcement
# audit found in athanor's own code). The CHANGELOG/STATE/migration prose locks
# below still assert the v0.18.0 ceremony evidence, which remains present.
TARGET_VERSION = "0.18.5"

CHANGELOG = REPO_ROOT / "CHANGELOG.md"
STATE_MD = REPO_ROOT / "docs" / "STATE.md"
MIGRATION_MD = REPO_ROOT / "docs" / "v0.18.0-migration.md"
ROADMAP_MD = REPO_ROOT / "docs" / "ROADMAP.md"

PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"
ATHANOR_JSON = REPO_ROOT / "athanor.json"
TEMPLATE_JSON = REPO_ROOT / "templates" / "athanor.json"
SCHEMA_JSON = REPO_ROOT / "schemas" / "athanor-config.schema.json"

CAPABILITY_PROBE = REPO_ROOT / "scripts" / "hooks" / "capability_probe.py"
HOOK_CAPABILITY_REPORT = REPO_ROOT / ".athanor" / "hook-capability.json"

_URL_VERSION_RE = re.compile(r"/v?(\d+\.\d+\.\d+)/schemas/")


# --- A. CHANGELOG / STATE / migration prose ---

def test_changelog_has_v018_section():
    """MUST — CHANGELOG.md must contain `## [0.18.0]` heading."""
    body = CHANGELOG.read_text(encoding="utf-8")
    assert re.search(r"^##\s+\[0\.18\.0\]", body, re.MULTILINE), (
        "CHANGELOG.md must contain a `## [0.18.0]` section heading"
    )


def test_changelog_v018_mentions_freeze():
    """MUST — v0.18.0 section names 'Freeze' as the headline shipped item."""
    body = CHANGELOG.read_text(encoding="utf-8")
    section_match = re.search(
        r"^##\s+\[0\.18\.0\][^\n]*\n(.*?)(?=^##\s+\[|\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    assert section_match, "v0.18.0 section must exist"
    section = section_match.group(1)
    assert "Freeze" in section, (
        "v0.18.0 section must mention 'Freeze' as the headline shipped item"
    )


def test_state_md_current_phase_is_v018():
    """MUST — docs/STATE.md `## Current Phase` heading references v0.18.0."""
    body = STATE_MD.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^##\s+Current Phase[^\n]*\n",
        re.MULTILINE,
    )
    m = pattern.search(body)
    assert m, "docs/STATE.md must have a `## Current Phase` heading"
    heading_line = m.group(0)
    assert "0.18.0" in heading_line or "0.18." in heading_line, (
        f"docs/STATE.md `## Current Phase` heading must reference v0.18.0; "
        f"got {heading_line!r}"
    )


def test_migration_doc_exists():
    """MUST — docs/v0.18.0-migration.md exists with non-trivial content."""
    assert MIGRATION_MD.is_file(), (
        f"Migration doc must exist at {MIGRATION_MD}"
    )
    content = MIGRATION_MD.read_text(encoding="utf-8")
    assert len(content) > 500, (
        "Migration doc must have non-trivial content (>500 chars)"
    )
    # Must mention the headline feature and the D2 residual.
    assert "Freeze" in content, "Migration doc must mention 'Freeze'"
    assert "D2" in content, "Migration doc must mention 'D2' residual"


def test_roadmap_documents_v018_deferrals():
    """MUST — docs/ROADMAP.md documents v0.18.1 and v0.18.2 deferrals."""
    body = ROADMAP_MD.read_text(encoding="utf-8")
    assert "v0.18.1" in body, "ROADMAP must reference v0.18.1"
    assert "v0.18.2" in body, "ROADMAP must reference v0.18.2"
    # v0.18.1 admission criteria must be present (one of three trigger words).
    assert (
        "freeze-violations.jsonl" in body
        or "git-worktree" in body
    ), "ROADMAP v0.18.1 must document admission criteria"
    # v0.18.2 design precondition must mention UPS / UserPromptSubmit.
    assert (
        "UserPromptSubmit" in body
        or "UPS" in body
    ), "ROADMAP v0.18.2 must reference UserPromptSubmit precondition"


# --- B. Version parity across 5-file manifest ---

def _read_plugin_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    v = data.get("version")
    assert v, f"{path} has no top-level `version`"
    return v


def _read_marketplace_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    plugins = data.get("plugins", [])
    assert plugins, f"{path} has no plugins[]"
    v = plugins[0].get("version")
    assert v, f"{path} plugins[0] has no `version`"
    return v


def _read_schema_url_version(path: Path, key: str) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    url = data.get(key, "")
    m = _URL_VERSION_RE.search(url)
    assert m, f"{path} `{key}` URL has no recognisable version segment: {url!r}"
    return m.group(1)


def test_plugin_json_version_is_v018():
    assert _read_plugin_version(PLUGIN_JSON) == TARGET_VERSION


def test_marketplace_json_version_is_v018():
    assert _read_marketplace_version(MARKETPLACE_JSON) == TARGET_VERSION


def test_athanor_json_schema_url_is_v018():
    assert _read_schema_url_version(ATHANOR_JSON, "$schema") == TARGET_VERSION


def test_template_json_schema_url_is_v018():
    assert _read_schema_url_version(TEMPLATE_JSON, "$schema") == TARGET_VERSION


def test_schema_id_is_v018():
    assert _read_schema_url_version(SCHEMA_JSON, "$id") == TARGET_VERSION


def test_all_five_version_files_agree():
    """MUST — all 5 version-pinned files agree on TARGET_VERSION."""
    versions = {
        "plugin.json": _read_plugin_version(PLUGIN_JSON),
        "marketplace.json": _read_marketplace_version(MARKETPLACE_JSON),
        "athanor.json $schema": _read_schema_url_version(ATHANOR_JSON, "$schema"),
        "templates/athanor.json $schema": _read_schema_url_version(
            TEMPLATE_JSON, "$schema"
        ),
        "schemas/athanor-config.schema.json $id": _read_schema_url_version(
            SCHEMA_JSON, "$id"
        ),
    }
    mismatches = {k: v for k, v in versions.items() if v != TARGET_VERSION}
    assert not mismatches, (
        f"Version-pinned files do not agree on {TARGET_VERSION}: {mismatches}"
    )


# --- C. Capability probe re-run ---

def test_capability_probe_script_present():
    """MUST — capability_probe.py exists and is invokable."""
    assert CAPABILITY_PROBE.is_file(), (
        f"capability_probe.py must exist at {CAPABILITY_PROBE}"
    )


def test_capability_probe_runs_and_writes_report():
    """MUST — capability_probe.py runs cleanly and refreshes the report file."""
    # Run from the repo root so .athanor/ is created in the repo, not pytest cwd.
    result = subprocess.run(
        [sys.executable, str(CAPABILITY_PROBE)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"capability_probe.py exited {result.returncode}\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert HOOK_CAPABILITY_REPORT.is_file(), (
        f"capability_probe.py did not write {HOOK_CAPABILITY_REPORT}"
    )
    # Sanity check report is JSON.
    report = json.loads(HOOK_CAPABILITY_REPORT.read_text(encoding="utf-8"))
    assert isinstance(report, dict), (
        "hook-capability.json report must be a JSON object"
    )


# --- D. Honesty residual prose checks ---

def test_changelog_v018_documents_d2_residual():
    """MUST — v0.18.0 CHANGELOG section documents the D2 honesty residual."""
    body = CHANGELOG.read_text(encoding="utf-8")
    section_match = re.search(
        r"^##\s+\[0\.18\.0\][^\n]*\n(.*?)(?=^##\s+\[|\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    assert section_match, "v0.18.0 section must exist"
    section = section_match.group(1)
    assert "D2" in section, (
        "v0.18.0 CHANGELOG must document the D2 honesty residual literal"
    )
    assert "Codex" in section, (
        "v0.18.0 CHANGELOG must name 'Codex' in the residual paragraph"
    )
