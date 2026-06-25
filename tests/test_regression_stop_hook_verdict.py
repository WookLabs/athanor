"""Regression — Stop-hook terminal `VERDICT: FAIL|PARTIAL` self-contradiction block.

Gap under lock (the T1-4 anchor gap)
------------------------------------
`scripts/hooks/stop_verify_claims.py` matched a **whitelist of phrases** only —
there was no structured, greppable *positive* evidence anchor and no rule that a
material completion claim paired with its OWN self-reported failure verdict is a
self-contradiction. Phase 1 added the producer-side `### Check → Command →
Output → VERDICT: PASS|FAIL|PARTIAL` convention to
`skills/verification-before-completion/SKILL.md`; this module locks the
consumer-side hook rule (the keystone, Key Decision 2):

  * A material claim co-occurring with a **terminal `VERDICT: FAIL` or
    `VERDICT: PARTIAL`** is a self-contradiction → **block (exit 2)**.
  * **`VERDICT: PASS` MUST NOT become a release path** — the v=2 nonce sentinel
    stays the SOLE sanctioned exit-0 (the forgery-hole guard, Risk R1). A
    `VERDICT: PASS` with NO sentinel routes through the existing material-claim
    gate exactly as today; it neither auto-releases nor adds a new block.

The new branch sits INSIDE the existing gated region — AFTER `is_material_claim`
is True and BEFORE the circuit-breaker — so it inherits the `profile=off` opt-out
(line ~1096) and the v=2 sentinel release (line ~1127): it can never bypass the
opt-out and never adds a new exit-0 path (Risk R3). It reuses
`_match_is_suppressed` so a `VERDICT: FAIL` inside a quoted/attributed/historical
line does not false-block (Risk R4).

These tests are RED before Phase 2 (no `_terminal_verdict` helper / branch
exists; a claim + `VERDICT: FAIL` exits 2 only by the *coincidental* presence of
a whitelist phrase, NOT by the VERDICT rule — the no-whitelist-phrase + VERDICT
cases below pin the new behavior and fail until the branch lands).

Invocation style mirrors tests/test_regression_stop_hook_script.py — subprocess
the script with a synthetic `last_assistant_message` stdin payload (the
legacy-first parser path), `cwd` driving config/profile resolution, and the
`_clean_hook_state` fixture preventing counter/nonce leakage across tests.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"
HOOK_STATE_DIR = REPO_ROOT / ".athanor" / "sessions" / "active" / ".hook-state"


@pytest.fixture(autouse=True)
def _clean_hook_state():
    """Reset stop-hook state before/after each test to prevent circuit-breaker
    counter or nonce leakage across tests when they run against REPO_ROOT cwd
    (mirrors tests/test_regression_stop_hook_script.py)."""
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)
    yield
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)


def _run(message: str, *, cwd: str | None = None, env=None) -> tuple[int, str, str]:
    """Invoke the script with a legacy-shape `last_assistant_message` payload.

    Returns (returncode, stdout, stderr). `cwd` drives config/profile
    resolution (walk-up to athanor.json, stopping at the .git boundary).
    """
    stdin_data = json.dumps({"last_assistant_message": message})
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin_data,
        text=True,
        capture_output=True,
        cwd=cwd or str(REPO_ROOT),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _opted_in_project(tmp_path: Path, profile: str = "standard") -> str:
    """Create a tmp project dir with `.git` + athanor.json(profile) and return
    its path string for use as `cwd`. The `.git` dir bounds config walk-up so a
    real ancestor athanor.json above the pytest tmp dir cannot leak in.
    """
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".git").mkdir()
    (proj / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": profile, "stopLoopThreshold": 3}}),
        encoding="utf-8",
    )
    return str(proj)


# ---------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------
def test_script_file_exists():
    assert SCRIPT.is_file(), f"Script not at {SCRIPT}"


# ---------------------------------------------------------------------------
# 1. Material claim + terminal `VERDICT: FAIL` → exit 2 (the keystone block).
#    Standard profile, no sentinel, breaker below threshold (fresh tmp dir).
#    A whitelist phrase ("all done" / "implementation complete") is present so
#    the response ENTERS the gated region; the block is attributed to the
#    VERDICT rule by asserting the VERDICT-naming stderr — the generic whitelist
#    block emits a different message, so these are genuinely RED until the
#    branch lands (the exit-2 alone would pass coincidentally on the whitelist).
# ---------------------------------------------------------------------------
def test_claim_plus_terminal_verdict_fail_blocks(tmp_path):
    cwd = _opted_in_project(tmp_path)
    msg = (
        "All done implementing the feature.\n"
        "### Check: regression suite\n"
        "Command: uv run python -m pytest -q\n"
        "Output: 3 failed, 80 passed\n"
        "VERDICT: FAIL\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 2, (
        f"material claim + terminal VERDICT: FAIL must block (exit 2); got {rc}, "
        f"stderr={err!r}"
    )
    low = err.lower()
    assert "verdict" in low, (
        "the block must be attributed to the VERDICT rule (stderr names the "
        "terminal VERDICT contradiction), not only the coincidental whitelist "
        f"phrase; got: {err!r}"
    )


def test_claim_plus_terminal_verdict_partial_blocks(tmp_path):
    cwd = _opted_in_project(tmp_path)
    msg = (
        "Implementation complete.\n"
        "### Check: integration coverage\n"
        "Command: uv run python -m pytest tests/integration -q\n"
        "Output: 1 failed, 12 passed (one flaky path unresolved)\n"
        "VERDICT: PARTIAL\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 2, (
        f"material claim + terminal VERDICT: PARTIAL must block (exit 2); got {rc}, "
        f"stderr={err!r}"
    )
    low = err.lower()
    assert "verdict" in low, (
        "the PARTIAL block must be attributed to the VERDICT rule (stderr names "
        f"the contradiction), not only the whitelist phrase; got: {err!r}"
    )


def test_block_stderr_names_the_contradiction(tmp_path):
    """The blocking stderr must name the self-contradiction (verdict-paired),
    so the model gets an actionable signal, not just the generic whitelist text.
    """
    cwd = _opted_in_project(tmp_path)
    msg = (
        "All done.\n"
        "VERDICT: FAIL\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 2, f"expected exit 2; got {rc}, stderr={err!r}"
    low = err.lower()
    assert "verdict" in low and ("fail" in low or "partial" in low), (
        "blocking stderr must name the terminal VERDICT: FAIL/PARTIAL "
        f"contradiction; got: {err!r}"
    )


# ---------------------------------------------------------------------------
# 2. THE FORGERY-HOLE GUARD (Key Decision 2 / Risk R1):
#    Material claim + terminal `VERDICT: PASS` + NO sentinel → does NOT
#    auto-release. It routes through the existing material-claim gate exactly as
#    today: the claim phrase ("tests pass") still trips the whitelist → exit 2.
#    PASS adds NO new exit-0 path.
# ---------------------------------------------------------------------------
def test_claim_plus_verdict_pass_no_sentinel_does_not_release(tmp_path):
    cwd = _opted_in_project(tmp_path)
    msg = (
        "tests pass and the build is green.\n"
        "### Check: full suite\n"
        "Command: uv run python -m pytest -q\n"
        "Output: 0 failed, 83 passed\n"
        "VERDICT: PASS\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 2, (
        "VERDICT: PASS must NOT become a release path — a material claim with a "
        "bare PASS token and no v=2 sentinel must still route through the "
        f"existing material-claim gate (exit 2). got {rc}, stderr={err!r}"
    )
    # The v=2 sentinel must remain the SOLE sanctioned exit-0; PASS is not it.
    assert "verification-before-completion" in err.lower(), (
        "PASS-without-sentinel must fall through to the standard material-claim "
        f"block directing to the verification skill; got: {err!r}"
    )


def test_verdict_pass_with_no_material_claim_still_exits_0(tmp_path):
    """A terminal VERDICT: PASS with NO material claim does NOTHING new: the
    response has nothing to gate, so it exits 0 (PASS adds no block, no
    release — it is inert in the hook)."""
    cwd = _opted_in_project(tmp_path)
    msg = (
        "Here is my analysis of the architecture trade-offs.\n"
        "VERDICT: PASS\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 0, (
        "VERDICT: PASS with no material claim must exit 0 (inert); the hook only "
        f"gates material claims. got {rc}, stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# 3. profile=off ALWAYS wins (opt-out never overridden by the VERDICT branch).
#    The branch sits AFTER the profile=off early return, so a claim +
#    VERDICT: FAIL under profile=off must STILL exit 0.
# ---------------------------------------------------------------------------
def test_profile_off_claim_plus_verdict_fail_still_exits_0(tmp_path):
    cwd = _opted_in_project(tmp_path, profile="off")
    msg = (
        "All done.\n"
        "VERDICT: FAIL\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 0, (
        "profile=off must disable the gate entirely — even a material claim "
        "paired with terminal VERDICT: FAIL must exit 0 (the VERDICT branch sits "
        f"AFTER the profile=off early return). got {rc}, stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# 4. NO material claim + terminal `VERDICT: FAIL` → exit 0.
#    The branch fires ONLY when a material claim is also present (it lives after
#    is_material_claim True). A lone honest failure report (no completion claim)
#    must not block — that would punish honesty.
# ---------------------------------------------------------------------------
def test_verdict_fail_without_material_claim_exits_0(tmp_path):
    cwd = _opted_in_project(tmp_path)
    msg = (
        "Investigating the failure; I have not finished yet.\n"
        "### Check: reproduce the bug\n"
        "Command: uv run python -m pytest tests/test_x.py -q\n"
        "Output: 1 failed\n"
        "VERDICT: FAIL\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 0, (
        "a terminal VERDICT: FAIL with NO material completion claim must exit 0 "
        "(the branch only fires when a material claim co-occurs); honest "
        f"in-progress failure reporting must not be punished. got {rc}, stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# 5. Homoglyph / NFKC-folded VERDICT still matched (via _normalize_for_match).
#    A fullwidth "ＶＥＲＤＩＣＴ" or Cyrillic-substituted token must normalize to
#    "verdict" so the contradiction is still caught.
# ---------------------------------------------------------------------------
def test_homoglyph_verdict_fail_still_blocks(tmp_path):
    cwd = _opted_in_project(tmp_path)
    # Fullwidth Latin "ＶＥＲＤＩＣＴ" (NFKC → "VERDICT") + fullwidth "ＦＡＩＬ".
    fullwidth_verdict = "ＶＥＲＤＩＣＴ"  # ＶＥＲＤＩＣＴ
    fullwidth_fail = "ＦＡＩＬ"  # ＦＡＩＬ
    msg = (
        "All done.\n"
        f"{fullwidth_verdict}: {fullwidth_fail}\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 2, (
        "a homoglyph/NFKC-folded VERDICT: FAIL must still be matched (the helper "
        "runs the message through _normalize_for_match before matching), so the "
        f"contradiction is caught. got {rc}, stderr={err!r}"
    )
    assert "verdict" in err.lower(), (
        "the homoglyph block must be attributed to the VERDICT rule (proves the "
        "match survived normalization), not only the whitelist phrase; got: "
        f"{err!r}"
    )


# ---------------------------------------------------------------------------
# 6. VERDICT: FAIL inside a quoted / attributed / historical line does NOT
#    false-block (reuse _match_is_suppressed).
# ---------------------------------------------------------------------------
def test_attributed_verdict_fail_does_not_false_block(tmp_path):
    """A VERDICT: FAIL that is reported as something someone *said* (attribution
    context) must be suppressed via _match_is_suppressed, so an unrelated
    material claim in the same response is not falsely blocked by it.

    The whitelist still applies independently; to isolate the VERDICT-suppression
    behavior the message carries NO whitelist phrase — only the attributed
    VERDICT. It must exit 0 (the attributed VERDICT is suppressed, and there is
    no other claim).
    """
    cwd = _opted_in_project(tmp_path)
    # Same-line attribution: the reviewer SAID "VERDICT: FAIL" historically.
    msg = (
        "The previous reviewer said \"VERDICT: FAIL\" about the old branch, "
        "but that was last week.\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 0, (
        "a VERDICT: FAIL inside an attributed/quoted historical line must be "
        "suppressed (reuse _match_is_suppressed) and must not block an otherwise "
        f"claim-free response. got {rc}, stderr={err!r}"
    )


def test_conditional_verdict_fail_does_not_false_block(tmp_path):
    """A VERDICT: FAIL inside a conditional clause ('if ... VERDICT: FAIL') is
    speculative, not a self-report — suppressed via the conditional-context
    machinery reused by _match_is_suppressed."""
    cwd = _opted_in_project(tmp_path)
    msg = (
        "If the suite regresses the gate should print VERDICT: FAIL here.\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 0, (
        "a VERDICT: FAIL inside a conditional clause must be suppressed (reuse "
        f"the conditional-context check); got {rc}, stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# 7. LAST terminal VERDICT wins. A non-terminal PASS earlier followed by a
#    terminal FAIL → the FAIL governs → block. (_terminal_verdict returns the
#    LAST match.)
# ---------------------------------------------------------------------------
def test_last_verdict_governs_pass_then_fail_blocks(tmp_path):
    cwd = _opted_in_project(tmp_path)
    msg = (
        "All done.\n"
        "### Check: unit tests\n"
        "VERDICT: PASS\n"
        "### Check: integration tests\n"
        "VERDICT: FAIL\n"
    )
    rc, _, err = _run(msg, cwd=cwd)
    assert rc == 2, (
        "when multiple VERDICT lines exist, the LAST (terminal) one governs — "
        "a trailing VERDICT: FAIL after an earlier PASS must block (exit 2). "
        f"got {rc}, stderr={err!r}"
    )
    assert "verdict" in err.lower(), (
        "the block must come from the LAST-VERDICT rule (stderr names the "
        f"contradiction), proving _terminal_verdict returns the last match; got: {err!r}"
    )
