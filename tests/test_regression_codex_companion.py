"""Regression tests for the Codex companion plugin.

The Codex companion is intentionally separate from the Claude Code plugin
runtime. It must expose prefix-safe Codex skills and a repo-local marketplace
entry without changing Athanor's Claude hooks or command surface.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEX_PLUGIN_ROOT = REPO_ROOT / "plugins" / "athanor-codex"
CODEX_MANIFEST = CODEX_PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CODEX_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
CODEX_MIRROR_SOURCE_MAP = REPO_ROOT / "docs" / "codex-mirror-source-map.md"
CODEX_MIRROR_PARITY_GATE = REPO_ROOT / "scripts" / "gates" / "codex_mirror_parity.py"
PARENT_RECEIPT_VALIDATOR = (
    REPO_ROOT / "skills" / "lfg-loop" / "references" / "receipt-validator.md"
)
CODEX_LFG_GOAL_SKILL = (
    CODEX_PLUGIN_ROOT / "skills" / "athanor-lfg-loop" / "SKILL.md"
)
EXPECTED_SKILLS = {
    "athanor-analyze",
    "athanor-assess",
    "athanor-debug",
    "athanor-deep-plan",
    "athanor-discuss",
    "athanor-lfg",
    "athanor-lfg-loop",
    "athanor-lite-plan",
    "athanor-plan",
    "athanor-prompt-gen",
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


def _run_mirror_report(*extra_args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "scripts/gates/codex_mirror_parity.py", "--json", *extra_args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


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
    assert "prompt" in manifest["interface"]["longDescription"].lower()


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


def test_codex_mirror_source_map_lists_all_claude_and_codex_surfaces():
    assert CODEX_MIRROR_SOURCE_MAP.is_file()
    assert CODEX_MIRROR_PARITY_GATE.is_file()

    text = CODEX_MIRROR_SOURCE_MAP.read_text(encoding="utf-8")
    required_tokens = [
        "skills/assess/SKILL.md",
        "plugins/athanor-codex/skills/athanor-assess/SKILL.md",
        "skills/prompt-gen/SKILL.md",
        "plugins/athanor-codex/skills/athanor-prompt-gen/SKILL.md",
        "skills/deep-plan/SKILL.md",
        "plugins/athanor-codex/skills/athanor-deep-plan/SKILL.md",
        "skills/lite-plan/SKILL.md",
        "plugins/athanor-codex/skills/athanor-lite-plan/SKILL.md",
        "skills/ce-test-browser/SKILL.md",
        "Claude-only",
        "agents/releaser.md",
        "plugins/athanor-codex/skills/athanor-release/SKILL.md",
        "agents/ci-watcher.md",
        "plugins/athanor-codex/skills/athanor-ci-watch/SKILL.md",
        "Unsupported Claude-only runtime surfaces",
        "hook-backed enforcement",
        "Claude PreToolUse",
        "Claude Task",
    ]
    for token in required_tokens:
        assert token in text, f"mirror source map missing token: {token!r}"


def test_codex_mirror_parity_gate_reports_current_source_map_pass():
    report = _run_mirror_report()

    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["missing_mirror_rows"] == 0
    assert report["summary"]["unexpected_mirror_rows"] == 0
    assert report["summary"]["stale_version_refs"] == 0
    assert report["summary"]["description_anchor_mismatches"] == 0
    assert report["summary"]["unsupported_claude_only_surfaces"] >= 4
    assert report["profile"] == {
        "id": "codex-mirror-parity",
        "description": "Read-only verifier for the Claude-to-Codex mirror source map.",
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "irreversible_actions": 0,
    }

    rows = {row["codex_surface"]: row for row in report["rows"]}
    assert rows["athanor-assess"]["status"] == "mirror"
    assert rows["athanor-assess"]["claude_surface"] == "assess"
    assert rows["athanor-prompt-gen"]["status"] == "mirror"
    assert rows["athanor-prompt-gen"]["claude_surface"] == "prompt-gen"
    assert rows["athanor-release"]["status"] == "codex-agent-mirror"
    assert rows["athanor-ci-watch"]["status"] == "codex-agent-mirror"


def test_codex_mirror_parity_gate_fails_when_source_map_drops_prompt_gen(tmp_path):
    source_copy = tmp_path / "codex-mirror-source-map.md"
    body = CODEX_MIRROR_SOURCE_MAP.read_text(encoding="utf-8")
    filtered = "\n".join(
        line
        for line in body.splitlines()
        if "prompt-gen" not in line and "athanor-prompt-gen" not in line
    )
    source_copy.write_text(filtered + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/gates/codex_mirror_parity.py",
            "--json",
            "--source-map",
            str(source_copy),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "prompt-gen" in report["checks_by_id"]["mirror.expected_claude_surfaces"][
        "missing"
    ]
    assert "athanor-prompt-gen" in report["checks_by_id"]["mirror.expected_codex_surfaces"][
        "missing"
    ]


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
        "hook-backed enforcement",
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


def test_codex_prompt_gen_skill_absorbs_prompt_routing_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-prompt-gen" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "Generated Prompt",
        "Recommended Next Skill",
        "Success Criteria",
        "Open Questions",
        "athanor-plan",
        "athanor-lfg-loop",
        "Output-only default",
        "raw request is input material",
        "not an execution instruction",
        "Do not run downstream commands",
        "Do not implement",
        "Do not silently call the recommended skill",
        "separate user approval",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-prompt-gen missing contract token: {token!r}"


def test_codex_verify_skill_absorbs_completion_evidence_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-verify" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "material claim",
        "evidence",
        "tests",
        "commands",
        "Do not claim hook-backed enforcement",
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
        "Do not claim hook-backed enforcement",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-lfg missing contract token: {token!r}"


def test_codex_lfg_loop_skill_absorbs_receipt_ledger_contract():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-lfg-loop" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    required_tokens = [
        "Validated Receipt-Ledger Loop",
        ".athanor/loops",
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
        "Do not claim hook-backed enforcement",
    ]
    for token in required_tokens:
        assert token in text, f"athanor-lfg-loop missing contract token: {token!r}"


def test_codex_lfg_loop_skill_includes_receipt_validator_table():
    text = (CODEX_PLUGIN_ROOT / "skills" / "athanor-lfg-loop" / "SKILL.md").read_text(
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
        assert token in text, f"athanor-lfg-loop missing validator token: {token!r}"


def _normalize_ws(text: str) -> str:
    """Collapse all runs of whitespace (incl. newlines) to single spaces.

    The parent rule spans multiple lines because of markdown reflow; the
    companion mirror may wrap differently. Whitespace-insensitive comparison
    lets us assert the *semantics* survive without pinning line breaks.
    """
    return " ".join(text.split())


def test_codex_lfg_loop_undetermined_rule_matches_parent():
    """Two-way parity: the companion's UNDETERMINED aggregate semantics must
    match the parent receipt-validator's non-blocking rule.

    The expected tokens are DERIVED from the parent
    `skills/lfg-loop/references/receipt-validator.md` (not hardcoded in
    isolation): we first assert the parent still carries the canonical rule
    (a derivation guard — if the parent rule is reworded or removed, this
    fails and forces re-derivation), then assert the companion mirrors the
    same non-blocking semantics. A change to *either* side breaks the test.
    """
    parent_text = PARENT_RECEIPT_VALIDATOR.read_text(encoding="utf-8")
    companion_text = CODEX_LFG_GOAL_SKILL.read_text(encoding="utf-8")

    parent_norm = _normalize_ws(parent_text)
    companion_norm = _normalize_ws(companion_text)

    # The parent's canonical UNDETERMINED non-blocking rule. These tokens are
    # the stable contract surface; we re-assert them against the parent first
    # so the derivation source is verified, then carry them to the companion.
    canonical_rule_tokens = [
        # The headline non-blocking semantics phrase.
        "8 `VALID` + 1 `UNDETERMINED` still aggregates as `all_valid`",
        # The blocking guard — UNDETERMINED is tolerated only with no INVALID.
        "provided no step is `INVALID`",
        # The explicit non-blocking label.
        "non-blocking",
    ]

    # Derivation guard: the parent MUST still contain the rule we derive from.
    for token in canonical_rule_tokens:
        assert token in parent_norm, (
            "parent receipt-validator.md no longer carries the canonical "
            f"UNDETERMINED rule token {token!r}; re-derive parity expectations."
        )

    # Parity assertion: the companion mirror MUST carry the same semantics.
    for token in canonical_rule_tokens:
        assert token in companion_norm, (
            "companion athanor-lfg-loop SKILL.md is out of parity with the "
            f"parent UNDETERMINED non-blocking rule; missing token {token!r}."
        )

    # Stronger semantic check: the companion's `all_valid` bucket must NOT
    # define itself as a bare "every/all row VALID" with no UNDETERMINED
    # tolerance. Confirm the non-blocking carve-out co-occurs with `all_valid`.
    assert "non-blocking for aggregate" in companion_norm, (
        "companion must state UNDETERMINED is non-blocking for aggregate, "
        "matching parent receipt-validator.md semantics."
    )


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
