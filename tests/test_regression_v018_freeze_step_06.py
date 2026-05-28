"""Regression test for v0.18.0 ST-1.1 — Step 0.6 Freeze Allowlist router pointer.

v0.18.0 introduces Plan-Scoped Freeze Manifest as Phase 1 of the
Freeze-First release. The Splitter `files:` declaration becomes
load-bearing for Freeze; a per-session allowlist is built before
worker dispatch and (when ``hooks.freeze.mode`` is enabled in
``athanor.json``) consumed by a PreToolUse freeze guard.

This test pins ST-1.1 (router-side surface):
  1. ``skills/work/SKILL.md`` adds a Step 0.6 reference between
     Step 0.5 (Task Splitter Dispatch) and Step 1 (Initialize
     TodoList & Announce). The Step 0.6 stub MUST stay ≤ 10
     content lines (router pointer only — detailed prose lives
     in ``references/freeze.md``).
  2. ``skills/work/SKILL.md`` total line count stays ≤ 260
     (was 250 cap pre-v0.18.0; +10 lines absorbed for Step 0.6).
  3. ``skills/work/references/freeze.md`` exists and is substantive:
     - documents the builder contract (``build_freeze_allowlist.py``);
     - documents the Bash gated-pattern list (``> file``, ``>> file``,
       ``tee file``, ``sed -i FILE``, ``mv X Y``, ``cp X Y``);
     - documents the D2 residual (subprocess writes NOT gated);
     - documents the default-included paths
       (``.athanor/sessions/<id>/...``);
     - documents the opt-in mode = "off" default.
  4. The Step 0.6 stub cross-links ``references/freeze.md`` so the
     reference is not orphaned.

Plan reference: ``.athanor/sessions/2026-05-28-004/plan.md`` §Phase 1
"Plan-Scoped Freeze Allowlist Builder", v0.18.0 ST-1.1.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"
FREEZE_REF = REPO_ROOT / "skills" / "work" / "references" / "freeze.md"


def _read_skill() -> str:
    assert WORK_SKILL.exists(), f"{WORK_SKILL} must exist"
    return WORK_SKILL.read_text(encoding="utf-8")


def _read_freeze_ref() -> str:
    assert FREEZE_REF.exists(), (
        f"{FREEZE_REF} must exist after v0.18.0 ST-1.1 — it carries the "
        f"full Freeze prose contract referenced from SKILL.md Step 0.6."
    )
    return FREEZE_REF.read_text(encoding="utf-8")


def test_work_skill_total_cap_relaxed_to_260_for_step_06():
    """MUST: skills/work/SKILL.md ≤ 260 lines (was 250 cap; +10 for Step 0.6)."""
    line_count = len(_read_skill().splitlines())
    assert line_count <= 260, (
        f"skills/work/SKILL.md is {line_count} lines; v0.18.0 ST-1.1 cap is ≤ 260 "
        f"(250 pre-v0.18.0 baseline + 10 for Step 0.6 router stub). Move heavier "
        f"freeze prose to skills/work/references/freeze.md."
    )


def test_work_skill_has_step_06_freeze_section():
    """MUST: Step 0.6 header exists, between Step 0.5 and Step 1."""
    body = _read_skill()
    assert "### Step 0.6" in body, (
        "skills/work/SKILL.md must add a `### Step 0.6` section for the "
        "Freeze Allowlist build (v0.18.0 ST-1.1)."
    )
    # Sequencing: Step 0.5 must precede Step 0.6 must precede Step 1.
    p_step_05 = body.find("### Step 0.5")
    p_step_06 = body.find("### Step 0.6")
    p_step_1 = body.find("### Step 1")
    assert p_step_05 != -1, "Step 0.5 section must remain in SKILL.md"
    assert p_step_1 != -1, "Step 1 section must remain in SKILL.md"
    assert p_step_05 < p_step_06 < p_step_1, (
        "Step 0.6 must be placed between Step 0.5 (Splitter) and Step 1 "
        "(TodoList init), preserving Protocol section ordering."
    )


def test_step_06_stub_is_router_thin_max_10_lines():
    """MUST: Step 0.6 stub body ≤ 10 content lines (router pointer only)."""
    body = _read_skill()
    p_step_06 = body.find("### Step 0.6")
    p_step_1 = body.find("### Step 1")
    assert p_step_06 != -1 and p_step_1 != -1
    section = body[p_step_06:p_step_1]
    # Drop the header line itself + trailing blank lines; count remaining
    # non-empty content lines.
    lines = section.splitlines()
    assert lines and lines[0].startswith("### Step 0.6"), (
        f"unexpected Step 0.6 header: {lines[0] if lines else '<empty>'!r}"
    )
    content_lines = [
        ln for ln in lines[1:]
        if ln.strip() and not ln.startswith("### ")
    ]
    assert len(content_lines) <= 10, (
        f"Step 0.6 stub has {len(content_lines)} content lines; cap is 10. "
        f"Move detailed prose to references/freeze.md. Lines:\n  "
        + "\n  ".join(content_lines)
    )


def test_step_06_cross_links_freeze_reference():
    """MUST: Step 0.6 cross-links references/freeze.md."""
    body = _read_skill()
    p_step_06 = body.find("### Step 0.6")
    p_step_1 = body.find("### Step 1")
    section = body[p_step_06:p_step_1]
    assert "references/freeze.md" in section, (
        "Step 0.6 stub must cross-link `references/freeze.md` so the "
        "reference is not orphaned (v0.18.0 ST-1.1)."
    )


def test_freeze_reference_exists_and_is_substantive():
    """MUST: skills/work/references/freeze.md exists and is substantive."""
    body = _read_freeze_ref()
    assert len(body) > 1500, (
        f"skills/work/references/freeze.md is only {len(body)} bytes; "
        f"ST-1.1 calls for a comprehensive contract document."
    )


def test_freeze_reference_documents_builder_contract():
    """MUST: freeze.md references the builder script path + output JSON."""
    body = _read_freeze_ref()
    # Builder script reference
    assert "build_freeze_allowlist.py" in body, (
        "freeze.md must reference the builder script "
        "`scripts/work/build_freeze_allowlist.py`."
    )
    # Output path reference
    assert "freeze-allowlist.json" in body, (
        "freeze.md must reference the output path "
        "`.athanor/sessions/<id>/freeze-allowlist.json`."
    )
    # Default-included session path
    assert ".athanor/sessions/" in body, (
        "freeze.md must document the default-included session path "
        "(`.athanor/sessions/<id>/...`)."
    )


def test_freeze_reference_documents_bash_gated_patterns():
    """MUST: freeze.md lists the conservative Bash gated patterns."""
    body = _read_freeze_ref()
    required_patterns = [
        "> file",
        ">> file",
        "tee file",
        "sed -i",
        "mv ",
        "cp ",
    ]
    missing = [p for p in required_patterns if p not in body]
    assert not missing, (
        f"freeze.md must document the Bash gated-pattern list. "
        f"Missing: {missing}"
    )


def test_freeze_reference_documents_d2_residual():
    """MUST: freeze.md documents the D2 residual — subprocess writes NOT gated."""
    body = _read_freeze_ref()
    # Look for either "subprocess" or the explicit pattern list from the plan.
    lower = body.lower()
    assert "subprocess" in lower, (
        "freeze.md must mention `subprocess` writes (D2 honesty residual: "
        "subprocess writes via Bash like `python -c`, `make build`, "
        "`codex exec` are NOT gated)."
    )
    # And it must say "not gated" / "NOT gated" somewhere near the residual.
    assert re.search(r"not\s+gated", lower), (
        "freeze.md must explicitly state that subprocess writes are NOT "
        "gated (D2 residual honesty)."
    )


def test_freeze_reference_documents_opt_in_default():
    """MUST: freeze.md documents that hooks.freeze.mode defaults to off."""
    body = _read_freeze_ref()
    assert "hooks.freeze" in body, (
        "freeze.md must reference the `hooks.freeze` config block in "
        "athanor.json."
    )
    # Default = "off" — opt-in posture.
    lower = body.lower()
    assert '"off"' in body or "= off" in lower or "default" in lower and "off" in lower, (
        "freeze.md must document that `hooks.freeze.mode` defaults to `off` "
        "(opt-in posture)."
    )


def test_freeze_reference_documents_dispatcher_integration():
    """MUST: freeze.md describes the dispatcher → freeze_guard call shape."""
    body = _read_freeze_ref()
    # Dispatcher integration must be named.
    assert "pretool" in body.lower() or "PreToolUse" in body, (
        "freeze.md must document the PreToolUse dispatcher integration."
    )
    assert "freeze_guard" in body or "freeze guard" in body.lower(), (
        "freeze.md must reference the `freeze_guard` evaluator that the "
        "dispatcher invokes after the kernel guard returns 0."
    )
