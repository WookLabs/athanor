"""Regression tests for the Codex companion plugin.

The Codex companion is intentionally separate from the Claude Code plugin
runtime. It must expose prefix-safe Codex skills and a repo-local marketplace
entry without changing Athanor's Claude hooks or command surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEX_PLUGIN_ROOT = REPO_ROOT / "plugins" / "athanor-codex"
CODEX_MANIFEST = CODEX_PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CODEX_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
EXPECTED_SKILLS = {
    "athanor-analyze",
    "athanor-debug",
    "athanor-discuss",
    "athanor-lfg",
    "athanor-lfg-goal",
    "athanor-plan",
    "athanor-ci-watch",
    "athanor-release",
    "athanor-review",
    "athanor-scope-drift",
    "athanor-setup",
    "athanor-verify",
    "athanor-work",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_skill_frontmatter(skill_name: str) -> dict:
    skill_md = CODEX_PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill_md} must start with frontmatter"
    end = text.find("\n---", 4)
    assert end != -1, f"{skill_md} must close frontmatter"
    frontmatter = yaml.safe_load(text[4:end])
    assert isinstance(frontmatter, dict)
    return frontmatter


def test_codex_companion_manifest_is_codex_native():
    manifest = _load_json(CODEX_MANIFEST)

    assert manifest["name"] == "athanor-codex"
    assert manifest["skills"] == "./skills/"
    assert "hooks" not in manifest
    assert "mcpServers" not in manifest
    assert "apps" not in manifest
    assert manifest["interface"]["displayName"] == "Athanor Codex"
    assert "Athanor" in manifest["interface"]["defaultPrompt"]
    assert "analyze" in manifest["interface"]["longDescription"].lower()
    assert "verify" in manifest["interface"]["longDescription"].lower()
    assert "lfg" in manifest["interface"]["longDescription"].lower()
    assert "work" in manifest["interface"]["longDescription"].lower()
    assert "discuss" in manifest["interface"]["longDescription"].lower()
    assert "release" in manifest["interface"]["longDescription"].lower()
    assert "ci" in manifest["interface"]["longDescription"].lower()


def test_codex_companion_marketplace_selector():
    marketplace = _load_json(CODEX_MARKETPLACE)

    assert marketplace["name"] == "athanor"
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}
    assert "athanor-codex" in entries
    entry = entries["athanor-codex"]
    assert entry["source"] == {"source": "local", "path": "./plugins/athanor-codex"}
    assert entry["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert entry["category"] == "Developer Tools"


def test_codex_companion_exposes_only_prefix_safe_skills():
    skill_dirs = {
        path.name
        for path in (CODEX_PLUGIN_ROOT / "skills").iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    assert skill_dirs == EXPECTED_SKILLS

    for skill_name in EXPECTED_SKILLS:
        frontmatter = _load_skill_frontmatter(skill_name)
        assert frontmatter["name"] == skill_name
        assert frontmatter["description"].strip()
        assert skill_name.startswith("athanor-")


def test_codex_companion_keeps_claude_runtime_separate():
    assert (REPO_ROOT / ".claude-plugin" / "plugin.json").is_file()
    assert (REPO_ROOT / "hooks" / "hooks.json").is_file()
    assert (CODEX_PLUGIN_ROOT / "hooks").exists() is False


def test_codex_companion_documents_install_and_refresh_flow():
    readme = CODEX_PLUGIN_ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")

    # Structural tokens only — do NOT pin a machine-specific absolute path.
    # (v0.18.7 regression: the README and this test had hardcoded the wrong
    # repo dir `06_athanor`; locking an absolute path made fixing it break
    # the test. Assert the command *shape* instead.)
    required_tokens = [
        "codex plugin marketplace add ",
        "codex plugin add athanor-codex@athanor",
        "update_plugin_cachebuster.py",
        "Claude Stop hook",
        "Claude PreToolUse",
        "Claude Task",
    ]
    for token in required_tokens:
        assert token in text, f"README missing required token: {token!r}"

    # Fail loud if the known-wrong dev path ever returns.
    assert "06_athanor" not in text, (
        "README references the stale wrong repo path '06_athanor'; "
        "the repository lives at .../03_athanor."
    )


def test_codex_work_skill_absorbs_execution_contract_without_hooks():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-work" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "Spec-then-TDD",
        "test-aware",
        "direct",
        "done_with_concerns",
        "needs_context",
        "blocked",
        ".athanor/sessions",
        "work-log.md",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-work missing contract token: {token!r}"
    assert "Do not claim Claude hook enforcement" in text


def test_codex_discuss_skill_absorbs_dual_mode_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-discuss" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "synthesis",
        "clarify",
        "requirements.md",
        "Evidence gap",
        "Specificity gap",
        "Counterfactual gap",
        "Attachment gap",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-discuss missing contract token: {token!r}"
    assert "one question per turn" in text.lower()


def test_codex_analyze_skill_absorbs_fast_analysis_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-analyze" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "focus areas",
        "repo structure",
        "Historical Context",
        "findings",
        ".athanor/sessions",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-analyze missing contract token: {token!r}"


def test_codex_verify_skill_absorbs_completion_evidence_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-verify" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "material claim",
        "evidence",
        "tests",
        "commands",
        "Do not claim Claude Stop hook enforcement",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-verify missing contract token: {token!r}"


def test_codex_lfg_skill_absorbs_end_to_end_pipeline_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-lfg" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "Step 1",
        "athanor-plan",
        "Step 2",
        "athanor-work",
        "Step 3",
        "athanor-review",
        "Step 7",
        "commit",
        "push",
        "PR",
        "Step 8",
        "CI",
        "<promise>DONE</promise>",
        "Do not claim Claude Stop hook enforcement",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-lfg missing contract token: {token!r}"


def test_codex_lfg_goal_skill_absorbs_receipt_ledger_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-lfg-goal" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "Validated Receipt-Ledger Loop",
        ".athanor/goals",
        "G-markers",
        "CNNN-lfg-receipt.md",
        "receipt-validator",
        "3-tier",
        "Tier 1",
        "Tier 2",
        "Tier 3",
        "<promise>DONE</promise>",
        "insufficient",
        "maxIterations",
        "Do not claim Claude Stop hook enforcement",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-lfg-goal missing contract token: {token!r}"


def test_codex_lfg_goal_skill_includes_receipt_validator_table():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-lfg-goal" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "9-step verification command table",
        "Step 1 plan",
        "Step 2 work",
        "Step 3 review",
        "Step 4 review-fix commit",
        "Step 5 residual handoff",
        "Step 6 browser test",
        "Step 7 commit-push-PR",
        "Step 8 CI watch",
        "Step 9 DONE",
        "VALID",
        "INVALID",
        "UNDETERMINED",
        "aggregate_status",
        "all_valid",
        "completed_with_residuals",
        "invalid_steps_present",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-lfg-goal missing validator token: {token!r}"


def test_codex_release_skill_absorbs_release_ceremony_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-release" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "5-file version bump",
        "plugin.json",
        "marketplace.json",
        "athanor.json",
        "templates/athanor.json",
        "schemas/athanor-config.schema.json",
        "CHANGELOG.md",
        "docs/STATE.md",
        "test pins",
        "python3 scripts/check_release_ready.py --ci",
        "Do not claim Claude Task dispatch",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-release missing contract token: {token!r}"


def test_codex_ci_watch_skill_absorbs_ci_autofix_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-ci-watch" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "gh pr checks",
        "--watch",
        "gh run view",
        "--log-failed",
        "maxIterations",
        "infrastructure failure",
        "gh run rerun",
        "fix",
        "commit",
        "push",
        "Do not fabricate CI status",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-ci-watch missing contract token: {token!r}"
