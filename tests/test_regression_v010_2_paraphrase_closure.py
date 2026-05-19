"""Regression test for v0.10.2 invariants — Stop hook paraphrase regex
layer + NFKC + cyrillic confusables fold + vendor-aware whitelist.

Tests the closure of three honesty-arc deferred items:
- B2 (sec-003): paraphrase bypass — regex verb-anchor patterns catch
  paraphrased state assertions ("CI is green", "build is healthy").
- ADV-006: cyrillic homoglyph — NFKC + Cyrillic→Latin fold catches
  homoglyph-substituted whitelist phrases ("tеsts pass" with Cyrillic 'е').
- A2: vendor-aware whitelist — extended phrase set catches idioms emitted
  by vendored CE/superpowers skills ("review complete", "checks passed").

Plan reference: docs/plans/2026-05-19-005-feat-v0.10.2-paraphrase-bypass-closure-plan.md
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts" / "hooks"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def stop_module():
    """Load stop_verify_claims fresh to pick up v0.10.2 changes."""
    if "stop_verify_claims" in sys.modules:
        del sys.modules["stop_verify_claims"]
    return importlib.import_module("stop_verify_claims")


# ---- U1: NFKC + confusables fold ----


def test_normalize_helper_exists(stop_module):
    """MUST: _normalize_for_match function present in module."""
    assert hasattr(stop_module, "_normalize_for_match"), (
        "stop_verify_claims must export _normalize_for_match()"
    )


def test_normalize_ascii_passthrough(stop_module):
    norm = stop_module._normalize_for_match
    assert norm("tests pass") == "tests pass"


def test_normalize_fullwidth_to_halfwidth(stop_module):
    """NFKC collapses fullwidth ASCII to halfwidth."""
    norm = stop_module._normalize_for_match
    # ｔｅｓｔｓ (fullwidth) → tests
    fullwidth = "ｔｅｓｔｓ ｐａｓｓ"
    assert norm(fullwidth) == "tests pass"


def test_normalize_cyrillic_homoglyph_e(stop_module):
    """Cyrillic 'е' (U+0435) folds to Latin 'e'."""
    norm = stop_module._normalize_for_match
    # 't' + Cyrillic 'е' + 'sts pass' — looks identical but bytes differ
    cyrillic = "tеsts pass"
    assert norm(cyrillic) == "tests pass"


def test_normalize_cyrillic_homoglyph_a(stop_module):
    """Cyrillic 'а' (U+0430) folds to Latin 'a'."""
    norm = stop_module._normalize_for_match
    # "p" + Cyrillic "а" + "ss" + " all tests"
    cyrillic = "pаss all tests"
    assert norm(cyrillic) == "pass all tests"


def test_normalize_cyrillic_homoglyph_capitals(stop_module):
    """Cyrillic 'А' (U+0410) folds to Latin 'A' (after lowercase)."""
    norm = stop_module._normalize_for_match
    # NOTE: normalize also lowercases, so capitals → lowercase first
    cyrillic = "Аll tests pass"
    result = norm(cyrillic)
    assert "all tests pass" in result, f"Expected fold + lowercase; got {result!r}"


def test_normalize_lowercases(stop_module):
    """Normalize is case-insensitive (lowercases at the end)."""
    norm = stop_module._normalize_for_match
    assert norm("TESTS PASS") == "tests pass"


def test_normalize_mixed_cyrillic_and_fullwidth(stop_module):
    """Combined attack: fullwidth + Cyrillic letters in same string."""
    norm = stop_module._normalize_for_match
    # ｔ (fullwidth) + Cyrillic е + sts ｐ (fullwidth) + ass
    mixed = "ｔеsts ｐass"
    assert norm(mixed) == "tests pass"


def test_normalize_empty_string(stop_module):
    norm = stop_module._normalize_for_match
    assert norm("") == ""


def test_normalize_non_confused_greek_omicron_documented_residual(stop_module):
    """KNOWN RESIDUAL (documented v0.10.2 scope): Greek ο (U+03BF) is NOT
    in the v0.10.2 Cyrillic-only fold table. A bypass using Greek
    homoglyphs would not be caught at this release.

    This test asserts the CURRENT behavior (residual is preserved). If a
    future release adds Greek to the fold, this test should be deleted
    or inverted, not left to silently fail.
    """
    norm = stop_module._normalize_for_match
    # Greek ο in "tests pass" — current scope keeps it unchanged
    greek = "tests p" + "ο" + "ss"  # 'tests p' + Greek omicron + 'ss'
    result = norm(greek)
    assert "ο" in result, (
        "v0.10.2 scope: Greek homoglyphs NOT folded. If this assertion "
        "fails, the fold table was expanded — update or delete this test."
    )


# ---- U2: paraphrase regex patterns ----


def test_paraphrase_patterns_constant_exists(stop_module):
    """MUST: MATERIAL_CLAIM_PATTERNS list present and non-empty."""
    assert hasattr(stop_module, "MATERIAL_CLAIM_PATTERNS")
    assert len(stop_module.MATERIAL_CLAIM_PATTERNS) >= 4, (
        "Expected at least 4 paraphrase regex patterns"
    )


@pytest.mark.parametrize("message", [
    "CI is green.",
    "CI is now green.",
    "ci is currently green",
    "All tests are green.",
    "all tests are now passing",
    "All tests are currently green",
    "The build is healthy.",
    "the build is now healthy",
    "the build is clean",
])
def test_paraphrase_positives_caught(stop_module, message):
    """MUST: paraphrased state assertions are caught."""
    assert stop_module.is_material_claim(message), (
        f"Paraphrase positive missed: {message!r}"
    )


@pytest.mark.parametrize("message", [
    "We should make sure CI passes.",  # advisory, not assertion
    "I'm working on the test suite.",  # no state claim
    "The plan describes how tests are structured.",  # describes, not asserts
])
def test_paraphrase_negatives_not_caught(stop_module, message):
    """MUST: pure prose discussing tests without asserting state is NOT
    caught. This is the false-positive guard for the v0.10.2 layer."""
    assert not stop_module.is_material_claim(message), (
        f"Paraphrase negative false-positive: {message!r}"
    )


@pytest.mark.parametrize("message", [
    # Conditional / speculative tense — regex cannot distinguish without
    # semantic analysis. Documented as v0.10.2 residual per plan §Risk
    # Analysis.
    "Once the build is green, ship it.",
    "If all tests are green, merge.",
    # Pre-existing v0.7.7 limitation (substring of "tests pass" inside
    # prose) — unchanged by v0.10.2.
    "When tests pass through this filter, the user sees the result.",
])
def test_known_false_positives_documented(stop_module, message):
    """KNOWN RESIDUAL (v0.10.3+ candidates): the v0.10.2 regex layer DOES
    catch these even though they're conditional or descriptive, not
    assertive. Closure requires semantic analysis (transcript-event
    introspection or LLM-class similarity). This test asserts the
    CURRENT behavior so the residual is visible.

    If a future release adds attribution/speculative-tense detection,
    invert these assertions; do not silently let them shift.
    """
    assert stop_module.is_material_claim(message), (
        f"Known v0.10.2 residual: {message!r} should still be caught "
        f"(conditional/prose false-positive). If this fails, residual was "
        f"closed — update test to assert the new behavior."
    )


# ---- ADV-006 cyrillic homoglyph end-to-end ----


def test_cyrillic_homoglyph_caught_via_literal_whitelist(stop_module):
    """Cyrillic-substituted version of a literal whitelist phrase is
    caught (the normalization step folds before substring match)."""
    # "tests pass" with Cyrillic е (U+0435)
    cyrillic_payload = "Done! tеsts pass after my changes."
    assert stop_module.is_material_claim(cyrillic_payload), (
        "Cyrillic homoglyph 'tеsts pass' must be caught after NFKC fold"
    )


def test_fullwidth_caught_via_literal_whitelist(stop_module):
    """Fullwidth-character version of whitelist phrase is caught after
    NFKC normalization."""
    fullwidth = "ｔｅｓｔｓ ｐａｓｓ"
    assert stop_module.is_material_claim(fullwidth + " confirmed."), (
        "Fullwidth 'tests pass' must be caught after NFKC"
    )


# ---- U3: vendor-aware whitelist additions ----


@pytest.mark.parametrize("message", [
    "Review complete.",
    "All checks passing on the PR.",
    "<promise>DONE</promise>",
    "Implementation complete.",
    "Branch merged into main.",
])
def test_vendor_aware_whitelist_additions(stop_module, message):
    """MUST: v0.10.2 vendor-aware phrase additions are caught."""
    assert stop_module.is_material_claim(message), (
        f"Vendor-aware idiom missed: {message!r}"
    )


# ---- Existing literal whitelist still works (regression check) ----


def test_existing_en_whitelist_still_works(stop_module):
    """REGRESSION: v0.7.7 literal whitelist phrases stay caught."""
    assert stop_module.is_material_claim("tests pass")
    assert stop_module.is_material_claim("build succeeded")
    assert stop_module.is_material_claim("agent task completed")


def test_existing_ko_whitelist_still_works(stop_module):
    """REGRESSION: v0.7.7 Korean literal whitelist still caught."""
    assert stop_module.is_material_claim("테스트 통과")
    assert stop_module.is_material_claim("빌드 성공")
    assert stop_module.is_material_claim("배포 완료")


def test_skip_categories_not_caught(stop_module):
    """REGRESSION: skip categories (analysis, planning, opinions) stay
    out of scope per v0.7.7 prompt scope."""
    assert not stop_module.is_material_claim("Here's a plan to add tests")
    assert not stop_module.is_material_claim("I think this approach is best")
    assert not stop_module.is_material_claim("Researching the right pattern")


# ---- Module-load invariants ----


def test_module_load_asserts_pattern_list_non_empty(stop_module):
    """MUST (D3): MATERIAL_CLAIM_PATTERNS must be non-empty (module-load
    assertion in the script catches an empty list)."""
    assert len(stop_module.MATERIAL_CLAIM_PATTERNS) > 0


def test_patterns_are_compiled_regex_objects(stop_module):
    """MUST: every entry in MATERIAL_CLAIM_PATTERNS is a compiled regex."""
    import re
    for p in stop_module.MATERIAL_CLAIM_PATTERNS:
        assert hasattr(p, "search"), (
            f"Pattern {p!r} is not a compiled regex object"
        )
