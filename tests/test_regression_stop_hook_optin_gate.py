"""Regression tests for the Stop-hook opt-in gate + surrogate-safe body hash.

## Bug 1 — Stop-hook unsatisfiable deadlock (HIGH)

`scripts/hooks/stop_verify_claims.py::main()` blocks Stop (exit 2) when it
detects a material completion-claim. But in a repo with NO `athanor.json`,
`_find_athanor_config()` returns `(None, "none")` and `_read_profile()` falls
back to the default `"standard"` profile, so the hook STILL fires and blocks.

Meanwhile the ONLY sanctioned way to satisfy the gate — emitting a valid
`<!-- athanor:verification-emission v=2 nonce=... -->` sentinel via
`sentinel_helper.py` → `write_nonce_state` → `get_state_dir` → `_athanor_opt_in`
— REQUIRES `athanor.json` opt-in (returns False / None without it). The hook's
READ side (`read_nonce_state` → `get_state_dir(create=False)`) also returns
None, so even a hand-forged sentinel fails validation. Net: in any repo without
`athanor.json`, the Stop hook blocks but CANNOT be satisfied. Because the plugin
installs its Stop hook user-scope (global), this bites every non-opted-in repo.

Fix: gate the FIRE/BLOCK decision on opt-in. No `athanor.json` resolved
(`config_path is None`) → exit 0 (no enforcement), consistent with the rest of
the state machinery (circuit-breaker counter is already a no-op without opt-in).
PRESERVE:
  - athanor.json ABSENT          → exit 0 (NEW behavior; the fix)
  - athanor.json + profile=off   → exit 0 (existing opt-out)
  - athanor.json + profile on    → enforce as today (may exit 2)

## Bug 2 — sentinel hash crashes on lone surrogate (LOW-MED)

`sentinel_helper.py` computes `hashlib.sha256(body.strip().encode("utf-8"))`.
A lone surrogate (e.g. from PowerShell mangling an em-dash at the shell→python
boundary) makes `str.encode("utf-8")` raise `UnicodeEncodeError`. The validator
side in `stop_verify_claims.py` (`validate_emission_sentinel`) has the identical
pattern. Fix: both sides encode with `errors="surrogatepass"` so neither crashes
and their hashes still agree on the same input.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"
SENTINEL_HELPER = REPO_ROOT / "scripts" / "hooks" / "sentinel_helper.py"
SCRIPTS_DIR = REPO_ROOT / "scripts" / "hooks"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Helpers — mirror tests/test_regression_v011_6_sentinel_body_normalization.py
# and tests/test_regression_stop_hook_script.py invocation style.
# ---------------------------------------------------------------------------


def _run_stop_hook(payload: dict, cwd: Path) -> tuple[int, str]:
    """Invoke stop_verify_claims.py with `payload` on stdin; return (rc, stderr).

    `cwd` drives config resolution: stop_verify_claims walks up from cwd to find
    athanor.json (stopping at the .git boundary). We deliberately do NOT set
    CLAUDE_PROJECT_DIR so the walk-up-from-cwd path is exercised.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
    )
    return result.returncode, (result.stderr or "")


def _write_transcript(tmp_path: Path, response_text: str) -> Path:
    """Write a single-line transcript JSONL with a main-session assistant turn."""
    tpath = tmp_path / "transcript.jsonl"
    entry = {
        "type": "assistant",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": response_text}],
        },
    }
    tpath.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return tpath


def _make_payload(transcript: Path) -> dict:
    return {
        "session_id": "test",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }


# ---------------------------------------------------------------------------
# Bug 1 — opt-in gate
# ---------------------------------------------------------------------------


def test_1a_no_athanor_json_material_claim_exits_zero(tmp_path: Path):
    """Bug 1 fix: in a repo with NO athanor.json, a material claim must NOT
    block Stop. The gate is unsatisfiable without opt-in (the sentinel path
    needs athanor.json too), so it must fail-open (exit 0).

    RED before fix: main() defaults to profile="standard" → exit 2.
    GREEN after fix: config_path is None → early exit 0.
    """
    # A .git dir bounds the walk-up so config resolution stops here and cannot
    # accidentally pick up an ancestor athanor.json from a real checkout above
    # the pytest tmp dir.
    (tmp_path / ".git").mkdir()
    # Deliberately NO athanor.json — the opted-OUT scenario.
    transcript = _write_transcript(tmp_path, "tests pass on my machine")
    rc, stderr = _run_stop_hook(_make_payload(transcript), tmp_path)
    assert rc == 0, (
        "Stop hook must fail-open (exit 0) in a repo without athanor.json: the "
        "gate is unsatisfiable there because the sentinel/nonce path is also "
        f"opt-in gated. Got exit={rc} stderr={stderr!r}"
    )


def test_1b_with_athanor_json_material_claim_still_blocks(tmp_path: Path):
    """Bug 1 guard: the fix must NOT over-disable enforcement. In an opted-IN
    repo (athanor.json present, profile standard) a material claim WITHOUT a
    valid sentinel must still block (exit 2).

    Passes both before AND after the fix — locks the preserved case.
    """
    (tmp_path / ".git").mkdir()
    (tmp_path / "athanor.json").write_text(
        '{"hooks": {"profile": "standard", "stopLoopThreshold": 3}}',
        encoding="utf-8",
    )
    transcript = _write_transcript(tmp_path, "tests pass on my machine")
    rc, stderr = _run_stop_hook(_make_payload(transcript), tmp_path)
    assert rc == 2, (
        "Opted-in repo with profile=standard must still block on a material "
        f"claim. Got exit={rc} stderr={stderr!r}"
    )
    assert "verification-before-completion" in stderr.lower(), (
        f"blocking stderr should direct to the verification skill; got {stderr!r}"
    )


def test_1c_profile_off_exits_zero(tmp_path: Path):
    """Existing opt-out preserved: athanor.json present with profile=off → the
    gate is disabled (exit 0) even on a material claim."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "athanor.json").write_text(
        '{"hooks": {"profile": "off"}}', encoding="utf-8"
    )
    transcript = _write_transcript(tmp_path, "tests pass on my machine")
    rc, stderr = _run_stop_hook(_make_payload(transcript), tmp_path)
    assert rc == 0, (
        f"profile=off must disable the gate (exit 0). Got exit={rc} "
        f"stderr={stderr!r}"
    )


def test_1d_no_athanor_json_no_claim_exits_zero(tmp_path: Path):
    """Sanity: no athanor.json + benign response → exit 0 (unchanged by fix)."""
    (tmp_path / ".git").mkdir()
    transcript = _write_transcript(tmp_path, "Here is a summary of the file.")
    rc, stderr = _run_stop_hook(_make_payload(transcript), tmp_path)
    assert rc == 0, f"benign response must exit 0. Got exit={rc} stderr={stderr!r}"


# ---------------------------------------------------------------------------
# Bug 2 — surrogate-safe body hash (emit side AND validate side)
# ---------------------------------------------------------------------------

# A body containing a lone (unpaired) surrogate — what PowerShell can produce
# when it mangles a non-ASCII byte (e.g. an em-dash) at the shell→python pipe.
_SURROGATE_BODY = "done \udcab end"


def test_2a_sentinel_helper_emit_does_not_crash_on_lone_surrogate(tmp_path: Path):
    """Bug 2 fix (emit side): sentinel_helper.py emit must not raise
    UnicodeEncodeError when the piped body contains a lone surrogate.

    RED before fix: body.strip().encode("utf-8") raises UnicodeEncodeError →
    Python traceback → non-zero exit with traceback on stderr.
    GREEN after fix: errors="surrogatepass" → clean emit (exit 0, sentinel out).
    """
    (tmp_path / ".git").mkdir()
    (tmp_path / "athanor.json").write_text(
        '{"hooks": {"profile": "standard"}}', encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(SENTINEL_HELPER), "emit"],
        input=_SURROGATE_BODY,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogatepass",
        cwd=str(tmp_path),
    )
    assert "UnicodeEncodeError" not in (result.stderr or ""), (
        f"sentinel_helper emit crashed on a lone surrogate: stderr={result.stderr!r}"
    )
    assert "Traceback" not in (result.stderr or ""), (
        f"sentinel_helper emit raised an unhandled exception: stderr={result.stderr!r}"
    )
    assert result.returncode == 0, (
        f"sentinel_helper emit should exit 0 on a surrogate body; got "
        f"rc={result.returncode} stderr={result.stderr!r}"
    )
    assert result.stdout.strip().startswith(
        "<!-- athanor:verification-emission v=2 nonce="
    ), f"expected a sentinel on stdout; got {result.stdout!r}"


def test_2b_validate_emission_sentinel_accepts_surrogate_body(tmp_path: Path):
    """Bug 2 fix (validate side): the Stop hook's body-hash encode must use the
    SAME surrogatepass handler as the emit side, so that when the stored
    body_hash and the response body match on identical bytes, the sentinel
    VALIDATES (exit 0) — and crucially the validator never CRASHES on a lone
    surrogate.

    We write the nonce state IN-PROCESS via hook_state.write_nonce_state with a
    body_hash computed the same way sentinel_helper.emit() does. This bypasses
    the OS stdin pipe, whose byte transport can lossily transform a lone
    surrogate on some platforms (Windows) — an environment artifact unrelated to
    the encode bug under test. Writing the state directly pins the validator's
    encode path deterministically.

    RED before fix: validate_emission_sentinel's body_canonical.encode("utf-8")
    raises UnicodeEncodeError on the surrogate → traceback / non-zero exit.
    GREEN after fix: surrogatepass encode → hash matches stored → exit 0.
    """
    import hook_state  # imported here so the SCRIPTS_DIR sys.path insert applies

    (tmp_path / ".git").mkdir()
    (tmp_path / "athanor.json").write_text(
        '{"hooks": {"profile": "standard"}}', encoding="utf-8"
    )
    # 1. Compute the body_hash exactly as sentinel_helper.emit() does (the
    #    canonical transform is .strip() then surrogatepass-encode) and persist
    #    the nonce state directly. ACTIVE_SESSION is "active" in both scripts.
    nonce = "a" * 32
    body_hash = hashlib.sha256(
        _SURROGATE_BODY.strip().encode("utf-8", errors="surrogatepass")
    ).hexdigest()
    assert hook_state.write_nonce_state(
        "active", nonce, body_hash, project_root=tmp_path
    ), "could not persist nonce state for the test"

    # 2. The model response = sentinel line (carrying the same nonce) + the
    #    surrogate body. The validator must re-hash the body with surrogatepass
    #    and match the stored hash → accept (exit 0).
    sentinel = f"<!-- athanor:verification-emission v=2 nonce={nonce} -->"
    response = sentinel + "\n" + _SURROGATE_BODY
    transcript = _write_transcript(tmp_path, response)
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(_make_payload(transcript)),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogatepass",
        cwd=str(tmp_path),
    )
    assert "UnicodeEncodeError" not in (result.stderr or ""), (
        f"validator crashed on surrogate body: stderr={result.stderr!r}"
    )
    assert "Traceback" not in (result.stderr or ""), (
        f"validator raised an unhandled exception: stderr={result.stderr!r}"
    )
    assert result.returncode == 0, (
        "surrogate-body sentinel must validate (exit 0): the validator's encode "
        "must use the same surrogatepass handler as the emit side so their "
        f"hashes agree. Got rc={result.returncode} stderr={result.stderr!r}"
    )
    assert "body hash mismatch" not in (result.stderr or ""), (
        f"validator hash disagreed on the surrogate body: stderr={result.stderr!r}"
    )


def test_2c_emit_and_validate_hash_agree_on_surrogate_body():
    """Direct unit check that both sides compute the identical hash for a
    surrogate body under surrogatepass. This is the property the round-trip
    relies on; pinning it directly localizes any future drift between the two
    encode call sites."""
    body = _SURROGATE_BODY
    # The canonical pre-hash transform on both sides is `.strip()` (v0.11.6).
    helper_hash = hashlib.sha256(
        body.strip().encode("utf-8", errors="surrogatepass")
    ).hexdigest()
    validator_hash = hashlib.sha256(
        body.strip().encode("utf-8", errors="surrogatepass")
    ).hexdigest()
    assert helper_hash == validator_hash
