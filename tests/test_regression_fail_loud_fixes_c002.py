"""Regression locks for the C002-G2 fail-loud fixes (athanor /athanor:assess
Priority #2 + #3 — "fail-loud over silent fallback" violations the package
preaches but locally broke).

BUG 1 — bare-path sentinel invocation (Stop-hook invariant #4 degradation):
  `skills/verification-before-completion/SKILL.md` invoked the sentinel helper
  by BARE relative path (`python3 scripts/hooks/sentinel_helper.py emit`). In an
  opted-in USER project (cwd != plugin root, the common case) that path does not
  resolve, the nonce is never written, and the Stop hook re-enters (churn). The
  v0.11.4 convention anchors plugin-root scripts via `${CLAUDE_PLUGIN_ROOT}`.
  Fix: the runnable invocation is now `${CLAUDE_PLUGIN_ROOT}`-anchored.
  `skills/lfg-goal/references/receipt-validator.md` carried the same prose
  invocation path and was anchored to match.

BUG 2 — missing `*)` default arm (silent fallback):
  `skills/plan/references/codex-availability.md` had TWO
  `case "$CODEX_FALLBACK" in` blocks with arms self-critic/skip/fail but NO
  `*)` default. A schema-invalid `codex.fallback` value left `review_strategy`
  UNSET -> silent fallback downstream. Fix: both case blocks now carry a
  fail-loud `*)` arm that aborts (exit 1).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFY_SKILL = REPO_ROOT / "skills" / "verification-before-completion" / "SKILL.md"
RECEIPT_VALIDATOR = REPO_ROOT / "skills" / "lfg-goal" / "references" / "receipt-validator.md"
CODEX_AVAIL = REPO_ROOT / "skills" / "plan" / "references" / "codex-availability.md"

ANCHORED = "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/sentinel_helper.py"


# ---- BUG 1: sentinel invocation is plugin-root-anchored ----

def test_verification_skill_sentinel_is_plugin_root_anchored():
    content = VERIFY_SKILL.read_text(encoding="utf-8")
    assert ANCHORED in content, (
        "verification-before-completion/SKILL.md must invoke the sentinel helper "
        f"via the plugin-root-anchored path {ANCHORED!r} (v0.11.4 convention) so "
        "it resolves in an opted-in USER project where cwd != plugin root."
    )


def test_verification_skill_has_no_bare_sentinel_invocation():
    """The runnable `python3 ... sentinel_helper.py emit` line must not be a
    bare relative path (which fails to resolve outside the plugin root)."""
    content = VERIFY_SKILL.read_text(encoding="utf-8")
    # A bare invocation = `python3` immediately followed by an unanchored
    # `scripts/hooks/sentinel_helper.py` (no ${CLAUDE_PLUGIN_ROOT}/ and no
    # leading quote-with-var). Match the runnable form specifically.
    bare = re.search(
        r"python3?\s+(?:\"?)scripts/hooks/sentinel_helper\.py", content
    )
    assert bare is None, (
        "verification skill still contains a BARE `python3 scripts/hooks/"
        "sentinel_helper.py` invocation — it must be ${CLAUDE_PLUGIN_ROOT}-"
        f"anchored. Offending span: {bare.group(0) if bare else ''!r}"
    )


def test_receipt_validator_sentinel_reference_is_anchored():
    """receipt-validator.md prose names the same invocation path; it was
    anchored for correctness parity."""
    content = RECEIPT_VALIDATOR.read_text(encoding="utf-8")
    assert ANCHORED in content, (
        "lfg-goal/references/receipt-validator.md must reference the sentinel "
        f"helper via the anchored path {ANCHORED!r} to match the v0.11.4 "
        "convention used elsewhere."
    )
    bare = re.search(r"(?<!\{)scripts/hooks/sentinel_helper\.py", content)
    # The only allowed occurrence is the anchored one (preceded by
    # ${CLAUDE_PLUGIN_ROOT}/). Verify no bare occurrence remains.
    # Re-scan excluding the anchored substring.
    stripped = content.replace(ANCHORED, "")
    assert "scripts/hooks/sentinel_helper.py" not in stripped, (
        "receipt-validator.md still contains a bare sentinel_helper.py path "
        "outside the ${CLAUDE_PLUGIN_ROOT} anchor."
    )


# ---- BUG 2: both codex.fallback case blocks have a fail-loud default arm ----

def _codex_case_blocks(content: str) -> list[str]:
    """Return the body text of each `case "$CODEX_FALLBACK" in ... esac` block."""
    return re.findall(
        r'case\s+"\$CODEX_FALLBACK"\s+in(.*?)esac',
        content,
        re.DOTALL,
    )


def test_codex_availability_has_two_case_blocks():
    content = CODEX_AVAIL.read_text(encoding="utf-8")
    blocks = _codex_case_blocks(content)
    assert len(blocks) == 2, (
        f"Expected exactly 2 `case \"$CODEX_FALLBACK\" in` blocks in "
        f"codex-availability.md; found {len(blocks)}."
    )


def test_each_codex_case_block_has_fail_loud_default_arm():
    """Per-block check: every case block must carry a `*)` default arm that
    fail-loud aborts (exit 1) — no silent fallthrough leaving review_strategy
    unset on a schema-invalid codex.fallback value."""
    content = CODEX_AVAIL.read_text(encoding="utf-8")
    blocks = _codex_case_blocks(content)
    assert blocks, "no `case \"$CODEX_FALLBACK\" in` blocks found"
    for i, block in enumerate(blocks, start=1):
        assert "*)" in block, (
            f"case block #{i} is missing a `*)` default arm — a schema-invalid "
            f"codex.fallback value would leave review_strategy UNSET (silent "
            f"fallback). Block body:\n{block}"
        )
        # The default arm must fail loud (exit 1), not silently assign.
        default_arm = block.split("*)", 1)[1]
        assert "exit 1" in default_arm, (
            f"case block #{i} `*)` default arm must fail loud with `exit 1`, "
            f"not a silent assignment. Arm:\n{default_arm}"
        )


def test_codex_default_arm_count_at_least_two():
    """Robust belt-and-suspenders: at least two `*)` arms across both blocks."""
    content = CODEX_AVAIL.read_text(encoding="utf-8")
    blocks = _codex_case_blocks(content)
    total_defaults = sum(b.count("*)") for b in blocks)
    assert total_defaults >= 2, (
        f"Expected >=2 `*)` default arms across the codex.fallback case blocks; "
        f"found {total_defaults}."
    )
