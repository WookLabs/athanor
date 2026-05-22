"""Regression: contract for v0.13.0 `/athanor:lfg-goal` skill surface.

This test file asserts the contract that Subtask 4's
`skills/lfg-goal/SKILL.md` MUST satisfy. The skill file does not exist
yet at the time this test file is authored (Subtask 2 of the v0.13.0
plan); every underlying assertion would fail today. Each test is
therefore decorated `@pytest.mark.xfail(strict=False)` so the suite
remains green during the rest of the v0.13.0 work session. Subtask 4
will REMOVE the xfail decorators after creating SKILL.md, flipping
XFAIL → regular GREEN.

The v0.12.0 deprecation-test subtasks (5+17) used the same
xfail-then-remove pattern; this file follows that precedent.

`strict=False` is intentional: if Subtask 4 lands a passing
implementation but forgets to remove a decorator, the test reports
XPASS rather than failing the suite.

Decision references (see `.athanor/sessions/2026-05-22-002/decisions.md`):
- D8 — `lfgGoal.maxIterations` default = 5
- D9 — `lfgGoal.consolidateCycles` default = false
- D10 — both invocation forms supported (inline goal + --goal-file)
- D11 — no new identity invariant; reuse the existing 4 (Thin Leader +
  cross-model adversarial planning + Spec-then-TDD discipline + Stop
  hook runtime gate)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "lfg-goal" / "SKILL.md"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _read_skill_text() -> str:
    """Return the full SKILL.md body. Raises FileNotFoundError if missing.

    Each test wraps this in its own assertion path so that xfail captures
    the underlying failure (missing file OR missing content) uniformly.
    """
    return SKILL_PATH.read_text(encoding="utf-8")


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse the leading YAML-ish frontmatter delimited by `---` lines.

    athanor SKILL.md frontmatter uses simple `key: value` pairs (multi-line
    description folded via `>` is also present in `skills/lfg/SKILL.md`).
    This helper extracts top-level scalar fields only; nested structures
    are returned as the raw remainder string for the body of the file.

    Returns (frontmatter_dict, body_text). Raises ValueError if no
    frontmatter block is found.
    """
    if not text.startswith("---"):
        raise ValueError("SKILL.md missing leading '---' frontmatter delimiter")
    # split into [empty, frontmatter, body...] — only first two `---` lines
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("SKILL.md frontmatter not terminated by closing '---'")
    fm_raw, body = parts[1], parts[2]
    fm: dict[str, str] = {}
    current_key: str | None = None
    for line in fm_raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # top-level scalar: `key: value`
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if m and not line.startswith(" "):
            key = m.group(1)
            value = m.group(2).strip()
            fm[key] = value
            current_key = key
        elif current_key is not None and line.startswith(" "):
            # folded continuation — append to current key's value
            fm[current_key] = (fm[current_key] + " " + stripped).strip()
    return fm, body


# ---------------------------------------------------------------------------
# Test 1 — file exists at depth-1
# ---------------------------------------------------------------------------


def test_skill_file_exists():
    """MUST: `skills/lfg-goal/SKILL.md` exists at depth-1 path.

    athanor's Claude Code skill auto-discovery resolves skills only when
    the SKILL.md sits directly under `skills/<slot>/` (depth 1). The
    v0.13.0 plan mandates this slot for the new `/athanor:lfg-goal`
    skill.
    """
    assert SKILL_PATH.is_file(), (
        f"Expected skill file at {SKILL_PATH.relative_to(REPO_ROOT)}; "
        "Subtask 4 has not created it yet."
    )


# ---------------------------------------------------------------------------
# Test 2 — frontmatter required fields
# ---------------------------------------------------------------------------


def test_frontmatter_has_required_fields():
    """MUST: frontmatter contains `name: lfg-goal` and `user-invocable: true`.

    Mirrors the canonical shape in `skills/lfg/SKILL.md`: `name`,
    `description`, `user-invocable`, `allowed-tools`. The slot name and
    user-invocable flag are the load-bearing entries for skill
    auto-discovery as a user-callable command.
    """
    text = _read_skill_text()
    fm, _body = _split_frontmatter(text)
    assert fm.get("name") == "lfg-goal", (
        f"frontmatter `name` must equal 'lfg-goal'; got {fm.get('name')!r}"
    )
    assert fm.get("user-invocable") == "true", (
        f"frontmatter `user-invocable` must equal 'true'; got "
        f"{fm.get('user-invocable')!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Validated Receipt-Ledger Loop literal in body
# ---------------------------------------------------------------------------


def test_skill_body_contains_validated_receipt_ledger_loop():
    """MUST: body contains the literal phrase 'Validated Receipt-Ledger Loop'.

    Plan v0.13.0 §Approach names the three-layer architecture as the
    'Validated Receipt-Ledger Loop'. The SKILL.md must reproduce this
    exact heading so users and downstream tooling can locate the
    section.
    """
    text = _read_skill_text()
    _fm, body = _split_frontmatter(text)
    assert "Validated Receipt-Ledger Loop" in body, (
        "skill body must contain literal 'Validated Receipt-Ledger Loop' phrase"
    )


# ---------------------------------------------------------------------------
# Test 4 — v0.11.1 using-superpowers boundary subsection
# ---------------------------------------------------------------------------


def test_using_superpowers_boundary_subsection_present():
    """MUST: body contains `### v0.11.1 using-superpowers boundary` heading.

    Per the v0.11.1 boundary lock (see CLAUDE.md §Defense Mechanisms),
    every athanor-native Thin Leader skill carries an identical
    `### v0.11.1 using-superpowers boundary` subsection placed
    immediately after the §Identity heading. `/athanor:lfg-goal` is a
    Thin Leader skill (it dispatches the receipt-validator + judges +
    cycles, never executes work directly) and therefore inherits the
    boundary requirement.
    """
    text = _read_skill_text()
    _fm, body = _split_frontmatter(text)
    assert "### v0.11.1 using-superpowers boundary" in body, (
        "skill body must contain '### v0.11.1 using-superpowers boundary' "
        "subsection heading (matches the 10-skill native roster lock)"
    )


# ---------------------------------------------------------------------------
# Test 5 — <promise>DONE</promise> insufficiency clause
# ---------------------------------------------------------------------------


def test_promise_done_insufficiency_clause_present():
    """MUST: body states `<promise>DONE</promise>` alone is insufficient for cycle completion.

    Plan v0.13.0 §Layer 2 §Adversarial 3-tier check makes the
    receipt-validator the sole authority for cycle DONE. The SKILL.md
    must explicitly state that the bare `<promise>DONE</promise>`
    sentinel (which `/athanor:lfg` emits at the end of a single cycle)
    is NOT a sufficient signal — a validator-passed receipt is
    required. This clause closes the silent-bypass hole flagged by
    Reviewer-B H1/H2/H3.
    """
    text = _read_skill_text()
    _fm, body = _split_frontmatter(text)
    assert "<promise>DONE</promise>" in body, (
        "skill body must reference the literal `<promise>DONE</promise>` "
        "sentinel string"
    )
    # heuristic: insufficiency stated with explicit 'insufficient' OR
    # 'not sufficient' OR 'cannot infer' phrasing within the same body
    insufficiency_signals = (
        "insufficient",
        "not sufficient",
        "cannot infer",
        "is not enough",
        "alone does not",
        "alone is not",
    )
    body_lower = body.lower()
    assert any(sig in body_lower for sig in insufficiency_signals), (
        "skill body must include an explicit insufficiency clause near the "
        "`<promise>DONE</promise>` reference (e.g., 'insufficient', "
        "'cannot infer', 'not sufficient')"
    )


# ---------------------------------------------------------------------------
# Test 6 — four identity invariants named in body (D11)
# ---------------------------------------------------------------------------


def test_four_identity_invariants_prose_present():
    """MUST: all 4 athanor identity invariants are named in the body.

    Per D11 (decisions.md), `/athanor:lfg-goal` does NOT introduce a new
    identity invariant. It reuses the existing four declared in
    CLAUDE.md §"Vendored Surface — Identity Guard Layer":

    1. Thin Leader contract
    2. Cross-model adversarial planning (`/athanor:plan`)
    3. Spec-then-TDD discipline (`/athanor:work` Splitter classification)
    4. Stop hook runtime gate (`stop_verify_claims.py`)

    The SKILL.md must name all four so the orchestration layer's
    inheritance is explicit and the boundary contract is auditable.
    """
    text = _read_skill_text()
    _fm, body = _split_frontmatter(text)
    body_lower = body.lower()
    missing: list[str] = []
    if "thin leader" not in body_lower:
        missing.append("Thin Leader")
    if "cross-model" not in body_lower:
        missing.append("cross-model adversarial planning")
    if "spec-then-tdd" not in body_lower:
        missing.append("Spec-then-TDD discipline")
    if "stop hook" not in body_lower:
        missing.append("Stop hook runtime gate")
    assert not missing, (
        "skill body must name all 4 identity invariants; missing: "
        f"{missing}"
    )


# ---------------------------------------------------------------------------
# Test 7 — D8 default maxIterations = 5
# ---------------------------------------------------------------------------


def test_d8_default_max_iterations_5_documented():
    """MUST: body documents `maxIterations: 5` as the default.

    D8 (decisions.md) confirms the default per user dialog: 5 cycles is
    the documented runway before the circuit breaker trips. The
    SKILL.md must surface this default so users do not need to read
    `athanor.json` to learn the limit.

    Acceptable phrasings (any one passes):
    - `maxIterations: 5`
    - `max-iterations 5`
    - `default 5`
    - `5 cycles` (when near the keyword 'default' or 'maxIterations')
    """
    text = _read_skill_text()
    _fm, body = _split_frontmatter(text)
    body_lower = body.lower()
    signals = (
        "maxiterations: 5",
        "maxiterations=5",
        "max-iterations 5",
        "max-iterations=5",
        "max-iterations: 5",
        "default: 5",
        "default 5",
        "default of 5",
        "(default 5)",
    )
    assert any(sig in body_lower for sig in signals), (
        "skill body must document the D8 maxIterations=5 default; "
        f"none of {signals!r} found"
    )


# ---------------------------------------------------------------------------
# Test 8 — D9 default consolidateCycles = false
# ---------------------------------------------------------------------------


def test_d9_default_consolidate_cycles_false_documented():
    """MUST: body documents `consolidateCycles: false` as the default.

    D9 (decisions.md) confirms per-cycle release as the default: each
    cycle ships its own PR + tag. `consolidateCycles=true` (single PR
    + final release) is the documented opt-in. The SKILL.md must
    surface the default so users understand the version-space impact
    before invoking.
    """
    text = _read_skill_text()
    _fm, body = _split_frontmatter(text)
    body_lower = body.lower()
    signals = (
        "consolidatecycles: false",
        "consolidatecycles=false",
        "consolidate-cycles false",
        "consolidate-cycles: false",
        "default: false",
        "default false",
        "default of false",
        "per-cycle release",
        "per-cycle pr",
    )
    assert any(sig in body_lower for sig in signals), (
        "skill body must document the D9 consolidateCycles=false default "
        "(or its 'per-cycle release' equivalent prose); "
        f"none of {signals!r} found"
    )


# ---------------------------------------------------------------------------
# Test 9 — D10 both invocation forms documented
# ---------------------------------------------------------------------------


def test_both_invocation_forms_documented():
    """MUST: body documents both inline AND `--goal-file` invocation forms.

    D10 (decisions.md) keeps both forms supported:
    - Inline: `/athanor:lfg-goal "ship a CLI that does X"` —
      auto-generated goal-id, simple goals.
    - File:   `/athanor:lfg-goal --goal-file goals/cli-feature.md` —
      pre-curated goal file for long-form / repeat use.

    Both forms must appear in the SKILL.md user-facing prose.
    """
    text = _read_skill_text()
    _fm, body = _split_frontmatter(text)
    body_lower = body.lower()

    # inline form signal: the command + a quoted text argument
    inline_pattern = re.compile(r"/athanor:lfg-goal\s+[\"']", re.IGNORECASE)
    has_inline = bool(inline_pattern.search(body))
    assert has_inline, (
        "skill body must show the inline invocation form, e.g., "
        "`/athanor:lfg-goal \"<text>\"`"
    )

    # --goal-file form signal: literal flag string
    assert "--goal-file" in body_lower, (
        "skill body must document the `--goal-file <path>` invocation form"
    )
