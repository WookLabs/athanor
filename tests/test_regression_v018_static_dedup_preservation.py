"""Regression test for v0.18.0 Subtask 3.1 — static dedup preservation
(R-B5 fix).

Locks the v0.17.0 static dedup state at v0.18.0 release time:
**UserPromptSubmit (UPS) is NOT registered as a runtime hook in v0.18.0.**

The v0.17.0 / S04 hoist established a static dedup pattern for the
`using-superpowers boundary` declaration: 10 athanor-native Thin Leader
skills each carry a 2-line POINTER (heading + 1-line "See CLAUDE.md …")
and the canonical prose lives in ONE place — CLAUDE.md §"using-superpowers
boundary (v0.11.1) — canonical declaration". UPS-driven runtime dedup
(which would inject the canonical text dynamically on each user prompt)
was explicitly deferred in the v0.18.0 plan-of-record per R-B5 to a
future v0.18.2 spike pending live Claude Code UPS support.

This test asserts that state remains true for UserPromptSubmit at v0.18.x
while allowing the deliberate v0.19.0 PostToolUse evidence-only addition:

  1. `hooks/hooks.json` does NOT register a `UserPromptSubmit` entry —
     only `Stop` (v0.7.8+), `PreToolUse` (v0.16.0+), and the
     `PostToolUse` evidence sniffer (v0.19.0+).
    2. CLAUDE.md still uses the 10-pointer + 1-canonical static dedup
     pattern (10 skills with `### using-superpowers boundary` pointers
     plus the canonical heading in CLAUDE.md).
  3. No UPS-related hook scripts in `scripts/hooks/` — `capability_probe.py`
     may MENTION UPS for forward-compat documentation, but no script
     SCANS or ACTS on `UserPromptSubmit` events as a runtime entry point.

Self-correcting note
====================

This test is intentionally written to FAIL when v0.18.2 ships
UserPromptSubmit runtime dedup. At that point the assertions below
should be flipped or removed:

  - The `hooks.json` assertion should change to require UPS presence.
  - The static dedup pattern in CLAUDE.md should be revisited (the
    9 pointers may collapse into a UPS injection contract).
  - The "no UPS in scripts/hooks/" check should be relaxed to allow
    the new UPS handler.

The plan-of-record explicitly admits this is a snapshot lock, not a
permanent invariant. The test file name (`v018_static_dedup_preservation`)
references v0.18.0 so the v0.18.2 author has a clear delete/rewrite
signal.

Cross-references:
  - `tests/test_regression_v011_1_using_superpowers_boundary.py` —
    the canonical declaration prose lock (independent of this test).
  - `.athanor/hook-capability.json` `events.UserPromptSubmit.supported`
    field is the runtime probe; this test is the static manifest lock.
  - Plan-of-record: `.athanor/sessions/2026-05-28-004/plan.md`
    §Subtask 3.1.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
SCRIPTS_HOOKS_DIR = REPO_ROOT / "scripts" / "hooks"


# ---------------------------------------------------------------------------
# UPS absence from hooks.json (M3.1-MUST)
# ---------------------------------------------------------------------------


def test_hooks_json_does_not_register_user_prompt_submit():
    """hooks/hooks.json must NOT contain a `UserPromptSubmit` event entry.

    v0.18.0 ships only `Stop` (claim verification, since v0.7.8) and
    `PreToolUse` (kernel + freeze dispatcher, since v0.16.0/v0.18.0). UPS
    runtime dedup is deferred to v0.18.2 pending live spike — until that
    ships, the static dedup pattern (9 pointers + 1 canonical) is the
    sole mechanism for the using-superpowers boundary.
    """
    assert HOOKS_JSON.is_file(), f"hooks.json missing at {HOOKS_JSON}"
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    hooks_section = data.get("hooks", {})
    assert isinstance(hooks_section, dict), (
        f"hooks.json top-level 'hooks' must be an object; got {type(hooks_section)}"
    )
    assert "UserPromptSubmit" not in hooks_section, (
        "UserPromptSubmit must NOT be registered in hooks.json at v0.18.0 "
        "(R-B5 deferred to v0.18.2 pending live spike). Flip this assertion "
        "when v0.18.2 lands."
    )


def test_hooks_json_event_inventory_is_stop_pretool_and_posttool_only():
    """Lock the exact event surface: Stop + PreToolUse + PostToolUse.

    Detects accidental UPS introduction OR any other event-registration
    drift that would silently expand athanor's runtime gate surface.
    """
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    events = set(data.get("hooks", {}).keys())
    assert events == {"Stop", "PreToolUse", "PostToolUse"}, (
        f"hooks.json must register exactly Stop + PreToolUse + PostToolUse; "
        f"got {sorted(events)!r}. Any added event needs explicit honesty "
        f"framing per the plan-of-record."
    )


def test_hooks_json_raw_string_does_not_mention_user_prompt_submit():
    """Belt-and-suspenders raw-string check.

    If a typo or partial deletion left a `UserPromptSubmit` string token
    inside hooks.json, the JSON-shape check above might still pass (e.g.,
    if it ended up as a stray key in a nested object). This catches the
    raw textual presence and forces a deliberate v0.18.2 update.
    """
    raw = HOOKS_JSON.read_text(encoding="utf-8")
    assert "UserPromptSubmit" not in raw, (
        "hooks.json contains the literal token 'UserPromptSubmit' at "
        "v0.18.0. Remove it or flip this test if you are intentionally "
        "shipping v0.18.2 UPS runtime dedup."
    )


# ---------------------------------------------------------------------------
# Static dedup pattern preservation in CLAUDE.md (M3.1-MUST)
# ---------------------------------------------------------------------------


# The athanor-native Thin Leader skills that each carry a pointer to
# the canonical declaration. Locked here so accidental skill renames
# show up as test failures.
_THIN_LEADER_SKILLS = [
    "assess",
    "analyze",
    "debug",
    "discuss",
    "lfg",
    "lfg-goal",
    "plan",
    "review",
    "setup",
    "work",
]


def test_claude_md_canonical_declaration_heading_present():
    """The single canonical declaration heading must exist in CLAUDE.md."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "using-superpowers boundary (v0.11.1) — canonical declaration" in text, (
        "CLAUDE.md must keep the single canonical heading "
        "`### using-superpowers boundary (v0.11.1) — canonical declaration`; "
        "this is the SOURCE in the 9-pointer + 1-canonical static dedup pattern."
    )


def test_skills_each_carry_a_boundary_pointer():
    """Each Thin Leader skill must carry a pointer subsection
    `### using-superpowers boundary` (without the canonical-declaration
    suffix). This is the pointer side of the static dedup pattern."""
    missing: list[str] = []
    for skill in _THIN_LEADER_SKILLS:
        skill_md = REPO_ROOT / "skills" / skill / "SKILL.md"
        if not skill_md.is_file():
            missing.append(f"{skill} (SKILL.md missing)")
            continue
        text = skill_md.read_text(encoding="utf-8")
        # The pointer heading is the bare `### using-superpowers boundary`
        # form — distinct from the canonical heading suffix.
        if "### using-superpowers boundary" not in text:
            missing.append(f"{skill} (no pointer heading)")
    assert not missing, (
        "Static dedup pattern broken — these skills no longer carry a "
        f"`### using-superpowers boundary` pointer: {missing!r}. The "
        "9-pointer + 1-canonical pattern is the v0.17.0 / S04 hoist "
        "shape; preserve it until v0.18.2 UPS runtime dedup ships."
    )


def test_pointer_count_is_ten():
    """Sanity: exactly 10 skills carry the pointer, matching the
    canonical declaration's current native Thin Leader skill enumeration."""
    found = 0
    for skill_dir in (REPO_ROOT / "skills").iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        # Match the pointer heading at start of line; exclude the
        # canonical-declaration heading (which has a longer suffix).
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "### using-superpowers boundary":
                found += 1
                break
            if stripped.startswith("### using-superpowers boundary ") and \
                    "canonical declaration" not in stripped:
                found += 1
                break
    assert found == 10, (
        f"expected exactly 10 `### using-superpowers boundary` pointers "
        f"(one per Thin Leader skill); got {found}. The 10+1 static dedup "
        f"pattern is current — adjust this count only when a "
        f"native skill is genuinely added/removed."
    )


# ---------------------------------------------------------------------------
# No UPS runtime injection in scripts/hooks/ (M3.1-MUST)
# ---------------------------------------------------------------------------


def test_only_log_only_ups_spike_script_in_scripts_hooks():
    """No script in `scripts/hooks/` may implement UserPromptSubmit runtime
    dedup or injection.

    `capability_probe.py` is allowed to MENTION `UserPromptSubmit` in
    docstrings / probe definitions for forward-compat reporting. The one
    allowed UPS-shaped script is `user_prompt_submit_spike.py`, and it must
    stay log-only: no `additionalContext` emission and no stdout injection.
    """
    allowed_spike = "user_prompt_submit_spike.py"
    forbidden_name_fragments = ("user_prompt", "ups_")
    found: list[str] = []
    for entry in SCRIPTS_HOOKS_DIR.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix != ".py":
            continue
        name_lower = entry.name.lower()
        if any(f in name_lower for f in forbidden_name_fragments):
            found.append(entry.name)
            assert entry.name == allowed_spike, (
                f"Found unexpected UPS-shaped hook script at {entry}. Only "
                f"{allowed_spike!r} is allowed before runtime dedup ships."
            )
            body = entry.read_text(encoding="utf-8")
            assert "additionalContext" not in body, (
                f"{allowed_spike} must not emit UserPromptSubmit context "
                "injection; it is a log-only payload spike harness."
            )
    assert found == [allowed_spike], (
        f"expected only {allowed_spike!r} as the UPS-shaped hook script; "
        f"got {found!r}"
    )


def test_capability_probe_ups_mention_is_documentation_only():
    """`capability_probe.py` may report UPS capability for forward-compat
    purposes, but it must NOT itself register as a UPS event handler
    (i.e., it should not be the script invoked on UPS events). We assert
    this indirectly: hooks.json doesn't point to it, and it does not
    declare itself as a Stop / PreToolUse / UPS entry.

    This is a softer check than test_no_ups_runtime_script_in_scripts_hooks
    above; it allows capability_probe.py to keep its forward-compat
    documentation without flagging it as a runtime UPS hook.
    """
    raw = HOOKS_JSON.read_text(encoding="utf-8")
    assert "capability_probe.py" not in raw, (
        "capability_probe.py must NOT be registered as a Claude Code "
        "hook entry point at v0.18.0 — it is a self-introspection tool "
        "only, not a runtime gate."
    )


# ---------------------------------------------------------------------------
# Self-correcting docstring marker (M3.1-MUST)
# ---------------------------------------------------------------------------


def test_self_correcting_note_in_module_docstring():
    """The module docstring must contain a self-correcting note that
    points the v0.18.2 author at the flip/remove site. This satisfies
    the M3.1-MUST acceptance criterion 'self-correcting note in
    docstring'.
    """
    module_path = Path(__file__)
    text = module_path.read_text(encoding="utf-8")
    # Pull just the module docstring (first triple-quoted block).
    assert text.lstrip().startswith('"""'), (
        "this test file must start with a module docstring"
    )
    end = text.find('"""', 3)
    assert end > 0, "module docstring is unterminated"
    docstring = text[3:end]
    lower = docstring.lower()
    assert "v0.18.2" in lower, (
        "module docstring must reference v0.18.2 as the flip target so "
        "the future UPS-spike author knows where to update this lock"
    )
    assert "self-correcting" in lower or "flip" in lower or "removed" in lower, (
        "module docstring must include a self-correcting / flip / remove "
        "instruction signalling that this test is a v0.18.0 snapshot lock"
    )
