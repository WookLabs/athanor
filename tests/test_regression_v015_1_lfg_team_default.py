"""Regression: v0.15.1 LFG team default — 4 contract tests.

Locks the v0.15.1 LFG `--team` default change and related version-pinned
invariants that ship with the v0.15.1 patch release.

Tests:
  1. lfg Step 2 invokes /athanor:work with --team flag
  2. athanor.json work.defaultMode remains "solo" (global default NOT changed)
  3. plugin.json keywords contain no stale vendored keywords
  4. schema fallbackAfterMs description deferral updated past v0.15+

S09 history: previously included a test
``test_codex_doc_deferral_not_current_version`` that scanned the
athanor.json ``codex._doc`` string for stale "deferred to v0.15+"
phrasing. S09 hard-removed all ``_doc`` fields from athanor.json per
user decision U3, so the field no longer exists; the schema
``description`` field still carries the deferral note and is locked
by test 4 below.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. lfg Step 2 invokes /athanor:work with --team flag
# ---------------------------------------------------------------------------
def test_lfg_step2_invokes_work_with_team_flag():
    """Step 2 of lfg/SKILL.md must invoke `/athanor:work --team`.

    v0.15.1 changed the LFG default from solo to team mode. The Step 2
    section must contain `--team` in proximity to `/athanor:work` so the
    LFG leader dispatches team-mode execution by default.
    """
    skill_path = REPO_ROOT / "skills" / "lfg" / "SKILL.md"
    body = skill_path.read_text(encoding="utf-8")

    # Find the Step 2 section
    step2_start = body.find("### Step 2")
    step3_start = body.find("### Step 3")
    assert step2_start >= 0, "Could not find Step 2 section in lfg/SKILL.md"
    assert step3_start > step2_start, "Could not find Step 3 after Step 2"
    step2_body = body[step2_start:step3_start]

    assert "/athanor:work" in step2_body, (
        "lfg Step 2 must reference /athanor:work"
    )
    assert "--team" in step2_body, (
        "lfg Step 2 must include --team flag in /athanor:work invocation "
        "(v0.15.1 default change)"
    )


# ---------------------------------------------------------------------------
# 2. athanor.json work.defaultMode remains "solo"
# ---------------------------------------------------------------------------
def test_athanor_json_default_mode_is_solo():
    """athanor.json work.defaultMode must remain "solo".

    Regression lock: the v0.15.1 change makes LFG default to --team, but
    the GLOBAL default in athanor.json must stay "solo" so that standalone
    /athanor:work invocations are not affected.
    """
    config_path = REPO_ROOT / "athanor.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    default_mode = config.get("work", {}).get("defaultMode")
    assert default_mode == "solo", (
        f"athanor.json work.defaultMode must be 'solo' (global default); "
        f"got {default_mode!r}. LFG overrides to --team at the skill level, "
        f"not the global config level."
    )


# ---------------------------------------------------------------------------
# 3. plugin.json keywords contain no stale vendored keywords
# ---------------------------------------------------------------------------
def test_plugin_json_no_stale_vendored_keywords():
    """plugin.json keywords must not contain stale vendored-era keywords.

    Post-v0.12.0 the vendored surface was removed. Keywords like
    "vendored-ce" or "vendored-superpowers" are stale leftovers.
    """
    plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
    plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    keywords = plugin.get("keywords", [])
    stale = {"vendored-ce", "vendored-superpowers"}
    found = stale & set(keywords)
    assert not found, (
        f"plugin.json keywords contain stale vendored-era entries: {found}. "
        f"These should have been removed at v0.12.0 (concept absorption pivot)."
    )


# ---------------------------------------------------------------------------
# 4. schema fallbackAfterMs description deferral updated past v0.15+
# ---------------------------------------------------------------------------
def test_schema_deferral_not_current_version():
    """Schema timeoutMs description must NOT contain "deferred to v0.15+".

    Same rationale as test 4: the v0.15.x release line is current, so
    deferral references to "v0.15+" are stale. The schema description
    for fallbackAfterMs deferral must point to v0.16+ or later.
    """
    schema_path = REPO_ROOT / "schemas" / "athanor-config.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    codex_props = (
        schema.get("properties", {})
        .get("codex", {})
        .get("properties", {})
    )
    descriptions: list[str] = []
    for val in codex_props.values():
        desc = val.get("description") if isinstance(val, dict) else None
        if isinstance(desc, str):
            descriptions.append(desc)
    combined = "\n".join(descriptions)
    assert "deferred to v0.15+" not in combined, (
        "Schema codex sub-object still says 'deferred to v0.15+' — this is "
        "the current release line. Update to 'deferred to v0.16+' or later."
    )
