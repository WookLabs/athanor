"""Release-story regression tests for the v0.19 evidence branch.

The xhigh audit item 8 says not to bump the plugin version unless this branch
is explicitly being shipped as v0.19.0. Until that release pass happens, the
Unreleased changelog section must carry the branch story so the runtime changes
are not invisible while the manifests remain pinned to the current release.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
STATE_MD = REPO_ROOT / "docs" / "STATE.md"
VALIDATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "validate-plugin.yml"
ROADMAP = REPO_ROOT / "docs" / "ROADMAP.md"


def _unreleased_section() -> str:
    body = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(
        r"^##\s+\[Unreleased\]\s*\n(.*?)(?=^##\s+\[|\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    assert match, "CHANGELOG.md must contain an [Unreleased] section"
    return match.group(1)


def test_unreleased_documents_v019_evidence_branch_story():
    """Unreleased must name the evidence-branch changes before release bump."""
    section = _unreleased_section()
    required = [
        "PostToolUse",
        "hook payload corpus",
        "hooks.evidence.mode",
        "UserPromptSubmit spike",
        "hook payload capture harness",
        "release-specific pass",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain the v0.19 evidence branch story; "
        f"missing: {missing}"
    )


def test_v019_branch_does_not_bump_plugin_version_before_release_pass():
    """Version bump is deferred until explicitly shipping the release."""
    version = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
    assert version == "0.18.8"
    assert "release-specific pass" in _unreleased_section()


def test_state_known_gaps_do_not_claim_ci_is_ubuntu_only():
    """STATE must not keep the stale CI-matrix known gap after Windows CI lands."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert "matrix:" in workflow

    state = STATE_MD.read_text(encoding="utf-8")
    assert "CI matrix는 ubuntu-latest 단일" not in state


def test_strict_default_upgrade_policy_is_documented():
    """Strict evidence default needs migration framing before default changes."""
    body = ROADMAP.read_text(encoding="utf-8")
    marker = "### v0.19.0 — PostToolUse evidence sniffer"
    start = body.find(marker)
    assert start != -1
    section = body[start : body.find("\n### ", start + 1)]
    for token in (
        "Strict default migration policy",
        "new installs",
        "existing installs",
        "hooks.evidence.mode",
        "warn",
        "strict",
    ):
        assert token in section


def test_ci_runs_hook_fixture_replay_as_named_gate():
    """Hook replay should fail as its own CI step, not only inside pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Hook payload replay gate" in workflow
    assert "python scripts/gates/replay_hook_fixtures.py" in workflow
    assert "--fixture-root tests/fixtures/hooks --json" in workflow


def test_ci_runs_hook_performance_budget_as_named_gate():
    """Catalog hook budgets should be executable CI gates, not doc-only fields."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Hook performance budget gate" in workflow
    assert "python scripts/gates/check_hook_performance_budget.py" in workflow
    assert "--json" in workflow
