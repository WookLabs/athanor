"""Regression tests for v0.11.5 — CLAUDE.md doc-drift invariants.

Companion-to-runtime-closure framing (Decision D9): the v0.11.2 cuts and
v0.11.3/4 stop-hook fixes closed code-level honesty gaps but left
CLAUDE.md prose at the pre-cut shape. This file locks three drift
classes so prose stays in sync with code:

1.1 — CE skill counts (e.g., "37 CE skills") must equal the actual
      `skills/ce-*` directory population.
1.2 — Hook-event names CLAUDE.md asserts as registered/auto-loaded
      must be present in `hooks/hooks.json`.
1.3 — Sentinel version designators ("v=N") asserted as current must
      match `SENTINEL_PATTERN` in
      `scripts/hooks/stop_verify_claims.py`.

Plus 1.4 — synthetic self-test of the historical-context exemption
filter (HISTORICAL_MARKERS left-context window).

Scanner architecture (Decision D3): every drift class uses a
two-layer scanner — Layer A is a narrow regex matching the current
canonical shape of the claim, Layer B is a broader claim-verb regex
that catches paraphrases. Both layers feed through a shared
left-context HISTORICAL_MARKERS filter (Decision D4) that exempts
attributed historical references from the assertion.

RED-first (Subtask 1 of v0.11.5 plan): tests 1.1/1.2/1.3 carry
`pytest.mark.xfail(strict=False)` because their GREEN state arrives
only after Subtasks 2/3/4 land the corresponding prose corrections.
Test 1.4 is a self-contained exemption-filter regression and runs
normally.

Plan reference: .athanor/sessions/2026-05-21-003/plan.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
SKILLS_DIR = REPO_ROOT / "skills"
STOP_HOOK_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"


# ---------------------------------------------------------------------------
# Shared scanner primitives — Decisions D3, D4
# ---------------------------------------------------------------------------

# Left-context window size used for the HISTORICAL_MARKERS filter. The
# window is the slice of CLAUDE.md text ending at the start of the
# scanned match. ~80 chars is enough to catch "originally N foo, cut to
# M in v0.11.2" patterns without bleeding into unrelated upstream
# sentences.
LEFT_CONTEXT_WINDOW = 80

# Phrases that mark a numeric/structural reference as attributed
# historical context rather than a current claim. Case-insensitive
# substring match against the left-context window.
HISTORICAL_MARKERS = (
    "originally",
    "previously",
    "before v0.11",
    "cut from",
    "v0.11.2 cut",
    "post-v0.11.2",
    "pre-cut",
    "earlier",
    "formerly",
    "초기",
    "이전",
    "당초",
)


def _is_historical(text: str, match_start: int) -> bool:
    """True iff a HISTORICAL_MARKER appears in the left-context window."""
    start = max(0, match_start - LEFT_CONTEXT_WINDOW)
    window = text[start:match_start].lower()
    return any(marker in window for marker in HISTORICAL_MARKERS)


# ---------------------------------------------------------------------------
# Test 1.1 — CE skill count vs. actual skills/ce-* directories
# ---------------------------------------------------------------------------

# Layer A — narrow current-state matcher. Captures the count integer.
# Three lexical shapes covered: "N CE skills", "N ce-* skills",
# "N skills vendored from compound-engineering".
_CE_COUNT_LAYER_A = re.compile(
    r"\b(\d+)\s+(?:"
    r"CE\s+skills?"
    r"|ce-\*\s+skills?"
    r"|skills?\s+vendored\s+from\s+compound-engineering"
    r")\b",
    re.IGNORECASE,
)

# Layer B — broader claim-verb scan: "N skills" within ~60 chars of
# a "compound-engineering" mention. Used to catch paraphrases the
# narrow matcher misses.
_CE_COUNT_LAYER_B = re.compile(r"\b(\d+)\s+skills?\b", re.IGNORECASE)
_COMPOUND_MENTION = re.compile(r"compound-engineering", re.IGNORECASE)


def _scan_ce_counts(text: str) -> list[tuple[int, int]]:
    """Return list of (count, match_start) for non-exempt CE-count claims.

    Combines Layer A + Layer B (deduped by match_start) and filters
    through HISTORICAL_MARKERS.
    """
    hits: dict[int, int] = {}  # match_start -> count

    for m in _CE_COUNT_LAYER_A.finditer(text):
        if _is_historical(text, m.start()):
            continue
        hits[m.start()] = int(m.group(1))

    # Layer B: scan "N skills" then require a compound-engineering
    # mention within +/- 60 chars (proximity filter), and skip Layer-A
    # already-covered spans.
    for m in _CE_COUNT_LAYER_B.finditer(text):
        if m.start() in hits:
            continue
        window_start = max(0, m.start() - 60)
        window_end = min(len(text), m.end() + 60)
        proximity = text[window_start:window_end]
        if not _COMPOUND_MENTION.search(proximity):
            continue
        if _is_historical(text, m.start()):
            continue
        hits[m.start()] = int(m.group(1))

    return [(count, start) for start, count in hits.items()]


def _actual_ce_skill_count() -> int:
    return len(list(SKILLS_DIR.glob("ce-*")))


@pytest.mark.xfail(
    reason="RED-first (Subtask 1 of v0.11.5): GREEN after Subtask 2 prose fix",
    strict=False,
)
def test_claude_md_ce_count_matches_actual_skills_dir() -> None:
    """Every non-exempt CE-count claim in CLAUDE.md must match disk reality."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    actual = _actual_ce_skill_count()
    hits = _scan_ce_counts(text)

    assert hits, (
        "scanner found no CE-count claims in CLAUDE.md — patterns probably "
        "drifted. Inspect _CE_COUNT_LAYER_A / _CE_COUNT_LAYER_B."
    )

    drift = [(c, s) for (c, s) in hits if c != actual]
    assert not drift, (
        f"CLAUDE.md asserts CE skill counts that don't match disk "
        f"(actual: {actual} ce-* dirs under skills/). "
        f"Non-matching claims: {drift!r}"
    )


# ---------------------------------------------------------------------------
# Test 1.2 — Hook event mentions vs. hooks/hooks.json
# ---------------------------------------------------------------------------

# Hook event names Claude Code supports. We scan only these.
_HOOK_EVENT_NAMES = (
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "UserPromptSubmit",
    "SubagentStop",
    "Notification",
    "PreCompact",
)

# Verbs indicating CLAUDE.md is asserting the event is registered by
# athanor's hooks.json (English + Korean).
_REGISTRATION_VERBS = (
    "registers",
    "registered",
    "register",
    "loads",
    "loaded",
    "auto-load",
    "auto-loaded",
    "auto-loads",
    "fires",
    "invokes",
    "invoked",
    "자동 로드",
    "등록",
)

# Negative / contrastive markers — if present in the left context,
# the claim is NOT an athanor-registration assertion. Examples:
# "NOT registered", "would be registered", "rather than register".
_NEGATIVE_MARKERS = (
    "not registered",
    "would be registered",
    "rather than",
    "instead of",
    "could be registered",
    "would need to register",
    "system reminder channel",
    "platform mechanism",
    "claude code platform",
)


def _is_negative_context(text: str, match_start: int) -> bool:
    start = max(0, match_start - 120)
    end = min(len(text), match_start + 200)
    window = text[start:end].lower()
    return any(marker in window for marker in _NEGATIVE_MARKERS)


def _scan_hook_event_claims(text: str) -> list[tuple[str, int]]:
    """Return (event_name, position) for hook-event registration claims."""
    hits: list[tuple[str, int]] = []
    for event in _HOOK_EVENT_NAMES:
        # Layer A: event name within ~100 chars of a registration verb,
        # either direction. We avoid Python `\b` word boundaries here
        # because they collide with Hangul (category Lo): the pattern
        # `\bSessionStart\b` fails when followed by `에` since `t` and
        # `에` are both `\w` to the unicode-aware engine. Instead we
        # require a non-Latin-alphanumeric character on either side
        # (or string boundary).
        boundary_re = rf"(?:^|[^A-Za-z0-9_]){re.escape(event)}(?=$|[^A-Za-z0-9_])"
        for m in re.finditer(boundary_re, text):
            # `m.start()` points at the boundary char (or 0). Realign
            # to the actual event-name start.
            event_start = text.index(event, m.start(), m.end())
            # Reconstruct the m-like object surface used downstream.
            m_start = event_start
            m_end = event_start + len(event)
            class _M:
                def __init__(self, s: int, e: int) -> None:
                    self._s, self._e = s, e
                def start(self) -> int: return self._s
                def end(self) -> int: return self._e
            m = _M(m_start, m_end)
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 100)
            window = text[start:end].lower()
            if not any(verb in window for verb in _REGISTRATION_VERBS):
                continue
            if _is_historical(text, m.start()):
                continue
            if _is_negative_context(text, m.start()):
                continue
            # SessionStart lenience — CLAUDE.md sometimes describes
            # the Claude Code system-reminder / skill-discovery channel
            # for SessionStart in contexts that are NOT hooks.json
            # claims. Those contexts must disambiguate with explicit
            # platform-mechanism language (handled by
            # _NEGATIVE_MARKERS). A bare claim like "SessionStart에
            # 자동 로드된다" / "auto-loaded on SessionStart" without
            # platform-mechanism disambiguation IS a hooks.json
            # registration assertion and must be caught.
            hits.append((event, m.start()))
    return hits


def _registered_hook_events() -> set[str]:
    raw = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    return set(raw.get("hooks", {}).keys())


@pytest.mark.xfail(
    reason="RED-first (Subtask 1 of v0.11.5): GREEN after Subtask 3 prose fix",
    strict=False,
)
def test_claude_md_hook_event_claims_match_hooks_json() -> None:
    """Every hook event CLAUDE.md asserts as registered must exist in hooks.json."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    registered = _registered_hook_events()
    claims = _scan_hook_event_claims(text)

    assert claims, (
        "scanner found no hook-event registration claims in CLAUDE.md — "
        "patterns probably drifted. Inspect _HOOK_EVENT_NAMES / "
        "_REGISTRATION_VERBS."
    )

    unregistered = [(ev, pos) for (ev, pos) in claims if ev not in registered]
    assert not unregistered, (
        f"CLAUDE.md asserts these hook events are registered/auto-loaded, "
        f"but hooks/hooks.json does NOT register them: {unregistered!r}. "
        f"Actually-registered events: {sorted(registered)!r}"
    )


# ---------------------------------------------------------------------------
# Test 1.3 — Sentinel version mentions vs. SENTINEL_PATTERN
# ---------------------------------------------------------------------------

# Extract the version designator from the live SENTINEL_PATTERN source.
# Match shape: `SENTINEL_PATTERN = re.compile(\n    r"...athanor:verification-emission\s+v=N..."`
_SENTINEL_PATTERN_SOURCE_RE = re.compile(
    r"SENTINEL_PATTERN\s*=\s*re\.compile\([^)]*?"
    r"athanor:verification-emission[^)]*?v=(\d+)",
    re.DOTALL,
)


def _current_sentinel_version() -> int:
    src = STOP_HOOK_SCRIPT.read_text(encoding="utf-8")
    m = _SENTINEL_PATTERN_SOURCE_RE.search(src)
    assert m, (
        "could not extract current sentinel version from "
        "stop_verify_claims.py SENTINEL_PATTERN — pattern shape changed?"
    )
    return int(m.group(1))


# Layer A — narrow: `v=N` literal, the canonical shape used in
# CLAUDE.md.
_SENTINEL_VERSION_LAYER_A = re.compile(r"\bv=(\d+)\b")

# Layer B — paraphrase: "version N" / "protocol vN" near
# "sentinel" or "verification-emission".
_SENTINEL_VERSION_LAYER_B = re.compile(
    r"\b(?:version|protocol\s+v)\s*(\d+)\b", re.IGNORECASE
)
_SENTINEL_CONTEXT = re.compile(
    r"sentinel|verification-emission", re.IGNORECASE
)

# Markers that indicate the version is being mentioned in a
# deprecated / historical context.
_SENTINEL_HISTORICAL_MARKERS = HISTORICAL_MARKERS + (
    "legacy",
    "deprecated",
    "rejected",
    "forgeable",
    "was forgeable",
    "no longer",
    "obsolete",
    "기존",
    "구버전",
)

# Markers indicating an active / current assertion (these flag the
# match as a "current" claim we should validate against).
_SENTINEL_CURRENT_MARKERS = (
    "current",
    "active",
    "shipped",
    "required",
    "ships",
    "uses",
    "uses the",
    "prefixes",
    "must prefix",
    "is now",
    "현재",
)


def _scan_sentinel_versions(text: str) -> list[tuple[int, int]]:
    """Return (version_int, match_start) for current sentinel claims."""
    hits: dict[int, int] = {}

    def _is_sentinel_historical(start: int) -> bool:
        window_start = max(0, start - LEFT_CONTEXT_WINDOW)
        window = text[window_start:start].lower()
        return any(m in window for m in _SENTINEL_HISTORICAL_MARKERS)

    def _is_sentinel_current(start: int, end: int) -> bool:
        window_start = max(0, start - 120)
        window_end = min(len(text), end + 120)
        window = text[window_start:window_end].lower()
        return any(m in window for m in _SENTINEL_CURRENT_MARKERS)

    for m in _SENTINEL_VERSION_LAYER_A.finditer(text):
        # Proximity: only count v=N near sentinel/verification-emission
        # context, to avoid false positives like "v=2 was forgeable"
        # versus unrelated "v=1" in changelog snippets.
        window_start = max(0, m.start() - 100)
        window_end = min(len(text), m.end() + 100)
        proximity = text[window_start:window_end]
        if not _SENTINEL_CONTEXT.search(proximity):
            continue
        if _is_sentinel_historical(m.start()):
            continue
        if not _is_sentinel_current(m.start(), m.end()):
            # Neutral mentions (not flagged current) are not asserted
            # as canonical — skip.
            continue
        hits[m.start()] = int(m.group(1))

    for m in _SENTINEL_VERSION_LAYER_B.finditer(text):
        if m.start() in hits:
            continue
        window_start = max(0, m.start() - 100)
        window_end = min(len(text), m.end() + 100)
        proximity = text[window_start:window_end]
        if not _SENTINEL_CONTEXT.search(proximity):
            continue
        if _is_sentinel_historical(m.start()):
            continue
        if not _is_sentinel_current(m.start(), m.end()):
            continue
        hits[m.start()] = int(m.group(1))

    return [(v, s) for s, v in hits.items()]


@pytest.mark.xfail(
    reason="RED-first (Subtask 1 of v0.11.5): GREEN after Subtask 4 prose fix",
    strict=False,
)
def test_claude_md_sentinel_version_matches_pattern() -> None:
    """Every 'current' sentinel-version claim must match SENTINEL_PATTERN."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    current_version = _current_sentinel_version()
    hits = _scan_sentinel_versions(text)

    assert hits, (
        "scanner found no current sentinel-version claims in CLAUDE.md — "
        "patterns probably drifted. Inspect _SENTINEL_VERSION_LAYER_A / "
        "_SENTINEL_VERSION_LAYER_B / _SENTINEL_CURRENT_MARKERS."
    )

    drift = [(v, s) for (v, s) in hits if v != current_version]
    assert not drift, (
        f"CLAUDE.md asserts sentinel version(s) inconsistent with "
        f"SENTINEL_PATTERN (current: v={current_version}). "
        f"Non-matching claims: {drift!r}"
    )


# ---------------------------------------------------------------------------
# Test 1.4 — Historical-context exemption regression (self-test)
# ---------------------------------------------------------------------------

def test_historical_context_exemption_filter(tmp_path: Path) -> None:
    """The HISTORICAL_MARKERS filter must distinguish current vs. historical.

    Build two synthetic CLAUDE-shaped fixtures:
      (a) "37 CE skills" → current claim → scanner reports it.
      (b) "originally 37 CE skills, cut to 33 in v0.11.2" → exempt.
    """
    # Fixture (a) — current claim, no historical marker in left context.
    fixture_current = tmp_path / "CLAUDE_current.md"
    fixture_current.write_text(
        "## Vendored Surface\n\n"
        "athanor absorbs **37 CE skills** from compound-engineering "
        "v3.8.3 under /athanor:ce-*.\n",
        encoding="utf-8",
    )

    # Fixture (b) — same number, attributed historical context.
    fixture_historical = tmp_path / "CLAUDE_historical.md"
    fixture_historical.write_text(
        "## Vendored Surface\n\n"
        "athanor originally absorbed 37 CE skills from compound-engineering, "
        "cut from 37 to 33 in v0.11.2.\n",
        encoding="utf-8",
    )

    current_text = fixture_current.read_text(encoding="utf-8")
    historical_text = fixture_historical.read_text(encoding="utf-8")

    current_hits = _scan_ce_counts(current_text)
    historical_hits = _scan_ce_counts(historical_text)

    # (a) must report the 37 claim.
    assert current_hits, (
        "scanner failed to detect a current '37 CE skills' claim — "
        "Layer A regex is broken."
    )
    assert any(count == 37 for count, _ in current_hits), (
        f"scanner missed the 37 claim in current fixture: {current_hits!r}"
    )

    # (b) must exempt all matches (originally / cut from both in
    # left-context within LEFT_CONTEXT_WINDOW chars).
    assert not historical_hits, (
        f"HISTORICAL_MARKERS filter failed: scanner did not exempt "
        f"attributed historical references in fixture (b). "
        f"Spurious hits: {historical_hits!r}. "
        f"Expected zero — both '37' mentions are in attributed-history "
        f"context ('originally', 'cut from')."
    )
