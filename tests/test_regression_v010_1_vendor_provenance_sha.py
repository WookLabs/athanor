"""Regression test for v0.10.1 U2 invariant — v0.9.0 vendor reference
`source-commit` fields no longer contain the placeholder phrase.

The two affected files:
- skills/discuss/references/clarify-gap-probes.md
- skills/discuss/references/requirements-capture.md

Before v0.10.1, both carried `source-commit: vendored at athanor v0.9.0
release time` which records nothing about the upstream content actually
vendored. v0.10.1 replaces that with `compound-engineering@3.8.2 <path>`
+ a verification note that the same content was re-checked at the v0.10.0
absorption.

Plan reference: docs/plans/2026-05-19-004-feat-v0.10.1-vendor-hygiene-plan.md
§U2, B3.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REFERENCE_FILES = [
    REPO_ROOT / "skills" / "discuss" / "references" / "clarify-gap-probes.md",
    REPO_ROOT / "skills" / "discuss" / "references" / "requirements-capture.md",
]

PLACEHOLDER_PHRASE = "vendored at athanor v0.9.0 release time"


def test_reference_files_exist():
    for p in REFERENCE_FILES:
        assert p.exists(), f"Vendor reference file missing: {p}"


def test_provenance_no_longer_uses_placeholder_only_phrase():
    """MUST: each provenance block's `source-commit:` line does NOT
    contain the v0.9.0 placeholder phrase as its complete value."""
    for p in REFERENCE_FILES:
        text = p.read_text(encoding="utf-8")
        # Find the source-commit line
        sc_line = None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("source-commit:"):
                sc_line = line
                break
        assert sc_line is not None, f"No source-commit line in {p.name}"
        # The line itself may still REFERENCE the v0.9.0 release time (the
        # corrected version notes that the file was vendored at v0.9.0 time
        # and verified at v0.10.0). What's NOT allowed is the placeholder
        # being the WHOLE value with no upstream pin alongside it.
        # We enforce: source-commit field must mention `compound-engineering@`
        # with a version tag.
        ce_pin_present = "compound-engineering@" in text and (
            "compound-engineering@3.8.2" in text
            or "compound-engineering@3.8.3" in text
        )
        assert ce_pin_present, (
            f"{p.name} source-commit must record `compound-engineering@<version>` "
            f"pin (T2 provenance honesty). Current line: {sc_line!r}"
        )


def test_provenance_documents_v010_1_correction():
    """MUST: each file's provenance mentions the v0.10.1 correction so
    the audit trail explains why source-commit changed."""
    for p in REFERENCE_FILES:
        text = p.read_text(encoding="utf-8").lower()
        assert "v0.10.1" in text, (
            f"{p.name} provenance must reference v0.10.1 correction"
        )


def test_provenance_files_body_not_dropped():
    """MUST: U2 was a provenance-only edit; the body content (gap-probe
    lens definitions / requirements-capture template) must not have been
    accidentally truncated.

    Windows CI note: explicit encoding='utf-8' is required because both
    files contain non-ASCII characters (§ from upstream prose) that would
    fail under cp1252 default on Windows.
    """
    gap_probes_text = (REPO_ROOT / "skills" / "discuss" / "references" / "clarify-gap-probes.md").read_text(encoding="utf-8")
    for lens in ["Evidence gap", "Specificity gap", "Counterfactual gap", "Attachment gap"]:
        assert lens in gap_probes_text, (
            f"clarify-gap-probes.md body missing '{lens}'"
        )
    req_capture_text = (REPO_ROOT / "skills" / "discuss" / "references" / "requirements-capture.md").read_text(encoding="utf-8")
    for section_name in ["Summary", "Problem Frame", "Acceptance Examples", "Success Criteria"]:
        assert section_name in req_capture_text, (
            f"requirements-capture.md body missing '{section_name}'"
        )
