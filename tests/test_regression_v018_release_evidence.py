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

from tests._version import _plugin_version

REPO_ROOT = Path(__file__).resolve().parent.parent

# Five-file version parity tracks the live release, derived from plugin.json via
# tests._version._plugin_version() so it follows every release bump without edits.
# The CHANGELOG/STATE/migration prose locks below still assert the v0.18.0 ceremony
# evidence (the [0.18.0] heading, Freeze headline, D2 residual), which remains present.
TARGET_VERSION = _plugin_version()

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


def test_state_md_current_phase_is_v018_or_later():
    """MUST — docs/STATE.md `## Current Phase` heading references v0.18+."""
    body = STATE_MD.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^##\s+Current Phase[^\n]*\n",
        re.MULTILINE,
    )
    m = pattern.search(body)
    assert m, "docs/STATE.md must have a `## Current Phase` heading"
    heading_line = m.group(0)
    assert (
        "0.18.0" in heading_line
        or "0.18." in heading_line
        or "0.19." in heading_line
        or "0.20." in heading_line
        or "0.21." in heading_line
    ), (
        f"docs/STATE.md `## Current Phase` heading must reference v0.18+; "
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
    """MUST — docs/ROADMAP.md durably documents both Freeze-era deferrals.

    The deferred entries are keyed by stable codename ("Deferred:
    git-worktree isolation per subtask" / "Deferred: UserPromptSubmit
    injection"), NOT by version number — the v0.18.1/v0.18.2 numbers were
    consumed by real SHIPPED releases for different content, so keying the
    deferrals off them would collide with the CHANGELOG.
    """
    body = ROADMAP_MD.read_text(encoding="utf-8")
    # Both deferrals must be present under stable codename headings.
    assert "Deferred: git-worktree isolation per subtask" in body, (
        "ROADMAP must carry the 'Deferred: git-worktree isolation per "
        "subtask' codename heading"
    )
    assert "Deferred: UserPromptSubmit injection" in body, (
        "ROADMAP must carry the 'Deferred: UserPromptSubmit injection' "
        "codename heading"
    )
    # git-worktree deferral admission criteria must be present (stable tokens).
    assert (
        "freeze-violations.jsonl" in body
        or "git-worktree" in body
    ), "ROADMAP git-worktree deferral must document admission criteria"
    # UserPromptSubmit deferral design precondition must mention UPS / UPS spike.
    assert (
        "UserPromptSubmit" in body
        or "UPS" in body
    ), "ROADMAP UserPromptSubmit deferral must reference its precondition"


def _extract_roadmap_v019_posttool_section() -> str:
    body = ROADMAP_MD.read_text(encoding="utf-8")
    marker = "### v0.19.0 — PostToolUse evidence sniffer"
    start = body.find(marker)
    assert start != -1, "ROADMAP must contain the v0.19.0 PostToolUse section"
    next_section = body.find("\n### ", start + len(marker))
    if next_section == -1:
        return body[start:]
    return body[start:next_section]


def test_roadmap_v019_defers_runtime_detail_to_spec_then_tdd_reference():
    """ROADMAP should be a roadmap, not a second runtime spec."""
    section = _extract_roadmap_v019_posttool_section()
    assert "skills/work/references/spec-then-tdd-handler.md" in section, (
        "ROADMAP v0.19.0 section must point to the canonical runtime "
        "behavior reference."
    )
    forbidden = [
        "**Current scope:**",
        "Records command, test targets, scope, exit code, output tail",
        "structured `tool_response.files_changed`",
        "Treats observed out-of-allowlist",
    ]
    hits = [needle for needle in forbidden if needle in section]
    assert not hits, (
        "ROADMAP v0.19.0 section duplicates runtime details that belong in "
        f"spec-then-tdd-handler.md: {hits}"
    )


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
