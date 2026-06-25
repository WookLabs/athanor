"""Regression — output.language directive injection + interpretation contract lock.

Locks the v0.18.8 `output.language` feature (presentation-language preference,
distinct axis from `triggers.language`) across three surfaces:

1. **Config axis existence + default polarity.** `athanor.json`,
   `templates/athanor.json`, and `schemas/athanor-config.schema.json` all carry
   the `output.language` key. The TEMPLATE value is `"en"` (the shipped English
   default that must never silently flip), and the repo-local ROOT value is
   `"ko"` (this repo's ko preference).

2. **Directive injection evidence.** Each of the 9 Thin-Leader SKILL.md files
   names `output.language` at least once, proving the leader-side
   Present-to-User directive was injected.

3. **Interpretation contract.** `skills/setup/SKILL.md` is the single source of
   truth for interpretation: it carries the canonical `jq -r '.output.language`
   snippet and an `en` fallback.

It also locks two **absolute-weakening guards** (high-value anchors that the
output-language edits must not have stripped) and runs a **stop-phrase tone
smoke** (Step 5.7): the user-facing final-report template text in the 6 skills
that emit completion reports must not contain MATERIAL_CLAIMS_KO completion-claim
literals as *output* text. Those literals legitimately appear inside backticks in
directive prose that tells the leader to AVOID them — the smoke heuristic
distinguishes that directive-quoting context from bare output-template text.

Static text reads only — no subprocess, no network, no file mutation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ROOT_CONFIG = REPO_ROOT / "athanor.json"
TEMPLATE_CONFIG = REPO_ROOT / "templates" / "athanor.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "athanor-config.schema.json"
SETUP_SKILL = REPO_ROOT / "skills" / "setup" / "SKILL.md"
REVIEW_SKILL = REPO_ROOT / "skills" / "review" / "SKILL.md"
LFG_SKILL = REPO_ROOT / "skills" / "lfg" / "SKILL.md"
LFG_GOAL_SKILL = REPO_ROOT / "skills" / "lfg-goal" / "SKILL.md"
# The authoritative Korean completion-claim list the live Stop hook enforces;
# the test's MATERIAL_CLAIMS_KO must stay a strict subset of it.
STOP_HOOK_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"
# A reference doc (not a SKILL.md) that also quotes completion-claim literals
# inside backticks; included in the smoke corpus so its claim references stay
# directive-quoted under the tightened heuristic.
MULTI_STATUS_REF = REPO_ROOT / "skills" / "work" / "references" / "multi-status.md"

# The 9 Thin-Leader skills that must carry the output.language directive.
DIRECTIVE_SKILLS = (
    "plan",
    "review",
    "work",
    "lfg",
    "lfg-goal",
    "analyze",
    "debug",
    "discuss",
    "setup",
)

# The 6 skills whose SKILL.md bodies contain a user-facing final-report template
# (and therefore must not leak completion-claim literals as output text).
STOP_PHRASE_SKILLS = ("work", "lfg", "lfg-goal", "review", "analyze", "debug")

# Korean material-claim literals the Stop hook treats as completion claims.
#
# MAJOR-2 (P3): widened beyond the original 5-element subset to add the
# merge/deploy/review completion verbs a Korean pipeline-completion summary
# (/athanor:lfg Step 9.5, /athanor:lfg-goal terminal) would most likely reach
# for. This tuple MUST stay a *strict subset of* the hook's MATERIAL_CLAIMS_KO
# in scripts/hooks/stop_verify_claims.py — the smoke must never claim to catch
# more than the live hook. test_material_claims_ko_is_subset_of_hook locks that.
MATERIAL_CLAIMS_KO = (
    "완료했습니다",
    "통과했습니다",
    "수정 완료",
    "구현 완료",
    "적용 완료",
    # MAJOR-2 additions — merge/deploy/review/test completion verbs.
    "머지 완료",
    "배포 완료",
    "리뷰 완료",
    "테스트 통과",
    "머지했습니다",
    "배포됨",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _skill_path(name: str) -> Path:
    return REPO_ROOT / "skills" / name / "SKILL.md"


# --------------------------------------------------------------------------- #
# (a) Config axis existence + default polarity (template==en, root==ko, schema) #
# --------------------------------------------------------------------------- #


def test_output_language_template_default_is_en():
    """templates/athanor.json output.language locks the English default."""
    cfg = _load_json(TEMPLATE_CONFIG)
    assert "output" in cfg, "templates/athanor.json missing 'output' object"
    assert cfg["output"].get("language") == "en", (
        "templates/athanor.json output.language must be 'en' (shipped English "
        f"default must not silently flip); got {cfg['output'].get('language')!r}"
    )


def test_output_language_root_config_is_ko():
    """athanor.json (this repo) output.language is the repo-local ko setting."""
    cfg = _load_json(ROOT_CONFIG)
    assert "output" in cfg, "athanor.json missing 'output' object"
    assert cfg["output"].get("language") == "ko", (
        "athanor.json output.language must be 'ko' (this repo's preference); "
        f"got {cfg['output'].get('language')!r}"
    )


def test_output_language_schema_key_with_enum():
    """Schema declares output.properties.language with a ko+en enum."""
    schema = _load_json(SCHEMA_PATH)
    output = schema["properties"]["output"]
    language = output["properties"]["language"]
    enum = language.get("enum")
    assert enum is not None, "schema output.language must declare an enum"
    assert "ko" in enum and "en" in enum, (
        f"schema output.language enum must contain ko and en; got {enum!r}"
    )


# --------------------------------------------------------------------------- #
# (b) Directive injection — all 9 skills name output.language                  #
# --------------------------------------------------------------------------- #


# The canonical interpretation section name. The 8 non-setup skills must point
# at it (delimiter-agnostic — citation styles vary, but this section-name string
# is identical everywhere); setup IS the producer and carries the heading itself.
CANONICAL_POINTER = "output.language 해석 (canonical)"


def test_all_nine_skills_carry_output_language_directive():
    """Each of the 9 Thin-Leader skills references output.language ≥ once,
    and each of the 8 non-setup skills cites the canonical interpretation
    section by name (consumer→producer pointer)."""
    missing = [
        name
        for name in DIRECTIVE_SKILLS
        if "output.language" not in _read(_skill_path(name))
    ]
    assert not missing, (
        "these skills are missing the output.language directive: " f"{missing}"
    )
    missing_pointer = [
        name
        for name in DIRECTIVE_SKILLS
        if name != "setup" and CANONICAL_POINTER not in _read(_skill_path(name))
    ]
    assert not missing_pointer, (
        "these non-setup skills are missing the canonical-pointer substring "
        f"{CANONICAL_POINTER!r}: {missing_pointer}"
    )


# --------------------------------------------------------------------------- #
# (c) Interpretation contract — setup SKILL.md jq snippet + en fallback        #
# --------------------------------------------------------------------------- #


def test_setup_skill_has_canonical_jq_snippet():
    """setup SKILL.md carries the canonical jq -r '.output.language interpreter
    under the canonical section heading (producer/consumer co-lock)."""
    body = _read(SETUP_SKILL)
    assert "jq -r '.output.language" in body, (
        "setup SKILL.md must carry the canonical jq -r '.output.language "
        "interpretation snippet (single source of truth)"
    )
    assert "### output.language 해석 (canonical)" in body, (
        "setup SKILL.md must declare the canonical heading "
        "'### output.language 해석 (canonical)' that the 8 consumer skills "
        "point at (producer/consumer co-lock)"
    )


def test_setup_skill_has_en_fallback():
    """setup SKILL.md interpretation contract falls back to en (OUTPUT_LANG=en)."""
    body = _read(SETUP_SKILL)
    assert "OUTPUT_LANG=en" in body, (
        "setup SKILL.md must declare the en fallback (OUTPUT_LANG=en) for "
        "absent/malformed/unsupported output.language values"
    )


# --------------------------------------------------------------------------- #
# (d) Absolute-weakening guards — anchors the output edits must not have lost  #
# --------------------------------------------------------------------------- #


def test_review_skill_retains_report_anchors():
    """review SKILL.md keeps its Executive Summary + Lens Scores headings."""
    body = _read(REVIEW_SKILL)
    assert "## Executive Summary" in body, (
        "review SKILL.md lost the '## Executive Summary' anchor"
    )
    assert "## Lens Scores" in body, (
        "review SKILL.md lost the '## Lens Scores' anchor"
    )


def test_lfg_skill_retains_done_sentinel():
    """lfg SKILL.md keeps the <promise>DONE</promise> completion sentinel."""
    body = _read(LFG_SKILL)
    assert "<promise>DONE</promise>" in body, (
        "lfg SKILL.md lost the <promise>DONE</promise> sentinel"
    )


# --------------------------------------------------------------------------- #
# (e) Stop-phrase tone smoke (Step 5.7)                                        #
# --------------------------------------------------------------------------- #

# Directive-context markers: a line bearing one of these is telling the leader
# to AVOID / instead-use / re-tone the claim, not emitting it as output.
_DIRECTIVE_MARKERS = ("회피", "대신", "어조", "금지")


# Max char distance from an occurrence to a directive marker for the marker
# to be considered "adjacent" (and thus to license a bare-looking occurrence).
_MARKER_PROXIMITY = 30


def _occurrence_is_directive_quote(line: str, literal: str) -> bool:
    """True iff EVERY occurrence of `literal` on `line` is directive-quoting.

    Per-occurrence heuristic (kept deliberately simple — see module docstring).
    An individual occurrence is directive-quoting iff:
      * it lies inside a backtick span (`…`), OR
      * a directive marker (회피/대신/어조/금지) occurs within
        ``_MARKER_PROXIMITY`` chars of the occurrence on that line.
    A real completion-report output template would print the literal bare
    (no backticks, no nearby avoid-directive marker) — that is what we flag.

    The function returns False if ANY occurrence fails the per-occurrence test,
    so a line that backtick-quotes a first occurrence but prints a second one
    bare is correctly flagged.
    """
    backtick_spans = [
        (m.start(), m.end()) for m in re.finditer(r"`[^`]*`", line)
    ]
    marker_positions = [
        m.start()
        for marker in _DIRECTIVE_MARKERS
        for m in re.finditer(re.escape(marker), line)
    ]
    for occ in re.finditer(re.escape(literal), line):
        start, end = occ.start(), occ.end()
        in_backticks = any(b0 <= start < b1 for b0, b1 in backtick_spans)
        near_marker = any(
            min(abs(pos - start), abs(pos - end)) <= _MARKER_PROXIMITY
            for pos in marker_positions
        )
        if not (in_backticks or near_marker):
            return False
    return True


def test_stop_phrase_literals_only_in_directive_context():
    """No MATERIAL_CLAIMS_KO literal appears as bare report-output template text.

    Every real occurrence across the 6 report-emitting skills must be a
    directive quote (backtick-wrapped and/or on an avoid-directive line). A bare
    occurrence would mean a completion-claim phrase shipped as user-facing output
    template text, which the Stop hook would (rightly) flag.
    """
    corpus = [(name, _skill_path(name)) for name in STOP_PHRASE_SKILLS]
    corpus.append(("work/references/multi-status.md", MULTI_STATUS_REF))
    violations = []
    for label, path in corpus:
        for lineno, line in enumerate(_read(path).splitlines(), start=1):
            for literal in MATERIAL_CLAIMS_KO:
                if literal in line and not _occurrence_is_directive_quote(
                    line, literal
                ):
                    violations.append(
                        f"{label}:{lineno} bare completion-claim literal "
                        f"{literal!r}: {line.strip()!r}"
                    )
    assert not violations, (
        "completion-claim literals leaked into report-output template text "
        "(expected only as backtick-wrapped directive quotes): "
        + "; ".join(violations)
    )


# --------------------------------------------------------------------------- #
# (e2) Unit-level anchors pinning the _occurrence_is_directive_quote heuristic #
# --------------------------------------------------------------------------- #


def test_stop_phrase_heuristic_flags_bare_claim():
    """A bare completion-claim sentence is flagged (not directive-quoted)."""
    assert (
        _occurrence_is_directive_quote("작업을 완료했습니다.", "완료했습니다") is False
    )


def test_stop_phrase_heuristic_allows_backtick_directive():
    """A backtick-wrapped literal on an avoid-directive line is allowed."""
    line = "`완료했습니다` 같은 단정 어조는 회피한다"
    assert _occurrence_is_directive_quote(line, "완료했습니다") is True


def test_stop_phrase_heuristic_allows_marker_adjacent_bare_literal():
    """A bare literal within proximity of a directive marker is allowed."""
    # No backticks, but '회피' sits within _MARKER_PROXIMITY chars.
    line = "완료했습니다 어조는 회피"
    assert _occurrence_is_directive_quote(line, "완료했습니다") is True


def test_stop_phrase_heuristic_flags_bare_second_occurrence():
    """A backtick-quoted first occurrence does NOT whitelist a bare second one.

    This is the per-occurrence tightening: the FIRST `완료했습니다` is inside a
    backtick span, but the second is bare and far from any directive marker, so
    the line must be flagged.
    """
    line = "`완료했습니다` 라는 표현은 이렇게 쓴다 그리고 또 완료했습니다 라고 단정한다"
    assert _occurrence_is_directive_quote(line, "완료했습니다") is False


def test_stop_phrase_heuristic_distant_marker_does_not_whitelist():
    """A directive marker far (> proximity) from a bare occurrence is ignored."""
    # '회피' is pushed well beyond _MARKER_PROXIMITY chars from the literal.
    line = "완료했습니다" + " " * (_MARKER_PROXIMITY + 5) + "회피"
    assert _occurrence_is_directive_quote(line, "완료했습니다") is False


# --------------------------------------------------------------------------- #
# (f) Korean completion-summary step (lfg Step 9.5 + lfg-goal terminal)        #
#     Locks the v0.22.x 한글 완료 요약 contract: the step exists in both        #
#     skills, sits after the machine packet, fires on all lfg-goal terminal     #
#     exits, follows the canonical output.language resolver, keeps machine      #
#     tokens English, is honestly labeled advisory, and is hook-safe prose.     #
# --------------------------------------------------------------------------- #

# Summary-section markers (either form is accepted as "the summary exists").
_SUMMARY_MARKERS = ("한글 완료 요약", "Korean completion summary")


def _hook_material_claims_ko() -> tuple[str, ...]:
    """Extract the hook's MATERIAL_CLAIMS_KO literals (base list + the
    vendor-aware ``.extend([...])`` block) by static text parse — no import,
    so the test never executes the hook module. Used to prove the test's
    MATERIAL_CLAIMS_KO is a strict subset of what the live hook enforces.
    """
    body = _read(STOP_HOOK_SCRIPT)
    literals: list[str] = []
    # Base assignment: MATERIAL_CLAIMS_KO = [ ... ]
    m = re.search(r"MATERIAL_CLAIMS_KO\s*=\s*\[(.*?)\]", body, re.DOTALL)
    assert m, "could not locate MATERIAL_CLAIMS_KO base list in the hook script"
    literals += re.findall(r'"([^"]+)"', m.group(1))
    # Vendor-aware extension block: MATERIAL_CLAIMS_KO.extend([ ... ])
    m2 = re.search(
        r"MATERIAL_CLAIMS_KO\.extend\(\[(.*?)\]\)", body, re.DOTALL
    )
    if m2:
        literals += re.findall(r'"([^"]+)"', m2.group(1))
    return tuple(literals)


def _section_text(body: str, start_marker: str, end_markers: tuple[str, ...]) -> str:
    """Return the slice of ``body`` from ``start_marker`` up to the first of
    ``end_markers`` after it (or end-of-file). Raises if the start marker is
    absent. Used to scope hook-safety / token-boundary checks to the summary
    block rather than the whole file.
    """
    start = body.find(start_marker)
    assert start != -1, f"start marker {start_marker!r} not found"
    end = len(body)
    for em in end_markers:
        idx = body.find(em, start + len(start_marker))
        if idx != -1:
            end = min(end, idx)
    return body[start:end]


def _lfg_summary_section() -> str:
    """The lfg Step 9.5 block: `### Step 9.5` → `## Athanor identity invariants`."""
    return _section_text(
        _read(LFG_SKILL),
        "### Step 9.5",
        ("## Athanor identity invariants",),
    )


def _lfg_goal_summary_section() -> str:
    """The lfg-goal terminal `## 한글 완료 요약` block → EOF (it is terminal)."""
    return _section_text(
        _read(LFG_GOAL_SKILL),
        "## 한글 완료 요약",
        (),  # terminal section — runs to end of file
    )


def _has_marker(text: str) -> bool:
    return any(marker in text for marker in _SUMMARY_MARKERS)


def test_material_claims_ko_is_subset_of_hook():
    """[MAJOR-2] The test's widened MATERIAL_CLAIMS_KO must stay a STRICT subset
    of the live hook's set — the smoke must never over-claim (catch more than
    the hook actually blocks). Also confirms the widening landed (>5 literals).
    """
    hook_set = set(_hook_material_claims_ko())
    missing = [lit for lit in MATERIAL_CLAIMS_KO if lit not in hook_set]
    assert not missing, (
        "test MATERIAL_CLAIMS_KO contains literals the live hook does NOT "
        f"treat as completion claims (over-claim): {missing}"
    )
    # MAJOR-2 widening sanity: the specific merge/deploy/review verbs landed.
    for required in ("머지 완료", "배포 완료", "리뷰 완료", "테스트 통과",
                     "머지했습니다", "배포됨"):
        assert required in MATERIAL_CLAIMS_KO, (
            f"MAJOR-2 widening missing required literal {required!r}"
        )


def test_lfg_has_korean_completion_summary_step():
    """lfg SKILL.md carries the 한글 완료 요약 step (marker + `### Step 9.5`)."""
    body = _read(LFG_SKILL)
    assert _has_marker(body), (
        "lfg SKILL.md missing the Korean completion-summary marker "
        f"(one of {_SUMMARY_MARKERS})"
    )
    assert "### Step 9.5" in body, (
        "lfg SKILL.md missing the '### Step 9.5' completion-summary heading"
    )


def test_lfg_summary_after_machine_packet():
    """Ordering: `### Step 9.5` sits AFTER `### Step 9` (the machine packet) and
    BEFORE `## Athanor identity invariants` (still inside the protocol)."""
    body = _read(LFG_SKILL)
    off_step9 = body.find("### Step 9 ")  # trailing space → the H3, not 9.5
    off_step95 = body.find("### Step 9.5")
    off_invariants = body.find("## Athanor identity invariants")
    assert off_step9 != -1, "lfg SKILL.md missing '### Step 9 ' heading"
    assert off_step95 != -1, "lfg SKILL.md missing '### Step 9.5' heading"
    assert off_invariants != -1, (
        "lfg SKILL.md missing '## Athanor identity invariants' anchor"
    )
    assert off_step9 < off_step95 < off_invariants, (
        "Step 9.5 must come after the Step 9 machine packet and before the "
        f"identity invariants; got step9={off_step9}, step9.5={off_step95}, "
        f"invariants={off_invariants}"
    )


def test_lfg_goal_has_korean_completion_summary():
    """lfg-goal SKILL.md carries the terminal summary AND covers ALL terminal
    exits (MAJOR-3): no-progress AND max-iter(ations) AND a goal-complete/abort
    token — proving it fires on residual exits, not just Tier 3."""
    section = _lfg_goal_summary_section()
    assert _has_marker(section), (
        "lfg-goal summary section missing the Korean completion-summary marker"
    )
    assert "no-progress" in section, (
        "lfg-goal summary missing the 'no-progress' residual-exit terminal "
        "(MAJOR-3: must cover residual exits, not only Tier 3)"
    )
    assert ("max-iter" in section or "max-iterations" in section), (
        "lfg-goal summary missing the max-iter(ations) residual-exit terminal"
    )
    assert any(
        tok in section
        for tok in ("goal_complete", "mark_goal_complete", "mark_goal_abandoned",
                    "aborted")
    ), (
        "lfg-goal summary missing a goal-complete/abort terminal token"
    )


def test_summary_machine_tokens_stay_english():
    """BOTH skills: a machine-token-boundary clause (`stays? English` /
    `machine-parsed`) co-occurs with the summary marker, so a future edit that
    Korean-izes `merge:` / `validation_status` fails the test."""
    for label, section in (
        ("lfg", _lfg_summary_section()),
        ("lfg-goal", _lfg_goal_summary_section()),
    ):
        assert _has_marker(section), f"{label}: summary marker absent in section"
        assert re.search(r"stays? English", section) or "machine-parsed" in section, (
            f"{label}: summary section missing a machine-token-stays-English "
            "boundary clause ('stay(s) English' or 'machine-parsed')"
        )


def test_summary_directive_follows_output_language_resolver():
    """BOTH skills: the summary cites the canonical resolver pointer substring
    `output.language 해석 (canonical)` (no reinvented i18n path)."""
    for label, section in (
        ("lfg", _lfg_summary_section()),
        ("lfg-goal", _lfg_goal_summary_section()),
    ):
        assert CANONICAL_POINTER in section, (
            f"{label}: summary section missing the canonical-pointer substring "
            f"{CANONICAL_POINTER!r}"
        )


def test_summary_step_labeled_advisory():
    """BOTH skills: the summary block carries an `advisory` + `Present-to-User`
    (or `NOT a runtime gate`) honesty label — not mislabeled as enforced."""
    for label, section in (
        ("lfg", _lfg_summary_section()),
        ("lfg-goal", _lfg_goal_summary_section()),
    ):
        ok = ("NOT a runtime gate" in section) or (
            "advisory" in section and "Present-to-User" in section
        )
        assert ok, (
            f"{label}: summary section missing the advisory/Present-to-User "
            "honesty label (or 'NOT a runtime gate')"
        )


def test_summary_prose_is_hook_safe():
    """Section-scoped hook-safety: re-run the per-line directive-quote heuristic
    over the Step 9.5 / 한글 완료 요약 section of BOTH skills under the WIDENED
    MATERIAL_CLAIMS_KO, asserting zero bare completion-claim literals. Now
    meaningful because the widened tuple includes merge/deploy/review verbs."""
    violations = []
    for label, section in (
        ("lfg", _lfg_summary_section()),
        ("lfg-goal", _lfg_goal_summary_section()),
    ):
        for lineno, line in enumerate(section.splitlines(), start=1):
            for literal in MATERIAL_CLAIMS_KO:
                if literal in line and not _occurrence_is_directive_quote(
                    line, literal
                ):
                    violations.append(
                        f"{label} summary-section line {lineno}: bare "
                        f"completion-claim literal {literal!r}: {line.strip()!r}"
                    )
    assert not violations, (
        "bare completion-claim literals in the Korean completion-summary prose "
        "(expected only backtick-wrapped on a 회피-marked line): "
        + "; ".join(violations)
    )
