"""Regression test for the v0.7.7 _doc honesty contract.

The v0.7.7 release marks `models` and `hooks.profile`/`hooks.disabled` as
deprecated in schema. This test pins the SAME honest framing in the
user-visible `_doc` strings — schema metadata is not user-facing, but
`_doc` strings ARE read at editor hover and /athanor:setup output time.

Caught by PR #10 dual review (Codex Reviewer B): v0.7.7 CHANGELOG named
the v0.7.6 false claims yet `_doc` strings still made those claims
verbatim. Fixed in commit 57a9a09. This test prevents silent regression.

Scope: athanor.json + templates/athanor.json. The skills/setup/SKILL.md
embedded fallback uses an intentionally older compact shape (no `_doc`
strings — see Wave 1A worker note in d74d839); it's not in scope for
this test.

What this test enforces (positive assertions):
  1. Each deprecated block's `_doc` STARTS with "DEPRECATED in v0.7.7"
     (so the deprecation is the lead claim, not buried after legacy text).
  2. Each `_doc` is substantive (>= 200 chars) so the deprecation comes
     with an explanation of why and what to do instead.
  3. Each `_doc` mentions a forward-version (v0.7.8 OR v0.7.9 OR v0.8.0)
     where the key will be removed or replaced — gives users a horizon.

What it does NOT enforce: that the old false-claim phrases appear
nowhere. The new `_doc` strings QUOTE the v0.7.6 claim verbatim to
refute it ("The v0.7.6 documentation claimed 'X' but every skill
hardcodes..."), which is exactly the honest framing we want. A naive
phrase blocklist would false-positive on this attributed reference.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEPRECATION_LEAD_PATTERN = re.compile(r"^DEPRECATED in v0\.7\.7", re.IGNORECASE)
FORWARD_VERSION_PATTERN = re.compile(r"v0\.(7\.8|7\.9|8\.0)")
MIN_DOC_LENGTH = 200


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _check_doc_honesty(label, doc_string):
    """Assert a _doc string leads with DEPRECATED, is substantive, and forward-references."""
    assert doc_string, f"{label}: _doc string missing or empty"
    assert DEPRECATION_LEAD_PATTERN.match(doc_string), (
        f"{label}: _doc must lead with 'DEPRECATED in v0.7.7' "
        f"(deprecation is the lead claim, not buried). Got: {doc_string[:80]!r}..."
    )
    assert len(doc_string) >= MIN_DOC_LENGTH, (
        f"{label}: _doc must be substantive (>= {MIN_DOC_LENGTH} chars explaining why + what to do). "
        f"Got {len(doc_string)} chars."
    )
    assert FORWARD_VERSION_PATTERN.search(doc_string), (
        f"{label}: _doc must mention a future version (v0.7.8 / v0.7.9 / v0.8.0) "
        f"where the key will be removed or replaced — gives users a horizon."
    )


def test_athanor_json_models_doc_is_honest():
    cfg = _load_json(REPO_ROOT / "athanor.json")
    _check_doc_honesty("athanor.json models._doc", cfg.get("models", {}).get("_doc", ""))


def test_athanor_json_hooks_doc_is_honest():
    cfg = _load_json(REPO_ROOT / "athanor.json")
    _check_doc_honesty("athanor.json hooks._doc", cfg.get("hooks", {}).get("_doc", ""))


def test_template_models_doc_is_honest():
    cfg = _load_json(REPO_ROOT / "templates/athanor.json")
    _check_doc_honesty("templates/athanor.json models._doc", cfg.get("models", {}).get("_doc", ""))


def test_template_hooks_doc_is_honest():
    cfg = _load_json(REPO_ROOT / "templates/athanor.json")
    _check_doc_honesty("templates/athanor.json hooks._doc", cfg.get("hooks", {}).get("_doc", ""))
