"""Regression tests for v0.16.0 multi-status executor contract (Phase 1.4).

Verifies that the v0.16.0 multi-status executor expansion is reflected in
both ``skills/work/SKILL.md`` and ``docs/agent-roles/executor.md``:

  - 5 status values documented (done, failure, done_with_concerns,
    needs_context, blocked) plus backwards-compat ``success`` alias.
  - Each new status has its required companion field documented
    (``concerns:`` / ``context_needed:`` / ``blocker:``).
  - ``needs_context`` handler in SKILL.md respects the Thin Leader
    contract — leader does NOT read project source itself.
  - ``blocked_queue`` is both initialized (Step 0/1) and drained (Step 3).
  - Team mode section references all 3 new statuses.
  - Legacy ``failure`` retry/skip/abort path is preserved.

These tests are STATIC ASSERTIONS that grep the canonical SKILL.md and
executor.md files. They lock the v0.16.0 multi-status executor contract
documented in the Phase 1 (Wave 1, ST1-3) plan-of-record.

Plan reference: v0.16.0 multi-status executor — Phase 1.4 (ST4).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"
WORK_REFS_DIR = REPO_ROOT / "skills" / "work" / "references"
EXECUTOR_AGENT = REPO_ROOT / "docs" / "agent-roles" / "executor.md"

# The 5 status values in the v0.16.0 multi-status executor contract.
ALL_STATUSES = [
    "done",
    "failure",
    "done_with_concerns",
    "needs_context",
    "blocked",
]

# The 3 NEW statuses (not legacy success/failure).
NEW_STATUSES = ["done_with_concerns", "needs_context", "blocked"]


def _read(path: Path) -> str:
    """Read a UTF-8 file, assert it exists and is non-trivial.

    v0.17.0 (ST-S01): when reading WORK_SKILL.md, the function transparently
    concatenates the thin router with every file under
    ``skills/work/references/*.md`` so v0.16.0 multi-status contract
    assertions that grep for handler prose continue to find it after the
    SKILL.md split. The split moved heavy prose to references/ without
    changing the contract.
    """
    assert path.exists(), f"{path} does not exist"
    text = path.read_text(encoding="utf-8")
    if path == WORK_SKILL and WORK_REFS_DIR.is_dir():
        # Append references corpus so test greps still hit the relocated prose.
        ref_chunks = []
        for ref in sorted(WORK_REFS_DIR.glob("*.md")):
            ref_chunks.append(f"\n\n<!-- begin {ref.name} -->\n")
            ref_chunks.append(ref.read_text(encoding="utf-8"))
            ref_chunks.append(f"\n<!-- end {ref.name} -->\n")
        text = text + "".join(ref_chunks)
    assert len(text.encode("utf-8")) > 500, (
        f"{path} is unexpectedly small ({len(text.encode('utf-8'))} bytes); "
        f"expected >500 bytes for a v0.16.0 multi-status contract surface"
    )
    return text


# ---------------------------------------------------------------------------
# 1. All statuses documented in skills/work/SKILL.md
# ---------------------------------------------------------------------------


def test_all_statuses_documented_in_skill():
    """All 5 status values appear in skills/work/SKILL.md."""
    text = _read(WORK_SKILL)
    missing = [s for s in ALL_STATUSES if s not in text]
    assert not missing, (
        f"skills/work/SKILL.md is missing v0.16.0 status value(s): {missing}. "
        f"All of {ALL_STATUSES} must be documented."
    )


# ---------------------------------------------------------------------------
# 2. All statuses documented in docs/agent-roles/executor.md
# ---------------------------------------------------------------------------


def test_all_statuses_documented_in_executor_agent():
    """All 5 status values appear in docs/agent-roles/executor.md."""
    text = _read(EXECUTOR_AGENT)
    missing = [s for s in ALL_STATUSES if s not in text]
    assert not missing, (
        f"docs/agent-roles/executor.md is missing v0.16.0 status value(s): {missing}. "
        f"All of {ALL_STATUSES} must be documented in the agent definition."
    )


# ---------------------------------------------------------------------------
# 3. Backwards-compat success alias mentioned
# ---------------------------------------------------------------------------


def test_backwards_compat_success_mentioned():
    """``success`` appears as backwards-compat alias for ``done`` in both files."""
    skill_text = _read(WORK_SKILL)
    agent_text = _read(EXECUTOR_AGENT)

    # SKILL.md must spell out the legacy success → done mapping somewhere.
    assert "success" in skill_text, (
        "skills/work/SKILL.md must mention legacy `success` status for "
        "backwards-compat aliasing."
    )
    # Look for an explicit alias/mapping/legacy marker near `success`.
    skill_lower = skill_text.lower()
    assert (
        "backwards-compat" in skill_lower
        or "legacy" in skill_lower
        or "alias" in skill_lower
    ), (
        "skills/work/SKILL.md must explain the `success` ↔ `done` "
        "relationship via the words backwards-compat / legacy / alias."
    )

    # executor.md must also mention it so worker authors writing against
    # the agent definition see the alias.
    assert "success" in agent_text, (
        "docs/agent-roles/executor.md must mention legacy `success` status as a "
        "backwards-compat alias for `done`."
    )
    agent_lower = agent_text.lower()
    assert (
        "backwards-compat" in agent_lower
        or "legacy" in agent_lower
        or "alias" in agent_lower
    ), (
        "docs/agent-roles/executor.md must explain the `success` ↔ `done` "
        "relationship via the words backwards-compat / legacy / alias."
    )


# ---------------------------------------------------------------------------
# 4. done_with_concerns requires concerns field
# ---------------------------------------------------------------------------


def test_done_with_concerns_requires_concerns_field():
    """SKILL.md documents ``concerns:`` as the required field for done_with_concerns.

    v0.17.0 (ST-S01): the status name appears in both router and
    ``references/multi-status.md``. The proximity check scans EVERY
    occurrence and passes if ANY occurrence has the contractual evidence
    in its 2KB window.
    """
    text = _read(WORK_SKILL)
    assert "done_with_concerns" in text, (
        "skills/work/SKILL.md must document `done_with_concerns` status."
    )
    assert "concerns:" in text, (
        "skills/work/SKILL.md must document the `concerns:` field "
        "(required companion field for done_with_concerns status)."
    )
    # Scan every occurrence; at least one window must carry the contractual
    # non-empty / required language (otherwise the field-status binding is
    # not anchored anywhere).
    pos = 0
    contract_anchored = False
    while True:
        idx = text.find("done_with_concerns", pos)
        if idx == -1:
            break
        window = text[max(0, idx - 200) : idx + 2000]
        window_lower = window.lower()
        if "concerns" in window and (
            "non-empty" in window_lower or "required" in window_lower
        ):
            contract_anchored = True
            break
        pos = idx + 1
    assert contract_anchored, (
        "skills/work/SKILL.md must mark `concerns:` as a non-empty / "
        "required list for `done_with_concerns` status (within 2KB of "
        "at least one occurrence of the status name)."
    )


# ---------------------------------------------------------------------------
# 5. needs_context requires context_needed field
# ---------------------------------------------------------------------------


def test_needs_context_requires_context_needed_field():
    """SKILL.md documents ``context_needed:`` as the required field for needs_context.

    v0.17.0 (ST-S01): proximity scan covers every occurrence of the status
    name across SKILL.md + references corpus.
    """
    text = _read(WORK_SKILL)
    assert "needs_context" in text, (
        "skills/work/SKILL.md must document `needs_context` status."
    )
    assert "context_needed" in text, (
        "skills/work/SKILL.md must document the `context_needed:` field "
        "(required companion field for needs_context status)."
    )
    pos = 0
    contract_anchored = False
    while True:
        idx = text.find("needs_context", pos)
        if idx == -1:
            break
        window = text[max(0, idx - 200) : idx + 2000]
        window_lower = window.lower()
        if "context_needed" in window and (
            "required" in window_lower or "must" in window_lower
        ):
            contract_anchored = True
            break
        pos = idx + 1
    assert contract_anchored, (
        "skills/work/SKILL.md must mark `context_needed:` as a required "
        "field for `needs_context` status (within 2KB of at least one "
        "occurrence of the status name)."
    )


# ---------------------------------------------------------------------------
# 6. blocked requires blocker field
# ---------------------------------------------------------------------------


def test_blocked_requires_blocker_field():
    """SKILL.md documents ``blocker:`` as the required field for blocked status."""
    text = _read(WORK_SKILL)
    assert "blocked" in text, (
        "skills/work/SKILL.md must document `blocked` status."
    )
    assert "blocker:" in text, (
        "skills/work/SKILL.md must document the `blocker:` field "
        "(required companion field for blocked status)."
    )
    # Find the `status: blocked` handler block (the v0.16.0 handler) and
    # confirm `blocker:` is documented inside that block.
    handler_match = re.search(
        r"`?status:?\s*blocked`?[\s\S]{0,3000}", text
    )
    assert handler_match, (
        "skills/work/SKILL.md must contain a `status: blocked` handler "
        "block referencing the `blocker:` field."
    )
    handler_window = handler_match.group(0)
    assert "blocker" in handler_window, (
        "skills/work/SKILL.md must mention `blocker` field near the "
        "`status: blocked` handler block (companion field binding)."
    )


# ---------------------------------------------------------------------------
# 7. needs_context handler respects Thin Leader (no leader-reads-source)
# ---------------------------------------------------------------------------


def test_needs_context_does_not_violate_thin_leader():
    """The needs_context handler must NOT instruct the leader to read project source itself.

    Per Thin Leader contract, the leader resolves a worker's context
    request by (a) asking the user, or (b) dispatching a research worker —
    never by reading project files itself.
    """
    text = _read(WORK_SKILL)
    # Find the `needs_context` handler section.
    handler_idx = text.find("status: needs_context")
    if handler_idx == -1:
        handler_idx = text.find("`needs_context`")
    assert handler_idx != -1, (
        "skills/work/SKILL.md must contain a `needs_context` handler section."
    )

    # Take a generous handler window (3KB) to cover the full handler block.
    handler_window = text[handler_idx : handler_idx + 3000]
    handler_lower = handler_window.lower()

    # The handler must explicitly affirm Thin Leader compliance somewhere
    # in its body — i.e., either reference the Thin Leader concept by name
    # or explicitly forbid leader-reads-source.
    assert (
        "thin leader" in handler_lower
        or "leader must not read" in handler_lower
        or "leader still does not read" in handler_lower
        or "does not read project" in handler_lower
        or "must not read project" in handler_lower
    ), (
        "skills/work/SKILL.md `needs_context` handler must explicitly affirm "
        "Thin Leader compliance (either by name or by an explicit "
        "'leader does not / must not read project source' clause)."
    )

    # Anti-pattern check: handler must NOT contain phrasing that instructs
    # the leader to read project files to answer the worker's question.
    forbidden_anti_patterns = [
        "leader reads the project source",
        "leader reads project source",
        "leader should read the source",
        "leader opens the file",
    ]
    for pattern in forbidden_anti_patterns:
        assert pattern not in handler_lower, (
            f"skills/work/SKILL.md `needs_context` handler must NOT contain "
            f"the Thin-Leader-violating phrase: {pattern!r}"
        )


# ---------------------------------------------------------------------------
# 8. blocked_queue initialized AND drained
# ---------------------------------------------------------------------------


def test_blocked_queue_initialized_and_drained():
    """``blocked_queue`` appears in both initialization (Step 1) and drain (Step 3) sections."""
    text = _read(WORK_SKILL)
    assert "blocked_queue" in text, (
        "skills/work/SKILL.md must reference `blocked_queue` "
        "(v0.16.0 blocker accumulator)."
    )

    # Locate Step 1 initialization (`blocked_queue = []` or similar init phrase).
    init_match = re.search(
        r"blocked_queue\s*=\s*\[\s*\]|blocked_queue.*?initialized",
        text,
        flags=re.IGNORECASE,
    )
    assert init_match, (
        "skills/work/SKILL.md must initialize `blocked_queue = []` "
        "(or equivalent) in Step 1 (per-run state initialization)."
    )

    # Locate Step 3 drain (drain phrase + Step 3 section header proximity).
    step3_idx = text.find("### Step 3")
    assert step3_idx != -1, (
        "skills/work/SKILL.md must contain a `### Step 3` section."
    )
    step3_window = text[step3_idx : step3_idx + 3000]
    assert "blocked_queue" in step3_window, (
        "skills/work/SKILL.md Step 3 (Work Log Finalization) must "
        "reference `blocked_queue` for the v0.16.0 drain pass."
    )
    assert "drain" in step3_window.lower(), (
        "skills/work/SKILL.md Step 3 must mention `drain` "
        "(blocked_queue drain pass at end of run)."
    )


# ---------------------------------------------------------------------------
# 9. Team mode references all 3 new statuses
# ---------------------------------------------------------------------------


def test_team_mode_references_new_statuses():
    """The Team Mode section references all 3 new statuses (done_with_concerns,
    needs_context, blocked)."""
    text = _read(WORK_SKILL)
    # Find the Team Mode section header. The canonical heading is
    # `## Team Mode (Wave-Based Parallel Execution)` per SKILL.md L972.
    team_idx = text.find("## Team Mode")
    assert team_idx != -1, (
        "skills/work/SKILL.md must contain a `## Team Mode` section header."
    )
    team_section = text[team_idx:]  # everything from Team Mode onward
    missing = [s for s in NEW_STATUSES if s not in team_section]
    assert not missing, (
        f"skills/work/SKILL.md Team Mode section is missing reference to "
        f"v0.16.0 new status(es): {missing}. All 3 new statuses "
        f"({NEW_STATUSES}) must be addressed in wave semantics."
    )


# ---------------------------------------------------------------------------
# 10. Legacy failure path unchanged (retry/skip/abort)
# ---------------------------------------------------------------------------


def test_legacy_failure_path_unchanged():
    """Failure handling still references retry / skip / abort (legacy v0.7.x path)."""
    text = _read(WORK_SKILL)
    # All three legacy actions must still be present somewhere in SKILL.md
    # (the v0.16.0 expansion only adds new branches; it does not remove the
    # legacy failure path).
    text_lower = text.lower()
    for action in ("retry", "skip", "abort"):
        assert action in text_lower, (
            f"skills/work/SKILL.md must still reference legacy failure "
            f"action `{action}` (v0.16.0 must not remove the legacy "
            f"retry/skip/abort prompt)."
        )

    # Additionally lock the failure branch documentation: the SKILL.md
    # must explicitly state that `status: failure` is unchanged from
    # the legacy path (per v0.16.0 plan-of-record).
    assert "status: failure" in text or "`failure`" in text, (
        "skills/work/SKILL.md must explicitly document `status: failure` "
        "as the legacy failure branch."
    )

    # Confirm the failure branch and the retry/skip/abort prompt are
    # connected — the prompt or a nearby block must reference the
    # legacy failure handling.
    # We accept either: (a) "retry / skip / abort" near `failure`, or
    # (b) a "[1] 재시도 ... [2] 스킵 ... [3] 중단" Korean prompt anywhere
    # (since SKILL.md uses Korean for the user-facing prompt).
    has_english_prompt = re.search(
        r"retry\s*/\s*skip\s*/\s*abort", text_lower
    )
    has_korean_prompt = (
        "재시도" in text and "스킵" in text and "중단" in text
    )
    assert has_english_prompt or has_korean_prompt, (
        "skills/work/SKILL.md must contain the legacy failure prompt "
        "(either English `retry / skip / abort` or Korean "
        "`재시도 / 스킵 / 중단`)."
    )
