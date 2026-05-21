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

v0.10.2 paraphrase + NFKC + vendor-aware closure
(docs/plans/2026-05-19-005-feat-v0.10.2-paraphrase-bypass-closure-plan.md):
  Honesty-arc framing: the v0.7.9 docstring originally claimed paraphrase
  regex + NFKC + confusables fold were shipped. v0.10.1 U6 audit found
  they were NEVER implemented and corrected the docstring honestly. v0.10.2
  actually ships the work:
  - Paraphrase bypass (sec-003) — closed via MATERIAL_CLAIM_PATTERNS.
  - Cyrillic homoglyph (ADV-006) — closed via NFKC + 17-char Cyrillic→
    Latin fold in _normalize_for_match().
  - Vendor-aware whitelist (A2) — closed via MATERIAL_CLAIMS_EN/KO
    extensions for CE/superpowers idioms.

v0.10.3 residual closure
(docs/plans/2026-05-19-006-feat-v0.10.3-stop-hook-residual-closure-plan.md):
  Closes the three accuracy residuals v0.10.2 documented honestly:
  - R1 (Greek/Armenian homoglyph fold) — closed: _CYRILLIC_TO_LATIN_TABLE
    renamed to _CONFUSABLES_TO_LATIN_TABLE and extended with Greek
    (α ε ι ν ο ρ υ + 7 uppercase) + Armenian (ո). Backwards-compat
    alias on the old name retained for any external importer.
  - R2 (conditional/speculative tense suppression) — closed:
    _is_conditional_or_speculative_context() inspects the clause
    containing a match (between the most recent ., , ; ? ! \n boundary
    and match_start). If the first token is in {if, once, when, whenever,
    should, could, would, unless} OR the Korean prefix is 만약/만일,
    the match is suppressed.
  - R3 (attribution / quoted-context skip) — closed:
    _is_attributed_quote_context() does (a) paired-quote check (same-line
    odd quote count before + matching close after match span); (b) EN
    attribution-verb window (within 40 chars before match, on same
    line, scan for said/claimed/wrote/etc.); (c) KO attribution-verb
    window (within 40 chars AFTER match, on same line, scan for
    라고-했/라고-적/라고-말 — Korean attribution markers follow the
    quote).

v0.11.3 input-layer fix (post-mortem)
(docs/plans/2026-05-20-002 originated; .athanor/sessions/2026-05-21-001/plan.md):
  v0.7.8 → v0.11.2 (5 release cycles): the script's stdin parser called
  `payload.get("last_assistant_message")` and treated `None` as fail-open.
  Claude Code actually sends `{"session_id": "...", "transcript_path":
  "<jsonl>", "stop_hook_active": false, "hook_event_name": "Stop"}`; the
  message body lives inside the transcript JSONL, not in the payload as a
  string. Every Stop event silently fail-opened with stderr "last_assistant_
  message missing or non-string"; the gate was non-functional from v0.7.8
  through v0.11.2 inclusive. The 35+ existing tests in
  test_regression_stop_hook_script.py used the same incorrect assumed shape
  and so passed while production was dead.

  v0.11.3 introduces _content_to_text(content) and
  _read_last_assistant_message(payload). The new parser accepts BOTH shapes:
  legacy-first early return on payload["last_assistant_message"] (preserves
  the 35+ existing tests as backwards-compat lock); otherwise read
  payload["transcript_path"] as JSONL, iterate lines in reverse with
  per-line JSONDecodeError tolerance (partial-final-line race), filter on
  `entry.get("isSidechain") is not True` (sub-agent turn skip), match first
  `entry["type"] == "assistant"` AND `entry["message"]["role"] ==
  "assistant"`, extract `entry["message"]["content"]`, run through
  _content_to_text (handles string OR list of text/tool_use/thinking
  typed blocks, drops tool_use and thinking, concatenates text). The
  `stop_hook_active` flag is pass-through; re-entry semantics remain
  governed by the existing hook_state circuit breaker (read_stop_counter /
  write_stop_counter / reset_stop_counter, NOT increment — earlier docs
  used a convenience name not present in the actual API).

  The detection layers shipped in v0.7.9 (nonce sentinel) / v0.10.2
  (paraphrase + NFKC + Cyrillic + vendor-aware) / v0.10.3 (Greek/Armenian
  + conditional + attribution) are unchanged and now reachable.
  tests/test_regression_v011_3_stop_hook_input_layer.py adds 25 mandatory
  + 1 xfail-tolerant tests against the real Claude Code payload shape.

  Scope note (added v0.11.4): the v0.11.3 fix above was reachable only in
  athanor's source repo until v0.11.4's ${CLAUDE_PLUGIN_ROOT} path fix.

v0.11.4 plugin-root deployment fix (post-mortem)
(.athanor/sessions/2026-05-21-002/plan.md):
  The v0.11.3 input-layer fix made the script find the message via
  transcript_path correctly — but only when CC resolved the hook
  command relative to athanor's source repo. `hooks/hooks.json`
  registered the command as `python3 scripts/hooks/stop_verify_claims.py`
  — a bare relative path. CC resolves hook commands relative to the
  user's PROJECT cwd, not the plugin install dir. For any user with
  athanor installed user-scope but working in another project, CC
  exited 2 with "python3: can't open file" and treated the hook as
  missing (non-blocking). Result: from v0.7.8 (script introduction)
  through v0.11.3 (input-layer fix), the gate was silently absent in
  every project except athanor's own source repo.

  v0.11.4 closes the deployment-path gap. hooks/hooks.json now uses
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"`
  — the env var is set by Claude Code for plugin hooks and expands
  to the plugin install path. Industry pattern: superpowers,
  claude-mem, openai-codex all use ${CLAUDE_PLUGIN_ROOT}. v0.11.3
  + v0.11.4 are companion-fixes of one latent bug — script wrong +
  path wrong — surfaced in pieces by source-repo-only manual testing.

  tests/test_regression_stop_command_hook.py::test_stop_hook_command_uses_plugin_root_or_absolute_path
  locks the invariant.

Residual known limitations (carried forward to v0.11.0+):
  - **LLM-class paraphrase patterns subtler than verb-anchor regex**
    (e.g., "we verified the test suite ran clean" with subtle clause
    embedding). v0.11.0+ candidate for semantic similarity layer.
  - **Speculative tense WITHOUT prefix marker** ("Probably CI is green").
    v0.10.3 R2 catches explicit prefix markers only.
  - **Multi-paragraph quote spans / code-block context** for attribution.
    v0.10.3 R3 uses a same-line constraint.
  - **Cherokee, full-width Latin, other-script confusables**. v0.10.3 R1
    covers Cyrillic + Greek + Armenian only.
  - A model with file-system access can write its own nonce state and emit
    matching sentinel — bypass cost raised but not eliminated. v0.11.0+
    candidate via Claude Code transcript-event introspection.
  - Mid-session profile mutation (model writes athanor.json mid-turn) is not
    guarded.

v0.10.0 scope (vendored-surface coverage):
  This script triggers on every `Stop` event regardless of which skill
  produced the model's last turn. The v0.10.2 vendor-aware whitelist
  extension (A2 closure) raises coverage on vendored CE/superpowers skill
  idioms. The gate remains "best-effort across all skills" — coverage is
  whitelist + regex + normalization based, not semantic. See CLAUDE.md
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
# v0.10.3 — extended with Greek + Armenian look-alikes (R1 closure).
# Renamed _CYRILLIC_TO_LATIN_TABLE → _CONFUSABLES_TO_LATIN_TABLE since the
# table now covers multiple scripts. Old name kept as alias for any external
# importer that may exist.
# Conservative set: each entry is a character that is visually
# indistinguishable from a Latin equivalent at common font sizes.
# Greek/Armenian additions tuned by attack-vector relevance — `ο/α/ε/υ/ν/ρ`
# (Greek lowercase) and `ո` (Armenian small `o`) are the high-frequency
# substitution targets for whitelist phrases.
# Other-script confusables (Cherokee, full-width Latin not handled by
# NFKC, etc.) NOT in v0.10.3 scope — expand deliberately.
_CONFUSABLES_TO_LATIN_TABLE = str.maketrans({
    # ---- Cyrillic lowercase (v0.10.2) ----
    "а": "a",  # U+0430
    "е": "e",  # U+0435
    "о": "o",  # U+043E
    "р": "p",  # U+0440
    "с": "c",  # U+0441
    "у": "y",  # U+0443
    "х": "x",  # U+0445
    # ---- Cyrillic uppercase (v0.10.2) ----
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
    # ---- Greek lowercase (v0.10.3) ----
    "α": "a",  # U+03B1
    "ε": "e",  # U+03B5
    "ι": "i",  # U+03B9
    "ν": "v",  # U+03BD — Greek nu looks like Latin v
    "ο": "o",  # U+03BF
    "ρ": "p",  # U+03C1 — Greek rho looks like Latin p
    "υ": "u",  # U+03C5
    # ---- Greek uppercase (v0.10.3) ----
    "Α": "A",  # U+0391
    "Ε": "E",  # U+0395
    "Ι": "I",  # U+0399
    "Ο": "O",  # U+039F
    "Ρ": "P",  # U+03A1
    "Τ": "T",  # U+03A4
    "Υ": "Y",  # U+03A5
    # ---- Armenian (v0.10.3) ----
    "ո": "o",  # U+0578 Armenian small letter vo
})
# Backwards-compat alias for any external code that imported the old name
# before v0.10.3. Internal call sites use _CONFUSABLES_TO_LATIN_TABLE.
_CYRILLIC_TO_LATIN_TABLE = _CONFUSABLES_TO_LATIN_TABLE


def _normalize_for_match(text: str) -> str:
    """Normalize a message before material-claim detection.

    Layers:
      1. Unicode NFKC normalization (collapses fullwidth, ligatures,
         compatibility-decomposition characters).
      2. Multi-script confusables fold:
         - v0.10.2: Cyrillic→Latin (17 characters).
         - v0.10.3: + Greek (~13 characters) + Armenian (1 character).
      3. Lowercase (matches EN whitelist case-insensitivity; KO is unaffected).

    Idempotent: norm(norm(x)) == norm(x).

    Returns the normalized text. Empty input returns empty string.
    """
    if not text:
        return ""
    nfkc = unicodedata.normalize("NFKC", text)
    folded = nfkc.translate(_CONFUSABLES_TO_LATIN_TABLE)
    return folded.lower()


# v0.10.3 — Conditional / speculative tense markers (R2 closure).
# When a material-claim phrase matches, we check whether the clause
# containing the match starts with a marker from these sets. If yes,
# the match is suppressed (false-positive reduction).
_CLAUSE_BOUNDARY_CHARS = set(".,;:?!\n")
_CONDITIONAL_MARKERS_EN = frozenset({
    "if", "once", "when", "whenever", "should", "could", "would", "unless",
})
# Korean markers are prefix-based (we check stripped-clause startswith).
# Suffix markers (`...면`, `...한다면`) require morphological analysis to
# detect reliably; v0.10.3 covers only the explicit-prefix common case.
_CONDITIONAL_MARKERS_KO = ("만약", "만일")


def _clause_start_for(text: str, match_start: int) -> int:
    """Find the index of the first non-whitespace character of the clause
    containing position `match_start`. The clause starts immediately after
    the most recent clause-boundary char (or at index 0).
    """
    i = match_start - 1
    while i >= 0:
        if text[i] in _CLAUSE_BOUNDARY_CHARS:
            i += 1
            break
        i -= 1
    if i < 0:
        i = 0
    # Skip leading whitespace inside the clause
    while i < match_start and text[i].isspace():
        i += 1
    return i


def _is_conditional_or_speculative_context(text: str, match_start: int) -> bool:
    """Return True if the clause containing `match_start` opens with a
    conditional or speculative marker (English or Korean).

    Detection is intentionally conservative — only explicit-prefix markers.
    Speculative-tense expressed without prefix marker
    (e.g., "Probably CI is green") is NOT caught; documented v0.10.4+ candidate.
    """
    clause_start = _clause_start_for(text, match_start)
    clause = text[clause_start:match_start]
    # Empty clause prefix (match at start of clause): no marker by definition.
    if not clause.strip():
        return False
    # Check Korean prefix first (raw text, no lowercasing needed for Korean)
    stripped = clause.lstrip()
    for marker in _CONDITIONAL_MARKERS_KO:
        if stripped.startswith(marker):
            return True
    # Check English: first whitespace-separated token, lowercased
    first_token = stripped.split(None, 1)[0].lower() if stripped else ""
    # Strip trailing punctuation from the token (e.g., "if,")
    first_token = first_token.rstrip(".,;:?!")
    if first_token in _CONDITIONAL_MARKERS_EN:
        return True
    return False


# v0.10.3 — Attribution markers (R3 closure).
# When a match is inside paired quotes or shortly after an attribution
# verb, suppress it (the match is a historical reference, not a current
# state assertion).
_QUOTE_CHARS = ('"', "'", "`")
_ATTRIBUTION_VERBS_EN = (
    "said", "claimed", "wrote", "noted", "commented", "mentioned",
    "stated", "reported", "said:",
)
_ATTRIBUTION_VERBS_KO = ("라고 했", "라고 적", "라고 말")
_ATTRIBUTION_WINDOW = 40  # chars before match_start to scan


def _is_attributed_quote_context(text: str, match_start: int,
                                 match_end: int) -> bool:
    """Return True if the match falls inside paired quotes OR within
    `_ATTRIBUTION_WINDOW` chars after an attribution verb.

    Heuristic — fails open on ambiguity (returns False). Multi-paragraph
    quote spans and code-block context NOT covered (v0.10.4+ candidate).
    """
    # 1. Paired-quote check: for each quote char, find the most recent
    #    occurrence before match_start. If it's on the same line as the
    #    match and there's another occurrence of the same char between
    #    match_end and the next newline, the match is inside the quote.
    line_start = text.rfind("\n", 0, match_start) + 1  # 0 if no newline
    line_end = text.find("\n", match_end)
    if line_end < 0:
        line_end = len(text)
    line_segment_before = text[line_start:match_start]
    line_segment_after = text[match_end:line_end]
    for qch in _QUOTE_CHARS:
        count_before = line_segment_before.count(qch)
        # An odd number of quotes before the match (on the same line) means
        # we're inside an unclosed quote opened earlier on this line.
        if count_before % 2 == 1 and qch in line_segment_after:
            return True

    # 2. Attribution-verb check (English): English markers PRECEDE the
    #    quoted content (`he said tests pass`). Scan the window before
    #    match_start, clipped to current line.
    window_start = max(line_start, match_start - _ATTRIBUTION_WINDOW)
    window_before_en = text[window_start:match_start].lower()
    for verb in _ATTRIBUTION_VERBS_EN:
        if verb in window_before_en:
            return True

    # 3. Attribution-verb check (Korean): Korean markers FOLLOW the quoted
    #    content (`테스트 통과 라고 했어요`). Scan the window after match_end,
    #    clipped to current line.
    window_end = min(line_end, match_end + _ATTRIBUTION_WINDOW)
    raw_window_after = text[match_end:window_end]
    for verb in _ATTRIBUTION_VERBS_KO:
        if verb in raw_window_after:
            return True

    return False


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


# v0.11.3 input-layer fix — see also script docstring "v0.11.3 input-layer fix
# (post-mortem)" section (added in Subtask 3).
#
# The v0.7.8 implementation read `payload.get("last_assistant_message")` from
# the Stop event payload. That field is not part of the actual Claude Code
# Stop hook payload shape (CC provides `transcript_path` — a JSONL file
# containing the conversation history). As a result the v0.7.8 gate
# fail-opened on every real Stop event from v0.7.8 through v0.10.3
# inclusive — a multi-version self-violation of the honesty arc, since the
# scripts/docstrings claimed the gate was enforced. v0.11.3 acknowledges
# and corrects this by parsing the transcript.
#
# Design notes for the helpers below:
#   - LEGACY-FIRST early return (decision D7): if the payload literally
#     contains `last_assistant_message` as a string, return it. This
#     preserves all 35+ existing tests in test_regression_stop_hook_script.py
#     as backwards-compatibility locks.
#   - Reverse-scan JSONL, line by line, with json.JSONDecodeError tolerance
#     (partial-line race tolerance — Claude Code is mid-write when the
#     hook fires).
#   - Sub-agent filter (decision D2): skip entries with `isSidechain == True`.
#     Sub-agent assistant turns must NOT count as the model's "last
#     response" — they're transient worker output, not the main session's
#     completion claim.
#   - `stop_hook_active` flag (decision D3): pass-through. Do NOT branch on
#     it in the parser. Re-entry semantics are governed by the existing
#     `hook_state.read_stop_counter` / `write_stop_counter` /
#     `reset_stop_counter` circuit breaker per v0.7.9 design — branching on
#     the flag here would double-count and short-circuit the breaker.
#   - Memory-cap / line-cap optimization (e.g., chunked tail-read for
#     multi-MB transcripts) is deferred to v0.11.4. Current implementation
#     reads the full file; acceptable for typical session sizes.


def _content_to_text(content) -> str:
    """Normalize Claude Code message-content into a plain text string.

    `content` is either:
      - a plain string (legacy / older content shape) → return verbatim.
      - a list of typed blocks. Recognized types: `text` (concatenated),
        `tool_use` (skipped), `thinking` (skipped). Unknown types are
        skipped silently.

    Returns "" for empty / non-list / non-string input.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = block.get("text", "")
            if isinstance(text, str):
                parts.append(text)
        # tool_use, thinking, and unknown types are skipped silently.
    return "".join(parts)


def _read_last_assistant_message(payload: dict) -> str | None:
    """Extract the model's last main-session assistant message text from a
    Claude Code Stop event payload.

    Decision order (v0.11.3, decisions D2/D3/D7):
      1. LEGACY-FIRST: if `payload["last_assistant_message"]` is a string,
         return it. Preserves backwards-compatibility with synthetic test
         payloads using the v0.7.8 docstring shape (D7).
      2. Real CC path: open `payload["transcript_path"]` as JSONL.
         Reverse-scan the lines. For each line:
           - Skip blank lines and lines that fail `json.loads` (partial-line
             race tolerance — Claude Code may be mid-write).
           - Match: `entry["type"] == "assistant"` AND
             `entry["message"]["role"] == "assistant"` AND
             `entry.get("isSidechain") != True` (D2 sub-agent filter).
           - Extract `entry["message"]["content"]` via `_content_to_text`.
           - Return the first non-empty match.
      3. Fallthrough → return None. Caller's main() emits the existing
         fail-open stderr.

    `stop_hook_active` is intentionally not inspected here (D3 pass-through).
    """
    # 1. Legacy path.
    legacy = payload.get("last_assistant_message")
    if isinstance(legacy, str):
        return legacy
    # 2. Real CC path.
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        return None
    try:
        with open(transcript_path, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return None
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError:
            # Partial-line race — tolerate and continue scanning.
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "assistant":
            continue
        if entry.get("isSidechain") is True:
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        text = _content_to_text(message.get("content"))
        if text:
            return text
        # Empty-text assistant entry — continue scanning for a non-empty one.
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


def _match_is_suppressed(message: str, normalized: str,
                         match_start_norm: int, match_end_norm: int) -> bool:
    """Apply v0.10.3 context suppressions to a candidate match.

    Context checks run against the ORIGINAL message (case + non-folded text
    preserved) so attribution verbs and conditional markers retain their
    natural form. The position is mapped from the normalized text to the
    raw text by length-preservation: NFKC + str.translate + .lower() all
    preserve string length character-by-character (translate is 1-char→
    1-char; lower is 1-char→1-char for the letters in our matching set).

    Returns True if the match should be suppressed (i.e., the match is
    inside a conditional clause or an attributed quote).
    """
    if _is_conditional_or_speculative_context(message, match_start_norm):
        return True
    if _is_attributed_quote_context(message, match_start_norm, match_end_norm):
        return True
    return False


def is_material_claim(message: str) -> bool:
    """Detect any whitelisted material-claim phrase in the message body.

    Detection pipeline:
      1. Normalize via `_normalize_for_match()` — NFKC + multi-script
         confusables fold (Cyrillic/Greek/Armenian → Latin) + lowercase.
         Closes homoglyph and fullwidth attacks.
      2. Substring match against `MATERIAL_CLAIMS_EN` (normalized).
      3. Substring match against `MATERIAL_CLAIMS_KO` (raw `message` —
         Korean is case-irrelevant; also checks `normalized` for
         homoglyph-attacked Korean).
      4. Regex search against `MATERIAL_CLAIM_PATTERNS` (verb-anchored
         paraphrases of state assertions; runs on normalized text).

    v0.10.3 — every candidate match runs through context suppressions
    (`_match_is_suppressed()`):
      - Conditional / speculative clause prefix (`if`, `once`, `should`,
        `만약`, etc.) → match suppressed.
      - Attributed quoted context (paired quotes OR within 40 chars after
        `said`/`claimed`/`라고 했` etc.) → match suppressed.

    Returns True on the first non-suppressed match.

    Known residuals (v0.11.0+ candidates):
      - LLM-class paraphrase patterns subtler than the regex layer catches.
      - Speculative tense without prefix marker ("Probably CI is green").
      - Multi-paragraph quote spans / code-block context.
      - Cherokee, full-width Latin, other-script confusables.
      - Sentinel forgery via filesystem nonce state (sec-001 residual).
      - Mid-session profile mutation.
    """
    if not message:
        return False
    normalized = _normalize_for_match(message)
    # Literal EN whitelist (normalized substring)
    for phrase in MATERIAL_CLAIMS_EN:
        pos = normalized.find(phrase)
        if pos >= 0:
            if _match_is_suppressed(message, normalized, pos, pos + len(phrase)):
                continue
            return True
    # Literal KO whitelist (raw or normalized — Korean rarely benefits from
    # confusables fold but it's cheap to check both)
    for phrase in MATERIAL_CLAIMS_KO:
        pos_raw = message.find(phrase)
        if pos_raw >= 0:
            if _match_is_suppressed(message, normalized, pos_raw, pos_raw + len(phrase)):
                continue
            return True
        pos_norm = normalized.find(phrase)
        if pos_norm >= 0:
            if _match_is_suppressed(message, normalized, pos_norm, pos_norm + len(phrase)):
                continue
            return True
    # Regex layer (paraphrase patterns)
    for pattern in MATERIAL_CLAIM_PATTERNS:
        m = pattern.search(normalized)
        if m:
            if _match_is_suppressed(message, normalized, m.start(), m.end()):
                continue
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

    # v0.11.3 input-layer fix: previously this read `last_assistant_message`
    # directly from the payload, which is NOT a field Claude Code actually
    # provides (real CC payload only includes `transcript_path`). The helper
    # below handles both shapes — legacy string (backwards-compat with the
    # 35+ existing test payloads) and real CC transcript path.
    last_msg = _read_last_assistant_message(payload)
    if not isinstance(last_msg, str):
        # No recoverable last assistant message — fail-open with an audit
        # signal so silent payload-drift is detectable.
        _stderr(
            "could not extract last assistant message from payload "
            "(neither legacy `last_assistant_message` string nor a readable "
            "`transcript_path` with a main-session assistant entry); "
            "passing (fail-open)"
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
