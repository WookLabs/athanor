"""Regression test for the v0.7.8 R10/U2 invariant — verification skill emits
the re-entry-prevention sentinel as the first instruction.

The v0.7.8 Stop hook (`scripts/hooks/stop_verify_claims.py`) detects the
emission sentinel `<!-- athanor:verification-emission v=1 -->` at the first
non-whitespace line of `last_assistant_message` and exits 0 silently. Without
this sentinel, the verification skill's own evidence output (which contains
material-claim-shaped statements like "tests passed, exit 0") would re-trigger
the gate, creating an infinite Stop loop.

This test pins:
  1. The `## Emission Sentinel` section exists in the verification skill.
  2. The literal sentinel string `<!-- athanor:verification-emission v=1 -->`
     appears in the section.
  3. The Emission Sentinel section appears BEFORE the `## The Iron Law`
     section (load-bearing: the model reads the skill top-down and must see
     the sentinel instruction first).
  4. The Provenance block documents the v0.7.8 local addition (per
     docs/DEPENDENCIES.md vendoring convention).

Plan reference: docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-command-mode-plan.md
§R10 (regression-test contract) and §U2 (verification-skill emission sentinel).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_FILE = REPO_ROOT / "skills/verification-before-completion/SKILL.md"

SENTINEL_LITERAL = "athanor:verification-emission v=2 nonce="


def _load():
    return SKILL_FILE.read_text(encoding="utf-8")


def _section_index(content, heading):
    """Return the line index of `heading`, or -1 if absent."""
    for i, line in enumerate(content.splitlines()):
        if line.strip() == heading:
            return i
    return -1


def test_emission_sentinel_section_exists():
    content = _load()
    assert "## Emission Sentinel" in content, (
        "Verification skill must declare a §Emission Sentinel section "
        "(plan §U2 — required for v0.7.8 hook re-entry prevention)."
    )


def test_literal_sentinel_string_present():
    content = _load()
    assert SENTINEL_LITERAL in content, (
        f"Verification skill must contain the literal sentinel string "
        f"{SENTINEL_LITERAL!r} so the model can copy it verbatim."
    )


def test_emission_sentinel_precedes_iron_law():
    content = _load()
    sentinel_idx = _section_index(content, "## Emission Sentinel")
    iron_law_idx = _section_index(content, "## The Iron Law")
    assert sentinel_idx >= 0, "§Emission Sentinel heading not found"
    assert iron_law_idx >= 0, "§The Iron Law heading not found"
    assert sentinel_idx < iron_law_idx, (
        f"§Emission Sentinel (line {sentinel_idx + 1}) must precede "
        f"§The Iron Law (line {iron_law_idx + 1}). The model reads the skill "
        f"top-down; placing the sentinel instruction after the Iron Law risks "
        f"the skill body satisfying the Iron Law without emitting the sentinel."
    )


def test_emission_sentinel_precedes_overview():
    """The sentinel must be the FIRST behavioral instruction the model reads."""
    content = _load()
    sentinel_idx = _section_index(content, "## Emission Sentinel")
    overview_idx = _section_index(content, "## Overview")
    assert sentinel_idx >= 0
    assert overview_idx >= 0
    assert sentinel_idx < overview_idx, (
        f"§Emission Sentinel must precede §Overview so the model sees the "
        f"sentinel requirement before any other skill content."
    )


def test_sentinel_section_describes_first_line_anchoring():
    """The sentinel section must explain the response-start anchoring contract
    so a future model understands why a sentinel on line 2 won't satisfy."""
    content = _load()
    # Slice the §Emission Sentinel section body
    section_start = _section_index(content, "## Emission Sentinel")
    lines = content.splitlines()
    section_end = len(lines)
    for j in range(section_start + 1, len(lines)):
        if lines[j].startswith("## "):
            section_end = j
            break
    section_body = "\n".join(lines[section_start:section_end])
    # Must communicate "first line" or "first non-whitespace" anchoring
    assert any(
        anchor_phrase in section_body.lower()
        for anchor_phrase in (
            "first line",
            "first non-whitespace",
            "response-start",
            "response start",
            "line 1",
        )
    ), (
        "§Emission Sentinel section must explain that the sentinel is anchored "
        "at the response start (line 1 / first non-whitespace line). Otherwise "
        "a model might place it after a greeting and silently fail the contract."
    )


def test_provenance_documents_v078_local_addition():
    """The Provenance block must record the v0.7.8 §Emission Sentinel
    addition (vendored-skill modification convention)."""
    content = _load()
    # Extract the Provenance block
    match = re.search(r"<!--\s*Provenance:.*?-->", content, re.DOTALL)
    assert match, "Provenance block not found in verification skill SKILL.md"
    provenance = match.group(0)
    assert "v0.7.8" in provenance, (
        "Provenance block must record the v0.7.8 local addition of "
        "§Emission Sentinel (per docs/DEPENDENCIES.md vendoring convention)."
    )
    assert "Emission Sentinel" in provenance, (
        "Provenance block must name the §Emission Sentinel addition explicitly."
    )
