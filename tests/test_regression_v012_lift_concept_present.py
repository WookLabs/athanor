"""Regression tests for v0.12.0 concept LIFT presence.

Subtask 13 extends the original Subtask 9 file with MUST 3 coverage
(R-ID / A-ID / AE-ID schemes + Key Flows section in
skills/discuss/references/requirements-capture.md).

Per Subtask 10 discovery: F-ID is documented in §"ID conventions" but the
Key Flows template uses bold leader labels (e.g. `**Trigger:**`) for flow
sub-fields. The F-ID prefix itself appears in §"ID conventions" prose and
in the Key Flows template lines (`- F1. [Flow name]`). For robustness we
assert the §"Key Flows" section heading is present AND R-/A-/AE-ID prefix
regexes match somewhere in the document body.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_debug_skill_has_systematic_debugging_discipline_lift():
    """MUST 2 — sp-systematic-debugging Iron Law + Four Phases + Jesse Vincent attribution lifted into skills/debug/SKILL.md per Subtask 9."""
    debug_md = (REPO_ROOT / "skills" / "debug" / "SKILL.md").read_text(encoding="utf-8")
    assert "Systematic Debugging Discipline" in debug_md
    assert "Iron Law" in debug_md
    assert "Four Phases" in debug_md
    assert "Jesse Vincent" in debug_md
    assert "superpowers" in debug_md


def test_requirements_capture_has_id_schemes():
    """MUST 3 — skills/discuss/references/requirements-capture.md documents R-ID / A-ID / AE-ID prefix schemes AND declares the §"Key Flows" section.

    F-ID is intentionally checked via the §"Key Flows" structural heading
    rather than a literal regex prefix at-large, because the template uses
    bold leader labels (`**Trigger:**`, `**Actors:**`, …) for flow sub-fields
    and the F1./F2. line shape only appears inside the template fenced block.
    """
    rc_path = (
        REPO_ROOT / "skills" / "discuss" / "references" / "requirements-capture.md"
    )
    body = rc_path.read_text(encoding="utf-8")

    # R-ID / A-ID / AE-ID prefix patterns must each have at least one match.
    # The format documented in the file is `R1.`, `A1.`, `AE1.` (no hyphen)
    # but the spec allows both `R1` and `R-1`. Accept either via optional `-?`.
    r_id_pattern = re.compile(r"\bR-?\d+\b")
    a_id_pattern = re.compile(r"\bA-?\d+\b")
    ae_id_pattern = re.compile(r"\bAE-?\d+\b")

    assert r_id_pattern.search(body), (
        "requirements-capture.md must contain at least one R-ID prefix "
        "(e.g., R1, R2)"
    )
    assert a_id_pattern.search(body), (
        "requirements-capture.md must contain at least one A-ID prefix "
        "(e.g., A1, A2)"
    )
    assert ae_id_pattern.search(body), (
        "requirements-capture.md must contain at least one AE-ID prefix "
        "(e.g., AE1, AE2)"
    )

    # Structural Flow check — §"Key Flows" section heading must be present
    # (substitutes for F-ID literal regex per Subtask 10 discovery).
    assert re.search(r"^#{2,3}\s+Key Flows\s*$", body, flags=re.MULTILINE), (
        "requirements-capture.md must declare a 'Key Flows' section "
        "(structural substitute for F-ID literal check)"
    )

    # ID conventions section explicitly names the four ID schemes.
    assert "ID conventions" in body, (
        "requirements-capture.md must declare an 'ID conventions' subsection"
    )
