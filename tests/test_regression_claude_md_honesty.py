"""Regression test for CLAUDE.md Stop-hook contract honesty.

History:
  - v0.7.6 falsely claimed the Stop hook was "Enforced at plugin layer".
  - v0.7.7 demoted to "advisory (prompt-based)" — the spike was not yet
    in place; the prompt-mode hook genuinely could not force invocation.
  - v0.7.8 RE-PROMOTES to "enforced (command-based)" — the spike (PASS,
    docs/STATE.md §"Command-hook Stop blocking spike (2026-05-18)") and
    the new `type: command` registration deliver real runtime gating.

This test pins the v0.7.8 contract. Three invariants:
  1. Status-table row uses the `enforced (command-based)` label.
  2. The v0.7.6 lie "Enforced at plugin layer" MUST remain absent
     (different from v0.7.8's honest "enforced (command-based)" —
     the v0.7.6 string was wrong; the v0.7.8 string is true).
  3. Subsection describes the runtime gate concretely: mentions the
     script path, the sentinel mechanism, and the `profile: "off"`
     opt-out.

Plan reference: docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-command-mode-plan.md §U7.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

# v0.16.0 CLAUDE.md diet (ST15 retarget): verbose Stop-hook subsection +
# Spec-then-TDD discipline subsection moved to archive. The status-table
# row and one-paragraph enforcement summaries stay inline in CLAUDE.md;
# the verbose internals (script path narrative, sentinel mechanics,
# profile opt-out detail, spike evidence, branch semantics, honesty
# arc) now canonically live in these two files. Tests scanning for
# those verbose signals read from the archive.
STOP_HOOK_ARCHIVE = REPO_ROOT / "docs" / "archive" / "stop-hook-postmortem.md"
DEFENSE_DETAIL_ARCHIVE = REPO_ROOT / "docs" / "archive" / "defense-mechanisms-detail.md"


def _load_claude_md() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


def _load_stop_hook_archive() -> str:
    """Concatenated post-mortem + defense-mechanisms-detail archive content.

    The Stop-hook verbose subsection narrative is split between the two
    archive files (v0.11.3/v0.11.4 post-mortem material in
    `stop-hook-postmortem.md`; runtime contract + sentinel mechanics +
    opt-out + spike-evidence narrative in `defense-mechanisms-detail.md`).
    Returning the union lets scans hit either origin.
    """
    return (
        STOP_HOOK_ARCHIVE.read_text(encoding="utf-8")
        + "\n"
        + DEFENSE_DETAIL_ARCHIVE.read_text(encoding="utf-8")
    )


def _load_defense_detail_archive() -> str:
    return DEFENSE_DETAIL_ARCHIVE.read_text(encoding="utf-8")


def _extract_stop_hook_subsection(content: str) -> str:
    """Return the body between the Stop hook `###` heading and the next H2/H3 heading.

    Pre-v0.16.0 this extracted the verbose subsection from CLAUDE.md. Post-
    diet (ST15 retarget) the verbose narrative lives in archive files; this
    helper now operates on whichever content string is passed in (the
    CLAUDE.md lite summary still carries the heading, and the archive
    files carry the verbose headings).
    """
    lines = content.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.startswith("### Completion-Claim Verification (Stop hook"):
            start_idx = i
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if lines[j].startswith("## ") or lines[j].startswith("### "):
            end_idx = j
            break
    return "\n".join(lines[start_idx:end_idx])


def _extract_stop_hook_table_row(content: str) -> str:
    """Return the status-table row mentioning the Stop hook entry."""
    for line in content.splitlines():
        if "Completion-Claim Verification (Stop hook)" in line and line.lstrip().startswith("|"):
            return line
    return ""


# ---- tests ----


def test_stop_hook_row_uses_enforced_command_based_label():
    """v0.7.8 contract: status table row uses `enforced (command-based)` label."""
    row = _extract_stop_hook_table_row(_load_claude_md())
    assert row, "Status-table row for Stop hook not found in CLAUDE.md"
    lower = row.lower()
    assert "enforced" in lower, (
        f"v0.7.8: Stop hook row must contain 'enforced'; got: {row!r}"
    )
    assert "command-based" in lower or "command-hook" in lower or "command hook" in lower, (
        f"v0.7.8: Stop hook row must say 'command-based' (or equivalent); got: {row!r}"
    )


def test_enforced_at_plugin_layer_phrase_absent():
    """The v0.7.6 false phrase 'Enforced at plugin layer via `hooks/hooks.json`'
    must NOT reappear. Note: 'enforced (command-based)' is honest v0.7.8
    wording — this test only forbids the specific v0.7.6 false phrasing."""
    content = _load_claude_md()
    assert "Enforced at plugin layer" not in content, (
        "CLAUDE.md contains 'Enforced at plugin layer' — that exact v0.7.6 "
        "phrasing was a lie. v0.7.8 honest wording is 'enforced (command-based)'."
    )


def test_subsection_heading_says_enforced_command_based():
    """Subsection heading reflects v0.7.8 contract."""
    content = _load_claude_md()
    heading = None
    for line in content.splitlines():
        if line.startswith("### Completion-Claim Verification (Stop hook"):
            heading = line
            break
    assert heading is not None, (
        "Subsection heading 'Completion-Claim Verification (Stop hook ...' not found"
    )
    lower = heading.lower()
    assert "enforced" in lower, (
        f"v0.7.8: subsection heading must say 'enforced'; got: {heading!r}"
    )
    assert "command" in lower, (
        f"v0.7.8: subsection heading must mention 'command'; got: {heading!r}"
    )


def test_subsection_describes_script_path():
    """Verbose Stop-hook narrative must cite the actual gate script.

    v0.16.0 retarget (ST15): verbose detail moved from CLAUDE.md to
    `docs/archive/stop-hook-postmortem.md` + `docs/archive/defense-
    mechanisms-detail.md`. The script-path mention is canonical in the
    archive; the CLAUDE.md lite summary may also retain it.
    """
    archive = _load_stop_hook_archive()
    assert "scripts/hooks/stop_verify_claims.py" in archive, (
        "Stop-hook archive must name the gate script "
        "`scripts/hooks/stop_verify_claims.py` so users can find it."
    )


def test_subsection_describes_sentinel_mechanism():
    """Verbose Stop-hook narrative must describe the re-entry-prevention sentinel.

    v0.16.0 retarget (ST15): verbose detail moved to archive.
    """
    archive = _load_stop_hook_archive()
    assert "athanor:verification-emission" in archive, (
        "Stop-hook archive must describe the verification-emission sentinel "
        "that prevents re-entry loops on the verification skill's own output."
    )


def test_subsection_describes_profile_off_opt_out():
    """Verbose Stop-hook narrative must document the per-project opt-out.

    v0.16.0 retarget (ST15): the `hooks.profile: "off"` opt-out detail
    lives canonically in `docs/archive/defense-mechanisms-detail.md`
    §"Per-project opt-out".
    """
    archive = _load_stop_hook_archive()
    assert (
        'profile: "off"' in archive
        or '"profile": "off"' in archive
        or "profile: 'off'" in archive
    ), (
        "Stop-hook archive must document the `hooks.profile: \"off\"` "
        "per-project opt-out so users have a documented escape hatch."
    )


def test_subsection_cites_spike_evidence():
    """Verbose Stop-hook narrative must reference the empirical spike evidence
    in docs/STATE.md.

    v0.16.0 retarget (ST15): spike-evidence citation lives canonically in
    `docs/archive/stop-hook-postmortem.md` + `docs/archive/defense-
    mechanisms-detail.md` (companion-fix arc destination).
    """
    archive = _load_stop_hook_archive()
    assert "STATE.md" in archive, (
        "Stop-hook archive must cite docs/STATE.md (where the 2026-05-18 "
        "spike evidence lives)."
    )
    assert "spike" in archive.lower() or "2026-05-18" in archive, (
        "Stop-hook archive must reference the spike (by name or date)."
    )


# ---- v0.8.0 Spec-then-TDD discipline row + subsection ----


def _extract_spec_then_tdd_row(content: str) -> str:
    """Return the v0.8.0 Defense Mechanisms row mentioning Spec-then-TDD.

    v0.10.0: scope search to the Defense Mechanisms section so the
    Commands-table `/athanor:work` row (which also mentions Spec-then-TDD
    discipline as an identity callout starting at v0.10.0) is not picked
    up by mistake.
    """
    lines = content.splitlines()
    in_defense = False
    for line in lines:
        if line.startswith("## Defense Mechanisms"):
            in_defense = True
            continue
        if in_defense and line.startswith("## ") and not line.startswith("## Defense"):
            break
        if in_defense and "Spec-then-TDD" in line and line.lstrip().startswith("|"):
            return line
    return ""


def _extract_spec_then_tdd_subsection(content: str) -> str:
    """Return the body between the Spec-then-TDD `###` heading and the next H2/H3."""
    lines = content.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.startswith("### Spec-then-TDD Discipline"):
            start_idx = i
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if lines[j].startswith("## ") or lines[j].startswith("### "):
            end_idx = j
            break
    return "\n".join(lines[start_idx:end_idx])


def test_spec_then_tdd_row_present_with_advisory_label():
    """v0.8.0: Defense Mechanisms table has a Spec-then-TDD row labeled
    'advisory (planner-classified)'."""
    row = _extract_spec_then_tdd_row(_load_claude_md())
    assert row, (
        "Defense Mechanisms status table must contain a row for "
        "'Spec-then-TDD' discipline (v0.8.0)"
    )
    lower = row.lower()
    assert "advisory" in lower, (
        f"Spec-then-TDD row must use 'advisory' label; got: {row!r}"
    )
    assert "planner-classified" in lower or "planner classified" in lower, (
        f"Spec-then-TDD row must mention 'planner-classified'; got: {row!r}"
    )


def test_spec_then_tdd_row_no_overclaim_language():
    """v0.8.0 honesty arc: the Spec-then-TDD row must NOT use 'enforced' or
    'required' overclaim language (this mechanism is advisory only)."""
    row = _extract_spec_then_tdd_row(_load_claude_md())
    assert row, "Spec-then-TDD row not found"
    lower = row.lower()
    overclaim_phrases = ["tdd enforced", "spec-driven required", "spec driven required"]
    for phrase in overclaim_phrases:
        assert phrase not in lower, (
            f"Spec-then-TDD row contains overclaim phrase '{phrase}'; "
            f"the mechanism is advisory only"
        )


def test_spec_then_tdd_subsection_present():
    """v0.8.0: a Spec-then-TDD discipline subsection describes the mechanism.

    v0.16.0 retarget (ST15): the verbose Spec-then-TDD subsection moved to
    `docs/archive/defense-mechanisms-detail.md` §"Spec-then-TDD Discipline
    (Splitter Internals)". The CLAUDE.md lite subsection (post-diet) still
    carries the heading + advisory label; either origin satisfies the
    "subsection present" invariant.
    """
    # Prefer the canonical archive subsection; fall back to the CLAUDE.md
    # lite summary if it still carries the heading (post-diet it does).
    archive_subsection = _extract_spec_then_tdd_subsection(_load_defense_detail_archive())
    inline_subsection = _extract_spec_then_tdd_subsection(_load_claude_md())
    subsection = archive_subsection or inline_subsection
    assert subsection, (
        "Spec-then-TDD discipline subsection must be present in either "
        "`docs/archive/defense-mechanisms-detail.md` (canonical, verbose) "
        "or CLAUDE.md (lite summary)."
    )
    # Heading semantics: archive uses "Spec-then-TDD Discipline (Splitter
    # Internals)"; CLAUDE.md uses "Spec-then-TDD Discipline (advisory —
    # planner-classified)". Accept either by requiring the section body
    # (combined inline + archive) to carry the 'advisory' label.
    combined_lower = (archive_subsection + "\n" + inline_subsection).lower()
    assert "advisory" in combined_lower, (
        "Spec-then-TDD subsection must carry the 'advisory' label (the "
        "mechanism is advisory only, not enforced)."
    )


def test_spec_then_tdd_claude_summary_points_to_canonical_reference():
    """CLAUDE.md should summarize the identity/status only and defer runtime
    branch/gate detail to the split handler reference."""
    subsection = _extract_spec_then_tdd_subsection(_load_claude_md())
    assert subsection, "CLAUDE.md must keep a lite Spec-then-TDD subsection"
    assert "skills/work/references/spec-then-tdd-handler.md" in subsection, (
        "CLAUDE.md Spec-then-TDD subsection must point to the canonical "
        "runtime behavior reference."
    )


def test_spec_then_tdd_claude_summary_does_not_repeat_runtime_detail():
    """CLAUDE.md must not duplicate schema/gate details that belong in
    spec-then-tdd-handler.md."""
    subsection = _extract_spec_then_tdd_subsection(_load_claude_md())
    forbidden = [
        "red_evidence",
        "full_suite_passed",
        "test_paths_touched",
        "scripts/work/evidence_gate.py",
        "test-evidence.jsonl",
        "freeze-change-evidence.jsonl",
    ]
    hits = [needle for needle in forbidden if needle in subsection]
    assert not hits, (
        "CLAUDE.md Spec-then-TDD subsection duplicates runtime details that "
        f"belong in spec-then-tdd-handler.md: {hits}"
    )


def test_spec_then_tdd_subsection_describes_three_branches():
    """The subsection must describe all three execution_note branches.

    v0.16.0 retarget (ST15): branch-detail prose lives canonically in
    `docs/archive/defense-mechanisms-detail.md` §"Branch semantics" /
    §"Splitter classification".
    """
    archive = _load_defense_detail_archive()
    lower = archive.lower()
    assert "spec-then-tdd" in lower
    assert "test-aware" in lower
    assert "direct" in lower


def test_spec_then_tdd_subsection_what_it_does_not_catch():
    """Honesty arc: archive subsection must include a 'What it does NOT catch'
    paragraph (matching the v0.7.8 honesty pattern).

    v0.16.0 retarget (ST15): honesty-arc detail lives canonically in
    `docs/archive/defense-mechanisms-detail.md` §"What it does NOT catch".
    The CLAUDE.md lite summary also carries a one-line "What it does NOT
    catch" sentence; the archive is the verbose canonical home.
    """
    archive = _load_defense_detail_archive()
    lower = archive.lower()
    not_catch_signals = [
        "what it does not catch",
        "does not catch",
        "limitation",
        "advisory limitation",
    ]
    assert any(s in lower for s in not_catch_signals), (
        f"Spec-then-TDD archive must include a 'What it does NOT catch' or "
        f"equivalent honesty paragraph. Expected one of: {not_catch_signals}"
    )


def test_no_tdd_enforced_overclaim_in_claude_md():
    """v0.8.0 honesty arc: 'TDD enforced' and 'Spec-driven required' must NOT
    appear anywhere in CLAUDE.md (negative assertion across the whole file)."""
    content = _load_claude_md()
    lower = content.lower()
    forbidden = ["tdd enforced", "spec-driven required", "spec driven required"]
    for phrase in forbidden:
        assert phrase not in lower, (
            f"CLAUDE.md contains overclaim phrase '{phrase}' — v0.8.0 honesty "
            f"arc requires advisory framing for the Spec-then-TDD discipline"
        )


# ---- v0.9.0 /athanor:discuss dual-mode honesty ----


def _extract_discuss_command_row(content: str) -> str:
    """Return the Commands-table row mentioning /athanor:discuss."""
    for line in content.splitlines():
        if "/athanor:discuss" in line and line.lstrip().startswith("|"):
            return line
    return ""


def test_discuss_purpose_mentions_dual_mode_or_clarification():
    """v0.9.0: Commands table row for /athanor:discuss should now indicate
    dual mode (clarify + synthesis) or intent clarification."""
    row = _extract_discuss_command_row(_load_claude_md())
    assert row, "Commands-table row for /athanor:discuss not found"
    lower = row.lower()
    dual_signals = [
        "dual mode",
        "dual-mode",
        "intent clarification",
        "clarify",
        "clarify mode",
    ]
    assert any(s in lower for s in dual_signals), (
        f"v0.9.0: /athanor:discuss row must indicate dual mode (clarify ↔ "
        f"synthesis) or intent clarification. Expected one of: {dual_signals}. "
        f"Got: {row!r}"
    )


def test_no_overclaim_for_discuss_clarify():
    """v0.9.0 honesty arc: discuss clarify mode must NOT use overclaim
    phrasing like 'intent-clarification enforced' or 'ce-brainstorm
    equivalent' which would mis-represent the actual mechanism (advisory
    dialog + planner-classified gap probes)."""
    content = _load_claude_md()
    lower = content.lower()
    forbidden = [
        "intent-clarification enforced",
        "intent clarification enforced",
        "ce-brainstorm equivalent",
        "ce brainstorm equivalent",
        "clarify enforced",
    ]
    for phrase in forbidden:
        assert phrase not in lower, (
            f"CLAUDE.md contains overclaim phrase '{phrase}' — v0.9.0 honesty "
            f"arc requires 'advisory dialog mode' framing for /athanor:discuss "
            f"clarify mode"
        )
