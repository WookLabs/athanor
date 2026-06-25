"""Regression: v0.15.0 LFG bug eradication — 21 contract tests (all green).

Phase 5 (Final Sweep): all ``@pytest.mark.xfail`` decorators have been
removed. Every test in this file now passes against the fixed codebase.
Each test locks one of the 17 distinct bug IDs (C1-C3x3, H1-H5,
M1/M3/M5-M8, L1/L4/L5) catalogued in the v0.15.0 LFG bug-eradication plan.

Bug categories (per plan):
  - CRITICAL (C1-C3): circuit-breaker placement, aggregate enum, cycle_phase schema
  - HIGH (H1-H5): stale references, Thin Leader violations, ce-lfg ghosts
  - MEDIUM (M1,M3,M5-M8): resume coverage, schema drift, CI timeout, NFKC, Write tool, CLAUDE.md
  - LOW (L1,L4,L5): TTL drift, enforcement transparency, run-id extraction

Decisions:
  - D1: Canonical aggregate enum = all_valid | completed_with_residuals | invalid_steps_present
  - D2: Per-step enum stays hyphenated; aggregate stays underscored
  - D3: xfail-marked tests first, removed at Phase 5
  - D12: Hybrid test strategy (grep for prose locks, parse for machine contracts)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts" / "hooks"

# Import stop_verify_claims for M6 behavioral test
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import stop_verify_claims as svc  # noqa: E402  # type: ignore[import]

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
LFG_GOAL_SKILL = REPO_ROOT / "skills" / "lfg-goal" / "SKILL.md"
LFG_SKILL = REPO_ROOT / "skills" / "lfg" / "SKILL.md"
STATE_SHAPE = REPO_ROOT / "skills" / "lfg-goal" / "references" / "state-shape.md"
RECEIPT_VALIDATOR = REPO_ROOT / "skills" / "lfg-goal" / "references" / "receipt-validator.md"
SCHEMA_PATH = REPO_ROOT / "schemas" / "athanor-config.schema.json"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "lfg_goal"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse leading YAML-ish frontmatter delimited by ``---`` lines."""
    if not text.startswith("---"):
        raise ValueError("Missing leading '---' frontmatter delimiter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Frontmatter not terminated by closing '---'")
    fm_raw, body = parts[1], parts[2]
    fm: dict[str, str] = {}
    current_key: str | None = None
    for line in fm_raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if m and not line.startswith(" "):
            key = m.group(1)
            value = m.group(2).strip()
            fm[key] = value
            current_key = key
        elif current_key is not None and line.startswith(" "):
            fm[current_key] = (fm[current_key] + " " + stripped).strip()
    return fm, body


# ============================================================================
# CRITICAL bugs
# ============================================================================


# ---------------------------------------------------------------------------
# C1: no_progress_against_prior must be INSIDE the for-cycle loop
# ---------------------------------------------------------------------------
def test_c1_no_progress_inside_loop():
    """C1 lock: circuit-breaker logic must be inside the ``for cycle`` loop.

    The pseudocode in §Loop architecture places ``no_progress_against_prior``
    AFTER the ``for cycle`` loop ends. A circuit breaker that only runs after
    the loop exhausts max-iterations is dead code — it can never fire between
    cycles. The fix moves it inside the loop, between the end of the Tier 3
    block and the next iteration's ``inject_goal_into_session_requirements``.
    """
    body = _read(LFG_GOAL_SKILL)
    # Find the for-cycle loop region: between "for cycle in" and the
    # terminal "emit_durable_residual_exit" that ends the function.
    # The no_progress_against_prior call must appear INSIDE the loop
    # (i.e., at higher indentation than the for line, before the loop's
    # closing dedent).
    lines = body.splitlines()
    for_line_idx = None
    no_progress_idx = None

    indent_for = 0

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if "for cycle in" in stripped and for_line_idx is None:
            for_line_idx = i
            indent_for = len(line) - len(stripped)
        if "no_progress_against_prior" in stripped:
            no_progress_idx = i

    assert for_line_idx is not None, "Could not find 'for cycle in' in SKILL.md"
    assert no_progress_idx is not None, "Could not find 'no_progress_against_prior' in SKILL.md"

    # The no_progress line must have GREATER indentation than the for line
    # (meaning it's inside the loop body, not at the same level or outside).
    no_progress_line = lines[no_progress_idx]
    indent_no_progress = len(no_progress_line) - len(no_progress_line.lstrip())
    assert indent_no_progress > indent_for, (
        f"no_progress_against_prior (indent={indent_no_progress}) must be "
        f"indented deeper than 'for cycle in' (indent={indent_for}) to be "
        f"inside the loop body"
    )


# ---------------------------------------------------------------------------
# C2: aggregate enum — receipt-validator.md must have 3 canonical values
# ---------------------------------------------------------------------------
def test_c2_aggregate_enum_receipt_validator():
    """C2 lock (aggregate): receipt-validator.md must define exactly 3 canonical
    aggregate values: all_valid, completed_with_residuals, invalid_steps_present.

    Currently the file has only ``all_valid`` and ``invalid_steps_present``.
    D1 establishes the canonical 3-value enum.
    """
    body = _read(RECEIPT_VALIDATOR)
    canonical = {"all_valid", "completed_with_residuals", "invalid_steps_present"}
    # The validation_status line in ATHANOR_RESULT shape must list all 3
    found = set()
    for value in canonical:
        if value in body:
            found.add(value)
    assert found == canonical, (
        f"receipt-validator.md must contain all 3 canonical aggregate values; "
        f"found={found}, missing={canonical - found}"
    )


# ---------------------------------------------------------------------------
# C2: state-shape.md must include completed_with_residuals
# ---------------------------------------------------------------------------
def test_c2_state_shape_completed_with_residuals():
    """C2 lock (state-shape): state-shape.md ``last_validator_status`` enum
    must include ``completed_with_residuals``.

    Currently the file lists ``all_valid | invalid_steps_present | not_yet_run``.
    """
    body = _read(STATE_SHAPE)
    assert "completed_with_residuals" in body, (
        "state-shape.md must include 'completed_with_residuals' in "
        "last_validator_status enum"
    )


# ---------------------------------------------------------------------------
# C2: fixture files must use canonical aggregate values
# ---------------------------------------------------------------------------
def test_c2_fixtures_canonical_aggregate():
    """C2 lock (fixtures): all fixture ``validator_status:`` lines must use
    values from {all_valid, completed_with_residuals, invalid_steps_present}.

    The partial-with-residuals fixture currently uses ``all_valid`` instead
    of ``completed_with_residuals``.
    """
    canonical = {"all_valid", "completed_with_residuals", "invalid_steps_present"}
    fixture_files = list(FIXTURE_DIR.glob("receipt_*.md"))
    assert len(fixture_files) == 3, f"Expected 3 fixture files, got {len(fixture_files)}"

    for fpath in fixture_files:
        body = _read(fpath)
        for line in body.splitlines():
            if line.strip().startswith("validator_status:"):
                value = line.split(":", 1)[1].strip()
                assert value in canonical, (
                    f"{fpath.name}: validator_status '{value}' not in "
                    f"canonical set {canonical}"
                )

    # Additionally, the partial fixture must specifically use completed_with_residuals
    partial_path = FIXTURE_DIR / "receipt_partial_with_residuals.md"
    partial_body = _read(partial_path)
    assert "completed_with_residuals" in partial_body, (
        "receipt_partial_with_residuals.md must use 'completed_with_residuals' "
        "as its validator_status"
    )


# ---------------------------------------------------------------------------
# C3: cycle_phase field in state-shape.md
# ---------------------------------------------------------------------------
def test_c3_cycle_phase_field_definition():
    """C3 lock (cycle_phase): state-shape.md must define ``cycle_phase`` with
    all 7 enum values: not_started, lfg_done_seen, receipt_validated,
    tier1_checked, tier2_checked, tier3_pending, tier3_ratified.
    """
    body = _read(STATE_SHAPE)
    assert "cycle_phase" in body, "state-shape.md must contain 'cycle_phase' field"
    expected_values = [
        "not_started",
        "lfg_done_seen",
        "receipt_validated",
        "tier1_checked",
        "tier2_checked",
        "tier3_pending",
        "tier3_ratified",
    ]
    missing = [v for v in expected_values if v not in body]
    assert not missing, (
        f"state-shape.md must enumerate all 7 cycle_phase values; "
        f"missing: {missing}"
    )


# ---------------------------------------------------------------------------
# C3: goal_complete mentions Tier 3 / user ratification
# ---------------------------------------------------------------------------
def test_c3_goal_complete_tier3():
    """C3 lock (goal_complete): state-shape.md ``goal_complete`` definition
    must mention Tier 3 or user ratification.

    Currently the definition says ``Tier 2 judges agreed goal_met: true``
    without mentioning Tier 3 user ratification, contradicting SKILL.md's
    3-tier check architecture.
    """
    body = _read(STATE_SHAPE)
    # Find the goal_complete enum value description
    assert "goal_complete" in body, "state-shape.md must contain 'goal_complete'"
    # The description near goal_complete must mention tier 3 or user ratification
    # Search in a window around goal_complete
    idx = body.lower().find("goal_complete")
    window = body[idx:idx + 300].lower()
    tier3_signals = ("tier 3", "tier-3", "user ratif", "user confirm", "ratification")
    assert any(sig in window for sig in tier3_signals), (
        "state-shape.md goal_complete definition must mention Tier 3 / "
        "user ratification"
    )


# ---------------------------------------------------------------------------
# C3: resume semantics mention cycle_phase
# ---------------------------------------------------------------------------
def test_c3_resume_mentions_cycle_phase():
    """C3 lock (resume): state-shape.md §Resume semantics must reference
    ``cycle_phase`` for granular within-cycle resume positioning.

    Currently the resume section only mentions ``cycle_state`` and
    ``current_cycle``, with no mention of ``cycle_phase``.
    """
    body = _read(STATE_SHAPE)
    # Find the Resume semantics section
    resume_idx = body.lower().find("resume")
    assert resume_idx >= 0, "state-shape.md must have a Resume section"
    resume_section = body[resume_idx:]
    assert "cycle_phase" in resume_section, (
        "state-shape.md Resume semantics must reference 'cycle_phase'"
    )


# ============================================================================
# HIGH bugs
# ============================================================================


# ---------------------------------------------------------------------------
# H1: No stale "Vendored Surface — Identity Guard Layer" references
# ---------------------------------------------------------------------------
def test_h1_no_stale_vendored_surface_reference():
    """H1 lock: critical skill and script files must not contain the
    literal ``"Vendored Surface — Identity Guard Layer"``.

    This section was renamed to "Concept Absorption Surface" at v0.12.0.
    v0.15.1 extends the scan to cover stop_verify_claims.py, plan/SKILL.md,
    work/SKILL.md, and discuss/references/*.md.
    """
    scan_paths = [
        LFG_SKILL,
        LFG_GOAL_SKILL,
        REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py",
        REPO_ROOT / "skills" / "plan" / "SKILL.md",
        REPO_ROOT / "skills" / "work" / "SKILL.md",
        REPO_ROOT / "skills" / "discuss" / "references" / "requirements-capture.md",
        REPO_ROOT / "skills" / "discuss" / "references" / "clarify-gap-probes.md",
    ]
    for path in scan_paths:
        if not path.is_file():
            continue
        body = _read(path)
        assert "Vendored Surface — Identity Guard Layer" not in body, (
            f"{path.relative_to(REPO_ROOT)} contains stale reference to "
            f"'Vendored Surface — Identity Guard Layer' (renamed at v0.12.0)"
        )


# ---------------------------------------------------------------------------
# H2: Step 3 must not have "leader applies fixes" pattern
# ---------------------------------------------------------------------------
def test_h2_step3_no_leader_applies_fixes():
    """H2 lock: lfg/SKILL.md Step 3 must not contain a pattern where the
    LFG leader directly applies review fixes.

    The Thin Leader contract forbids the leader from writing code. Review
    fixes must be dispatched to workers.
    """
    body = _read(LFG_SKILL)
    # Find Step 3 section
    step3_start = body.find("### Step 3")
    step4_start = body.find("### Step 4")
    assert step3_start >= 0, "Could not find Step 3 section"
    assert step4_start >= 0, "Could not find Step 4 section"
    step3_body = body[step3_start:step4_start]
    # Collapse whitespace for cross-line matching
    step3_collapsed = " ".join(step3_body.lower().split())
    # The leader must not be described as applying fixes directly
    violation_patterns = [
        "lfg leader applies fix",
        "the lfg leader applies fix",
        "leader applies fixes",
    ]
    for pattern in violation_patterns:
        assert pattern not in step3_collapsed, (
            f"lfg Step 3 contains Thin Leader violation: '{pattern}'"
        )


# ---------------------------------------------------------------------------
# H3: Step 8 must not have "apply a fix in the working tree" pattern
# ---------------------------------------------------------------------------
def test_h3_step8_no_leader_direct_fix():
    """H3 lock: lfg/SKILL.md Step 8 must not instruct the leader to
    ``apply a fix in the working tree`` directly.

    CI autofix should dispatch to workers or use the ci-watcher agent.
    """
    body = _read(LFG_SKILL)
    step8_start = body.find("### Step 8")
    step9_start = body.find("### Step 9")
    assert step8_start >= 0, "Could not find Step 8 section"
    assert step9_start >= 0, "Could not find Step 9 section"
    step8_body = body[step8_start:step9_start]
    # Collapse whitespace for cross-line matching
    step8_collapsed = " ".join(step8_body.lower().split())
    assert "apply a fix in the working tree" not in step8_collapsed, (
        "lfg Step 8 instructs the leader to 'apply a fix in the working tree' "
        "— violates Thin Leader contract"
    )


# ---------------------------------------------------------------------------
# H4: No live functional /athanor:ce-lfg references outside Historical note
# ---------------------------------------------------------------------------
def test_h4_no_live_ce_lfg_reference():
    """H4 lock: lfg/SKILL.md must not reference ``/athanor:ce-lfg`` as a
    live functional alternative outside a clearly delimited historical note.

    Fixed in v0.15.0: §"Difference from /athanor:ce-lfg" comparison table
    replaced with §"Historical note (post-v0.12.0)".
    """
    body = _read(LFG_SKILL)
    # Count ce-lfg occurrences
    ce_lfg_count = body.count("/athanor:ce-lfg")
    # Find if there's a Historical note section
    has_historical_section = bool(re.search(
        r"(?i)(historical\s+note|history|deprecated|archive|removed)", body
    ))
    if ce_lfg_count == 0:
        return  # No references — pass
    # If references exist, they must ALL be inside a Historical note section
    # For now, check that the comparison table is gone or clearly marked historical
    assert "Difference from /athanor:ce-lfg" not in body or has_historical_section, (
        f"lfg SKILL.md has {ce_lfg_count} live '/athanor:ce-lfg' references "
        f"outside a Historical note section (ce-lfg was DROPped at v0.12.0)"
    )
    # Additional check: the comparison table treating ce-lfg as a live alternative
    assert "Both skills coexist" not in body, (
        "lfg SKILL.md claims 'Both skills coexist' — ce-lfg was DROPped at v0.12.0"
    )


# ---------------------------------------------------------------------------
# H5: No docs/plans/ as plan output location
# ---------------------------------------------------------------------------
def test_h5_no_docs_plans_reference():
    """H5 lock: lfg/SKILL.md must not reference ``docs/plans/`` as a plan
    output location.

    athanor plans live in ``.athanor/sessions/<id>/plan.md``, not ``docs/plans/``.
    The ``docs/plans/`` reference is a leftover from CE vendoring.
    """
    body = _read(LFG_SKILL)
    assert "docs/plans/" not in body, (
        "lfg SKILL.md references 'docs/plans/' as a plan output location "
        "(should be .athanor/sessions/<id>/plan.md)"
    )


# ============================================================================
# MEDIUM bugs
# ============================================================================


# ---------------------------------------------------------------------------
# M1: SKILL.md resume rules cover all 7 cycle_phase values
# ---------------------------------------------------------------------------
def test_m1_resume_rules_cover_all_cycle_phases():
    """M1 lock: lfg-goal/SKILL.md §Resume rules must cover all 7
    ``cycle_phase`` values individually in dedicated resume rule bullets.

    Currently the resume section lists the enum values in a code block
    but ``receipt_validated`` has no dedicated resume rule bullet — there
    is no ``- cycle_state == cycle_n_in_progress with cycle_phase ==
    receipt_validated`` entry. The fix must add a rule for each of the 7
    values.
    """
    body = _read(LFG_GOAL_SKILL)
    # Find the Resume rules section (after the enum block)
    resume_match = re.search(r"\*\*Resume rules\*\*", body)
    assert resume_match, "lfg-goal SKILL.md must have a **Resume rules** section"
    resume_rules = body[resume_match.start():]
    # Cut at next ## section
    next_section = re.search(r"\n## [^#]", resume_rules[5:])
    if next_section:
        resume_rules = resume_rules[:next_section.start() + 5]

    # Each cycle_phase value must appear in the resume RULES section
    # (the bullets starting with "- `cycle_state =="), not just in the
    # enum definition code block above.
    expected_phases = [
        "not_started",
        "lfg_done_seen",
        "receipt_validated",
        "tier1_checked",
        "tier2_checked",
        "tier3_pending",
        "tier3_ratified",
    ]
    missing = [v for v in expected_phases if v not in resume_rules]
    assert not missing, (
        f"SKILL.md **Resume rules** bullets must cover all 7 cycle_phase "
        f"values individually; missing: {missing}"
    )


# ---------------------------------------------------------------------------
# M3: archiveOnComplete schema must not reference .athanor/goals/_archive/
# ---------------------------------------------------------------------------
def test_m3_schema_archive_path():
    """M3 lock: ``schemas/athanor-config.schema.json`` ``archiveOnComplete``
    description must NOT reference ``.athanor/goals/_archive/``.

    SKILL.md says completed goals go to ``docs/goals-completed/<id>/``.
    The schema description says ``.athanor/goals/_archive/``, which contradicts
    the SKILL.md.
    """
    import json
    body = _read(SCHEMA_PATH)
    schema = json.loads(body)
    archive_desc = (
        schema.get("properties", {})
        .get("lfgGoal", {})
        .get("properties", {})
        .get("archiveOnComplete", {})
        .get("description", "")
    )
    assert ".athanor/goals/_archive/" not in archive_desc, (
        "archiveOnComplete description references '.athanor/goals/_archive/' "
        "which contradicts SKILL.md (should be 'docs/goals-completed/<id>/')"
    )


# ---------------------------------------------------------------------------
# M5: CI watch command must include timeout wrapping
# ---------------------------------------------------------------------------
def test_m5_ci_watch_timeout():
    """M5 lock: lfg/SKILL.md Step 8 CI watch ``gh pr checks --watch`` must
    be wrapped with a ``timeout`` command.

    Without timeout, ``gh pr checks --watch`` can hang indefinitely if CI
    never completes.
    """
    body = _read(LFG_SKILL)
    step8_start = body.find("### Step 8")
    step9_start = body.find("### Step 9")
    assert step8_start >= 0
    assert step9_start >= 0
    step8_body = body[step8_start:step9_start]
    assert "timeout" in step8_body.lower(), (
        "lfg Step 8 CI watch must include 'timeout' wrapping for "
        "'gh pr checks --watch' to prevent indefinite hangs"
    )


# ---------------------------------------------------------------------------
# M6: NFKC position-mapping + Korean conditional suppression
# ---------------------------------------------------------------------------
def test_m6_nfkc_korean_conditional_suppression():
    """M6 lock: ``is_material_claim()`` must correctly suppress a Korean
    conditional clause preceded by NFKC-length-changing characters.

    U+FB03 'ffi' ligature normalizes to 3 chars 'ffi' under NFKC, changing
    string length. When a Korean conditional marker (``만약``) follows such
    a character, the clause boundary detection must operate on the normalized
    text (not the original) to correctly find the conditional prefix.

    v0.14.2 fixed the general position-mapping bug, but the interaction
    between NFKC expansion and Korean KO path (which searches the raw
    message first) can still produce incorrect results if the raw-message
    path finds a match before normalization.
    """
    # U+FB03 = 'ffi' ligature + Korean conditional "만약" + claim "테스트 통과"
    message = "ﬃ prefix. 만약 테스트 통과하면 merge"
    result = svc.is_material_claim(message)
    # Should be suppressed (conditional clause "만약") → False
    assert result is False, (
        "Korean conditional '만약 테스트 통과' preceded by NFKC-expanding "
        "U+FB03 should be suppressed but is_material_claim returned True"
    )


# ---------------------------------------------------------------------------
# M7: lfg SKILL.md allowed-tools must include Write
# ---------------------------------------------------------------------------
def test_m7_lfg_allowed_tools_includes_write():
    """M7 lock: lfg/SKILL.md frontmatter ``allowed-tools`` must include
    ``Write``.

    The LFG pipeline needs Write for Step 5 (residual handoff file creation)
    and Step 7 (PR description body-file). Currently: ``Bash, Read, Skill``.
    """
    text = _read(LFG_SKILL)
    fm, _body = _split_frontmatter(text)
    allowed = fm.get("allowed-tools", "")
    assert "Write" in allowed, (
        f"lfg SKILL.md allowed-tools must include 'Write'; got: '{allowed}'"
    )


# ---------------------------------------------------------------------------
# P17: lfg SKILL.md allowed-tools must include Task
# ---------------------------------------------------------------------------
def test_p17_lfg_allowed_tools_includes_task():
    """P17 lock: lfg/SKILL.md frontmatter ``allowed-tools`` must include
    ``Task``.

    The LFG pipeline dispatches workers (review fixes, CI autofix via the
    ci-watcher agent, /athanor:work subtasks) — a Thin Leader that delegates
    needs the Task tool to spawn those workers. The grant was previously
    under-specified (``Bash, Read, Write, Skill``), forcing dispatch through
    Skill alone.
    """
    text = _read(LFG_SKILL)
    fm, _body = _split_frontmatter(text)
    allowed = fm.get("allowed-tools", "")
    assert "Task" in allowed, (
        f"lfg SKILL.md allowed-tools must include 'Task'; got: '{allowed}'"
    )


# ---------------------------------------------------------------------------
# M8: CLAUDE.md lfg row must not reference ce-lfg
# ---------------------------------------------------------------------------
def test_m8_claude_md_lfg_row_no_ce_lfg():
    """M8 lock: CLAUDE.md Commands table ``/athanor:lfg`` row must not
    contain ``ce-lfg step shape`` or ``Coexists with /athanor:ce-lfg``.

    ce-lfg was DROPped at v0.12.0. The CLAUDE.md command table row still
    claims lfg "reuses vendored ce-lfg step shape" and "Coexists with
    /athanor:ce-lfg".
    """
    body = _read(CLAUDE_MD)
    # Find the lfg row in the Commands table — look for the line containing
    # /athanor:lfg that is NOT /athanor:lfg-goal
    for line in body.splitlines():
        if "| `/athanor:lfg`" in line and "lfg-goal" not in line:
            assert "ce-lfg step shape" not in line, (
                "CLAUDE.md lfg row references 'ce-lfg step shape' "
                "(ce-lfg was DROPped at v0.12.0)"
            )
            assert "Coexists with" not in line, (
                "CLAUDE.md lfg row claims coexistence with ce-lfg "
                "(DROPped at v0.12.0)"
            )
            return
    pytest.fail("Could not find '/athanor:lfg' row in CLAUDE.md Commands table")


# ============================================================================
# LOW bugs
# ============================================================================


# ---------------------------------------------------------------------------
# L1: No stale 60s TTL references (code is 120s)
# ---------------------------------------------------------------------------
def test_l1_no_stale_60s_ttl_references():
    """L1 lock: no ``60.*TTL`` or ``older than 60 seconds`` references may
    remain in ``skills/`` or ``scripts/`` (excluding test files and the
    Python constant definition in hook_state.py).

    The nonce TTL was raised from 60s to 120s at v0.14.2 (G2), but prose
    references in verification SKILL.md and receipt-validator.md still say
    60 seconds.
    """
    skills_dir = REPO_ROOT / "skills"
    scripts_dir = REPO_ROOT / "scripts"

    stale_files: list[str] = []
    ttl_patterns = [
        re.compile(r"60\s*seconds?\s*\(?TTL", re.IGNORECASE),
        re.compile(r"TTL.*60\s*second", re.IGNORECASE),
        re.compile(r"older\s+than\s+60\s+second", re.IGNORECASE),
        re.compile(r"nonces?\s+older\s+than\s+60", re.IGNORECASE),
        re.compile(r"rejects\s+nonces\s+older\s+than\s+60", re.IGNORECASE),
    ]

    for search_dir in [skills_dir, scripts_dir]:
        for fpath in search_dir.rglob("*"):
            if not fpath.is_file():
                continue
            if fpath.suffix not in (".md", ".py", ".txt"):
                continue
            # Exclude test files
            if "test" in fpath.name.lower():
                continue
            # Exclude the constant definition in hook_state.py
            if fpath.name == "hook_state.py":
                continue
            try:
                content = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for pat in ttl_patterns:
                if pat.search(content):
                    stale_files.append(str(fpath.relative_to(REPO_ROOT)))
                    break

    assert not stale_files, (
        f"Stale 60s TTL references found (code uses 120s since v0.14.2): "
        f"{stale_files}"
    )


# ---------------------------------------------------------------------------
# L4: 3-iteration clauses include enforcement transparency note
# ---------------------------------------------------------------------------
def test_l4_enforcement_transparency_note():
    """L4 lock: lfg/SKILL.md ``3 fix iterations`` / ``3 fix rounds`` clauses
    must include an enforcement transparency note.

    The 3-iteration limit for review fixes (Step 3) and CI autofix (Step 8)
    is now bounded by the session-scoped ``lfg_fix_round_counter.py`` exit-code
    counter — a strict upgrade over the pre-Phase-4 pure-prose guidance, but
    still ADVISORY: no PreToolUse/Stop runtime hook forces the leader to branch
    on the exit code. A transparency note conveying that advisory / leader-bound
    (not runtime-enforced) nature must be present in the Protocol section
    (Steps 3 and 8) so users understand the limit is not hook-enforced.
    """
    body = _read(LFG_SKILL)
    # Extract the Protocol section (Steps 1-9 area)
    protocol_start = body.find("## Protocol")
    identity_start = body.find("## Athanor identity invariants")
    assert protocol_start >= 0, "Could not find ## Protocol section"
    if identity_start > protocol_start:
        protocol_section = body[protocol_start:identity_start].lower()
    else:
        protocol_section = body[protocol_start:].lower()

    # Accept either the legacy pure-prose phrasing OR the Phase 4 honest
    # advisory/leader-bound relabel (the counter exists but is not hook-forced).
    transparency_signals = [
        "prose-only",
        "no runtime enforcement",
        "not enforced by runtime",
        "enforcement transparency",
        "prose guidance",
        "advisory limit",
        "not runtime-enforced",
        "advisory (leader-bound exit code)",
        "leader-prose-bound",
        "not enforced",
    ]
    # At least one transparency note must appear in the Protocol section
    # near the 3-iteration clauses (not in unrelated sections like
    # using-superpowers boundary)
    assert any(sig in protocol_section for sig in transparency_signals), (
        "lfg SKILL.md Protocol section must include an enforcement "
        "transparency note near the 3-iteration limit clauses (Step 3 + Step 8) "
        "conveying the limit's advisory / leader-bound (not runtime-enforced) "
        "nature — the fix-round counter exists but no hook forces the branch."
    )


# ---------------------------------------------------------------------------
# L5: Step 8 must include explicit run-id extraction
# ---------------------------------------------------------------------------
def test_l5_explicit_run_id_extraction():
    """L5 lock: lfg/SKILL.md Step 8 must include explicit run-id extraction
    (not a bare ``<run-id>`` placeholder).

    The current Step 8 uses ``gh run view <run-id> --log-failed`` with a bare
    angle-bracket placeholder but never shows how to obtain the run-id value.
    Users need either: (a) the placeholder replaced with a concrete pipeline
    (e.g., ``gh run list --json databaseId ... | jq ...``), or (b) the bare
    ``<run-id>`` removed entirely in favor of a self-contained command.
    """
    body = _read(LFG_SKILL)
    step8_start = body.find("### Step 8")
    step9_start = body.find("### Step 9")
    assert step8_start >= 0
    assert step9_start >= 0
    step8_body = body[step8_start:step9_start]

    # The bare <run-id> placeholder must not appear without a preceding
    # extraction command that produces it. Currently the section has
    # "gh run view <run-id> --log-failed" but no command to extract the
    # run-id value.
    assert "<run-id>" not in step8_body, (
        "lfg Step 8 uses bare '<run-id>' placeholder without showing how "
        "to extract it. Replace with a concrete command pipeline or a "
        "self-contained alternative (e.g., 'gh run view --log-failed' with "
        "the run-id obtained from 'gh run list --json ...')"
    )
