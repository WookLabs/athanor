"""Regression tests for v0.11.3 Stop-hook input-layer fix.

The v0.7.8 implementation read `payload.get("last_assistant_message")` from
the Stop event payload. That field is the contract documented in early
internal notes, but the *actual* Claude Code Stop hook payload only
provides `transcript_path` — a JSONL file containing the conversation
history. The v0.7.8 implementation therefore silently fail-opened on every
real Stop event with `"last_assistant_message missing or non-string"`
stderr; the gate was non-functional from v0.7.8 through v0.10.3 inclusive.

v0.11.3 (this fix) introduces:
  - `_content_to_text(content)`: normalize Claude Code message-content
    (string OR list of typed blocks: `text`/`tool_use`/`thinking`) into a
    plain text string suitable for the v0.7.7 whitelist scanner.
  - `_read_last_assistant_message(payload)`: legacy-first early return on
    `last_assistant_message` (preserves 35+ existing tests); otherwise read
    `transcript_path` as JSONL, reverse-scan, skip sub-agent turns
    (`isSidechain == True`), return text of first main-session assistant entry.
  - `stop_hook_active` pass-through: do NOT short-circuit on the flag —
    re-entry semantics remain governed by `hook_state` circuit breaker.

These tests cover the input-layer parser only (Subtask 1). End-to-end
exit-2 behavior + payload-shape end-to-end scenarios are added in
Subtask 2 (this file is reused).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts/hooks/stop_verify_claims.py"
SCRIPTS_DIR = REPO_ROOT / "scripts" / "hooks"
HOOK_STATE_DIR = REPO_ROOT / ".athanor" / "sessions" / "active" / ".hook-state"

# Ensure scripts/hooks/ is importable for direct-function tests.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import stop_verify_claims  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_hook_state():
    """Match the convention in tests/test_regression_stop_hook_script.py."""
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)
    yield
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)


def _run(payload, *, cwd=None, env=None) -> tuple[int, str, str]:
    """Invoke the script with `payload` (dict or string) as stdin."""
    if isinstance(payload, dict):
        stdin_data = json.dumps(payload)
    else:
        stdin_data = payload
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin_data,
        text=True,
        capture_output=True,
        cwd=cwd or str(REPO_ROOT),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _write_jsonl(path: Path, entries: list[dict]) -> Path:
    """Write a list of dicts as JSONL (one JSON object per line). Returns path."""
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return path


def _main_assistant_entry(text: str, *, content_list: bool = True) -> dict:
    """Build a main-session assistant transcript entry with text content."""
    if content_list:
        content = [{"type": "text", "text": text}]
    else:
        content = text
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": content},
        "isSidechain": False,
    }


def _sidechain_assistant_entry(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        "isSidechain": True,
    }


# --- Criterion 1: legacy string path preserved (D7 — additive) ------------


def test_legacy_last_assistant_message_string_returns_string():
    """Legacy payload shape with `last_assistant_message` as a string still
    works — _read_last_assistant_message returns the string verbatim."""
    result = stop_verify_claims._read_last_assistant_message(
        {"last_assistant_message": "tests pass"}
    )
    assert result == "tests pass"


# --- Criterion 2: real CC path — single-line JSONL fixture -----------------


def test_transcript_jsonl_single_main_session_entry_returns_text(tmp_path):
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("tests pass")],
    )
    result = stop_verify_claims._read_last_assistant_message(
        {"transcript_path": str(jsonl)}
    )
    assert result == "tests pass"


# --- Criterion 3: nonexistent transcript path → None (no crash) -----------


def test_transcript_path_nonexistent_returns_none():
    result = stop_verify_claims._read_last_assistant_message(
        {"transcript_path": "/nonexistent/path.jsonl"}
    )
    assert result is None


# --- Criterion 4: tool_use blocks dropped → "" ----------------------------


def test_content_to_text_tool_use_only_returns_empty():
    result = stop_verify_claims._content_to_text(
        [{"type": "tool_use", "id": "x", "name": "y", "input": {}}]
    )
    assert result == ""


# --- Criterion 5: bare-string content passes through ----------------------


def test_content_to_text_string_passthrough():
    assert stop_verify_claims._content_to_text("plain string content") == "plain string content"


# --- Criterion 6: thinking blocks dropped, text blocks concatenated -------


def test_content_to_text_thinking_dropped_text_concatenated():
    blocks = [
        {"type": "thinking", "thinking": "tests pass"},
        {"type": "text", "text": "analyzing"},
    ]
    assert stop_verify_claims._content_to_text(blocks) == "analyzing"


# --- Criterion 7: partial-line race tolerance -----------------------------


def test_partial_json_last_line_returns_previous_line(tmp_path):
    """If the last line of the JSONL is mid-write (partial JSON), we tolerate
    it and return the previous valid main-session assistant entry."""
    transcript = tmp_path / "transcript.jsonl"
    with open(transcript, "w", encoding="utf-8") as f:
        f.write(json.dumps(_main_assistant_entry("tests pass")) + "\n")
        # Partial JSON (no newline, no closing brace) — Claude Code is
        # mid-write and we read the file at this instant.
        f.write('{"type":"assistant","message":')
    result = stop_verify_claims._read_last_assistant_message(
        {"transcript_path": str(transcript)}
    )
    assert result == "tests pass"


# --- Criterion 8: sidechain (sub-agent) entries skipped -------------------


def test_sidechain_entry_skipped_returns_main_session_entry(tmp_path):
    """Sub-agent assistant turns must not be treated as the model's last
    response (D2). Reverse-scan skips them and returns the most recent
    main-session assistant entry."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [
            _main_assistant_entry("tests pass"),
            _sidechain_assistant_entry("sub-agent transient output"),
        ],
    )
    result = stop_verify_claims._read_last_assistant_message(
        {"transcript_path": str(jsonl)}
    )
    assert result == "tests pass"


# --- Criterion 9: main() with real CC payload + material claim → exit 2 ---


def test_main_real_cc_payload_with_material_claim_exits_2(tmp_path):
    """End-to-end: a real CC payload (no `last_assistant_message`, only
    `transcript_path`) with a main-session material claim should now trigger
    the gate. Before v0.11.3 this fail-opened to exit 0."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("tests pass on my machine")],
    )
    rc, _, err = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    assert rc == 2, f"Expected exit 2 (gate engaged); got {rc}; stderr={err!r}"
    assert "verification-before-completion" in err.lower()


# --- Criterion 10: stop_hook_active flag is pass-through (D3) -------------


def test_main_stop_hook_active_true_does_not_short_circuit(tmp_path):
    """D3: stop_hook_active is pass-through. With `stop_hook_active: true`
    and a main-session material claim, the gate STILL engages — re-entry
    semantics are governed by hook_state circuit breaker, not by short-
    circuiting on this flag."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("tests pass")],
    )
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": True,
        }
    )
    assert rc == 2, f"Expected exit 2 (no short-circuit on stop_hook_active); got {rc}"


# --- Criterion 11 (SHOULD): circuit breaker after threshold consecutive blocks ---


def test_circuit_breaker_after_threshold_releases_gate(tmp_path):
    """After DEFAULT_STOP_LOOP_THRESHOLD (3) consecutive blocks on the same
    session, the existing hook_state circuit breaker releases the gate on
    the next invocation (exits 0 with stderr warning). This proves
    `stop_hook_active` pass-through is safe — circuit breaker, not the flag,
    governs re-entry loop termination."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("tests pass")],
    )
    payload = {
        "hook_event_name": "Stop",
        "session_id": "x",
        "transcript_path": str(jsonl),
        "stop_hook_active": True,
    }
    # First 3 invocations: gate engages (exit 2). Counter increments each.
    for attempt in range(3):
        rc, _, _ = _run(payload)
        assert rc == 2, (
            f"Attempt {attempt + 1} expected exit 2 (counter below threshold); got {rc}"
        )
    # 4th invocation: counter is at threshold (3) → circuit breaker opens.
    rc, _, err = _run(payload)
    assert rc == 0, (
        f"Expected exit 0 after circuit breaker opens; got {rc}; stderr={err!r}"
    )
    assert "circuit breaker" in err.lower() or "releasing" in err.lower()


# --- Criterion 14 (SHOULD, grep-based): no stale stderr substring in tests ---


def test_no_stale_last_assistant_message_missing_string_in_tests():
    """Phase 1 commit invariant: no tests assert against the v0.7.8 stderr
    string `last_assistant_message missing or non-string`. That stderr path
    is still emitted for the legacy-only payload but is no longer asserted
    in tests (we test the real CC path now)."""
    tests_dir = REPO_ROOT / "tests"
    offenders = []
    for p in tests_dir.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        if "last_assistant_message missing" in text or "missing or non-string" in text:
            # Allow this very file to mention the string in a docstring
            # explaining the rationale, but not as an assertion.
            if p.name == Path(__file__).name:
                # Substring may appear in this file's prose — only fail if
                # used inside a string literal asserted by a test.
                continue
            offenders.append(str(p.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"Stale v0.7.8 stderr substring found in: {offenders}"
    )


# =========================================================================
# Subtask 2: Phase 2 end-to-end scenarios (cases #1-#19 per plan.md).
#
# Subtask 1 already covered (helper-level + the most basic end-to-end paths)
# cases #1, #4, #5, #8, #14, #15, #16 (claim branch). Subtask 2 adds the
# remaining cases as full subprocess-level integration tests against the
# real CC payload shape so the wire-level contract is exercised
# end-to-end and not just at the parser-helper boundary.
# =========================================================================


def _tool_use_block(name: str = "Bash", input_: dict | None = None) -> dict:
    return {
        "type": "tool_use",
        "id": "toolu_abc",
        "name": name,
        "input": input_ or {"command": "ls"},
    }


# --- Case #2: tool_use-only main-session turn → exit 0 -------------------


def test_transcript_path_payload_with_tool_use_only_passes(tmp_path):
    """A main-session assistant turn whose content is purely tool_use
    (no text block) has no textual claim — `_content_to_text` returns "",
    downstream `if not last_msg.strip()` early-returns, exit 0."""
    entry = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [_tool_use_block()]},
        "isSidechain": False,
    }
    jsonl = _write_jsonl(tmp_path / "transcript.jsonl", [entry])
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    assert rc == 0, f"tool_use-only content should pass (exit 0); got {rc}"


# --- Case #3: mixed text + tool_use → gate trips on text claim -----------


def test_transcript_path_payload_mixed_text_and_tool_use_triggers_on_text_claim(
    tmp_path,
):
    """A main-session assistant turn with both a tool_use block AND a text
    block carrying a material claim must exit 2 — the text block is what
    matters; tool_use is dropped by `_content_to_text`."""
    entry = {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                _tool_use_block(),
                {"type": "text", "text": "build succeeded"},
            ],
        },
        "isSidechain": False,
    }
    jsonl = _write_jsonl(tmp_path / "transcript.jsonl", [entry])
    rc, _, err = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    assert rc == 2, f"mixed text+tool_use w/ claim should gate (exit 2); got {rc}"
    assert "verification-before-completion" in err.lower()


# --- Case #6: last assistant entry is the one that gates -----------------


def test_transcript_path_uses_last_assistant_entry_claim_last(tmp_path):
    """When the transcript contains multiple main-session assistant entries
    and only the LAST (most recent) has the material claim, the gate fires."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [
            _main_assistant_entry("just analyzing the code"),
            _main_assistant_entry("more analysis here"),
            _main_assistant_entry("tests pass"),
        ],
    )
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    assert rc == 2, f"last entry has claim — should gate; got {rc}"


def test_transcript_path_uses_last_assistant_entry_claim_first_only(tmp_path):
    """Inverse: when only the FIRST main-session assistant entry had a
    material claim but the most-recent entry is clean, the gate does NOT
    fire (reverse-scan returns the most-recent text-bearing entry)."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [
            _main_assistant_entry("tests pass"),
            _main_assistant_entry("now exploring an alternative approach"),
            _main_assistant_entry("reviewing the design"),
        ],
    )
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    assert rc == 0, f"only first entry had claim, last is clean; got {rc}"


# --- Case #7: string content (not list of blocks) ------------------------


def test_transcript_path_string_content_handled(tmp_path):
    """If `message.content` is a plain string (legacy / older shape) it is
    returned verbatim by `_content_to_text`; material claim still trips."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("tests pass", content_list=False)],
    )
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    assert rc == 2, f"string-content path should gate; got {rc}"


# --- Case #9: legacy `last_assistant_message` end-to-end still gates -----


def test_legacy_last_assistant_message_still_works():
    """Backwards-compat lock at the subprocess level: invoking with the
    legacy payload shape still trips the gate. Mirrors the helper-level
    test above but exercises the full main() flow."""
    rc, _, err = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "last_assistant_message": "tests pass",
        }
    )
    assert rc == 2, f"legacy shape should gate end-to-end; got {rc}; err={err!r}"


# --- Case #10: neither key present → fail-open ---------------------------


def test_neither_key_present_fails_open():
    """Payload with neither `last_assistant_message` nor `transcript_path`
    fail-opens to exit 0 with a stderr audit signal."""
    rc, _, err = _run({"hook_event_name": "Stop", "session_id": "x"})
    assert rc == 0, f"missing both keys should fail-open; got {rc}"
    assert "could not extract last assistant message" in err.lower() or "fail-open" in err.lower(), (
        f"expected fail-open audit signal in stderr; got: {err!r}"
    )


# --- Case #11: full real-CC payload shape (with claim) → exit 2 ----------


def test_real_cc_payload_shape_full_with_claim(tmp_path):
    """Lock the v0.11.3 fix against future Claude Code Stop event payload
    regressions: exact production shape `{session_id, transcript_path,
    stop_hook_active, hook_event_name}` with a claim in the fixture."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("tests pass")],
    )
    payload = {
        "session_id": "abc-def-123",
        "transcript_path": str(jsonl),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }
    rc, _, _ = _run(payload)
    assert rc == 2, f"production-shape payload with claim should gate; got {rc}"


# --- Case #12: full real-CC payload shape (without claim) → exit 0 -------


def test_real_cc_payload_shape_full_without_claim(tmp_path):
    """Inverse: production-shape payload, fixture has only analytical
    content → exit 0."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("Let me review the design choices here.")],
    )
    payload = {
        "session_id": "abc-def-123",
        "transcript_path": str(jsonl),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }
    rc, _, _ = _run(payload)
    assert rc == 0, f"production-shape payload without claim should pass; got {rc}"


# --- Case #13: v=2 sentinel inside a transcript text block → exit 0 ------


def test_v2_sentinel_in_transcript_text_block_exits_0(tmp_path):
    """The verification skill's v=2 sentinel emission, when carried inside
    a transcript text block (as it would be in production), still triggers
    the sentinel re-entry skip (exit 0). This locks the integration with
    `sentinel_helper.py` across the input-layer fix."""
    # Emit a fresh sentinel + body via the helper so nonce state is written.
    helper = REPO_ROOT / "scripts/hooks/sentinel_helper.py"
    body = "Verified pytest run: 81 passed, 0 failed."
    result = subprocess.run(
        [sys.executable, str(helper), "emit"],
        input=body, text=True, capture_output=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"sentinel_helper failed: {result.stderr}"
    sentinel = result.stdout.strip()
    full_text = sentinel + "\n" + body
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry(full_text)],
    )
    payload = {
        "session_id": "x",
        "transcript_path": str(jsonl),
        "stop_hook_active": False,
        "hook_event_name": "Stop",
    }
    rc, _, err = _run(payload)
    assert rc == 0, (
        f"v=2 sentinel-prefixed transcript text should exit 0; got {rc}; err={err!r}"
    )


# --- Case #16: stop_hook_active=true + clean content → exit 0 ------------


def test_main_stop_hook_active_true_with_clean_content_passes(tmp_path):
    """D3 corollary: the flag is pass-through, but it does NOT cause the
    gate to over-fire either. With `stop_hook_active: true` AND clean (no
    material claim) main-session content, the result is exit 0 — the gate
    only fires on actual claims. Confirms the parser does not branch on
    the flag in either direction."""
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("Thinking about the next step. No conclusions yet.")],
    )
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": True,
        }
    )
    assert rc == 0, (
        f"stop_hook_active=true with clean content should pass (no flag short-circuit, "
        f"no flag-induced over-fire); got {rc}"
    )


# --- Case #17: stale post-upgrade counter at zero still gates ------------


def test_post_upgrade_with_stale_zero_counter_still_gates(tmp_path):
    """Simulate a v0.11.2 → v0.11.3 upgrade where the project has a stale
    zero-valued circuit-breaker counter file (the v0.7.8 → v0.11.2 hook
    fail-opened, so the counter was never incremented). The first
    post-upgrade Stop event with a real-CC payload + claim MUST still gate
    (exit 2) — a zero counter does not interfere with first-trigger gating."""
    # Pre-seed an empty / zero counter via the hook_state module so the
    # path the running script will read is already materialized.
    from importlib import import_module
    hook_state = import_module("hook_state")
    # Reset to a clean zero state — the autouse fixture wiped the dir, so
    # we (re-)create it and write a zero counter.
    hook_state.reset_stop_counter("active")  # ensures state dir exists, counter at 0
    assert hook_state.read_stop_counter("active") == 0

    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry("tests pass")],
    )
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    assert rc == 2, f"stale-zero counter must not block first-trigger gate; got {rc}"


# --- Case #18: reverse-scan termination past sub-agent turns -------------


def test_transcript_path_reverse_scan_skips_past_subagent_to_main_assistant(
    tmp_path,
):
    """Locks the reverse-scan termination semantics: the parser must skip
    past sub-agent turns (`isSidechain: true`) AND tool_use-only sub-agent
    turns to land on the most-recent main-session assistant turn with a
    text claim.

    Fixture order (oldest → newest):
      1. main-assistant: clean
      2. main-assistant: "tests pass" (← reverse-scan should land here)
      3. sub-agent: "build succeeded" (skipped — isSidechain: true)
      4. sub-agent: tool_use only (skipped — isSidechain: true, no text)
    """
    sub_tool_only = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [_tool_use_block()]},
        "isSidechain": True,
    }
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [
            _main_assistant_entry("just analyzing"),
            _main_assistant_entry("tests pass"),
            _sidechain_assistant_entry("build succeeded"),
            sub_tool_only,
        ],
    )
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    assert rc == 2, (
        f"reverse-scan should skip 2 sub-agent entries and land on main-session "
        f"'tests pass' → exit 2; got {rc}"
    )


# --- Case #19 (xfail): code-fenced historical quote attribution ---------


@pytest.mark.xfail(
    reason=(
        "known: code-fenced historical quote can false-positive past v0.10.3 "
        "attribution layer when quoted on a separate line; documented residual "
        "for v0.11.4+"
    ),
    strict=False,
)
def test_transcript_path_code_fenced_historical_quote_not_false_positive(
    tmp_path,
):
    """v0.10.3 attribution detection should suppress code-fenced historical
    quotes. This test documents current behavior either way: if the gate
    trips (false positive), xfail records the residual; if it passes,
    xfail marks unexpected-success but `strict=False` allows that too."""
    fenced = (
        "Here's the v0.7.6 docs excerpt for context:\n"
        "```\n"
        "the v0.7.6 docs said \"tests pass\"\n"
        "```\n"
        "End of quote."
    )
    jsonl = _write_jsonl(
        tmp_path / "transcript.jsonl",
        [_main_assistant_entry(fenced)],
    )
    rc, _, _ = _run(
        {
            "hook_event_name": "Stop",
            "session_id": "x",
            "transcript_path": str(jsonl),
            "stop_hook_active": False,
        }
    )
    # The "expected" behavior is exit 0 (attribution suppression catches the
    # quote). If exit 2 happens, the xfail strict=False tolerates it.
    assert rc == 0, (
        f"code-fenced historical quote should be suppressed (exit 0); got {rc}"
    )
