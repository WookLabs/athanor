#!/usr/bin/env python3
"""
Athanor v0.7.8 Stop-hook command script.

Registered as `type: command` in hooks/hooks.json. On every Stop event, Claude
Code invokes this script with the event payload on stdin. The script decides
whether the model's last response made a material claim without supporting
evidence; if so, it exits 2 to block the Stop and feeds a stderr message back
to the model as continuation context (the model must then invoke the
`verification-before-completion` skill to produce fresh evidence).

Decision flow:
  1. Parse stdin (Claude Code Stop event JSON). Extract `last_assistant_message`.
     If stdin is missing/unparseable, exit 0 with a stderr warning (fail-open —
     a misconfigured pipeline should not brick the user's session).
  2. Read `hooks.profile` from athanor.json. If `"off"`, exit 0 silently —
     the user has opted out of the runtime gate.
  3. Check whether the response begins with the emission sentinel
     `<!-- athanor:verification-emission v=N -->` (anchored at the first
     non-whitespace line). If yes, exit 0 silently — the response is the
     verification skill's own output and must not re-trigger the gate.
  4. Run `is_material_claim()` over the response body. The phrase whitelist
     mirrors the v0.7.7 prompt-based hook's English + Korean trigger lists
     so users see no surprise expansion of the trigger surface between
     v0.7.7 (advisory prompt) and v0.7.8 (enforced command). Quoted
     historical references ("the v0.7.6 docs said 'tests pass'") may
     false-positive; sentence-level attribution detection is v0.8.0+ work.
  5. If a material claim is detected, exit 2 with a stderr message directing
     the model to invoke `verification-before-completion`.

Cross-platform note: invoked via `python3` in hooks/hooks.json. On Windows
hosts, Claude Code's plugin runtime resolves `python3` via the installed
Python distribution; the GitHub Actions Python setup-action handles this for
CI. Pure-Python (no jq dependency).

v0.7.9 hardening (docs/plans/2026-05-18-002-feat-v0.7.9-stop-hook-hardening-plan.md):
  - Sentinel forgery (sec-001): v=2 nonce-bound protocol. The verification
    skill writes {nonce, body_hash, timestamp} via scripts/hooks/sentinel_helper.py;
    this script validates all three before exiting 0. v=1 bare-string sentinels
    are rejected (fall through to material-claim check). Forgery cost raised
    from "emit one string" to "write JSON with matching hash + emit sentinel".
  - Parent-dir hijack (sec-002): config resolution priority is $CLAUDE_PROJECT_DIR
    → git-root → walk-up-stops-at-.git. Never crosses .git/ boundary upward.
  - Sentinel-loop circuit breaker (rel-001): consecutive exit-2 blocks per
    session are counted; after hooks.stopLoopThreshold (default 3), the gate
    releases (exit 0) with a stderr warning to prevent infinite loops.

Residual known limitations (deferred):
  - **Paraphrase bypass (sec-003) — STILL DEFERRED to v0.10.2+.** The
    is_material_claim() function is still pure literal substring matching
    against the v0.7.7 English + Korean whitelist (see function's own
    docstring "Known limitation"). The earlier v0.7.9 plan called for regex
    verb-anchor patterns + unicodedata.normalize('NFKC') + confusables fold,
    but those were NOT implemented in the v0.7.9 ship and were carried
    forward silently. v0.10.1 U6 re-verification (2026-05-19) confirmed
    this gap and corrected this docstring. v0.10.2 candidate for actual
    closure.
  - **Cyrillic homoglyph (ADV-006) — STILL DEFERRED.** Closure depends on
    the same unicodedata normalization step above. Same v0.10.2 candidate.
  - A model with file-system access can write its own nonce state and emit
    matching sentinel — bypass cost raised but not eliminated. v0.10.2+
    candidate via Claude Code transcript-event introspection.
  - Mid-session profile mutation (model writes athanor.json mid-turn) is not
    guarded.
  - LLM-class paraphrase patterns not covered by any layer (paraphrase
    layer itself absent — see sec-003 above).

v0.10.0 scope disclosure (vendored-surface honesty):
  This script triggers on every `Stop` event regardless of which skill produced
  the model's last turn. The whitelist phrase set was tuned to athanor-native
  skills' voice (v0.7.7 origin); CE-vendored (skills/ce-<name>/) and superpowers-
  vendored (skills/sp-<name>/) skills introduced at v0.10.0 may emit material
  claims in different idioms that escape the whitelist (false negatives). The
  gate is "best-effort across all skills" not "scoped to athanor-native". A
  vendor-aware whitelist expansion is deferred to v0.10.1+. See CLAUDE.md
  §"Vendored Surface — Identity Guard Layer" identity commitment #4.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import hook_state  # noqa: E402

# v=2 sentinel: nonce-bound, SHA-256 body hash, TTL-checked.
# Anchored at first non-whitespace line of last_assistant_message.
SENTINEL_PATTERN = re.compile(
    r"^\s*<!--\s*athanor:verification-emission\s+v=2\s+nonce=([a-f0-9]{32})\s*-->",
    re.IGNORECASE,
)
# Legacy v=1 detector — used only to emit a deprecation stderr warning so
# users running mixed v0.7.8 ↔ v0.7.9 skill versions get a clear signal.
LEGACY_V1_PATTERN = re.compile(
    r"^\s*<!--\s*athanor:verification-emission\s+v=1\s*-->",
    re.IGNORECASE,
)
ACTIVE_SESSION = hook_state.__dict__.get("ACTIVE_SESSION", "active")

# Material-claim phrase whitelist — ported verbatim from the v0.7.7 prompt
# in hooks/hooks.json (commit 999d747 v0.7.2 narrowed gating + v0.7.5
# disambiguation). Same trigger surface; only enforcement strength changes.
#
# Source of truth: the v0.7.7 hooks/hooks.json prompt text. When expanding,
# verify the addition reflects a phrase v0.7.7 considered material — do not
# introduce new categories without a planning cycle.
MATERIAL_CLAIMS_EN = [
    # English action verbs (past tense claims of work-state change)
    "tests pass",
    "tests passing",
    "tests passed",
    # Failure-state material claims (v0.7.7 prompt: "tests passing/failing")
    "tests failing",
    "tests failed",
    "tests broken",
    "build succeeded",
    "build success",
    "build passing",
    "build failed",
    "build failing",
    "build broken",
    "lint clean",
    "lint passing",
    "lint failed",
    "lint failing",
    "typecheck clean",
    "typecheck passing",
    "typecheck failed",
    "typecheck failing",
    "files created",
    "files removed",
    "files renamed",
    "files changed",
    "files modified",
    "bug fixed",
    "fixed the bug",
    "requirements met",
    "version bumped",
    "migration completed",
    "migrations completed",
    "deployment succeeded",
    "deployed to",
    "merged pr",
    "merged to main",
    "merged into main",
    "verification confirmed",
    "verification complete",
    "verified that",
    "agent task completed",
    "release shipped",
    "release complete",
    # Edit-applied claims
    "edits applied",
    "applied the edit",
    "applied the patch",
]
# Korean equivalents — must describe repo/test/build/release/migration/
# deployment/verification state (per v0.7.7 prompt scope). Verb stems require
# action-anchor pairing to count.
MATERIAL_CLAIMS_KO = [
    "테스트 통과",
    "테스트 패스",
    "테스트 실패",
    "빌드 성공",
    "빌드 통과",
    "빌드 실패",
    "린트 통과",
    "린트 실패",
    "타입체크 통과",
    "타입체크 실패",
    "수정했습니다",
    "수정 완료",
    "반영했습니다",
    "반영 완료",
    "구현했습니다",
    "구현 완료",
    "완료했습니다",
    "통과했습니다",
    "성공했습니다",
    "실패했습니다",
    "배포했습니다",
    "배포 완료",
    "배포됨",
    "생성했습니다",
    "생성 완료",
    "삭제했습니다",
    "삭제 완료",
    "수행했습니다",
    "수행 완료",
    "적용했습니다",
    "적용 완료",
    "머지 완료",
    "머지했습니다",
    "마이그레이션 완료",
    "마이그레이션 실패",
    "버그 수정",
    "버전 업데이트",
]

# v0.10.2 — vendor-aware whitelist additions (A2 closure).
# Idioms emitted by vendored CE/superpowers skills (skills/ce-*/, skills/sp-*/)
# that are not in the v0.7.7-derived athanor-native voice. Conservative
# additions — each phrase must ASSERT a state, not describe a capability.
MATERIAL_CLAIMS_EN.extend([
    # CE skill completion idioms
    "review complete",
    "review completed",
    "implementation complete",
    "implementation done",
    "task complete",
    "all done",
    # LFG-style autopilot signal
    "<promise>done</promise>",
    # PR/CI status assertions
    "ci passed",
    "checks passed",
    "all checks passing",
    "all checks passed",
    "branch merged",
    "pr opened",
    "pr created",
])
MATERIAL_CLAIMS_KO.extend([
    "리뷰 완료",
    "PR 생성 완료",
    "체크 통과",
    "모든 작업 완료",
])


# v0.10.2 — Cyrillic→Latin confusables fold (ADV-006 closure).
# Conservative set: 17 Cyrillic characters that are visually indistinguishable
# from Latin equivalents at common font sizes. Greek/Armenian/other-script
# homoglyphs are NOT in the v0.10.2 scope (documented as known residual in
# test_regression_v010_2_paraphrase_closure.py — expand deliberately, not
# greedily).
_CYRILLIC_TO_LATIN_TABLE = str.maketrans({
    # lowercase
    "а": "a",  # U+0430
    "е": "e",  # U+0435
    "о": "o",  # U+043E
    "р": "p",  # U+0440
    "с": "c",  # U+0441
    "у": "y",  # U+0443
    "х": "x",  # U+0445
    # uppercase
    "А": "A",  # U+0410
    "В": "B",  # U+0412
    "Е": "E",  # U+0415
    "К": "K",  # U+041A
    "М": "M",  # U+041C
    "Н": "H",  # U+041D
    "О": "O",  # U+041E
    "Р": "P",  # U+0420
    "С": "C",  # U+0421
    "Т": "T",  # U+0422
    "Х": "X",  # U+0425
})


def _normalize_for_match(text: str) -> str:
    """Normalize a message before material-claim detection.

    Layers (v0.10.2):
      1. Unicode NFKC normalization (collapses fullwidth, ligatures,
         compatibility-decomposition characters).
      2. Cyrillic→Latin confusables fold (conservative 17-character set).
      3. Lowercase (matches EN whitelist case-insensitivity; KO is unaffected).

    Idempotent: norm(norm(x)) == norm(x).

    Returns the normalized text. Empty input returns empty string.
    """
    if not text:
        return ""
    nfkc = unicodedata.normalize("NFKC", text)
    folded = nfkc.translate(_CYRILLIC_TO_LATIN_TABLE)
    return folded.lower()


# v0.10.2 — paraphrase regex patterns (B2 / sec-003 closure).
# Each pattern is verb-anchored to limit false positives. Conservative —
# fewer patterns is better than more. Module-load assertion below catches
# accidental emptying.
def _compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    compiled = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat, re.IGNORECASE))
        except re.error as exc:
            raise AssertionError(
                f"v0.10.2 paraphrase pattern failed to compile: {pat!r} — {exc}"
            ) from exc
    return compiled


_PATTERN_SOURCE: list[str] = [
    # CI-state assertions: "CI is green", "CI is now passing", "CI is healthy"
    r"\bci\s+(?:is\s+)(?:now\s+|currently\s+)?(?:green|passing|healthy)\b",
    # All-tests-state assertions
    r"\ball\s+(?:the\s+)?tests\s+(?:are\s+|were\s+)(?:now\s+|currently\s+)?(?:green|passing|clean)\b",
    # Build-state assertions
    r"\bthe\s+build\s+(?:is\s+|was\s+)(?:now\s+|currently\s+)?(?:green|healthy|clean|passing)\b",
    # Deploy assertions (paraphrase of "deployment succeeded")
    r"\bdeployed\s+(?:it\s+)?(?:to|onto)\s+(?:prod|production|main|staging)\b",
    # KO verb-anchored paraphrase: "테스트가 모두 통과", "테스트 다 통과"
    r"테스트(?:가|는)?\s*(?:다|모두|전부)?\s*통과(?:했|함|됨)",
    # KO build success paraphrase
    r"빌드(?:가|는)?\s*(?:다|모두)?\s*성공(?:했|함|됨)",
]
MATERIAL_CLAIM_PATTERNS: list[re.Pattern[str]] = _compile_patterns(_PATTERN_SOURCE)


# Module-load invariant: whitelists must be non-empty. An empty list would
# silently disable the gate (every Stop event would pass is_material_claim ->
# False). Surfaced loudly at script import so a regression cannot land
# unnoticed.
assert MATERIAL_CLAIMS_EN, "MATERIAL_CLAIMS_EN must not be empty — empty whitelist silently disables gate"
assert MATERIAL_CLAIMS_KO, "MATERIAL_CLAIMS_KO must not be empty — empty whitelist silently disables gate"
assert MATERIAL_CLAIM_PATTERNS, "MATERIAL_CLAIM_PATTERNS must not be empty — empty list silently disables v0.10.2 paraphrase layer"

ATHANOR_CONFIG_NAME = "athanor.json"
SUPPORTED_PROFILES = {"off", "standard"}


def _stderr(msg: str) -> None:
    """Emit one line of stderr; stderr is fed back to the model on exit 2 and
    visible in CI logs on exit 0. Both are useful — keep messages terse."""
    print(f"athanor (stop hook): {msg}", file=sys.stderr)


def _read_stdin_payload() -> dict | None:
    """Read the Stop event payload from stdin. Returns parsed dict or None
    if stdin is unavailable / unreadable / not JSON."""
    if sys.stdin.isatty():
        return None
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _find_athanor_config() -> tuple[Path | None, str]:
    """Locate athanor.json via priority chain (v0.7.9):

    1. ``$CLAUDE_PROJECT_DIR/athanor.json`` if env var set and file exists.
    2. Git repository root (first ancestor with ``.git/``) — but only if
       athanor.json is at that root. Closes the v0.7.8 parent-dir hijack
       (sec-002): an athanor.json in a parent of the repo no longer
       silently applies.
    3. Walk up from cwd, but STOP at any ``.git/`` boundary. Athanor configs
       above a repo root are no longer trusted from inside that repo.
       Also bounded by $HOME and depth=8.

    Returns ``(config_path, mechanism)`` where mechanism is one of
    ``"$CLAUDE_PROJECT_DIR"``, ``"git-root"``, ``"walk-up"``, or
    ``"none"``. The mechanism string is surfaced in the profile=off
    audit breadcrumb so users can see WHICH path resolved the config.
    """
    # 1. Explicit env var from Claude Code (when present).
    env_proj = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_proj:
        candidate = Path(env_proj) / ATHANOR_CONFIG_NAME
        if candidate.is_file():
            return (candidate.resolve(), "$CLAUDE_PROJECT_DIR")

    cur = Path.cwd().resolve()
    try:
        home = Path.home().resolve()
    except (OSError, RuntimeError):
        home = None

    # 2 + 3. Walk up; stop at .git boundary, $HOME, or depth 8.
    for _ in range(8):
        candidate = cur / ATHANOR_CONFIG_NAME
        has_git = (cur / ".git").is_dir()
        if candidate.is_file():
            mechanism = "git-root" if has_git else "walk-up"
            return (candidate, mechanism)
        if has_git:
            # Hit a .git boundary without finding athanor.json at this level.
            # Don't cross repo root upward — that was the v0.7.8 hijack.
            return (None, "none")
        if home is not None and cur == home:
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    return (None, "none")


def _read_profile() -> tuple[str, Path | None, str]:
    """Read `hooks.profile` from athanor.json.

    Returns ``(profile, config_path, mechanism)``:
      - ``profile`` is one of SUPPORTED_PROFILES (or "standard" default).
      - ``config_path`` is the resolved athanor.json path (or None).
      - ``mechanism`` is the resolution mechanism — "$CLAUDE_PROJECT_DIR",
        "git-root", "walk-up", or "none". Surfaced in the profile=off
        audit breadcrumb (v0.7.9 closes the v0.7.8 parent-dir hijack).

    Defensive handling unchanged from v0.7.8.
    """
    config_path, mechanism = _find_athanor_config()
    if config_path is None:
        return ("standard", None, mechanism)
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        _stderr(
            f"could not read {config_path} ({type(e).__name__}); "
            f"falling back to profile=standard"
        )
        return ("standard", config_path, mechanism)
    if not isinstance(data, dict):
        _stderr(
            f"{config_path} top-level is not an object; "
            f"falling back to profile=standard"
        )
        return ("standard", config_path, mechanism)
    hooks_section = data.get("hooks", {})
    if not isinstance(hooks_section, dict):
        _stderr(
            f"{config_path} `hooks` field is not an object "
            f"(got {type(hooks_section).__name__}); falling back to profile=standard"
        )
        return ("standard", config_path, mechanism)
    profile = hooks_section.get("profile", "standard")
    if not isinstance(profile, str) or profile not in SUPPORTED_PROFILES:
        _stderr(
            f"unknown hooks.profile value {profile!r}; treating as 'standard'. "
            f"Supported values: {sorted(SUPPORTED_PROFILES)}."
        )
        return ("standard", config_path, mechanism)
    return (profile, config_path, mechanism)


def validate_emission_sentinel(message: str) -> bool:
    """True iff `message` is a valid v=2 sentinel-bound verification response.

    v=2 protocol (athanor v0.7.9):
      1. Sentinel `<!-- athanor:verification-emission v=2 nonce=<32-hex> -->`
         must be the first non-whitespace line.
      2. The nonce must match the state file at
         `.athanor/sessions/active/.hook-state/nonce.json`.
      3. State timestamp must be within NONCE_TTL_SECONDS (60s).
      4. SHA-256 of the message body AFTER the sentinel line must match the
         stored `body_hash` from the verification skill's emit step.
      5. On all-pass: atomic-delete the state file (one-shot) and return True.
      6. On any-fail: return False; main() falls through to material-claim
         check and exits 2 if a claim is detected.

    Legacy v=1 sentinels are rejected (logged via stderr) — they were
    trivially forgeable in v0.7.8.
    """
    if not message:
        return False
    # v=1 legacy detection (emit deprecation warning; don't accept).
    if LEGACY_V1_PATTERN.match(message):
        _stderr(
            "rejected legacy v=1 sentinel — v0.7.9 requires v=2 nonce-bound "
            "format. Update your verification skill or upgrade vendored copy."
        )
        return False
    m = SENTINEL_PATTERN.match(message)
    if not m:
        return False
    nonce_in_msg = m.group(1).lower()
    state = hook_state.read_nonce_state(ACTIVE_SESSION)
    if state is None:
        return False  # No state — likely forgery attempt
    if not hook_state.is_nonce_fresh(state):
        _stderr("nonce state is stale (TTL exceeded); falling through")
        return False
    stored_nonce = state.get("nonce", "")
    if not isinstance(stored_nonce, str) or stored_nonce.lower() != nonce_in_msg:
        _stderr("nonce mismatch — sentinel rejected")
        return False
    # Extract body after the sentinel line and verify SHA-256.
    body_after = message[m.end():]
    # The helper hashed exactly what was piped in. The skill must emit
    # that same body byte-for-byte AFTER the sentinel line. Allow one
    # trailing newline between sentinel and body (markdown rendering quirks).
    body_canonical = body_after.lstrip("\n")
    actual_hash = hashlib.sha256(body_canonical.encode("utf-8")).hexdigest()
    stored_hash = state.get("body_hash", "")
    if not isinstance(stored_hash, str) or actual_hash != stored_hash:
        _stderr(
            "body hash mismatch — sentinel rejected. The response body after "
            "the sentinel does not match what was piped to sentinel_helper.py."
        )
        return False
    # One-shot: delete state so this nonce cannot be replayed.
    hook_state.delete_nonce_state(ACTIVE_SESSION)
    return True


def is_material_claim(message: str) -> bool:
    """Detect any whitelisted material-claim phrase in the message body.

    v0.10.2 detection pipeline (closure of B2 / sec-003 / ADV-006 / A2):
      1. Normalize via `_normalize_for_match()` — NFKC + Cyrillic→Latin
         confusables fold + lowercase. Closes homoglyph and fullwidth
         attacks; makes EN whitelist matching case-insensitive uniformly.
      2. Substring match against `MATERIAL_CLAIMS_EN` (normalized).
      3. Substring match against `MATERIAL_CLAIMS_KO` (raw `message` —
         Korean is case-irrelevant; we still check against `normalized`
         too so homoglyph-attacked Korean phrases get caught).
      4. Regex search against `MATERIAL_CLAIM_PATTERNS` (verb-anchored
         paraphrases of state assertions; runs on normalized text).

    Returns True on the first match.

    Known residuals (v0.10.3+ candidates):
      - LLM-class paraphrase patterns subtler than the regex layer catches.
      - Quoted historical references (`the v0.7.6 docs said "tests pass"`)
        — attribution detection is its own pass.
      - Greek/Armenian/other-script homoglyphs (v0.10.2 scope is
        Cyrillic-only fold).
      - Speculative-tense paraphrases ("I'll check if CI is green") —
        regex cannot distinguish without semantic analysis.
    """
    if not message:
        return False
    normalized = _normalize_for_match(message)
    for phrase in MATERIAL_CLAIMS_EN:
        if phrase in normalized:
            return True
    for phrase in MATERIAL_CLAIMS_KO:
        # KO unchanged from v0.7.7: raw match. Also check normalized
        # for homoglyph-attacked Korean (rare but covered).
        if phrase in message or phrase in normalized:
            return True
    for pattern in MATERIAL_CLAIM_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def _read_stop_loop_threshold() -> int:
    """Read `hooks.stopLoopThreshold` from athanor.json or default."""
    config_path, _ = _find_athanor_config()
    if config_path is None:
        return hook_state.DEFAULT_STOP_LOOP_THRESHOLD
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return hook_state.DEFAULT_STOP_LOOP_THRESHOLD
    if not isinstance(data, dict):
        return hook_state.DEFAULT_STOP_LOOP_THRESHOLD
    hooks_section = data.get("hooks", {})
    if not isinstance(hooks_section, dict):
        return hook_state.DEFAULT_STOP_LOOP_THRESHOLD
    threshold = hooks_section.get("stopLoopThreshold")
    if not isinstance(threshold, int) or threshold < 1:
        if threshold is not None:
            _stderr(
                f"invalid hooks.stopLoopThreshold {threshold!r}; "
                f"using default {hook_state.DEFAULT_STOP_LOOP_THRESHOLD}"
            )
        return hook_state.DEFAULT_STOP_LOOP_THRESHOLD
    return threshold


def main() -> int:
    payload = _read_stdin_payload()
    if payload is None:
        _stderr("stdin missing or unparseable; passing (fail-open)")
        return 0

    profile, config_path, mechanism = _read_profile()
    if profile == "off":
        # Audit breadcrumb — makes ancestor-hijack visible. The user (or a
        # future auditor) can see WHICH athanor.json disabled the gate AND
        # via which resolution mechanism (v0.7.9 closes parent-dir hijack).
        _stderr(
            f"gate disabled by hooks.profile=off in "
            f"{config_path if config_path else '<no config found>'} "
            f"(resolved via {mechanism})"
        )
        return 0

    last_msg = payload.get("last_assistant_message")
    if not isinstance(last_msg, str):
        # Payload shape variation — Claude Code may pass message-parts arrays,
        # nulls, or omit the field entirely depending on version. Fail-open
        # but with an audit signal so silent payload-drift is detectable.
        _stderr(
            f"last_assistant_message missing or non-string "
            f"(got {type(last_msg).__name__}); passing (fail-open)"
        )
        return 0
    if not last_msg.strip():
        _stderr("last_assistant_message is empty; passing (fail-open)")
        return 0

    if validate_emission_sentinel(last_msg):
        # v=2 sentinel validated — verification skill output. Reset counter.
        hook_state.reset_stop_counter(ACTIVE_SESSION)
        return 0  # silent re-entry skip

    if not is_material_claim(last_msg):
        return 0  # no material claim; nothing to gate

    # Material claim present → check circuit breaker before blocking.
    threshold = _read_stop_loop_threshold()
    counter = hook_state.read_stop_counter(ACTIVE_SESSION)
    if counter >= threshold:
        # Circuit breaker opens — release the loop.
        _stderr(
            f"circuit breaker open after {counter} consecutive blocks "
            f"(threshold={threshold}) — gate releasing this turn. If you keep "
            f"hitting this, the verification skill may be misconfigured or your "
            f"model is consistently producing material claims without invoking it. "
            f"Set hooks.profile=\"off\" in athanor.json to disable the gate, or "
            f"raise hooks.stopLoopThreshold to allow more retries."
        )
        hook_state.reset_stop_counter(ACTIVE_SESSION)
        return 0

    hook_state.write_stop_counter(ACTIVE_SESSION, counter + 1)
    _stderr(
        "material claim detected in last response without fresh verification "
        "evidence. Invoke the `verification-before-completion` skill NOW to "
        "produce command output, exit code, or explicit verification check "
        "supporting each claim before stopping. To disable this gate per-project, "
        'set "hooks": {"profile": "off"} in athanor.json.'
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
