"""Regression tests for v0.14.2 Cycle 1 bug fixes (G1 + G2 + G3).

G1: Position mapping invariant — _match_is_suppressed() must use normalized
    text (not original message) for context extraction, because match
    positions come from the normalized string. NFKC can change string
    length (e.g., U+FB03 ligature 'ffi' -> 3-char 'ffi'), making
    normalized positions invalid when applied to original text.

G2: Nonce TTL raised from 60s to 120s — complex verification workflows
    can exceed 60s between nonce creation and Stop hook validation.

G3: Atomic write race fix — tempfile.mkstemp() suffix now includes a
    random token via secrets.token_hex(4) to prevent collisions under
    concurrent writes.
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts" / "hooks"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import hook_state  # noqa: E402  # type: ignore[import]
import stop_verify_claims as svc  # noqa: E402  # type: ignore[import]


# ===========================================================================
# G1: Position mapping invariant — _match_is_suppressed uses normalized text
# ===========================================================================


class TestG1PositionMappingInvariant:
    """_match_is_suppressed must pass `normalized` (not `message`) to the
    context-extraction helpers so that positions from normalized-string
    matches are used consistently with the text being indexed."""

    def test_match_is_suppressed_source_uses_normalized_not_message(self):
        """Inspect the source of _match_is_suppressed to confirm it passes
        `normalized` to both helper functions, not `message`."""
        source = inspect.getsource(svc._match_is_suppressed)
        # Should call helpers with `normalized` as the text argument
        assert "_is_conditional_or_speculative_context(normalized," in source, (
            "_match_is_suppressed must pass `normalized` (not `message`) to "
            "_is_conditional_or_speculative_context"
        )
        assert "_is_attributed_quote_context(normalized," in source, (
            "_match_is_suppressed must pass `normalized` (not `message`) to "
            "_is_attributed_quote_context"
        )
        # Should NOT pass `message` to either helper
        assert "_is_conditional_or_speculative_context(message," not in source, (
            "_match_is_suppressed must NOT pass `message` to "
            "_is_conditional_or_speculative_context (position mismatch risk)"
        )
        assert "_is_attributed_quote_context(message," not in source, (
            "_match_is_suppressed must NOT pass `message` to "
            "_is_attributed_quote_context (position mismatch risk)"
        )

    def test_nfkc_length_changing_char_conditional_suppression(self):
        """A message with NFKC length-changing characters (U+FB03 ffi
        ligature) before a conditional clause should still be correctly
        suppressed. Before the fix, the position mismatch could cause
        the conditional prefix to be missed."""
        # U+FB03 = 'ffi' ligature (1 char -> 3 chars under NFKC)
        # Place it before a conditional clause with a material claim
        ligature = "ﬃ"  # ffi ligature
        # "ffi prefix. if tests pass then merge" — 'if' is conditional marker
        message = f"{ligature} prefix. if tests pass then merge"
        # After NFKC: "ffi prefix. if tests pass then merge"
        # The "tests pass" claim is in a conditional clause starting with "if"
        result = svc.is_material_claim(message)
        assert result is False, (
            "Material claim inside conditional clause after NFKC-expanding "
            "characters should be suppressed"
        )

    def test_nfkc_length_changing_char_attribution_suppression(self):
        """A message with NFKC length-changing characters before an
        attributed quote should still suppress the match correctly."""
        ligature = "ﬃ"  # ffi ligature
        message = f"{ligature} prefix. he said \"tests pass\" yesterday"
        result = svc.is_material_claim(message)
        assert result is False, (
            "Material claim inside attributed quote after NFKC-expanding "
            "characters should be suppressed"
        )

    def test_nfkc_length_changing_char_real_claim_not_suppressed(self):
        """A genuine material claim after NFKC-expanding characters should
        NOT be suppressed (no false negatives from the fix)."""
        ligature = "ﬃ"  # ffi ligature
        message = f"{ligature} prefix. tests pass successfully"
        result = svc.is_material_claim(message)
        assert result is True, (
            "Genuine material claim should still be detected even with "
            "NFKC-expanding characters in the message"
        )

    def test_multiple_ligatures_conditional_suppression(self):
        """Multiple NFKC-expanding characters amplify the position offset.
        Suppression must still work correctly."""
        # 3 ligatures = 3 chars original -> 9 chars normalized (+6 offset)
        prefix = "ﬃﬃﬃ"
        message = f"{prefix} text here. if all tests pass we can merge"
        result = svc.is_material_claim(message)
        assert result is False, (
            "Conditional suppression must work with multiple NFKC-expanding "
            "characters causing large position offsets"
        )

    def test_fullwidth_chars_conditional_suppression(self):
        """Fullwidth Latin characters (U+FF21-FF5A) are NFKC-normalized to
        ASCII. For single fullwidth chars the length is preserved (1:1),
        but this test confirms the pipeline works end-to-end."""
        # Fullwidth 'A' = U+FF21, under NFKC -> 'A' (same length but
        # different codepoint; confirms normalize pipeline consistency)
        message = "ＡＢＣ. if tests pass then ok"
        result = svc.is_material_claim(message)
        assert result is False, (
            "Conditional suppression should work with fullwidth characters"
        )


# ===========================================================================
# G2: Nonce TTL >= 120s
# ===========================================================================


class TestG2NonceTTL:
    """NONCE_TTL_SECONDS must be >= 120 to accommodate complex verification
    workflows (v0.14.2 fix)."""

    def test_nonce_ttl_at_least_120(self):
        assert hook_state.NONCE_TTL_SECONDS >= 120, (
            f"NONCE_TTL_SECONDS={hook_state.NONCE_TTL_SECONDS} is below the "
            f"v0.14.2 minimum of 120s; complex workflows may hit stale-nonce "
            f"errors"
        )

    def test_nonce_ttl_exact_value(self):
        """Pin the exact value so unintended changes are caught."""
        assert hook_state.NONCE_TTL_SECONDS == 120, (
            f"Expected NONCE_TTL_SECONDS=120, got {hook_state.NONCE_TTL_SECONDS}"
        )

    def test_is_nonce_fresh_within_new_ttl(self):
        """A nonce aged 90s (between old 60s TTL and new 120s TTL) should
        be considered fresh under the new TTL."""
        import time
        state = {"timestamp": time.time() - 90}
        assert hook_state.is_nonce_fresh(state) is True, (
            "A 90s-old nonce should be fresh with TTL=120s"
        )

    def test_is_nonce_stale_beyond_new_ttl(self):
        """A nonce aged 130s should be stale even under the new TTL."""
        import time
        state = {"timestamp": time.time() - 130}
        assert hook_state.is_nonce_fresh(state) is False, (
            "A 130s-old nonce should be stale with TTL=120s"
        )


# ===========================================================================
# G3: Atomic write race fix — tempfile includes random suffix
# ===========================================================================


class TestG3AtomicWriteRaceFix:
    """_atomic_write_json must use secrets.token_hex in the tempfile suffix
    to prevent collisions under concurrent writes."""

    def test_secrets_import_exists(self):
        """hook_state.py must import the secrets module."""
        import importlib
        # Re-import to ensure fresh module state
        mod = importlib.import_module("hook_state")
        assert hasattr(mod, "secrets") or "secrets" in dir(mod), (
            "hook_state.py must import the secrets module for tempfile randomness"
        )

    def test_atomic_write_source_uses_secrets_token_hex(self):
        """Inspect _atomic_write_json source to confirm secrets.token_hex
        is used in the tempfile suffix."""
        source = inspect.getsource(hook_state._atomic_write_json)
        assert "secrets.token_hex" in source, (
            "_atomic_write_json must use secrets.token_hex in tempfile suffix"
        )

    def test_atomic_write_source_suffix_not_bare_json(self):
        """The tempfile suffix must NOT be a bare '.json' (the pre-fix
        pattern that allowed collisions)."""
        source = inspect.getsource(hook_state._atomic_write_json)
        # Look for the old pattern: suffix=".json" (exact bare suffix)
        bare_suffix = re.search(r'suffix\s*=\s*"\.json"', source)
        assert bare_suffix is None, (
            "_atomic_write_json must not use bare suffix='.json'; "
            "use a random token to prevent concurrent-write collisions"
        )

    def test_concurrent_writes_no_leftover_tempfiles(self, tmp_path):
        """Multiple rapid writes to the same target should not leave
        orphaned tempfiles behind."""
        (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
        (tmp_path / ".athanor").mkdir()
        session = "concurrent-test"
        for i in range(20):
            hook_state.write_nonce_state(
                session, f"nonce-{i}", f"hash-{i}", project_root=tmp_path
            )
        state_dir = hook_state.get_state_dir(session, project_root=tmp_path)
        leftovers = [f for f in state_dir.iterdir() if f.name.startswith(".tmp-")]
        assert not leftovers, f"Found leftover tempfiles after rapid writes: {leftovers}"
        # Final state should be the last write
        state = hook_state.read_nonce_state(session, project_root=tmp_path)
        assert state["nonce"] == "nonce-19"

    def test_atomic_write_functional_correctness(self, tmp_path):
        """Verify _atomic_write_json still works correctly after the
        suffix change (functional smoke test)."""
        (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
        (tmp_path / ".athanor").mkdir()
        hook_state.write_nonce_state("s1", "abc", "def", project_root=tmp_path)
        state = hook_state.read_nonce_state("s1", project_root=tmp_path)
        assert state is not None
        assert state["nonce"] == "abc"
        assert state["body_hash"] == "def"
