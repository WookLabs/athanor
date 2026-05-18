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

Known limitations (see docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-
command-mode-plan.md §11 Risk Analysis and the v0.7.8 PR code review):
  - Sentinel forgery: a determined model can emit the sentinel as line 1
    without actually invoking verification. Fix requires evidence-binding
    (transcript event check, HMAC) — design work deferred to v0.7.9+.
  - Paraphrase evasion: literal-substring matching catches the whitelist;
    paraphrases ("CI is green", "verified the suite") slip through. Closing
    requires regex/semantic patterns — deferred.
  - Parent-directory athanor.json hijack: walk-up resolution will silently
    apply an ancestor's `profile: off`. Fix requires explicit project-root
    resolution — deferred.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Sentinel prefix: emission marker from skills/verification-before-completion/SKILL.md.
# Anchored at start of last_assistant_message (first non-whitespace line).
SENTINEL_PATTERN = re.compile(r"^\s*<!--\s*athanor:verification-emission\s+v=")

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

# Module-load invariant: whitelists must be non-empty. An empty list would
# silently disable the gate (every Stop event would pass is_material_claim ->
# False). Surfaced loudly at script import so a regression cannot land
# unnoticed.
assert MATERIAL_CLAIMS_EN, "MATERIAL_CLAIMS_EN must not be empty — empty whitelist silently disables gate"
assert MATERIAL_CLAIMS_KO, "MATERIAL_CLAIMS_KO must not be empty — empty whitelist silently disables gate"

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


def _find_athanor_config() -> Path | None:
    """Locate athanor.json by walking up from CWD.

    Claude Code's command-hook invocation sets the working directory to the
    plugin install root (or the project root for local plugin develops). We
    walk up to support both layouts plus user-projects that have athanor.json
    in a parent dir.

    KNOWN LIMITATION: an ancestor-directory athanor.json silently applies if
    the project has none. v0.7.9+ may switch to explicit project-root
    resolution via $CLAUDE_PROJECT_DIR or git-root detection.
    """
    cur = Path.cwd().resolve()
    # Cap walk depth to avoid runaway on weird filesystems.
    for _ in range(8):
        candidate = cur / ATHANOR_CONFIG_NAME
        if candidate.is_file():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _read_profile() -> tuple[str, Path | None]:
    """Read `hooks.profile` from athanor.json.

    Returns ``(profile, config_path)`` where ``profile`` is one of the
    SUPPORTED_PROFILES values (or "standard" as the default) and ``config_path``
    is the resolved athanor.json path (or None if no config was found).
    Returning the path lets the caller audit WHICH config disabled the gate
    — useful for diagnosing ancestor-directory hijacks.

    Defensive handling:
      - Missing/unreadable config -> ("standard", None)
      - Malformed JSON -> ("standard", config_path)
      - Bad encoding (UnicodeDecodeError, BOM, mojibake) -> ("standard", config_path)
      - `hooks` field is not a dict (e.g., string/null/list) -> ("standard", config_path)
      - Unknown profile value -> ("standard", config_path) with stderr warning
    """
    config_path = _find_athanor_config()
    if config_path is None:
        return ("standard", None)
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        _stderr(
            f"could not read {config_path} ({type(e).__name__}); "
            f"falling back to profile=standard"
        )
        return ("standard", config_path)
    if not isinstance(data, dict):
        _stderr(
            f"{config_path} top-level is not an object; "
            f"falling back to profile=standard"
        )
        return ("standard", config_path)
    hooks_section = data.get("hooks", {})
    if not isinstance(hooks_section, dict):
        _stderr(
            f"{config_path} `hooks` field is not an object "
            f"(got {type(hooks_section).__name__}); falling back to profile=standard"
        )
        return ("standard", config_path)
    profile = hooks_section.get("profile", "standard")
    if not isinstance(profile, str) or profile not in SUPPORTED_PROFILES:
        _stderr(
            f"unknown hooks.profile value {profile!r}; treating as 'standard'. "
            f"Supported values: {sorted(SUPPORTED_PROFILES)}."
        )
        return ("standard", config_path)
    return (profile, config_path)


def has_emission_sentinel(message: str) -> bool:
    """True iff the message's first non-whitespace line is the verification
    emission sentinel `<!-- athanor:verification-emission v=N -->`."""
    if not message:
        return False
    # Match the sentinel only at the start of the message (allowing leading
    # whitespace). A sentinel placed on line 2 after a greeting/heading does
    # NOT count — that's the brittleness trade-off documented in the skill.
    return bool(SENTINEL_PATTERN.match(message))


def is_material_claim(message: str) -> bool:
    """Detect any whitelisted material-claim phrase in the message body.

    Whitelist is the v0.7.7 prompt's combined English + Korean trigger set.
    Matching is case-insensitive for English; Korean is literal.

    Known limitation: literal substring matching can be evaded by paraphrasing
    ("CI is green", "verified the test suite"). Regex/semantic detection is
    v0.7.9+ work — see PR review residuals.
    """
    if not message:
        return False
    lowered = message.lower()
    for phrase in MATERIAL_CLAIMS_EN:
        if phrase in lowered:
            return True
    for phrase in MATERIAL_CLAIMS_KO:
        if phrase in message:
            return True
    return False


def main() -> int:
    payload = _read_stdin_payload()
    if payload is None:
        _stderr("stdin missing or unparseable; passing (fail-open)")
        return 0

    profile, config_path = _read_profile()
    if profile == "off":
        # Audit breadcrumb — makes ancestor-hijack visible. The user (or a
        # future auditor) can see WHICH athanor.json disabled the gate.
        _stderr(
            f"gate disabled by hooks.profile=off in "
            f"{config_path if config_path else '<no config found>'}"
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

    if has_emission_sentinel(last_msg):
        return 0  # silent re-entry skip

    if not is_material_claim(last_msg):
        return 0  # no material claim; nothing to gate

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
