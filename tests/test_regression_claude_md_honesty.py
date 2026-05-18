"""Regression test for the v0.7.7 M1 finding — CLAUDE.md Stop-hook honesty.

Pins the v0.7.7 relabel of the Stop hook from a false "enforced" claim to
"advisory (prompt-based)". Guards against silent reintroduction of the
v0.7.6 lie that the Stop hook is "Enforced at plugin layer".

Covers:
  - status table row uses `advisory` + `prompt-based` wording
  - "Enforced at plugin layer" phrase removed entirely
  - subsection heading renamed to advisory
  - Limitation paragraph present and names model self-classification
  - v0.7.8 command-hook upgrade forward-referenced in subsection

Plan reference: `.athanor/sessions/2026-05-18-001/plan.md` §4 M1.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


def _load_claude_md() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


def _extract_stop_hook_subsection(content: str) -> str:
    """Return the body between the Stop hook `###` heading and the next `##` or `###` heading.

    The subsection of interest starts at `### Completion-Claim Verification (Stop hook`
    and ends at the next markdown heading at H2 (`## `) or H3 (`### `) level.
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
    """Return the status-table row that mentions the Stop hook completion-claim entry."""
    for line in content.splitlines():
        if "Completion-Claim Verification (Stop hook)" in line and line.lstrip().startswith("|"):
            return line
    return ""


# ---- tests ----

def test_stop_hook_row_uses_advisory_label():
    """Status table row must mark Stop hook as `advisory` AND `prompt-based`."""
    row = _extract_stop_hook_table_row(_load_claude_md())
    assert row, "Status-table row for Stop hook not found in CLAUDE.md"
    lower = row.lower()
    assert "advisory" in lower, (
        f"Stop hook status row must contain 'advisory' (case-insensitive); got: {row!r}"
    )
    assert "prompt-based" in lower, (
        f"Stop hook status row must contain 'prompt-based' (case-insensitive); got: {row!r}"
    )


def test_enforced_at_plugin_layer_phrase_absent():
    """The v0.7.6 lie 'Enforced at plugin layer' must NOT appear anywhere in CLAUDE.md."""
    content = _load_claude_md()
    assert "Enforced at plugin layer" not in content, (
        "CLAUDE.md still contains the phrase 'Enforced at plugin layer' — "
        "this is the v0.7.6 false claim that v0.7.7 M1 explicitly removed."
    )


def test_subsection_renamed():
    """The Stop hook subsection heading must contain `advisory` (not `enforced`)."""
    content = _load_claude_md()
    heading = None
    for line in content.splitlines():
        if line.startswith("## Completion-Claim Verification (Stop hook") or \
           line.startswith("### Completion-Claim Verification (Stop hook"):
            heading = line
            break
    assert heading is not None, (
        "Subsection heading 'Completion-Claim Verification (Stop hook ...' not found"
    )
    lower = heading.lower()
    assert "advisory" in lower, (
        f"Subsection heading must contain 'advisory'; got: {heading!r}"
    )


def test_stop_hook_limitation_paragraph_present():
    """The Stop-hook subsection must include a Limitation paragraph naming self-classification."""
    content = _load_claude_md()
    subsection = _extract_stop_hook_subsection(content)
    assert subsection, "Stop hook subsection not found"
    assert "Limitation" in subsection, (
        "Stop hook subsection must include a 'Limitation' paragraph that "
        "describes what the prompt nudge cannot guarantee."
    )
    assert "self-classif" in subsection, (
        "Limitation paragraph must reference 'self-classif' (e.g., "
        "'model self-classifies') to make the failure mode explicit."
    )


def test_v078_forward_reference_present():
    """The Stop hook subsection must forward-reference the v0.7.8 command-hook upgrade."""
    subsection = _extract_stop_hook_subsection(_load_claude_md())
    assert subsection, "Stop hook subsection not found"
    assert ("command-based" in subsection) or ("command hook" in subsection) or (
        "command-hook" in subsection
    ), (
        "Stop hook subsection must forward-reference the v0.7.8 command-hook "
        "upgrade (mention 'command-based' or 'command hook')."
    )
