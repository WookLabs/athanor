"""Regression test for the v0.8.0 U2 invariant — Task Splitter assigns
execution_note + propagates acceptance_criteria per subtask.

The v0.8.0 Spec-then-TDD discipline puts the actual classification on
Task-Splitter-generated subtasks (rather than Planner A's phases). When the
Splitter expands plan.md into `## Subtasks`, each subtask must carry an
`execution_note` field and (when behavior-bearing) an `acceptance_criteria`
field copied from the parent phase's Verify MUST/SHOULD bullets.

This test pins:
  1. Splitter prompt lists all three execution_note values
  2. Splitter prompt contains classification heuristic prose
  3. Splitter prompt contains acceptance_criteria propagation rule
  4. Post-split validation checks the new fields

Plan reference: docs/plans/2026-05-19-001-feat-v0.8.0-tdd-sdd-integration-plan.md
§U2 + origin requirements R1, R2, R3.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"


def _load():
    return WORK_SKILL.read_text(encoding="utf-8")


def test_splitter_prompt_lists_execution_note_enum():
    """MUST: Splitter prompt mentions all three execution_note enum values."""
    body = _load()
    assert "spec-then-tdd" in body, "Splitter prompt must mention 'spec-then-tdd'"
    assert "test-aware" in body, "Splitter prompt must mention 'test-aware'"
    # 'direct' is a common word; require it to appear alongside execution_note
    # context. We approximate by checking the literal field name appears too.
    assert "execution_note" in body, "Splitter prompt must mention 'execution_note' field"
    # And 'direct' should appear in proximity to execution_note
    en_idx = body.find("execution_note")
    window = body[en_idx : en_idx + 800] if en_idx >= 0 else ""
    assert "direct" in window.lower(), (
        "Splitter prompt must mention 'direct' as an execution_note value near "
        "the execution_note field reference"
    )


def test_splitter_prompt_includes_classification_heuristic():
    """MUST: Splitter prompt explains how to classify each subtask."""
    body = _load()
    body_lower = body.lower()
    # Heuristic: source code + new behavior → spec-then-tdd
    source_code_signals = ["source code modification", "source code mod"]
    assert any(s in body_lower for s in source_code_signals), (
        f"Splitter prompt must mention source-code-modification heuristic. "
        f"Expected one of: {source_code_signals}"
    )
    # Heuristic: prose-only / doc-only → direct
    prose_signals = ["prose-only", "doc only", "_doc", "changelog"]
    assert any(s in body_lower for s in prose_signals), (
        f"Splitter prompt must mention prose-only heuristic. "
        f"Expected one of: {prose_signals}"
    )


def test_splitter_prompt_acceptance_criteria_propagation():
    """MUST: Splitter prompt instructs copying parent-phase Verify bullets
    into subtask acceptance_criteria field."""
    body = _load()
    body_lower = body.lower()
    assert "acceptance_criteria" in body, (
        "Splitter prompt must reference acceptance_criteria field"
    )
    # Propagation prose — "copy" or "from the parent" or "parent phase"
    propagation_signals = [
        "copy the parent phase",
        "parent phase",
        "verify must/should",
        "must/should bullets into",
        "parent phase's verify",
    ]
    assert any(s in body_lower for s in propagation_signals), (
        f"Splitter prompt must describe propagation from parent phase Verify "
        f"to subtask acceptance_criteria. Expected one of: {propagation_signals}"
    )


def test_splitter_prompt_only_spec_then_tdd_gets_ac():
    """MUST: AC field only required when execution_note == spec-then-tdd."""
    body = _load()
    # The AC propagation rule should clarify that acceptance_criteria is only
    # for spec-then-tdd subtasks (not test-aware, not direct).
    # We approximate by checking both terms co-occur in a small window.
    ac_idx = body.find("acceptance_criteria")
    assert ac_idx >= 0
    window = body[max(0, ac_idx - 300) : ac_idx + 500]
    assert "spec-then-tdd" in window, (
        "acceptance_criteria field reference must be near 'spec-then-tdd' "
        "context (only that execution_note value requires AC)"
    )


def test_post_split_validation_checks_new_fields():
    """MUST: Post-split validation step verifies execution_note + AC fields."""
    body = _load()
    body_lower = body.lower()
    # Post-split validation exists
    assert "post-split validation" in body_lower or "post-split" in body_lower
    # The validation prose should mention checking execution_note (broader
    # than checking just "spec-then-tdd")
    # We check that "validation" prose co-occurs with "execution_note" somewhere
    # in the file
    validation_idx = body_lower.find("post-split")
    assert validation_idx >= 0
    # The validation rules are usually within ~1000 chars after the heading
    window = body_lower[validation_idx : validation_idx + 2500]
    assert "execution_note" in window, (
        "Post-split validation must check the execution_note field "
        "(within ~2500 chars after 'Post-split' heading)"
    )


def test_subtask_output_format_includes_execution_note():
    """MUST: Subtask output format template shows execution_note field."""
    body = _load()
    # The output format example should include an `execution_note:` line
    assert "execution_note:" in body, (
        "Subtask output format template must show 'execution_note:' field "
        "(with colon — indicating it's a field name in the output YAML/Markdown)"
    )


def test_no_overclaim_in_splitter_classification():
    """MUST: classification is advisory — no 'enforced' or 'required' overclaim
    near the splitter prompt."""
    body = _load()
    # Find the splitter prompt area
    splitter_idx = body.lower().find("task splitter")
    if splitter_idx < 0:
        return  # caught by other tests
    window = body[splitter_idx : splitter_idx + 5000]
    # Negative — no "enforced" or "required" claim about the splitter itself
    # We tolerate "MUST" since it's used as keyword for assertions
    overclaim_phrases = [
        "tdd enforced",
        "spec-driven enforced",
        "spec-driven required",
        "execution_note enforced",
    ]
    for phrase in overclaim_phrases:
        assert phrase.lower() not in window.lower(), (
            f"Overclaim phrase '{phrase}' found near splitter prompt"
        )
