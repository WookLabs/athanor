"""
Regression suite for scripts/gates/lint_checks.py — five frontmatter/manifest
guards extracted from the v0.7.2 audit (5-agent team analysis, 2026-05).

Each guard has two cases:
  * fixture_*_fails  — synthetic broken state must trigger a violation.
  * current_*_passes — repo's actual file/dir must already satisfy the gate.

Stdlib + pytest only. UTF-8 throughout.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.gates.lint_checks import (
    agent_descriptions_unique_check,
    hook_events_known_check,
    hook_items_well_formed_check,
    marketplace_version_sync_check,
    vendored_skill_provenance_check,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# Guard 1: marketplace-version-sync
# ---------------------------------------------------------------------------
def test_marketplace_version_drift_fixture_fails():
    """fixture's marketplace plugins[0].version=0.7.0 vs plugin.json=0.7.2 -> FAIL."""
    plugin = REPO_ROOT / ".claude-plugin" / "plugin.json"
    fixture = FIXTURES / "fixture_marketplace_version_drift.json"
    ok, msg = marketplace_version_sync_check(plugin, fixture)
    assert not ok, f"expected drift fixture to fail, got msg={msg!r}"
    assert "marketplace-version-sync violation" in msg


def test_current_marketplace_in_sync():
    """Repo's actual plugin.json and marketplace.json versions must match."""
    plugin = REPO_ROOT / ".claude-plugin" / "plugin.json"
    market = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    ok, msg = marketplace_version_sync_check(plugin, market)
    assert ok, f"current repo version drift: {msg}"


# ---------------------------------------------------------------------------
# Guard 2: agent-descriptions-unique
# ---------------------------------------------------------------------------
def test_agent_description_collision_fixture_fails(tmp_path: Path):
    """fixture's description prefix collides with athanor-analyst's prefix."""
    real_agent = REPO_ROOT / "agents" / "analyst.md"
    fixture = FIXTURES / "fixture_agent_description_collision.md"
    assert real_agent.is_file()
    assert fixture.is_file()

    sim_dir = tmp_path / "agents"
    sim_dir.mkdir()
    shutil.copy2(real_agent, sim_dir / "analyst.md")
    shutil.copy2(fixture, sim_dir / "collider.md")

    ok, violations = agent_descriptions_unique_check(sim_dir)
    assert not ok, f"expected collision detection, got violations={violations!r}"
    assert any("description prefix collides" in v for v in violations)


def test_current_agents_descriptions_unique():
    """Repo's actual 7 agents must all have unique 60-char description prefixes."""
    agents_dir = REPO_ROOT / "agents"
    ok, violations = agent_descriptions_unique_check(agents_dir)
    assert ok, f"current agents have description collisions: {violations}"


# ---------------------------------------------------------------------------
# Guard 3: hook-events-known
# ---------------------------------------------------------------------------
def test_hook_unknown_event_fixture_fails():
    """fixture registers `Stoped` (typo) -> FAIL."""
    fixture = FIXTURES / "fixture_hook_unknown_event.json"
    ok, violations = hook_events_known_check(fixture)
    assert not ok, f"expected unknown-event detection, got violations={violations!r}"
    assert any("unknown event" in v and "'Stoped'" in v for v in violations)


def test_current_hooks_events_known():
    """Repo's actual hooks/hooks.json events must all be in the whitelist."""
    hooks = REPO_ROOT / "hooks" / "hooks.json"
    ok, violations = hook_events_known_check(hooks)
    assert ok, f"current hooks.json has unknown event keys: {violations}"


# ---------------------------------------------------------------------------
# Guard 4: hook-items-well-formed
# ---------------------------------------------------------------------------
def test_hook_command_missing_command_fixture_fails():
    """fixture has type=command without `command` field -> FAIL."""
    fixture = FIXTURES / "fixture_hook_command_missing_command.json"
    ok, violations = hook_items_well_formed_check(fixture)
    assert not ok, f"expected well-formed check to fail, got violations={violations!r}"
    assert any("missing required field 'command'" in v for v in violations)


def test_current_hooks_items_well_formed():
    """Repo's actual hooks/hooks.json items must satisfy per-type required fields."""
    hooks = REPO_ROOT / "hooks" / "hooks.json"
    ok, violations = hook_items_well_formed_check(hooks)
    assert ok, f"current hooks.json items malformed: {violations}"


# ---------------------------------------------------------------------------
# Guard 5: vendored-skill-provenance
# ---------------------------------------------------------------------------
def test_skill_missing_provenance_fixture_fails():
    """fixture vendored skill body has no `<!-- Provenance:` block -> FAIL."""
    fixture = FIXTURES / "fixture_skill_missing_provenance.md"
    ok, msg = vendored_skill_provenance_check(fixture)
    assert not ok, f"expected provenance check to fail, got msg={msg!r}"
    assert "vendored-skill-provenance violation" in msg


@pytest.mark.parametrize(
    "skill_name",
    ["scope-drift", "verification-before-completion"],
)
def test_current_vendored_skills_have_provenance(skill_name: str):
    """Repo's actual vendored skills must carry Provenance blocks."""
    skill_md = REPO_ROOT / "skills" / skill_name / "SKILL.md"
    ok, msg = vendored_skill_provenance_check(skill_md)
    assert ok, f"vendored skill {skill_name} missing provenance: {msg}"


# ---------------------------------------------------------------------------
# Sanity: malformed JSON fails clean (defensive)
# ---------------------------------------------------------------------------
def test_malformed_marketplace_fails_clean(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    plugin = REPO_ROOT / ".claude-plugin" / "plugin.json"
    ok, msg = marketplace_version_sync_check(plugin, bad)
    assert not ok
    assert "violation" in msg


def test_missing_hooks_file_fails_clean(tmp_path: Path):
    missing = tmp_path / "does-not-exist.json"
    ok, violations = hook_events_known_check(missing)
    assert not ok
    assert any("not found" in v for v in violations)
