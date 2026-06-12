"""Regression tests for the Codex companion plugin.

The Codex companion is intentionally separate from the Claude Code plugin
runtime. It must expose prefix-safe Codex skills and a repo-local marketplace
entry without changing Athanor's Claude hooks or command surface.

Companion-vs-parent pin directionality (M5 — one-way-pin rationale)
==================================================================

Most assertions in this module pin the companion plugin's content against
*hardcoded literals* (token lists, manifest values, dir-name sets). Exactly
one assertion *derives* its expectation from the parent (native Claude)
surface at test time. The distinction matters: a two-way derived pin breaks
the moment EITHER side drifts; a one-way verbatim pin breaks ONLY when the
companion drifts from the named literal — a parent-side edit alone does NOT
trip it. This block enumerates which pins are which and WHY one-way is the
correct (fail-loud, not fail-silent) choice for each one-way group.

Why one-way is acceptable in general
------------------------------------
A one-way pin asserts the companion still carries a *published contract
surface* (status vocabulary the worker must emit, LFG step headings users
type, the receipt-validator table, the release ceremony surface, etc.).
These surfaces are deliberately versioned: they should change only through a
considered companion release, never silently follow whatever the parent
happens to evolve into. If we instead *derived* every companion expectation
from the parent, a routine parent reword would silently mutate the
companion's asserted contract — masking a real divergence the maintainer
needs to see and ratify. The companion is a separate published artifact, so
"the parent changed, therefore the companion expectation changed too" is the
wrong default. With a one-way pin, a parent change that SHOULD propagate
surfaces as a loud, located failure at companion-update time (the literal no
longer matches), forcing a deliberate edit + re-pin rather than an invisible
drift. This is the same fail-loud-over-silent-fallback stance the repo holds
elsewhere: a stale pin is a feature, not a bug — it is the alarm.

Two-way DERIVED pin (breaks if EITHER companion OR parent drifts)
-----------------------------------------------------------------
* UNDETERMINED non-blocking parity rule
  -> ``test_codex_lfg_goal_undetermined_rule_matches_parent``
  Reads BOTH ``PARENT_RECEIPT_VALIDATOR``
  (``skills/lfg-goal/references/receipt-validator.md``) AND
  ``CODEX_LFG_GOAL_SKILL``. It first re-asserts the canonical UNDETERMINED
  tokens against the parent (a derivation guard: if the parent rule is
  reworded or removed the test fails and *forces re-derivation*), then
  asserts the companion mirrors the same non-blocking semantics. This pin is
  intentionally two-way because the aggregate-status rule ("8 VALID + 1
  UNDETERMINED still aggregates as all_valid, provided no step is INVALID")
  is a *shared algorithm contract*, not a companion-local prose surface — the
  two artifacts MUST agree on the actual gate semantics, so divergence on
  either side is a real bug worth a hard failure. (Note ``_normalize_ws``
  exists only to make this comparison whitespace-insensitive across markdown
  reflow; it is plumbing for this one two-way test.)

One-way VERBATIM pins (break ONLY when the companion drifts from the literal)
----------------------------------------------------------------------------
Plan-named groups:

* status vocabulary
  -> ``test_codex_work_skill_absorbs_execution_contract_without_hooks``
  Pins the ATHANOR_RESULT status enum the Codex worker must emit
  (``done_with_concerns`` / ``needs_context`` / ``blocked``) plus the
  execution-class tokens (Spec-then-TDD / test-aware / direct) and the
  no-hook-enforcement disclaimer, as companion-only literals. One-way is
  right: this is the worker's own output protocol; it must stay stable for
  the leader's parser regardless of how parent prose evolves.

* LFG step headings
  -> ``test_codex_lfg_skill_absorbs_end_to_end_pipeline_contract``
  Pins the user-facing pipeline step headings (``Step 1`` plan ...
  ``Step 8`` CI) and the ``<promise>DONE</promise>`` sentinel as
  companion-only literals. One-way is right: these step labels are a
  published surface Codex users follow; a parent renumbering should force a
  deliberate companion edit, not silently rewrite the asserted headings.

* receipt table
  -> ``test_codex_lfg_goal_skill_includes_receipt_validator_table``
  Pins the 9-step verification-command table and its aggregate buckets
  (``VALID`` / ``INVALID`` / ``UNDETERMINED`` / ``all_valid`` /
  ``completed_with_residuals`` / ``invalid_steps_present``) as companion-only
  literals. (Contrast: the *semantics* of the UNDETERMINED bucket are
  two-way derived above; this group pins only that the table's vocabulary is
  *present* in the companion, which is a companion-local structural surface.)
  One-way is right: the table is a published validator contract that should
  change only on a deliberate companion release.

* release surface
  -> ``test_codex_release_skill_absorbs_release_ceremony_contract``
  Pins the release-ceremony surface (5-file version bump set, the
  ``python3 scripts/check_release_ready.py --ci`` gate command, the
  no-Task-dispatch disclaimer) as companion-only literals. One-way is right:
  the release surface is a stable operational contract; a stale pin firing at
  companion-update time is exactly the alarm a maintainer wants.

Additional one-way groups (same rationale — companion-only structural/contract
surfaces; a parent edit alone must NOT silently move the expectation):

* ``test_codex_companion_manifest_is_codex_native`` — Codex manifest shape
  (``skills`` path, absence of ``hooks``/``mcpServers``/``apps``, interface
  display/long-description tokens).
* ``test_codex_companion_marketplace_selector`` — repo-local marketplace
  entry (source path, install/auth policy, category).
* ``test_codex_companion_exposes_only_prefix_safe_skills`` — the exact
  ``EXPECTED_SKILLS`` dir-name set and per-skill ``athanor-`` prefix.
* ``test_codex_companion_keeps_claude_runtime_separate`` — Claude runtime
  files present AND the companion ships no ``hooks`` dir (separation invariant).
* ``test_codex_companion_documents_install_and_refresh_flow`` — README install
  command *shapes* (deliberately NOT a machine-specific absolute path, per the
  v0.18.7 ``06_athanor`` regression) plus a fail-loud guard on the stale path.
* ``test_codex_discuss_skill_absorbs_dual_mode_contract`` — dual-mode tokens
  (synthesis/clarify, the four gap labels, one-question-per-turn).
* ``test_codex_analyze_skill_absorbs_fast_analysis_contract`` — fast-analysis
  contract tokens.
* ``test_codex_verify_skill_absorbs_completion_evidence_contract`` —
  completion-evidence tokens plus the no-Stop-hook-enforcement disclaimer.
* ``test_codex_lfg_goal_skill_absorbs_receipt_ledger_contract`` — the durable
  goal-ledger contract tokens (ledger paths, G-markers, 3-tier check,
  maxIterations, no-hook disclaimer).
* ``test_codex_ci_watch_skill_absorbs_ci_autofix_contract`` — CI autofix-loop
  tokens (``gh`` commands, maxIterations, no-fabricated-status disclaimer).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEX_PLUGIN_ROOT = REPO_ROOT / "plugins" / "athanor-codex"
CODEX_MANIFEST = CODEX_PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CODEX_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
PARENT_RECEIPT_VALIDATOR = (
    REPO_ROOT / "skills" / "lfg-goal" / "references" / "receipt-validator.md"
)
CODEX_LFG_GOAL_SKILL = (
    CODEX_PLUGIN_ROOT / "skills" / "athanor-lfg-goal" / "SKILL.md"
)
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


def _normalize_ws(text: str) -> str:
    """Collapse all runs of whitespace (incl. newlines) to single spaces.

    The parent rule spans multiple lines because of markdown reflow; the
    companion mirror may wrap differently. Whitespace-insensitive comparison
    lets us assert the *semantics* survive without pinning line breaks.
    """
    return " ".join(text.split())


def test_codex_lfg_goal_undetermined_rule_matches_parent():
    """Two-way parity: the companion's UNDETERMINED aggregate semantics must
    match the parent receipt-validator's non-blocking rule.

    The expected tokens are DERIVED from the parent
    `skills/lfg-goal/references/receipt-validator.md` (not hardcoded in
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
            "companion athanor-lfg-goal SKILL.md is out of parity with the "
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
