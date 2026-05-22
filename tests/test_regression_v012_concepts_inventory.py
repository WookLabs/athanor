"""Regression tests for v0.12.0 concept-kernel cutover inventory.

Covers MUSTs 4-6 from the v0.12.0 plan:

- MUST 4: concepts/ directory exists with exactly 7 files
  (1 README + 6 per-concept inventory files).
- MUST 5: each non-README concept file contains the fixed-shape provenance
  headers (Source:, Target:, Commit SHA:).
- MUST 6: NOTICE.md contains §"Concepts adopted from upstream" with all
  five numbered LIFT entries (### 1. through ### 5.).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONCEPTS_DIR = REPO_ROOT / "concepts"
NOTICE_PATH = REPO_ROOT / "NOTICE.md"

EXPECTED_CONCEPT_FILES = {
    "README.md",
    "review-personas.md",
    "systematic-debugging.md",
    "requirements-capture.md",
    "skill-discovery-preamble.md",
    "doc-review-mode.md",
    "brainstorm-requirements.md",
}


def test_concepts_directory_has_7_files():
    """MUST 4 — concepts/ exists with exactly 7 files."""
    assert CONCEPTS_DIR.is_dir(), (
        f"concepts/ directory must exist at {CONCEPTS_DIR}"
    )

    actual_files = {p.name for p in CONCEPTS_DIR.iterdir() if p.is_file()}
    assert len(actual_files) == 7, (
        f"concepts/ must contain exactly 7 files, found {len(actual_files)}: "
        f"{sorted(actual_files)}"
    )
    assert actual_files == EXPECTED_CONCEPT_FILES, (
        f"concepts/ file set mismatch.\n"
        f"  expected: {sorted(EXPECTED_CONCEPT_FILES)}\n"
        f"  actual:   {sorted(actual_files)}"
    )


def test_each_concept_file_has_source_target_sha_headers():
    """MUST 5 — each non-README concept file contains Source:, Target:, Commit SHA: headers."""
    concept_files = [
        p
        for p in CONCEPTS_DIR.iterdir()
        if p.is_file() and p.name != "README.md"
    ]
    assert len(concept_files) == 6, (
        f"Expected 6 non-README concept files, found {len(concept_files)}"
    )

    required_headers = ["Source:", "Target:", "Commit SHA:"]
    for cf in concept_files:
        body = cf.read_text(encoding="utf-8")
        for header in required_headers:
            assert header in body, (
                f"{cf.name} must contain '{header}' provenance header; "
                f"missing in body."
            )


def test_notice_md_has_concepts_adopted_section():
    """MUST 6 — NOTICE.md §"Concepts adopted from upstream" enumerates all 5 LIFT entries (### 1.–### 5.)."""
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
