"""Regression tests for the cross-runtime hook matrix.

The matrix is the P3 boundary from the ref deep research: it should make
Claude Code, Codex, and Athanor hook policy drift visible before any generator
or installer starts mutating user settings.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "hooks" / "catalog.json"
MATRIX_DOC = REPO_ROOT / "docs" / "cross-runtime-hook-matrix.md"


def _catalog_entries() -> list[dict[str, object]]:
    with CATALOG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)["hooks"]


def _section(body: str, heading: str) -> str:
    marker = f"## {heading}"
    start = body.find(marker)
    assert start != -1, f"missing section: {marker}"
    next_start = body.find("\n## ", start + len(marker))
    if next_start == -1:
        return body[start:]
    return body[start:next_start]


def _markdown_rows(section_body: str) -> list[dict[str, str]]:
    rows = []
    table_lines = [
        line.strip()
        for line in section_body.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    assert table_lines, f"no markdown table in section:\n{section_body}"
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def test_cross_runtime_matrix_document_exists_and_cites_primary_sources():
    body = MATRIX_DOC.read_text(encoding="utf-8")

    for token in (
        "https://code.claude.com/docs/en/hooks",
        "https://code.claude.com/docs/en/plugins-reference",
        "https://developers.openai.com/codex/hooks",
        "https://github.com/openai/codex",
    ):
        assert token in body


def test_matrix_maps_every_athanor_catalog_event_once():
    body = MATRIX_DOC.read_text(encoding="utf-8")
    rows = _markdown_rows(_section(body, "Athanor Catalog Mapping"))
    matrix_events = [row["Event"] for row in rows]
    catalog_events = sorted({str(entry["event"]) for entry in _catalog_entries()})

    assert sorted(matrix_events) == catalog_events
    assert len(matrix_events) == len(set(matrix_events))


def test_enabled_hooks_remain_shared_core_events():
    body = MATRIX_DOC.read_text(encoding="utf-8")
    rows = {
        row["Event"]: row
        for row in _markdown_rows(_section(body, "Athanor Catalog Mapping"))
    }
    enabled_events = {
        str(entry["event"])
        for entry in _catalog_entries()
        if entry["runtime_default"] == "enabled"
    }

    assert enabled_events == {"PreToolUse", "PostToolUse"}
    for event in enabled_events:
        row = rows[event]
        assert row["Athanor default"] == "enabled"
        assert row["Claude Code"] == "supported"
        assert row["Codex"] == "supported"


def test_capture_only_events_require_live_fixtures_before_promotion():
    body = MATRIX_DOC.read_text(encoding="utf-8")
    rows = {
        row["Event"]: row
        for row in _markdown_rows(_section(body, "Athanor Catalog Mapping"))
    }
    capture_only_events = {
        str(entry["event"])
        for entry in _catalog_entries()
        if entry["runtime_default"] == "capture-only"
    }

    assert capture_only_events
    for event in capture_only_events:
        row = rows[event]
        assert row["Athanor default"] == "capture-only"
        assert "live-redacted fixture" in row["Next action"]
        assert "no settings mutation" in row["Next action"]


def test_trust_and_install_policy_matrix_records_generator_boundary():
    body = MATRIX_DOC.read_text(encoding="utf-8")
    rows = _markdown_rows(_section(body, "Trust And Install Policy Matrix"))
    by_runtime = {row["Runtime"]: row for row in rows}

    for runtime in ("Claude Code", "Codex", "Athanor"):
        assert runtime in by_runtime

    assert "trust before execution" in by_runtime["Codex"]["Hook trust model"]
    assert "managed hooks" in by_runtime["Codex"]["Hook trust model"]
    assert "plugin validation" in by_runtime["Claude Code"]["Hook trust model"]
    assert "dry-run first" in by_runtime["Athanor"]["Installer boundary"]
    assert "no generator writes settings" in by_runtime["Athanor"]["Installer boundary"]


def test_hook_catalog_doc_points_to_cross_runtime_matrix():
    catalog_doc = (REPO_ROOT / "docs" / "hook-catalog.md").read_text(encoding="utf-8")

    assert "docs/cross-runtime-hook-matrix.md" in catalog_doc
