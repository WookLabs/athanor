"""v0.13.0 + v0.13.1 release-smoke regression test. Locks the v0.13.x deliverable surface as a single high-signal check."""
from __future__ import annotations
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_v013_release_surface_intact():
    """Locks all v0.13.0 + v0.13.1 deliverables in one assertion bundle.

    Catches regression of any single deliverable shipping in the v0.13.x release line.
    """
    # skill spec
    assert (REPO_ROOT / "skills" / "lfg-goal" / "SKILL.md").is_file()
    # 5 reference files
    refs = ["receipt-validator.md", "judge-rubric.md", "scope-change-critic.md", "state-shape.md", "goal-md-template.md"]
    for r in refs:
        assert (REPO_ROOT / "skills" / "lfg-goal" / "references" / r).is_file(), f"missing reference {r}"
    # 3 fixtures
    fixtures = ["receipt_valid.md", "receipt_invalid_missing_step3.md", "receipt_partial_with_residuals.md"]
    for f in fixtures:
        assert (REPO_ROOT / "tests" / "fixtures" / "lfg_goal" / f).is_file(), f"missing fixture {f}"
    # config block
    config = json.loads((REPO_ROOT / "athanor.json").read_text())
    assert "lfgGoal" in config, "athanor.json missing lfgGoal block"
    assert config["lfgGoal"]["maxIterations"] == 5, "D8 default violated"
    assert config["lfgGoal"]["consolidateCycles"] is False, "D9 default violated"
    # template parity
    template = json.loads((REPO_ROOT / "templates" / "athanor.json").read_text())
    assert template["lfgGoal"] == config["lfgGoal"], "athanor.json + templates/athanor.json lfgGoal parity violated"
    # version bump
    plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "0.13.1", f"plugin.json version not bumped: {plugin['version']}"


def test_companion_fix_arc_scripts_present():
    """v0.11.3-v0.11.8 companion-fix arc scripts must survive v0.13.x ship (D10/D11 preservation)."""
    assert (REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py").is_file()
    assert (REPO_ROOT / "scripts" / "hooks" / "hook_state.py").is_file()
    assert (REPO_ROOT / "scripts" / "hooks" / "sentinel_helper.py").is_file()
