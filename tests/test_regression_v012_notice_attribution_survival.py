"""Regression tests for v0.12.0 NOTICE.md attribution survival (Subtask 17).

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Phase 5 (Subtask 17) — surface-assertion tests for the post-cutover NOTICE.md.

These tests assert the post-v0.12.0 invariants for NOTICE.md attribution:

- The §"Concepts adopted from upstream" section enumerates all 5 numbered
  LIFT entries (### 1. through ### 5.). Subtask 12 delivered the section
  in place; this is the cross-check that the survival invariant holds
  for the surface that powers the LIFT manifest.
- The §"Removed in v0.12.0" subsection enumerates the removed vendored
  skill directories. Subtask 19 lands this prose; the test is marked
  xfail with strict=False until that subtask flips the assertion green.
- MIT license text is retained for BOTH compound-engineering AND
  superpowers attribution blocks. The literal "License: MIT" key appears
  at least twice — one per attribution block — and the MIT preamble
  paragraph is reproduced in each.

Voice constraints (D7): docstrings here use direct attribution to the
plan-of-record + the on-disk NOTICE.md ledger. The forbidden D7 phrases
("translated", "interpreted", "we discovered", "natural maturation") do
not appear in this file.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTICE_PATH = REPO_ROOT / "NOTICE.md"


def test_notice_md_has_concepts_adopted_section():
    """MUST 1.a — NOTICE.md §"Concepts adopted from upstream" enumerates
    all 5 numbered LIFT entries (### 1. through ### 5.).

    Subtask 12 wrote the section; this test re-asserts the invariant under
    the Subtask 17 surface-assertion ledger so a NOTICE.md regression that
    drops or renames the LIFT entries is caught directly.
    """
    body = NOTICE_PATH.read_text(encoding="utf-8")

    # Section heading present.
    assert re.search(
        r"^#{1,3}\s+Concepts adopted from upstream",
        body,
        flags=re.MULTILINE,
    ), (
        "NOTICE.md must contain a 'Concepts adopted from upstream' section "
        "heading"
    )

    # Each of the 5 numbered entries (### 1. ... ### 5.) must be present.
    for n in range(1, 6):
        pattern = rf"^###\s+{n}\.\s+\S"
        assert re.search(pattern, body, flags=re.MULTILINE), (
            f"NOTICE.md §'Concepts adopted from upstream' must include "
            f"'### {n}.' numbered LIFT entry"
        )


def test_notice_md_has_removed_section():
    """MUST 1.b — NOTICE.md §"Removed in v0.12.0" subsection lists the
    removed vendored skill directories.

    Pending Subtask 19. Marked xfail with strict=False so that an early
    landing (e.g. Subtask 19 ships before Subtask 17 lock-in) records an
    XPASS rather than failing the suite.
    """
    body = NOTICE_PATH.read_text(encoding="utf-8")

    # Section heading present at any heading level.
    assert re.search(
        r"^#{1,4}\s+Removed in v0\.12\.0",
        body,
        flags=re.MULTILINE,
    ), (
        "NOTICE.md must contain a 'Removed in v0.12.0' section heading "
        "post-Subtask 19"
    )

    # At least one removed `skills/<name>/` bullet inside the section.
    # Loose contract — the section body lists removed directories; exact
    # bullet shape is governed by Subtask 19's prose.
    assert re.search(
        r"skills/(?:ce|sp)-[a-z0-9-]+/?",
        body,
    ), (
        "NOTICE.md 'Removed in v0.12.0' section must enumerate removed "
        "skill directory paths (skills/ce-* or skills/sp-*)"
    )


def test_notice_md_retains_mit_license_text():
    """MUST 1.c — NOTICE.md retains MIT license attribution for both
    compound-engineering AND superpowers.

    The "License: MIT" key appears at least twice in the file — one per
    attribution block. The MIT preamble paragraph ("MIT License") is also
    reproduced verbatim in each license-text fence (the canonical license
    body opens with the literal "MIT License" header).
    """
    body = NOTICE_PATH.read_text(encoding="utf-8")

    # Count "License: MIT" / "License**: MIT" key occurrences (markdown
    # bold + colon flavours). At least 2 — one per upstream attribution.
    license_key_pattern = re.compile(
        r"\*?\*?License\*?\*?\s*:\s*MIT", re.IGNORECASE
    )
    matches = license_key_pattern.findall(body)
    assert len(matches) >= 2, (
        f"NOTICE.md must list 'License: MIT' at least twice (one per "
        f"upstream attribution block: compound-engineering + superpowers); "
        f"found {len(matches)} occurrence(s)"
    )

    # The literal "MIT License" header opens the license-text fence and
    # must appear at least twice (one per attribution block).
    mit_header_count = len(re.findall(r"^MIT License\s*$", body, flags=re.MULTILINE))
    assert mit_header_count >= 2, (
        f"NOTICE.md must reproduce the 'MIT License' header at least "
        f"twice (one per attribution block); found {mit_header_count}"
    )
