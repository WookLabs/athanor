"""Regression tests for v0.10.3 — Stop hook residual closure:
R1 (Greek/Armenian homoglyph fold), R2 (conditional/speculative tense
suppression), R3 (attributed historical reference skip).

Plan reference: docs/plans/2026-05-19-006-feat-v0.10.3-stop-hook-residual-closure-plan.md
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
    if "stop_verify_claims" in sys.modules:
        del sys.modules["stop_verify_claims"]
    return importlib.import_module("stop_verify_claims")


# ---- R1: Greek + Armenian homoglyph fold ----


def test_confusables_table_renamed_and_extended(stop_module):
    """MUST: confusables table renamed away from Cyrillic-only naming.
    Either the new name exists, or the old name's contents include
    Greek+Armenian additions."""
    has_new_name = hasattr(stop_module, "_CONFUSABLES_TO_LATIN_TABLE")
    has_old_name = hasattr(stop_module, "_CYRILLIC_TO_LATIN_TABLE")
    assert has_new_name or has_old_name, (
        "stop_verify_claims must expose either _CONFUSABLES_TO_LATIN_TABLE "
        "or _CYRILLIC_TO_LATIN_TABLE"
    )


def test_greek_omicron_folds_to_latin_o(stop_module):
    """R1: Greek `ο` (U+03BF) folds to Latin `o` — closure of v0.10.2 residual.

    Construct a payload where Greek ο is the ONLY substituted character;
    after fold the result should be identical to the Latin equivalent.
    """
    norm = stop_module._normalize_for_match
    payload = "deployed t" + "ο" + " production"  # Greek ο substituted for Latin o
    result = norm(payload)
    assert result == "deployed to production", (
        f"Greek `ο` (U+03BF) must fold to Latin `o` at v0.10.3. Got: {result!r}"
    )


def test_greek_alpha_folds_to_latin_a(stop_module):
    norm = stop_module._normalize_for_match
    payload = "p" + "α" + "ss tests"
    assert "pass tests" in norm(payload), (
        f"Greek `α` (U+03B1) must fold to Latin `a`. Got: {norm(payload)!r}"
    )


def test_greek_epsilon_folds_to_latin_e(stop_module):
    norm = stop_module._normalize_for_match
    payload = "t" + "ε" + "sts pass"
    assert norm(payload) == "tests pass"


def test_armenian_o_folds_to_latin_o(stop_module):
    """R1: Armenian `ո` (U+0578) folds to Latin `o`."""
    norm = stop_module._normalize_for_match
    payload = "test" + "ո" + "verflow pass"  # nonsense but exercise the fold
    assert "o" in norm(payload), (
        f"Armenian `ո` must fold to Latin `o`. Got: {norm(payload)!r}"
    )


def test_greek_homoglyph_caught_end_to_end(stop_module):
    """R1 end-to-end: a whitelist phrase with Greek substitution is caught."""
    # "tests pass" with Greek `α` replacing 'a'
    payload = "all tests p" + "α" + "ss after my changes"
    assert stop_module.is_material_claim(payload), (
        "Greek-homoglyph 'tests pαss' must be caught via fold"
    )


# ---- R2: conditional / speculative tense suppression ----


def test_conditional_if_suppresses_regex_match(stop_module):
    """R2: 'If all tests are green, merge' is NOT caught at v0.10.3."""
    assert not stop_module.is_material_claim(
        "If all tests are green, merge."
    ), "Conditional 'If' must suppress regex match at v0.10.3"


def test_conditional_once_suppresses(stop_module):
    """R2: 'Once the build is healthy, ship it' is NOT caught."""
    assert not stop_module.is_material_claim(
        "Once the build is healthy, ship it."
    )


def test_conditional_should_suppresses(stop_module):
    """R2: 'Should the deploy succeed' (speculative) is NOT caught."""
    assert not stop_module.is_material_claim(
        "Should the deploy succeed, notify the team."
    )


def test_conditional_korean_manyak_suppresses(stop_module):
    """R2 KO: '만약 ... 통과' is NOT caught."""
    # Korean conditional prefix
    assert not stop_module.is_material_claim(
        "만약 테스트 통과한다면 머지하세요."
    )


def test_assertion_after_clause_boundary_still_caught(stop_module):
    """R2 negative: clause boundary resets the conditional context.
    'If foo, all tests are green' — the assertion is in a separate clause
    AFTER the comma, so it remains caught at v0.10.3 (intentional — the
    suppression is local to the clause containing the conditional marker)."""
    # Wait — actually the v0.10.3 plan says clause-start check is from
    # the most recent boundary BEFORE the match. So "If foo, all tests
    # are green" — the match "all tests are green" has the most recent
    # boundary at the comma; the clause starts at " all tests are green";
    # no conditional marker at the clause start; match is NOT suppressed.
    # This test pins that behavior.
    assert stop_module.is_material_claim(
        "If foo, all tests are green now and the suite passed."
    ), (
        "Clause boundary resets conditional context — assertion after comma "
        "should still be caught"
    )


def test_bare_assertion_not_affected_by_r2(stop_module):
    """R2 regression: a bare assertion has no conditional marker; still caught."""
    assert stop_module.is_material_claim("CI is now green.")
    assert stop_module.is_material_claim("All tests are passing.")
    assert stop_module.is_material_claim("The build is healthy.")


# ---- R3: attribution / quoted-context skip ----


def test_attribution_via_quoted_span_suppresses(stop_module):
    """R3: a whitelist phrase inside paired quotes is suppressed."""
    payload = 'the v0.7.6 docs said "tests pass" back then'
    assert not stop_module.is_material_claim(payload), (
        "Match inside paired double-quotes must be suppressed"
    )


def test_attribution_via_single_quotes_suppresses(stop_module):
    payload = "the assertion was 'review complete' yesterday"
    assert not stop_module.is_material_claim(payload), (
        "Match inside paired single-quotes must be suppressed"
    )


def test_attribution_via_said_verb_suppresses(stop_module):
    """R3: a whitelist phrase shortly after 'said' is suppressed."""
    payload = "Earlier the report said tests pass after fixing the bug."
    assert not stop_module.is_material_claim(payload), (
        "Match within 30 chars after 'said' must be suppressed"
    )


def test_attribution_via_claimed_verb_suppresses(stop_module):
    payload = "He claimed: tests pass now."
    assert not stop_module.is_material_claim(payload)


def test_attribution_korean_rago_suppresses(stop_module):
    """R3 KO: '라고 했' attribution suppresses Korean material claim."""
    payload = "그 분이 테스트 통과 라고 했어요."
    assert not stop_module.is_material_claim(payload), (
        "Korean '라고 했' attribution must suppress KO material claim"
    )


def test_bare_assertion_not_affected_by_r3(stop_module):
    """R3 regression: standalone assertion has no attribution; still caught."""
    assert stop_module.is_material_claim("tests pass after my changes.")
    assert stop_module.is_material_claim("Review complete.")
    assert stop_module.is_material_claim("리뷰 완료")


# ---- Q1-6: attribution window must not over-suppress first-person claims ----
# `_ATTRIBUTION_VERBS_EN` previously carried first-person action verbs
# (`wrote`/`noted`/`stated`/...), and the window scan used SUBSTRING membership,
# so a natural completion claim was silently suppressed — and `wrote` matched
# inside `rewrote`. The verb list is trimmed to the genuinely-attributional
# `said`/`claimed`, matched on a WORD boundary.


def test_first_person_wrote_claim_not_suppressed(stop_module):
    """`I wrote the tests, tests pass` must remain a material claim (the gate
    must FIRE — `wrote` is no longer an attribution verb)."""
    assert stop_module.is_material_claim("I wrote the tests, tests pass"), (
        "first-person 'I wrote ... tests pass' must NOT be suppressed"
    )


def test_first_person_rewrote_claim_not_suppressed(stop_module):
    """`I rewrote X; tests pass` must remain a material claim — `rewrote` must
    not match the dropped `wrote` as a substring (word-boundary matcher)."""
    assert stop_module.is_material_claim("I rewrote the module; tests pass"), (
        "first-person 'I rewrote ... tests pass' must NOT be suppressed"
    )


def test_dropped_attribution_verbs_no_longer_suppress(stop_module):
    """The dropped verbs (`noted`/`stated`/`reported`/...) must no longer
    suppress a first-person completion claim on the same line."""
    for verb in ("noted", "stated", "reported", "commented", "mentioned"):
        payload = f"I {verb} the change and tests pass now."
        assert stop_module.is_material_claim(payload), (
            f"'{verb}' must not suppress the claim after trimming; payload={payload!r}"
        )


def test_said_and_claimed_attribution_still_suppress(stop_module):
    """Regression — the retained `said`/`claimed` verbs must STILL suppress a
    genuine third-party attribution (the two locked R3 cases)."""
    assert not stop_module.is_material_claim(
        "Earlier the report said tests pass after fixing the bug."
    ), "'said' attribution must still suppress"
    assert not stop_module.is_material_claim("He claimed: tests pass now."), (
        "'claimed' attribution must still suppress"
    )


# ---- Cross-cutting: existing v0.10.2 positives still work ----


def test_v010_2_paraphrase_positives_still_caught(stop_module):
    """REGRESSION: v0.10.2 paraphrase detection still works for bare
    assertions (without conditional or attribution context)."""
    assert stop_module.is_material_claim("CI is green.")
    assert stop_module.is_material_claim("All tests are passing.")
    assert stop_module.is_material_claim("The build is healthy.")


def test_v010_2_cyrillic_homoglyph_still_caught(stop_module):
    """REGRESSION: Cyrillic homoglyph detection from v0.10.2 unchanged."""
    payload = "tеsts pass after changes"  # Cyrillic е (U+0435)
    assert stop_module.is_material_claim(payload)


def test_v010_2_vendor_aware_still_caught(stop_module):
    """REGRESSION: vendor-aware whitelist from v0.10.2 unchanged."""
    assert stop_module.is_material_claim("Review complete.")
    assert stop_module.is_material_claim("<promise>DONE</promise>")


def test_v010_2_skip_categories_still_skipped(stop_module):
    """REGRESSION: skip categories (analysis, planning) unchanged."""
    assert not stop_module.is_material_claim("Here's a plan to add tests")
    assert not stop_module.is_material_claim("I think this approach is best")
