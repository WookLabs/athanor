"""Release-story regression tests for the v0.19 evidence branch."""
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
        r"^##\s+\[0\.19\.0\]\s+.*?\n(.*?)(?=^##\s+\[|\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    assert match, "CHANGELOG.md must contain a [0.19.0] release section"
    return match.group(1)


def test_v019_release_documents_evidence_branch_story():
    """The release entry must name the evidence-branch changes."""
    section = _unreleased_section()
    required = [
        "PostToolUse",
        "hook payload corpus",
        "hooks.evidence.mode",
        "UserPromptSubmit spike",
        "hook payload capture harness",
        "release bumps manifests",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain the v0.19 evidence branch story; "
        f"missing: {missing}"
    )


def test_v019_release_bumps_plugin_version():
    """The release pass bumps the plugin manifest."""
    version = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
    assert version.startswith("0.19.")
    assert "Ships the v0.19.0" in _unreleased_section()


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


def test_ci_runs_runtime_execution_adapter_fixture_gate():
    """P12 runtime backend routing should be checked before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Runtime execution adapter fixture gate" in workflow
    assert "python scripts/gates/runtime_execution_adapter.py" in workflow
    assert "--fixture-root tests/fixtures/runtime_execution --json" in workflow


def test_unreleased_documents_runtime_execution_adapter():
    """The Unreleased story must name the P12 runtime execution adapter."""
    section = _unreleased_section()
    required = [
        "Runtime execution adapter",
        "scripts/gates/runtime_execution_adapter.py",
        "dynamic workflow",
        "agent team",
        "worktree",
        "read-only",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P12 runtime execution adapter; "
        f"missing: {missing}"
    )


def test_unreleased_documents_live_command_trace_emitter():
    """The Unreleased story must name the P13 live command trace emitter."""
    section = _unreleased_section()
    required = [
        "Live command trace emitter",
        "scripts/evals/emit_workflow_trace.py",
        ".athanor/traces",
        "workflow.started",
        "workflow.finished",
        "local-first",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P13 live command trace emission; "
        f"missing: {missing}"
    )


def test_unreleased_documents_otel_trace_export_adapter():
    """The Unreleased story must name the P14 local OTel trace export adapter."""
    section = _unreleased_section()
    required = [
        "OTel-style trace export adapter",
        "scripts/evals/export_otel_trace.py",
        "schemas/otel-trace-export.schema.json",
        "gen_ai.operation.name",
        "privacy-safe",
        "local JSON",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P14 OTel-style trace export; "
        f"missing: {missing}"
    )


def test_ci_runs_workflow_episode_package_gate():
    """P15 portable episodes should be checked before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Workflow episode package gate" in workflow
    assert "python scripts/evals/package_workflow_episode.py" in workflow
    assert "--scenario-root tests/fixtures/workflow_evals" in workflow
    assert "--output-dir .athanor/episodes/workflow-evals --json" in workflow
    assert "python scripts/evals/run_workflow_scenarios.py --episode-root .athanor/episodes/workflow-evals --json" in workflow


def test_unreleased_documents_workflow_eval_episode_packaging():
    """The Unreleased story must name the P15 portable eval episode package."""
    section = _unreleased_section()
    required = [
        "Workflow eval episode packaging",
        "scripts/evals/package_workflow_episode.py",
        "schemas/workflow-eval-episode.schema.json",
        "--episode-root",
        "deterministic_grader_kinds",
        "network_access",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P15 workflow eval episode packaging; "
        f"missing: {missing}"
    )


def test_ci_runs_distribution_smoke_gate():
    """P16 plugin distribution smoke should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Distribution smoke gate" in workflow
    assert "python scripts/gates/distribution_smoke.py --json" in workflow


def test_unreleased_documents_distribution_smoke_gate():
    """The Unreleased story must name the P16 distribution smoke gate."""
    section = _unreleased_section()
    required = [
        "Distribution smoke gate",
        "scripts/gates/distribution_smoke.py",
        "claude plugin details",
        "4-agent",
        "always-on",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P16 distribution smoke; "
        f"missing: {missing}"
    )


def test_ci_runs_trace_memory_quality_gate():
    """P17 trace-memory quality should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Trace-memory quality gate" in workflow
    assert "python scripts/gates/trace_memory_quality.py" in workflow
    assert "--lesson-root tests/fixtures/trace_memory_quality/lessons" in workflow
    assert "--comparison-file tests/fixtures/trace_memory_quality/comparisons.json" in workflow


def test_unreleased_documents_trace_memory_quality_gate():
    """The Unreleased story must name the P17 trace-memory quality gate."""
    section = _unreleased_section()
    required = [
        "Trace-memory quality gate",
        "scripts/gates/trace_memory_quality.py",
        "promotion",
        "stale decay",
        "quarantine",
        "with/without lesson",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P17 trace-memory quality; "
        f"missing: {missing}"
    )


def test_ci_runs_native_runtime_probe_gate():
    """P19 native runtime probe should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Native runtime probe gate" in workflow
    assert "python scripts/gates/native_runtime_probe.py" in workflow
    assert "--fixture-root tests/fixtures/native_runtime_probe --json" in workflow


def test_unreleased_documents_native_runtime_probe():
    """The Unreleased story must name the P19 native runtime probe."""
    section = _unreleased_section()
    required = [
        "Native runtime probe",
        "scripts/gates/native_runtime_probe.py",
        "/goal",
        "/loop",
        "dynamic workflow",
        "agent team",
        "worktree",
        "dry-run",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P19 native runtime probe; "
        f"missing: {missing}"
    )


def test_ci_runs_maintenance_profile_gate():
    """P20 maintenance profile should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Maintenance profile gate" in workflow
    assert "python scripts/gates/maintenance_profile.py" in workflow
    assert "--skip-claude --ref-warn-days 99999 --samples 1 --json" in workflow


def test_unreleased_documents_maintenance_profile_gate():
    """The Unreleased story must name the P20 maintenance profile."""
    section = _unreleased_section()
    required = [
        "Maintenance profile gate",
        "scripts/gates/maintenance_profile.py",
        "/loop",
        "entropy cleanup",
        "distribution smoke",
        "observability",
        "native runtime probe",
        "read-only",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P20 maintenance profile; "
        f"missing: {missing}"
    )


def test_ci_runs_package_footprint_policy_gate():
    """P21 package footprint policy should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Package footprint policy gate" in workflow
    assert "python scripts/gates/package_footprint_policy.py --json" in workflow


def test_unreleased_documents_package_footprint_policy_gate():
    """The Unreleased story must name the P21 package footprint policy."""
    section = _unreleased_section()
    required = [
        "Package footprint policy gate",
        "scripts/gates/package_footprint_policy.py",
        "ship profile",
        "dev-only candidates",
        "read-only",
        "exclude-from-ship-profile",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P21 package footprint policy; "
        f"missing: {missing}"
    )


def test_ci_runs_external_eval_adapter_gate():
    """P22 external eval adapter should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "External eval adapter gate" in workflow
    assert "python scripts/evals/export_external_eval_adapter.py" in workflow
    assert "--episode-root .athanor/episodes/workflow-evals" in workflow
    assert "--output-dir .athanor/external-evals/workflow-evals --json" in workflow


def test_unreleased_documents_external_eval_adapter():
    """The Unreleased story must name the P22 external eval adapter."""
    section = _unreleased_section()
    required = [
        "External eval adapter",
        "scripts/evals/export_external_eval_adapter.py",
        "inspect-like",
        "harbor-like",
        "sandbox/manifest.json",
        "no default external execution",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P22 external eval adapter; "
        f"missing: {missing}"
    )


def test_ci_runs_native_runtime_playbook_gate():
    """P23 native runtime playbook should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Native runtime playbook gate" in workflow
    assert "python scripts/gates/native_runtime_playbook.py" in workflow
    assert "--fixture-root tests/fixtures/native_runtime_probe --json" in workflow


def test_unreleased_documents_native_runtime_playbook():
    """The Unreleased story must name the P23 native runtime playbook."""
    section = _unreleased_section()
    required = [
        "Native runtime playbook",
        "scripts/gates/native_runtime_playbook.py",
        "operator-approved",
        "manual-worktree",
        "dynamic-workflow",
        "agent-team",
        "auto_execute",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P23 native runtime playbook; "
        f"missing: {missing}"
    )


def test_ci_runs_reactive_channel_fixture_gate():
    """P24 reactive channel fixture should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Reactive channel fixture gate" in workflow
    assert "python scripts/gates/reactive_channel_fixture.py" in workflow
    assert "--fixture-root tests/fixtures/reactive_channels --json" in workflow


def test_unreleased_documents_reactive_channel_fixture():
    """The Unreleased story must name the P24 reactive channel fixture gate."""
    section = _unreleased_section()
    required = [
        "Reactive channel fixture gate",
        "scripts/gates/reactive_channel_fixture.py",
        "local-only",
        "dispatch-ci-watcher",
        "plan-review-response",
        "auto_execute",
        "listener",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P24 reactive channel fixture; "
        f"missing: {missing}"
    )


def test_ci_runs_package_knowledge_index_gate():
    """P25 package knowledge index should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Package knowledge index gate" in workflow
    assert "python scripts/gates/package_knowledge_index.py --json" in workflow


def test_unreleased_documents_package_knowledge_index():
    """The Unreleased story must name the P25 package knowledge index."""
    section = _unreleased_section()
    required = [
        "Package knowledge index",
        "docs/package-knowledge-index.md",
        "scripts/gates/package_knowledge_index.py",
        "README.md",
        "CLAUDE.md",
        "repo-local",
        "ship profile",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P25 package knowledge index; "
        f"missing: {missing}"
    )


def test_ci_runs_organization_operating_model_gate():
    """P26 organization operating model should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Organization operating model gate" in workflow
    assert "python scripts/gates/organization_operating_model.py --json" in workflow


def test_unreleased_documents_organization_operating_model():
    """The Unreleased story must name the P26 organization operating model."""
    section = _unreleased_section()
    required = [
        "Organization operating model",
        "docs/organization-operating-model.md",
        "scripts/gates/organization_operating_model.py",
        "office/stage graph",
        "receipt",
        "learning governance",
        "no default live listener",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P26 organization operating model; "
        f"missing: {missing}"
    )


def test_ci_runs_organization_work_item_registry_gate():
    """P27 organization work-item registry should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Organization work-item registry gate" in workflow
    assert "python scripts/gates/organization_work_item_registry.py --json" in workflow


def test_unreleased_documents_organization_work_item_registry():
    """The Unreleased story must name the P27 organization work-item registry."""
    section = _unreleased_section()
    required = [
        "Organization work-item registry",
        "docs/organization-work-item-registry.md",
        "scripts/gates/organization_work_item_registry.py",
        "stage history",
        "receipt_ref",
        "9.8",
        "work-item",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P27 organization work-item registry; "
        f"missing: {missing}"
    )


def test_ci_runs_organization_stage_receipt_gate():
    """P28 organization stage receipts should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Organization stage receipt gate" in workflow
    assert "python scripts/gates/organization_stage_receipt.py --json" in workflow


def test_unreleased_documents_organization_stage_receipts():
    """The Unreleased story must name the P28 organization stage receipt adapter."""
    section = _unreleased_section()
    required = [
        "Organization stage receipts",
        "docs/organization-stage-receipts.md",
        "scripts/gates/organization_stage_receipt.py",
        "--emit",
        "--apply-work-item-update",
        "lfg-goal",
        "stage receipt",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P28 organization stage receipts; "
        f"missing: {missing}"
    )


def test_ci_runs_policy_promotion_ledger_gate():
    """P29 policy promotion ledger should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Policy promotion ledger gate" in workflow
    assert "python scripts/gates/policy_promotion_ledger.py --json" in workflow


def test_unreleased_documents_policy_promotion_ledger():
    """The Unreleased story must name the P29 policy promotion ledger."""
    section = _unreleased_section()
    required = [
        "Policy promotion ledger",
        "docs/policy-promotion-ledger.md",
        "scripts/gates/policy_promotion_ledger.py",
        "candidate_policy",
        "gate_candidate",
        "retired",
        "rollback",
        "schema-backed",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P29 policy promotion ledger; "
        f"missing: {missing}"
    )


def test_ci_runs_organization_score_gate():
    """P30 organization score should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Organization score gate" in workflow
    assert "python scripts/gates/organization_score.py --json" in workflow


def test_unreleased_documents_organization_score_gate():
    """The Unreleased story must name the P30 organization score gate."""
    section = _unreleased_section()
    required = [
        "Organization score gate",
        "docs/organization-score.md",
        "scripts/gates/organization_score.py",
        "9.8",
        "weighted dimensions",
        "residual gaps",
        "scorecard prose",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P30 organization score gate; "
        f"missing: {missing}"
    )


def test_ci_runs_harness_decision_ledger_gate():
    """P18 harness decision ledger should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Harness decision ledger gate" in workflow
    assert "python scripts/gates/harness_decision_ledger.py --json" in workflow


def test_unreleased_documents_harness_decision_ledger():
    """The Unreleased story must name the P18 harness decision ledger."""
    section = _unreleased_section()
    required = [
        "Harness decision ledger",
        "docs/harness-decisions/*.json",
        "scripts/gates/harness_decision_ledger.py",
        "expected metrics",
        "observed results",
        "rollback/follow-up decisions",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P18 harness decision ledger; "
        f"missing: {missing}"
    )
