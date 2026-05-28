"""Regression tests for v0.11.5 — doc-drift invariants (extended in v0.11.7 and v0.12.0).

Companion-to-runtime-closure framing (Decision D9): the v0.11.2 cuts and
v0.11.3/4 stop-hook fixes closed code-level honesty gaps but left
CLAUDE.md prose at the pre-cut shape. v0.11.5 locked three drift
classes (1.1/1.2/1.3) so CLAUDE.md prose stays in sync with code.
v0.11.7 extends scope to multiple files (per-file extractor) and adds
two new drift classes (1.5, 1.6) that would have caught B2/B5/B6.

v0.12.0 scope note: the atomic vendored-surface cut reduces the CE skill
count from 33 to 1 (ce-test-browser KEEP per D8). Test 1.1's dynamic
comparison against `_actual_ce_skill_count()` continues to apply — every
non-exempt CE-count claim must match disk reality. Current-tense pre-cut
counts in CLAUDE.md prose are guarded by HISTORICAL_MARKERS exemption
(prefixed with "Originally" or similar) to align with post-cut disk
state. Test 1.2 (hook events) / 1.3 (sentinel version) / 1.5 (stale pin)
/ 1.6 (broken promise) scan athanor-native files and remain unchanged
in scope.

Drift classes:

1.1 — CE skill counts (e.g., "37 CE skills") must equal the actual
      `skills/ce-*` directory population.
1.2 — Hook-event names CLAUDE.md asserts as registered/auto-loaded
      must be present in `hooks/hooks.json`.
1.3 — Sentinel version designators ("v=N") asserted as current must
      match `SENTINEL_PATTERN` in
      `scripts/hooks/stop_verify_claims.py`.
1.4 — Synthetic self-test of the historical-context exemption
      filter (HISTORICAL_MARKERS left-context window) — covers 1.1
      and (v0.11.7) 1.5 / 1.6.
1.5 — (v0.11.7, NEW) Stale version-pin claims of the form
      "v0.N.M+ candidate / work / target" must reference a future
      version, not a version already shipped. Catches B2-class drift
      where carried-forward "v0.11.0+ candidate" header outlives the
      v0.11.0 ship date.
1.6 — (v0.11.7, NEW) Broken-future-promise patterns of the form
      "(v0.N.M)" following promise verbs (wait for / see / after /
      shipped in / in) must not reference an already-shipped version
      without a HISTORICAL_MARKERS exemption. Catches B5/B6-class
      drift where "--new-session flag (v0.8.0)" survives past
      v0.8.0 release without the flag actually landing.

Scanner architecture (Decision D3): every drift class uses a
two-layer scanner — Layer A is a narrow regex matching the current
canonical shape of the claim, Layer B is a broader claim-verb regex
that catches paraphrases. Both layers feed through a shared
left-context HISTORICAL_MARKERS filter (Decision D4) that exempts
attributed historical references from the assertion.

Per-file extractor architecture (v0.11.7, Decision D2): the
`INVARIANT_FILES` tuple of `(label, path, extractor_kind)` triples
lets each scanner work over multiple files with content-type-aware
parsing. Per-extractor helpers (`_extract_markdown`,
`_extract_python_docstring`) handle markdown prose vs. Python
module docstring extraction (via `ast.parse` + `ast.get_docstring`
+ `module.body[0].lineno` for accurate line offsets).

Per-file applicability matrix (v0.11.7):
    | Drift class             | CLAUDE.md | stop_verify | STATE.md | README.md |
    | 1.1 CE count            | YES       | NO          | NO       | YES       |
    | 1.2 Hook event names    | YES       | NO          | NO       | NO        |
    | 1.3 Sentinel version    | YES       | YES         | NO       | NO        |
    | 1.5 Stale version-pin   | YES       | YES         | YES      | YES       |
    | 1.6 Broken-future-promise | YES     | YES         | YES      | YES       |

Plan reference: .athanor/sessions/2026-05-21-004/plan.md (v0.11.7).
Earlier plan: .athanor/sessions/2026-05-21-003/plan.md (v0.11.5 initial).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
SKILLS_DIR = REPO_ROOT / "skills"
STOP_HOOK_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"
README_MD = REPO_ROOT / "README.md"
STATE_MD = REPO_ROOT / "docs" / "STATE.md"
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"

# v0.16.0 CLAUDE.md diet (ST15 retarget): the verbose Stop-hook subsection
# (sentinel-version detail, NFKC normalization, paraphrase regex layer)
# and Spec-then-TDD discipline narrative moved to two archive files. The
# CLAUDE.md `v=N` sentinel claims that lived in those subsections moved
# with them — the per-file CLAUDE.md scan will naturally pytest.skip
# post-diet because no current `v=N` claims remain inline. The drift
# class 1.3 scan must continue to cover the canonical archive locations
# so a stale sentinel-version claim there is still caught.
STOP_HOOK_POSTMORTEM_ARCHIVE = (
    REPO_ROOT / "docs" / "archive" / "stop-hook-postmortem.md"
)
DEFENSE_MECHANISMS_DETAIL_ARCHIVE = (
    REPO_ROOT / "docs" / "archive" / "defense-mechanisms-detail.md"
)


# ---------------------------------------------------------------------------
# Per-file extractor architecture — Decision D2 (v0.11.7)
# ---------------------------------------------------------------------------

# (label, path, extractor_kind) — extractor_kind in {markdown_prose, docstring}.
# CLAUDE.md uses markdown_prose; the stop-hook script uses docstring
# (ast.get_docstring) for content-aware parsing; STATE.md and README.md
# are also markdown_prose.
INVARIANT_FILES: tuple[tuple[str, Path, str], ...] = (
    ("CLAUDE.md", CLAUDE_MD, "markdown_prose"),
    (
        "stop_verify_claims",
        STOP_HOOK_SCRIPT,
        "docstring",
    ),
    ("STATE.md", STATE_MD, "markdown_prose"),
    ("README.md", README_MD, "markdown_prose"),
    # v0.16.0 ST15 retarget: verbose Stop-hook narrative + sentinel-version
    # detail moved to these archive files. Cover them for the same drift
    # classes (1.3 sentinel-version, 1.5 stale-pin, 1.6 broken-promise)
    # that previously scanned only the inline CLAUDE.md prose.
    (
        "stop-hook-postmortem",
        STOP_HOOK_POSTMORTEM_ARCHIVE,
        "markdown_prose",
    ),
    (
        "defense-mechanisms-detail",
        DEFENSE_MECHANISMS_DETAIL_ARCHIVE,
        "markdown_prose",
    ),
)


def _extract_markdown(path: Path) -> tuple[str, int]:
    """Return (text, line_offset) for a markdown file.

    `line_offset` is the source-file line of the first character of
    the extracted text — for a whole-file markdown read this is
    always line 1. A drift hit at local line N in the extracted text
    maps to source-file line `line_offset + N - 1` = N.
    """
    return path.read_text(encoding="utf-8"), 1


def _extract_python_docstring(path: Path) -> tuple[str, int]:
    """Return (docstring_raw_source, line_offset) for a Python module docstring.

    This helper extracts the RAW SOURCE TEXT of the module docstring
    (the bytes between the opening and closing triple-quote in the
    file), NOT the AST-parsed string value. The raw source preserves
    line breaks 1-to-1 with the file, which makes accurate
    source-line reporting possible even when the docstring contains
    embedded escape sequences (`\\n`, `\\t`) that the AST parser
    would otherwise expand into real newlines.

    `line_offset` is the source-file line of the docstring's OPENING
    triple-quote (= `tree.body[0].lineno`, 1-based). The raw source
    bytes returned start AT THE OPENING TRIPLE-QUOTE line (the quote
    is on local line 1 of the extracted text, same as the source
    file). A drift hit at docstring-local line N maps to source-file
    line `line_offset + N - 1` (1-based).

    Raises ValueError if the module has no docstring or if parsing
    fails.
    """
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    if not tree.body or not isinstance(tree.body[0], ast.Expr):
        raise ValueError(f"no module docstring in {path}")
    body0 = tree.body[0]
    if (
        not isinstance(body0.value, ast.Constant)
        or not isinstance(body0.value.value, str)
    ):
        raise ValueError(f"module body[0] is not a docstring in {path}")
    start_line = body0.lineno  # 1-based opening-quote line
    end_line = body0.end_lineno  # 1-based closing-quote line
    if end_line is None:
        raise ValueError(f"end_lineno unavailable for {path}")
    src_lines = src.splitlines(keepends=True)
    # 1-based slice [start_line, end_line] → 0-based [start_line-1, end_line)
    raw = "".join(src_lines[start_line - 1 : end_line])
    return raw, start_line


def _extract(path: Path, kind: str) -> tuple[str, int]:
    """Dispatch to the appropriate per-content-type extractor."""
    if kind == "markdown_prose":
        return _extract_markdown(path)
    if kind == "docstring":
        return _extract_python_docstring(path)
    raise ValueError(f"unknown extractor_kind: {kind!r}")


def _line_for_offset(text: str, offset: int, line_offset_base: int) -> int:
    """Return 1-based source-file line for a char offset in extracted text.

    `line_offset_base` is the source-file line of the first character
    of the extracted text (1-based, from `_extract_*` helpers).
    A char offset N in the extracted text falls on local line
    `text[:offset].count("\\n") + 1`; the corresponding source-file
    line is `line_offset_base + local_line - 1`.
    """
    local_line = text[:offset].count("\n") + 1
    return line_offset_base + local_line - 1


def _snippet(text: str, offset: int, width: int = 80) -> str:
    """Return a short single-line snippet centered on the match offset."""
    start = max(0, offset - width // 2)
    end = min(len(text), offset + width // 2)
    return text[start:end].replace("\n", " \\n ").strip()


# ---------------------------------------------------------------------------
# Shared scanner primitives — Decisions D3, D4
# ---------------------------------------------------------------------------

# Left-context window size used for the HISTORICAL_MARKERS filter. The
# window is the slice of file text ending at the start of the
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


# Files for each drift class — per-file applicability matrix (v0.11.7).
# Use file labels (not paths) so test IDs are readable.
_MATRIX_11 = ("CLAUDE.md", "README.md")
_MATRIX_12 = ("CLAUDE.md",)
# v0.16.0 ST15 retarget: extend 1.3 (sentinel-version drift) scan to the
# two archive files that now canonically carry the verbose Stop-hook
# narrative. CLAUDE.md remains in scope (the lite summary still carries
# a `v=2 nonce=...` mention in line 133's emission-sentinel reference).
_MATRIX_13 = (
    "CLAUDE.md",
    "stop_verify_claims",
    "stop-hook-postmortem",
    "defense-mechanisms-detail",
)


def _files_for_labels(labels: tuple[str, ...]) -> tuple[tuple[str, Path, str], ...]:
    by_label = {label: (label, path, kind) for label, path, kind in INVARIANT_FILES}
    return tuple(by_label[label] for label in labels if label in by_label)


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


@pytest.mark.parametrize(
    "label,path,kind",
    _files_for_labels(_MATRIX_11),
    ids=[label for label, _, _ in _files_for_labels(_MATRIX_11)],
)
def test_invariant_file_ce_count_matches_actual_skills_dir(
    label: str, path: Path, kind: str
) -> None:
    """Every non-exempt CE-count claim must match disk reality."""
    text, line_offset = _extract(path, kind)
    actual = _actual_ce_skill_count()
    hits = _scan_ce_counts(text)

    if not hits:
        # README.md may not contain any CE-count claim — that's
        # legitimate for files where the matrix says YES but the
        # surface doesn't currently exist. Skip rather than fail.
        pytest.skip(
            f"no CE-count claims found in {label} ({path}); per-file "
            "applicability matrix declares this file in scope but no "
            "current claims to validate."
        )

    drift = []
    for count, start in hits:
        if count == actual:
            continue
        line = _line_for_offset(text, start, line_offset)
        drift.append(
            {
                "label": label,
                "line": line,
                "count": count,
                "actual": actual,
                "snippet": _snippet(text, start),
                "rule": "1.1-ce-count",
                "source_file": str(path.relative_to(REPO_ROOT)),
            }
        )

    assert not drift, (
        f"{label} asserts CE skill counts that don't match disk "
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
            m_start = event_start
            m_end = event_start + len(event)
            start = max(0, m_start - 100)
            end = min(len(text), m_end + 100)
            window = text[start:end].lower()
            if not any(verb in window for verb in _REGISTRATION_VERBS):
                continue
            if _is_historical(text, m_start):
                continue
            if _is_negative_context(text, m_start):
                continue
            hits.append((event, m_start))
    return hits


def _registered_hook_events() -> set[str]:
    raw = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    return set(raw.get("hooks", {}).keys())


@pytest.mark.parametrize(
    "label,path,kind",
    _files_for_labels(_MATRIX_12),
    ids=[label for label, _, _ in _files_for_labels(_MATRIX_12)],
)
def test_invariant_file_hook_event_claims_match_hooks_json(
    label: str, path: Path, kind: str
) -> None:
    """Every hook event asserted as registered must exist in hooks.json."""
    text, line_offset = _extract(path, kind)
    registered = _registered_hook_events()
    claims = _scan_hook_event_claims(text)

    assert claims, (
        f"scanner found no hook-event registration claims in {label} — "
        "patterns probably drifted. Inspect _HOOK_EVENT_NAMES / "
        "_REGISTRATION_VERBS."
    )

    unregistered = []
    for ev, pos in claims:
        if ev in registered:
            continue
        line = _line_for_offset(text, pos, line_offset)
        unregistered.append(
            {
                "label": label,
                "line": line,
                "event": ev,
                "snippet": _snippet(text, pos),
                "rule": "1.2-hook-event",
                "source_file": str(path.relative_to(REPO_ROOT)),
            }
        )
    assert not unregistered, (
        f"{label} asserts these hook events are registered/auto-loaded, "
        f"but hooks/hooks.json does NOT register them: {unregistered!r}. "
        f"Actually-registered events: {sorted(registered)!r}"
    )


# ---------------------------------------------------------------------------
# Test 1.3 — Sentinel version mentions vs. SENTINEL_PATTERN
# ---------------------------------------------------------------------------

# Extract the version designator from the live SENTINEL_PATTERN source.
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


@pytest.mark.parametrize(
    "label,path,kind",
    _files_for_labels(_MATRIX_13),
    ids=[label for label, _, _ in _files_for_labels(_MATRIX_13)],
)
def test_invariant_file_sentinel_version_matches_pattern(
    label: str, path: Path, kind: str
) -> None:
    """Every 'current' sentinel-version claim must match SENTINEL_PATTERN."""
    text, line_offset = _extract(path, kind)
    current_version = _current_sentinel_version()
    hits = _scan_sentinel_versions(text)

    if not hits:
        pytest.skip(
            f"no current sentinel-version claims found in {label} "
            f"({path}); per-file applicability matrix declares the file "
            "in scope but no current claims to validate."
        )

    drift = []
    for v, start in hits:
        if v == current_version:
            continue
        line = _line_for_offset(text, start, line_offset)
        drift.append(
            {
                "label": label,
                "line": line,
                "version": v,
                "current": current_version,
                "snippet": _snippet(text, start),
                "rule": "1.3-sentinel-version",
                "source_file": str(path.relative_to(REPO_ROOT)),
            }
        )
    assert not drift, (
        f"{label} asserts sentinel version(s) inconsistent with "
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


def test_historical_context_exemption_filter_stale_version_pin(tmp_path: Path) -> None:
    """1.4b: HISTORICAL_MARKERS exemption must apply to stale-version-pin scans.

    (a) "v0.8.0+ work" without history marker → current claim → flagged.
    (b) "originally promised v0.8.0+ work, corrected in v0.10.3" → exempt.
    """
    fixture_current = tmp_path / "STATE_current.md"
    fixture_current.write_text(
        "## Residual notes\n\n"
        "Sentence-level attribution is v0.8.0+ work.\n",
        encoding="utf-8",
    )
    fixture_historical = tmp_path / "STATE_historical.md"
    fixture_historical.write_text(
        "## Residual notes\n\n"
        "Originally promised as v0.8.0+ work, corrected in v0.10.3 R3.\n",
        encoding="utf-8",
    )

    cur_text = fixture_current.read_text(encoding="utf-8")
    hist_text = fixture_historical.read_text(encoding="utf-8")

    cur_hits = _scan_stale_version_pins(cur_text, current_version=(0, 11, 6))
    hist_hits = _scan_stale_version_pins(hist_text, current_version=(0, 11, 6))

    assert cur_hits, (
        "scanner failed to detect a current 'v0.8.0+ work' stale pin "
        f"in fixture (a) — Layer A regex broken. cur_hits={cur_hits!r}"
    )
    assert not hist_hits, (
        f"HISTORICAL_MARKERS filter failed for 1.5 stale-pin: scanner "
        f"did not exempt attributed historical reference. Spurious hits: "
        f"{hist_hits!r}. Expected zero — 'originally' + 'corrected in' "
        f"in left context."
    )


def test_historical_context_exemption_filter_broken_promise(tmp_path: Path) -> None:
    """1.4c: HISTORICAL_MARKERS exemption must apply to broken-promise scans.

    (a) "wait for the --new-session flag (v0.8.0)" → broken promise → flagged.
    (b) "reclassified v0.11.7 as broken-promise (v0.8.0)" → exempt.
    """
    fixture_current = tmp_path / "session_lookup.md"
    fixture_current.write_text(
        "## Stale-session announcement\n\n"
        "create a new session manually or wait for the --new-session flag (v0.8.0).\n",
        encoding="utf-8",
    )
    fixture_historical = tmp_path / "session_lookup_fixed.md"
    fixture_historical.write_text(
        "## Stale-session announcement\n\n"
        "create a new session manually (the --new-session flag was originally "
        "promised in v0.8.0 release notes but never implemented; reclassified "
        "v0.11.7 as broken-promise — no current implementation target).\n",
        encoding="utf-8",
    )

    cur_text = fixture_current.read_text(encoding="utf-8")
    hist_text = fixture_historical.read_text(encoding="utf-8")

    cur_hits = _scan_broken_future_promises(cur_text, current_version=(0, 11, 6))
    hist_hits = _scan_broken_future_promises(hist_text, current_version=(0, 11, 6))

    assert cur_hits, (
        "scanner failed to detect a broken-promise '(v0.8.0)' reference "
        f"in fixture (a) — pattern regex broken. cur_hits={cur_hits!r}"
    )
    assert not hist_hits, (
        f"HISTORICAL_MARKERS filter failed for 1.6 broken-promise: scanner "
        f"did not exempt the reclassified retrospective mention. Spurious "
        f"hits: {hist_hits!r}."
    )


# ---------------------------------------------------------------------------
# Test 1.5 (v0.11.7, NEW) — stale version-pin scanner
# ---------------------------------------------------------------------------
#
# Pattern: "v0.N.M+ candidate" / "v0.N.M+ work" / "v0.N.M+ target".
# If (N, M) <= current shipped version AND no HISTORICAL_MARKERS context,
# the pin is stale (the referenced "future" version has already shipped).
#
# Catches B2-class drift: `stop_verify_claims.py` docstring carried the
# "Residual known limitations (carried forward to v0.11.0+)" header into
# v0.11.6 (post-v0.11.0).

# Layer A — narrow: "v0.N.M+ {candidate,work,target}"
_STALE_VERSION_PIN_LAYER_A = re.compile(
    r"v0\.(\d+)\.(\d+)\+\s+(?:candidate|work|target)",
    re.IGNORECASE,
)

# Layer B — paraphrase: "carried forward to v0.N.M+" near
# "Residual" / "known limitation"
_STALE_VERSION_PIN_LAYER_B = re.compile(
    r"carried\s+forward\s+to\s+v0\.(\d+)\.(\d+)\+",
    re.IGNORECASE,
)
_RESIDUAL_CONTEXT = re.compile(r"Residual|known\s+limitation", re.IGNORECASE)


def _current_plugin_version() -> tuple[int, int, int]:
    """Read .claude-plugin/plugin.json and return (major, minor, patch)."""
    raw = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    parts = raw["version"].split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


# Phrases that mark a stale-version-pin claim as legitimate retrospective
# narration rather than a current carry. Substring match,
# case-insensitive, against the LEFT_CONTEXT_WINDOW (+ extended right
# context for "corrected in"-style closures that appear after).
_STALE_PIN_HISTORICAL_MARKERS = HISTORICAL_MARKERS + (
    "originally promised",
    "originally claimed",
    "corrected in",
    "honestly corrected",
    "reclassified",
    "broken-promise",
    "shipped in",
    "landed in",
    "no longer",
)


def _is_stale_pin_historical(text: str, match_start: int, match_end: int) -> bool:
    """True iff a stale-pin HISTORICAL_MARKER appears in context window.

    Checks both LEFT_CONTEXT_WINDOW chars before the match AND ~80 chars
    after (catches "X is v0.8.0+ work, corrected in v0.10.3" pattern).
    """
    left_start = max(0, match_start - LEFT_CONTEXT_WINDOW)
    right_end = min(len(text), match_end + LEFT_CONTEXT_WINDOW)
    window = text[left_start:right_end].lower()
    return any(marker in window for marker in _STALE_PIN_HISTORICAL_MARKERS)


def _scan_stale_version_pins(
    text: str, current_version: tuple[int, int, int]
) -> list[dict]:
    """Return list of stale-pin hits.

    Each hit: {"version": (0, minor, patch), "start": int, "rule": str}.
    Filter through HISTORICAL_MARKERS + checks the referenced version
    is <= the current shipped version. The regex hard-codes "v0."
    (every athanor release through v0.11.x is 0.minor.patch); group(1)
    captures the minor number, group(2) captures the patch number.
    """
    # athanor versions are 0.minor.patch; compare on (minor, patch).
    current_minor_patch = (current_version[1], current_version[2])
    hits: list[dict] = []
    seen_starts: set[int] = set()

    for m in _STALE_VERSION_PIN_LAYER_A.finditer(text):
        if m.start() in seen_starts:
            continue
        if _is_stale_pin_historical(text, m.start(), m.end()):
            continue
        minor, patch = int(m.group(1)), int(m.group(2))
        if (minor, patch) > current_minor_patch:
            # Genuine future-version pin — not stale.
            continue
        seen_starts.add(m.start())
        hits.append(
            {
                "version": (0, minor, patch),
                "start": m.start(),
                "rule": "1.5-stale-pin-A",
            }
        )

    for m in _STALE_VERSION_PIN_LAYER_B.finditer(text):
        if m.start() in seen_starts:
            continue
        # Layer B requires nearby Residual/known-limitation context.
        proximity_start = max(0, m.start() - 80)
        proximity_end = min(len(text), m.end() + 80)
        if not _RESIDUAL_CONTEXT.search(text[proximity_start:proximity_end]):
            continue
        if _is_stale_pin_historical(text, m.start(), m.end()):
            continue
        minor, patch = int(m.group(1)), int(m.group(2))
        if (minor, patch) > current_minor_patch:
            continue
        seen_starts.add(m.start())
        hits.append(
            {
                "version": (0, minor, patch),
                "start": m.start(),
                "rule": "1.5-stale-pin-B",
            }
        )

    return hits


@pytest.mark.parametrize(
    "label,path,kind",
    INVARIANT_FILES,
    ids=[label for label, _, _ in INVARIANT_FILES],
)
def test_invariant_files_no_stale_version_pin(
    label: str, path: Path, kind: str
) -> None:
    """No "v0.N.M+ candidate/work/target" pin should reference a shipped version."""
    text, line_offset = _extract(path, kind)
    current_version = _current_plugin_version()
    hits = _scan_stale_version_pins(text, current_version)

    if not hits:
        return  # legitimate empty set — no claims, no drift

    drifts = []
    for h in hits:
        line = _line_for_offset(text, h["start"], line_offset)
        drifts.append(
            {
                "label": label,
                "line": line,
                "version": h["version"],
                "current": current_version,
                "snippet": _snippet(text, h["start"]),
                "rule": h["rule"],
                "source_file": str(path.relative_to(REPO_ROOT)),
            }
        )

    assert not drifts, (
        f"{label} contains stale version-pin claims (current shipped "
        f"version: {current_version}). Each match references a version "
        f"<= current with no HISTORICAL_MARKERS exemption. Drifts: "
        f"{drifts!r}"
    )


# ---------------------------------------------------------------------------
# Test 1.6 (v0.11.7, NEW) — broken-future-promise scanner
# ---------------------------------------------------------------------------
#
# Pattern: parenthetical "(v0.N.M)" following promise verbs like
# "wait for X (v0.N.M)" / "see Y (v0.N.M)" / "shipped in (v0.N.M)".
# If (N, M) <= current shipped version AND no HISTORICAL_MARKERS context,
# the promise is broken (the named version shipped without the feature).
#
# Catches B5/B6-class drift:
#   - CLAUDE.md:87 "wait for the --new-session flag (v0.8.0)"
#   - CLAUDE.md:229 "Sentence-level attributed-history detection is
#     v0.8.0+ work" — also caught by 1.5 (stale-pin), but the broader
#     "(v0.8.0)" parenthetical form lives elsewhere
#   - skills/discuss/SKILL.md:52 same broken-promise text

# Promise verbs / phrases — the parenthetical follows within ~80 chars.
# Anchored with word-boundary regex (built in `_PROMISE_VERB_RE` below)
# so short verbs like "in" don't match as a substring of "pipeline" or
# "version-pin". Multi-word phrases like "wait for" are matched as
# literal substrings since the words themselves are content-word
# boundaries — the entry "wait for" is implicitly bounded by spaces.
_PROMISE_VERBS = (
    "wait for",
    "waiting for",
    "see",
    "after",
    "shipped in",
    "ships in",
    "lands in",
    "deferred to",
    "target",
)

# Word-boundary regex of promise verbs. Each entry's word characters
# get `\b...\b` wrapping; multi-word entries become `\bfoo\s+bar\b`.
_PROMISE_VERB_RE = re.compile(
    "|".join(
        r"\b" + r"\s+".join(map(re.escape, verb.split())) + r"\b"
        for verb in _PROMISE_VERBS
    ),
    re.IGNORECASE,
)

_BROKEN_PROMISE_PARENTHETICAL = re.compile(r"\(v0\.(\d+)\.(\d+)\)")


# Phrases that mark a "(v0.N.M)" parenthetical as legitimate retrospective
# narration rather than a current promise carry.
_BROKEN_PROMISE_HISTORICAL_MARKERS = HISTORICAL_MARKERS + (
    "originally promised",
    "originally claimed",
    "corrected in",
    "honestly corrected",
    "reclassified",
    "broken-promise",
    "release notes",
    "promised in",
    "landed in",
    "shipped in",
    "shipped without",
    "but never implemented",
    "no current implementation target",
    "honesty-arc",
)


def _is_broken_promise_historical(text: str, start: int, end: int) -> bool:
    """True iff a HISTORICAL_MARKER appears in the ~80-char window around."""
    left_start = max(0, start - LEFT_CONTEXT_WINDOW)
    right_end = min(len(text), end + LEFT_CONTEXT_WINDOW)
    window = text[left_start:right_end].lower()
    return any(marker in window for marker in _BROKEN_PROMISE_HISTORICAL_MARKERS)


def _has_promise_verb_before(text: str, match_start: int) -> bool:
    """True iff a promise verb appears in the ~80-char left context.

    Uses word-boundary regex via `_PROMISE_VERB_RE` so short verbs
    like "in" do not match substrings of "pipeline" or "version-pin".
    """
    left_start = max(0, match_start - LEFT_CONTEXT_WINDOW)
    window = text[left_start:match_start]
    return _PROMISE_VERB_RE.search(window) is not None


def _scan_broken_future_promises(
    text: str, current_version: tuple[int, int, int]
) -> list[dict]:
    """Return list of broken-promise hits.

    Each hit: {"version": (0, minor, patch), "start": int}.
    Filter:
      - Must have a promise verb in left context.
      - Referenced version's (minor, patch) <= current's (minor, patch).
      - No HISTORICAL_MARKERS in surrounding window.

    The regex hard-codes "v0." (every athanor release through v0.11.x
    is 0.minor.patch); group(1) is minor, group(2) is patch.
    """
    current_minor_patch = (current_version[1], current_version[2])
    hits: list[dict] = []

    for m in _BROKEN_PROMISE_PARENTHETICAL.finditer(text):
        minor, patch = int(m.group(1)), int(m.group(2))
        if (minor, patch) > current_minor_patch:
            continue  # genuine future promise
        if not _has_promise_verb_before(text, m.start()):
            continue
        if _is_broken_promise_historical(text, m.start(), m.end()):
            continue
        hits.append({"version": (0, minor, patch), "start": m.start()})

    return hits


@pytest.mark.parametrize(
    "label,path,kind",
    INVARIANT_FILES,
    ids=[label for label, _, _ in INVARIANT_FILES],
)
def test_invariant_files_no_broken_future_promise(
    label: str, path: Path, kind: str
) -> None:
    """No "(v0.N.M)" parenthetical following a promise verb should reference
    an already-shipped version without a HISTORICAL_MARKERS exemption."""
    text, line_offset = _extract(path, kind)
    current_version = _current_plugin_version()
    hits = _scan_broken_future_promises(text, current_version)

    if not hits:
        return

    drifts = []
    for h in hits:
        line = _line_for_offset(text, h["start"], line_offset)
        drifts.append(
            {
                "label": label,
                "line": line,
                "version": h["version"],
                "current": current_version,
                "snippet": _snippet(text, h["start"]),
                "rule": "1.6-broken-promise",
                "source_file": str(path.relative_to(REPO_ROOT)),
            }
        )

    assert not drifts, (
        f"{label} contains broken-future-promise references (current "
        f"shipped version: {current_version}). Each match references a "
        f"version <= current following a promise verb, with no "
        f"HISTORICAL_MARKERS exemption. Drifts: {drifts!r}"
    )
