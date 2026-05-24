"""Regression tests for v0.13.2 Korean regex patterns — base-form detection.

Prior to the v0.13.2 fix, Korean verb-anchored paraphrase patterns in
MATERIAL_CLAIM_PATTERNS required a suffixed form (했/함/됨) to match.
Unsuffixed base forms like "테스트가 모두 통과" and "빌드가 성공" were
undetected — a false-negative gap in the Stop hook gate.

The regex fix makes the suffix group optional (`(?:했|함|됨)?`), so both
base and suffixed forms are now caught.  These tests lock that fix.

Five tests:
  1. Base form with particles   — "테스트가 모두 통과"
  2. Base form without suffix   — "빌드가 성공"
  3. Suffixed forms (regression lock) — "테스트가 모두 통과했", "빌드가 성공함"
  4. Substring layer base forms — "테스트 통과", "빌드 성공" in MATERIAL_CLAIMS_KO
  5. Full pipeline integration  — is_material_claim() end-to-end
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
    """Load stop_verify_claims fresh to pick up latest changes."""
    if "stop_verify_claims" in sys.modules:
        del sys.modules["stop_verify_claims"]
    return importlib.import_module("stop_verify_claims")


# ---- Test 1: base form with particles ----


def test_paraphrase_catches_base_form_with_particles(stop_module):
    """MUST: '테스트가 모두 통과' (base form, no suffix) detected as material claim.

    The regex r'테스트(?:가|는)?\\s*(?:다|모두|전부)?\\s*통과(?:했|함|됨)?'
    must match when the trailing suffix group is absent.
    """
    msg = "분석 결과, 테스트가 모두 통과 상태입니다."
    assert stop_module.is_material_claim(msg), (
        f"is_material_claim() should detect base-form Korean: {msg!r}"
    )


# ---- Test 2: base form without suffix ----


def test_paraphrase_catches_base_form_without_suffix(stop_module):
    """MUST: '빌드가 성공' (base form, no suffix) detected as material claim.

    The regex r'빌드(?:가|는)?\\s*(?:다|모두)?\\s*성공(?:했|함|됨)?'
    must match when the trailing suffix group is absent.
    """
    msg = "현재 빌드가 성공 상태로 확인됩니다."
    assert stop_module.is_material_claim(msg), (
        f"is_material_claim() should detect base-form Korean: {msg!r}"
    )


# ---- Test 3: suffixed forms (regression lock) ----


def test_paraphrase_still_catches_suffixed_forms(stop_module):
    """MUST: suffixed Korean forms remain detected — regression lock.

    Making the suffix optional must NOT break detection of the previously-
    caught suffixed variants (했/함/됨).
    """
    suffixed_cases = [
        "테스트가 모두 통과했",
        "빌드가 성공함",
        "테스트가 전부 통과됨",
        "빌드는 성공했",
    ]
    for msg in suffixed_cases:
        assert stop_module.is_material_claim(msg), (
            f"is_material_claim() should still detect suffixed Korean: {msg!r}"
        )


# ---- Test 4: substring layer base forms ----


def test_substring_layer_catches_exact_base_forms(stop_module):
    """MUST: '테스트 통과' and '빌드 성공' appear in MATERIAL_CLAIMS_KO.

    The substring whitelist is the first-pass Korean detection layer (before
    the regex paraphrase layer).  These bare forms must be present so that
    even a simple substring scan catches the most common phrasing.
    """
    ko_list = stop_module.MATERIAL_CLAIMS_KO
    assert "테스트 통과" in ko_list, (
        "'테스트 통과' must be in MATERIAL_CLAIMS_KO substring list"
    )
    assert "빌드 성공" in ko_list, (
        "'빌드 성공' must be in MATERIAL_CLAIMS_KO substring list"
    )


# ---- Test 5: full pipeline integration ----


def test_full_pipeline_integration_suffixless_korean(stop_module):
    """Integration: is_material_claim() detects unsuffixed Korean through
    the complete normalization + suppression + regex pipeline.

    This test differs from tests 1-3 by exercising multi-sentence messages
    with mixed content, verifying that the detection pipeline correctly
    finds the material claim even when buried in surrounding prose, AND
    that suppression contexts (conditional/speculative prefix) correctly
    suppress when present.
    """
    is_mc = stop_module.is_material_claim

    # Positive: base-form Korean embedded in a longer response
    positive_cases = [
        "작업 보고서입니다.\n\n현재 테스트가 모두 통과 상태이며, 다음 단계로 넘어가겠습니다.",
        "코드 리뷰를 마쳤습니다. 빌드가 성공 상태입니다.",
        "리팩토링 후 테스트 다 통과 확인했습니다.",
        "CI 파이프라인에서 빌드 성공 확인.",
    ]
    for msg in positive_cases:
        assert is_mc(msg), (
            f"Full pipeline should detect unsuffixed Korean in: {msg!r}"
        )

    # Negative: conditional/speculative prefix should suppress
    suppressed_cases = [
        "만약 테스트가 모두 통과하면 배포하겠습니다.",
    ]
    for msg in suppressed_cases:
        assert not is_mc(msg), (
            f"Full pipeline should suppress conditional Korean: {msg!r}"
        )
