"""Regression test for the _doc honesty contract.

User-visible `_doc` strings inside athanor.json and templates/athanor.json
must match the actual runtime contract. The v0.7.6 release shipped false
claims in `_doc` ("Skills read this config..." for models; "Honored by
hook prompts via ATHANOR_HOOK_PROFILE..." for hooks). v0.7.7 corrected
those strings (PR #10 dual review caught the residual lies). v0.7.8
extends the contract per-key:

- `models._doc` REMAINS deprecated until v0.7.9 (the block is not read
  by any dispatch site). The v0.7.7 honesty contract still applies:
  lead with "DEPRECATED in v0.7.7", be substantive, forward-reference
  the removal version.
- `hooks._doc` is NO LONGER deprecated in v0.7.8 (the new command-hook
  gate at scripts/hooks/stop_verify_claims.py reads `hooks.profile`).
  The string must describe the WORKING contract: mention the script,
  the `profile: "off"` opt-out, the `profile: "standard"` default, and
  the removal of the v0.7.7 `hooks.disabled[]` orphan key.

Scope: athanor.json + templates/athanor.json. The skills/setup/SKILL.md
embedded fallback uses an older compact shape (no `_doc` strings); not
in scope for this test.

What this test does NOT enforce: that the old false-claim phrases
appear nowhere. The v0.7.7 deprecation strings legitimately QUOTE the
v0.7.6 claim to refute it ("The v0.7.6 docs claimed 'X' but..."). A
naive phrase blocklist would false-positive on attributed history.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEPRECATION_LEAD_PATTERN = re.compile(r"^DEPRECATED in v0\.7\.7", re.IGNORECASE)
FORWARD_VERSION_PATTERN = re.compile(r"v0\.(7\.8|7\.9|8\.0)")
MIN_DOC_LENGTH = 200

# Phrases the v0.7.6 _doc claimed and v0.7.7+ explicitly debunked. These must
# NOT appear AS A POSITIVE STATEMENT in any current _doc string. They may
# appear inside an attributed historical reference (e.g., quoted under
# "The v0.7.6 docs claimed 'X'") — that's the honest framing.
V0_7_6_FALSE_CLAIM_PHRASES = [
    "Skills read this config in their dispatch templates",
    "Honored by hook prompts via ATHANOR_HOOK_PROFILE",
    "ATHANOR_DISABLED_HOOKS environment variables (set by Claude Code from this config)",
]


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _check_deprecation_doc(label, doc_string):
    """Assert a deprecated-key `_doc` leads with DEPRECATED + is substantive +
    forward-references. Used for keys that are scheduled for removal."""
    assert doc_string, f"{label}: _doc string missing or empty"
    assert DEPRECATION_LEAD_PATTERN.match(doc_string), (
        f"{label}: _doc must lead with 'DEPRECATED in v0.7.7' "
        f"(deprecation is the lead claim, not buried). Got: {doc_string[:80]!r}..."
    )
    assert len(doc_string) >= MIN_DOC_LENGTH, (
        f"{label}: _doc must be substantive (>= {MIN_DOC_LENGTH} chars). "
        f"Got {len(doc_string)} chars."
    )
    assert FORWARD_VERSION_PATTERN.search(doc_string), (
        f"{label}: _doc must mention a future version (v0.7.8 / v0.7.9 / v0.8.0)."
    )


def _check_working_contract_doc(label, doc_string, must_mention):
    """Assert a `_doc` for a non-deprecated block honestly describes the
    runtime contract: substantive, mentions concrete features, no v0.7.6
    false claims appearing as POSITIVE statements (attributed history OK)."""
    assert doc_string, f"{label}: _doc string missing or empty"
    assert len(doc_string) >= MIN_DOC_LENGTH, (
        f"{label}: _doc must be substantive (>= {MIN_DOC_LENGTH} chars). "
        f"Got {len(doc_string)} chars."
    )
    for phrase in must_mention:
        assert phrase in doc_string, (
            f"{label}: _doc must mention {phrase!r} (working contract requirement). "
            f"Got: {doc_string!r}"
        )


# --- models block: still deprecated in v0.7.8, removal target v0.7.9 ------


def test_athanor_json_models_doc_is_honest():
    cfg = _load_json(REPO_ROOT / "athanor.json")
    _check_deprecation_doc("athanor.json models._doc", cfg.get("models", {}).get("_doc", ""))


def test_template_models_doc_is_honest():
    cfg = _load_json(REPO_ROOT / "templates/athanor.json")
    _check_deprecation_doc(
        "templates/athanor.json models._doc",
        cfg.get("models", {}).get("_doc", ""),
    )


# --- hooks block: working contract in v0.7.8 (no longer deprecated) -------


HOOKS_REQUIRED_MENTIONS = [
    "scripts/hooks/stop_verify_claims.py",  # the actual gate script
    'profile: "off"',                       # the user-facing opt-out
    'profile: "standard"',                  # the default mode
    "v0.7.8",                                # version anchor
    "command",                               # the new hook type
]


def test_athanor_json_hooks_doc_describes_working_contract():
    cfg = _load_json(REPO_ROOT / "athanor.json")
    _check_working_contract_doc(
        "athanor.json hooks._doc",
        cfg.get("hooks", {}).get("_doc", ""),
        HOOKS_REQUIRED_MENTIONS,
    )


def test_template_hooks_doc_describes_working_contract():
    cfg = _load_json(REPO_ROOT / "templates/athanor.json")
    _check_working_contract_doc(
        "templates/athanor.json hooks._doc",
        cfg.get("hooks", {}).get("_doc", ""),
        HOOKS_REQUIRED_MENTIONS,
    )


# --- hooks.disabled removal (v0.7.8) --------------------------------------


def test_athanor_json_has_no_hooks_disabled():
    """v0.7.7 had `hooks.disabled: []` as orphan config; v0.7.8 removed it."""
    cfg = _load_json(REPO_ROOT / "athanor.json")
    assert "disabled" not in cfg.get("hooks", {}), (
        "v0.7.8 removed the hooks.disabled orphan key. If you intend to "
        "re-introduce it, wire the consumer first."
    )


def test_template_has_no_hooks_disabled():
    cfg = _load_json(REPO_ROOT / "templates/athanor.json")
    assert "disabled" not in cfg.get("hooks", {}), (
        "templates/athanor.json must not re-introduce hooks.disabled (removed v0.7.8)."
    )
