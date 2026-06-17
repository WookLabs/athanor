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
HOOK_INSTALLER_DOC = REPO_ROOT / "docs" / "hook-installer.md"


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


def test_ci_runs_workflow_scenario_eval_as_named_gate():
    """Workflow eval scenarios should be checked before the broad pytest suite."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Workflow scenario eval gate" in workflow
    assert "python scripts/evals/run_workflow_scenarios.py" in workflow
    assert "--scenario-root tests/fixtures/workflow_evals --json" in workflow


def test_ci_runs_durable_loop_fixture_gate():
    """Durable loop controller scenarios should be checked before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Durable loop fixture gate" in workflow
    assert "python scripts/loops/run_goal_loop_fixtures.py" in workflow
    assert "--fixture-root tests/fixtures/durable_loops --json" in workflow


def test_ci_runs_hook_installer_regression_gate():
    """Installer apply/remove regressions should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Hook installer regression gate" in workflow
    for path in (
        "tests/test_regression_hook_install_dry_run.py",
        "tests/test_regression_hook_installer_trust.py",
        "tests/test_regression_hook_installer_apply.py",
        "tests/test_regression_hook_installer_remove.py",
    ):
        assert path in workflow


def test_hook_installer_docs_cover_modes_trust_and_rollback():
    """Operator docs must cover trust review, modes, backups, and rollback."""
    body = HOOK_INSTALLER_DOC.read_text(encoding="utf-8")
    required = [
        "--mode dry-run",
        "--mode apply",
        "--mode remove",
        "--trust-state",
        "command_hash",
        "source_hashes",
        "schemas/hook-installer-trust.schema.json",
        "backup",
        "Rollback",
        "capture-only",
    ]
    missing = [token for token in required if token not in body]
    assert not missing, f"hook installer docs missing: {missing}"


def test_unreleased_documents_trust_aware_hook_installer():
    """The Unreleased story must name the trust-aware apply/remove path."""
    section = _unreleased_section()
    required = [
        "Trust-aware hook installer",
        "--mode apply",
        "--mode remove",
        "hash",
        "backup",
        "capture-only",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain the trust-aware installer path; "
        f"missing: {missing}"
    )


def test_ci_runs_cross_runtime_conformance_gate():
    """Cross-runtime drift should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Cross-runtime conformance gate" in workflow
    assert "python scripts/gates/runtime_conformance.py --json" in workflow


def test_unreleased_documents_cross_runtime_conformance_gate():
    """The Unreleased story must name the P9 conformance gate."""
    section = _unreleased_section()
    required = [
        "Cross-runtime conformance gate",
        "runtime-surface contract",
        "Codex companion",
        "hooks/catalog.json",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain the cross-runtime gate; "
        f"missing: {missing}"
    )


def test_ci_runs_observability_trend_snapshot_gate():
    """P10 observability snapshots should be checked before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Observability trend snapshot gate" in workflow
    assert "python scripts/observability/collect_trend_snapshot.py --json --samples 1" in workflow


def test_unreleased_documents_observability_trends():
    """The Unreleased story must name local observability trend tooling."""
    section = _unreleased_section()
    required = [
        "Observability trend snapshots",
        "scripts/observability/collect_trend_snapshot.py",
        "trace-to-scenario promotion",
        ".athanor/observability/trends.jsonl",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P10 observability trends; "
        f"missing: {missing}"
    )


def test_ci_runs_entropy_cleanup_report_gate():
    """P11 entropy cleanup should run before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Entropy cleanup report gate" in workflow
    assert "python scripts/gates/entropy_cleanup.py --json" in workflow


def test_unreleased_documents_entropy_cleanup_loop():
    """The Unreleased story must name the P11 entropy cleanup loop."""
    section = _unreleased_section()
    required = [
        "Entropy cleanup report gate",
        "scripts/gates/entropy_cleanup.py",
        "capture-only hook candidates",
        "ref freshness",
        "read-only",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P11 entropy cleanup; "
        f"missing: {missing}"
    )
