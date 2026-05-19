"""Regression test for v0.10.1 U3+U4 invariants — Splitter output schema
emits `classification_reason` field on every subtask, and the SKILL.md
heuristic block documents enough rationale to derive the 3 ambiguous-case
fixtures.

This is documentation-regression, not live-classifier regression — the
heuristic itself stays prose-level in SKILL.md (no LLM call at test time).

Plan reference: docs/plans/2026-05-19-004-feat-v0.10.1-vendor-hygiene-plan.md
§U3, U4, B1.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "splitter_cases"


def _load_skill_md() -> str:
    return WORK_SKILL.read_text(encoding="utf-8")


# ---- U3: schema has classification_reason field ----


def test_skill_md_step_0_5_rules_mention_classification_reason():
    """MUST: Step 0.5 Rules block instructs Splitter to emit
    `classification_reason` for every subtask."""
    body = _load_skill_md()
    lower = body.lower()
    assert "classification_reason" in lower, (
        "skills/work/SKILL.md Step 0.5 must mention classification_reason"
    )
    # v0.10.1 marker should be present so future readers see when the
    # field was added
    assert "v0.10.1" in body, (
        "skills/work/SKILL.md should mark v0.10.1 introduction of "
        "classification_reason"
    )


def test_skill_md_output_format_has_classification_reason_line():
    """MUST: Output Format §Subtasks template has a `classification_reason:`
    line directly after `execution_note:`."""
    body = _load_skill_md()
    # Locate Output Format section
    idx = body.find("## Output Format")
    assert idx >= 0, "Output Format section missing"
    section = body[idx : idx + 3000]
    assert "classification_reason" in section, (
        "Output Format template must include classification_reason: line"
    )


def test_skill_md_validation_step_checks_classification_reason():
    """MUST: Post-split Validation list includes a check for the new field."""
    body = _load_skill_md()
    idx = body.find("Post-split Validation")
    assert idx >= 0
    section = body[idx : idx + 2000]
    assert "classification_reason" in section, (
        "Post-split Validation must check classification_reason existence"
    )


def test_classification_reason_required_for_every_subtask_not_just_spec_then_tdd():
    """MUST: SKILL.md prose makes it explicit that classification_reason
    is required for ALL subtasks (not gated on execution_note value, unlike
    acceptance_criteria which is spec-then-tdd-only)."""
    body = _load_skill_md()
    lower = body.lower()
    # Look for explicit "every subtask" / "regardless of classification"
    # / "all subtask" language near classification_reason
    signals = [
        "every subtask",
        "regardless of classification",
        "for every subtask",
        "all subtask",
    ]
    found = [s for s in signals if s in lower]
    assert found, (
        f"SKILL.md must explicitly say classification_reason applies to "
        f"every subtask. Expected one of: {signals}"
    )


def test_classification_reason_length_contract_documented():
    """MUST: SKILL.md documents the one-line + length contract for the
    field (≤200 chars, no embedded newlines)."""
    body = _load_skill_md()
    lower = body.lower()
    # Length-or-line-shape contract signals
    contract_signals = [
        "one line",
        "one-line",
        "≤ 200",
        "200 chars",
        "no embedded newlines",
        "single line",
    ]
    found = [s for s in contract_signals if s in lower]
    assert found, (
        f"SKILL.md must document the classification_reason length/shape "
        f"contract. Expected one of: {contract_signals}"
    )


# ---- U4: fixtures load + cover three edges ----


def _load_fixtures() -> list[dict]:
    """Load all fixture YAML files. Uses lightweight parser (no PyYAML
    dep — keeps test surface minimal)."""
    fixtures = []
    for f in sorted(FIXTURES_DIR.glob("*.yaml")):
        text = f.read_text(encoding="utf-8")
        # Tiny YAML parser: extract top-level keys + lists. Sufficient for
        # the fixture shape we use.
        fix = {"_path": str(f)}
        current_list_key = None
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
            if m:
                key, val = m.group(1), m.group(2).rstrip()
                if val in ("", "|"):
                    if val == "|":
                        # multi-line string starts; we just record the next
                        # non-empty indented lines until indentation drops
                        current_list_key = None
                        fix[key] = ""
                        fix["__current_multiline_key"] = key
                    else:
                        current_list_key = key
                        fix[key] = []
                else:
                    current_list_key = None
                    fix[key] = val
                continue
            list_m = re.match(r"^\s+-\s+(.+)$", line)
            if list_m and current_list_key:
                fix[current_list_key].append(list_m.group(1).strip())
                continue
            indented = re.match(r"^\s+(.+)$", line)
            if indented and fix.get("__current_multiline_key"):
                fix[fix["__current_multiline_key"]] += indented.group(1) + "\n"
        fix.pop("__current_multiline_key", None)
        fixtures.append(fix)
    return fixtures


def test_three_fixtures_present():
    """MUST: at least 3 fixture cases cover the ambiguous edges."""
    fixtures = _load_fixtures()
    assert len(fixtures) >= 3, (
        f"Expected ≥3 splitter fixture cases; found {len(fixtures)}"
    )


def test_each_fixture_has_required_fields():
    """MUST: each fixture has case_id / subtask_brief / expected_classification
    / expected_reason_keywords / rationale."""
    fixtures = _load_fixtures()
    required = ["case_id", "subtask_brief", "expected_classification",
                "expected_reason_keywords", "rationale"]
    for fix in fixtures:
        missing = [k for k in required if not fix.get(k)]
        assert not missing, (
            f"Fixture {fix['_path']} missing field(s): {missing}"
        )


def test_all_three_classifications_covered():
    """MUST: fixtures cover all three classifications (spec-then-tdd,
    test-aware, direct)."""
    fixtures = _load_fixtures()
    classifications = {fix["expected_classification"] for fix in fixtures}
    assert classifications == {"spec-then-tdd", "test-aware", "direct"}, (
        f"Fixtures must cover all 3 classifications; covered: {classifications}"
    )


def test_skill_md_heuristic_supports_each_fixture():
    """MUST: the SKILL.md Step 0.5 heuristic block documents enough
    classification rules to *derive* the expected classification for
    each fixture's expected_reason_keywords."""
    body = _load_skill_md().lower()
    fixtures = _load_fixtures()
    for fix in fixtures:
        keywords = [k.lower() for k in fix["expected_reason_keywords"]]
        # At least 1 keyword from the fixture's expected reason should
        # appear verbatim in the heuristic block (otherwise the heuristic
        # wouldn't justify the classification).
        found = [k for k in keywords if k in body]
        assert found, (
            f"Fixture {fix['case_id']} expects reason with keywords "
            f"{keywords}, but none appear in SKILL.md heuristic block. "
            f"Heuristic and fixture have drifted."
        )
