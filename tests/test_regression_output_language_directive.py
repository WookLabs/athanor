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
MATERIAL_CLAIMS_KO = (
    "완료했습니다",
    "통과했습니다",
    "수정 완료",
    "구현 완료",
    "적용 완료",
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


def test_all_nine_skills_carry_output_language_directive():
    """Each of the 9 Thin-Leader skills references output.language ≥ once."""
    missing = [
        name
        for name in DIRECTIVE_SKILLS
        if "output.language" not in _read(_skill_path(name))
    ]
    assert not missing, (
        "these skills are missing the output.language directive: " f"{missing}"
    )


# --------------------------------------------------------------------------- #
# (c) Interpretation contract — setup SKILL.md jq snippet + en fallback        #
# --------------------------------------------------------------------------- #


def test_setup_skill_has_canonical_jq_snippet():
    """setup SKILL.md carries the canonical jq -r '.output.language interpreter."""
    body = _read(SETUP_SKILL)
    assert "jq -r '.output.language" in body, (
        "setup SKILL.md must carry the canonical jq -r '.output.language "
        "interpretation snippet (single source of truth)"
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


def _occurrence_is_directive_quote(line: str, literal: str) -> bool:
    """True if `literal` on `line` is directive-quoting, not bare output text.

    Heuristic (kept deliberately simple — see module docstring):
      * the literal is wrapped in a backtick span (`…`), AND/OR
      * the line carries a directive marker (회피/대신/어조/금지).
    A real completion-report output template would print the literal bare
    (no backticks, no avoid-directive context) — that is what we flag.
    """
    backtick_spans = [
        (m.start(), m.end()) for m in re.finditer(r"`[^`]*`", line)
    ]
    idx = line.index(literal)
    in_backticks = any(start <= idx < end for start, end in backtick_spans)
    has_marker = any(marker in line for marker in _DIRECTIVE_MARKERS)
    return in_backticks or has_marker


def test_stop_phrase_literals_only_in_directive_context():
    """No MATERIAL_CLAIMS_KO literal appears as bare report-output template text.

    Every real occurrence across the 6 report-emitting skills must be a
    directive quote (backtick-wrapped and/or on an avoid-directive line). A bare
    occurrence would mean a completion-claim phrase shipped as user-facing output
    template text, which the Stop hook would (rightly) flag.
    """
    violations = []
    for name in STOP_PHRASE_SKILLS:
        for lineno, line in enumerate(
            _read(_skill_path(name)).splitlines(), start=1
        ):
            for literal in MATERIAL_CLAIMS_KO:
                if literal in line and not _occurrence_is_directive_quote(
                    line, literal
                ):
                    violations.append(
                        f"{name}:{lineno} bare completion-claim literal "
                        f"{literal!r}: {line.strip()!r}"
                    )
    assert not violations, (
        "completion-claim literals leaked into report-output template text "
        "(expected only as backtick-wrapped directive quotes): "
        + "; ".join(violations)
    )
