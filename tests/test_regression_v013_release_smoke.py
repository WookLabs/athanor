"""v0.13.0 + v0.13.1 + v0.13.2 + v0.14.0 release-smoke regression test. Locks the v0.13.x + v0.14.0 deliverable surface as a single high-signal check."""
from __future__ import annotations
import json
from pathlib import Path

from tests._version import _plugin_version

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_v013_release_surface_intact():
    """Locks all v0.13.0 + v0.13.1 + v0.13.2 + v0.14.0 deliverables in one assertion bundle.

    Catches regression of any single deliverable shipping in the v0.13.x + v0.14.0 release line.
    """
    # skill spec
    assert (REPO_ROOT / "skills" / "lfg-loop" / "SKILL.md").is_file()
    # 5 reference files
    refs = [
        "receipt-validator.md",
        "judge-rubric.md",
        "scope-change-critic.md",
        "state-shape.md",
        "loop-md-template.md",
    ]
    for r in refs:
        assert (REPO_ROOT / "skills" / "lfg-loop" / "references" / r).is_file(), f"missing reference {r}"
    # 3 fixtures
    fixtures = ["receipt_valid.md", "receipt_invalid_missing_step3.md", "receipt_partial_with_residuals.md"]
    for f in fixtures:
        assert (REPO_ROOT / "tests" / "fixtures" / "lfg_loop" / f).is_file(), f"missing fixture {f}"
    # config block
    config = json.loads((REPO_ROOT / "athanor.json").read_text(encoding="utf-8"))
    assert "lfgLoop" in config, "athanor.json missing lfgLoop block"
    assert config["lfgLoop"]["maxIterations"] == 5, "D8 default violated"
    assert config["lfgLoop"]["consolidateCycles"] is False, "D9 default violated"
    # template parity
    template = json.loads(
        (REPO_ROOT / "templates" / "athanor.json").read_text(encoding="utf-8")
    )
    assert template["lfgLoop"] == config["lfgLoop"], "athanor.json + templates/athanor.json lfgLoop parity violated"
    # version bump
    plugin = json.loads(
        (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert plugin["version"] == _plugin_version(), f"plugin.json version not bumped: {plugin['version']}"


def test_active_hook_scripts_present():
    """The retained active hook surface is PreToolUse + PostToolUse only."""
    assert (REPO_ROOT / "scripts" / "hooks" / "pretool_dispatcher.py").is_file()
    assert (REPO_ROOT / "scripts" / "hooks" / "pretool_kernel_guard.py").is_file()
    assert (REPO_ROOT / "scripts" / "hooks" / "posttool_evidence_sniffer.py").is_file()
    assert not (REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py").exists()
