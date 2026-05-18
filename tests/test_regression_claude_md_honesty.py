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


def _load_claude_md() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


def _extract_stop_hook_subsection(content: str) -> str:
    """Return the body between the Stop hook `###` heading and the next H2/H3 heading."""
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
    """Subsection must cite the actual gate script."""
    subsection = _extract_stop_hook_subsection(_load_claude_md())
    assert subsection, "Stop hook subsection not found"
    assert "scripts/hooks/stop_verify_claims.py" in subsection, (
        "Subsection must name the gate script `scripts/hooks/stop_verify_claims.py` "
        "so users can find it."
    )


def test_subsection_describes_sentinel_mechanism():
    """Subsection must describe the re-entry-prevention sentinel."""
    subsection = _extract_stop_hook_subsection(_load_claude_md())
    assert "athanor:verification-emission" in subsection, (
        "Subsection must describe the verification-emission sentinel that "
        "prevents re-entry loops on the verification skill's own output."
    )


def test_subsection_describes_profile_off_opt_out():
    """Subsection must document the per-project opt-out."""
    subsection = _extract_stop_hook_subsection(_load_claude_md())
    assert 'profile: "off"' in subsection or '"profile": "off"' in subsection or "profile: 'off'" in subsection, (
        "Subsection must document the `hooks.profile: \"off\"` per-project opt-out "
        "so users have a documented escape hatch."
    )


def test_subsection_cites_spike_evidence():
    """Subsection must reference the empirical spike evidence in docs/STATE.md."""
    subsection = _extract_stop_hook_subsection(_load_claude_md())
    assert "STATE.md" in subsection, (
        "Subsection must cite docs/STATE.md (where the 2026-05-18 spike evidence lives)."
    )
    assert "spike" in subsection.lower() or "2026-05-18" in subsection, (
        "Subsection must reference the spike (by name or date)."
    )


# ---- v0.8.0 Spec-then-TDD discipline row + subsection ----


def _extract_spec_then_tdd_row(content: str) -> str:
    """Return the v0.8.0 Defense Mechanisms row mentioning Spec-then-TDD."""
    for line in content.splitlines():
        if "Spec-then-TDD" in line and line.lstrip().startswith("|"):
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
    """v0.8.0: a new ### subsection describes the Spec-then-TDD discipline."""
    subsection = _extract_spec_then_tdd_subsection(_load_claude_md())
    assert subsection, (
        "CLAUDE.md must contain a '### Spec-then-TDD Discipline' subsection "
        "describing the v0.8.0 mechanism"
    )
    # The heading itself should include 'advisory'
    first_line = subsection.splitlines()[0]
    assert "advisory" in first_line.lower(), (
        f"Spec-then-TDD subsection heading must include 'advisory'; got: {first_line!r}"
    )


def test_spec_then_tdd_subsection_describes_three_branches():
    """The subsection must describe all three execution_note branches."""
    subsection = _extract_spec_then_tdd_subsection(_load_claude_md())
    assert subsection
    lower = subsection.lower()
    assert "spec-then-tdd" in lower
    assert "test-aware" in lower
    assert "direct" in lower


def test_spec_then_tdd_subsection_what_it_does_not_catch():
    """Honesty arc: the subsection must include a 'What it does NOT catch'
    paragraph (matching the v0.7.8 honesty pattern)."""
    subsection = _extract_spec_then_tdd_subsection(_load_claude_md())
    assert subsection
    lower = subsection.lower()
    not_catch_signals = [
        "what it does not catch",
        "does not catch",
        "limitation",
        "advisory limitation",
    ]
    assert any(s in lower for s in not_catch_signals), (
        f"Spec-then-TDD subsection must include a 'What it does NOT catch' or "
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
