"""Regression: contract for v0.13.0 LFG-goal config block + schema extension.

This test file asserts the contract that Subtasks 5 (schema extension)
and 6 (athanor.json + templates/athanor.json default block) MUST satisfy.
Neither the schema property nor the runtime block exists yet at the time
this file is authored (Subtask 3 of the v0.13.0 plan); every underlying
assertion would fail today. Each test is therefore decorated
``@pytest.mark.xfail(strict=False)`` so the suite remains green during
the rest of the v0.13.0 work session. Subtasks 5 and 6 will REMOVE the
xfail decorators after landing their respective artifacts, flipping
XFAIL -> regular GREEN.

The v0.12.0 deprecation-test subtasks (5+17) used the same
xfail-then-remove pattern; Subtask 2 mirrored it for the `lfg-loop`
SKILL.md contract; this file mirrors it for the config-block surface.

``strict=False`` is intentional: if a later subtask lands a passing
implementation but forgets to remove a decorator, the test reports XPASS
rather than failing the suite.

Decision references (see ``.athanor/sessions/2026-05-22-002/decisions.md``):

- D8 -- ``lfgLoop.maxIterations`` default = 5
- D9 -- ``lfgLoop.consolidateCycles`` default = false

Unlock map (per Subtask 3 dispatch packet "Cross-subtask coordination"):

- Schema property block (tests 1 and 5) unlocks at **Subtask 5**.
- Runtime values + parity (tests 2, 3, 4) unlock at **Subtask 6**.
- Combined schema-validates-runtime test (test 5) unlocks once both
  Subtasks 5 and 6 have landed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "athanor-config.schema.json"
ROOT_CONFIG = REPO_ROOT / "athanor.json"
TEMPLATE_CONFIG = REPO_ROOT / "templates" / "athanor.json"
LFG_SKILL = REPO_ROOT / "skills" / "lfg" / "SKILL.md"


def _load_json(path: Path):
    """Read ``path`` as JSON. Bubbles FileNotFoundError / JSONDecodeError up so
    that xfail captures the underlying failure mode uniformly."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test 1 -- schema declares lfgLoop section
# ---------------------------------------------------------------------------


def test_schema_declares_lfg_loop_section():
    """MUST: schema ``properties.lfgLoop`` declares ``maxIterations`` and ``consolidateCycles``.

    Plan v0.13.0 §Phase 3a extends the runtime config schema so the
    ``lfgLoop`` section is first-class. The block MUST surface at least
    two properties: ``maxIterations`` (integer, D8 default 5) and
    ``consolidateCycles`` (boolean, D9 default false). This test locks
    the property-name shape; default-value enforcement lives in the
    runtime-instance tests below.
    """
    schema = _load_json(SCHEMA_PATH)
    properties = schema.get("properties") or {}
    lfg_loop = properties.get("lfgLoop")
    assert isinstance(lfg_loop, dict), (
        "schema must declare a top-level 'lfgLoop' object under properties; "
        f"got {type(lfg_loop).__name__}"
    )
    lfg_props = lfg_loop.get("properties") or {}
    assert "maxIterations" in lfg_props, (
        "schema lfgLoop block must declare a 'maxIterations' property"
    )
    assert "consolidateCycles" in lfg_props, (
        "schema lfgLoop block must declare a 'consolidateCycles' property"
    )


# ---------------------------------------------------------------------------
# Test 2 -- D8 default maxIterations = 5
# ---------------------------------------------------------------------------


def test_athanor_json_max_iterations_default_5():
    """MUST: ``athanor.json`` declares ``lfgLoop.maxIterations == 5`` (D8).

    D8 (decisions.md) confirms the default per user dialog: 5 cycles is
    the documented runway before the circuit breaker trips. The runtime
    config file must carry this default verbatim so users do not need
    to read the schema to learn the limit.
    """
    config = _load_json(ROOT_CONFIG)
    lfg_loop = config.get("lfgLoop")
    assert isinstance(lfg_loop, dict), (
        "athanor.json must declare a top-level 'lfgLoop' object; "
        f"got {type(lfg_loop).__name__}"
    )
    assert lfg_loop.get("maxIterations") == 5, (
        f"athanor.json lfgLoop.maxIterations must equal 5 per D8; got "
        f"{lfg_loop.get('maxIterations')!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 -- D9 default consolidateCycles = false
# ---------------------------------------------------------------------------


def test_athanor_json_consolidate_cycles_default_false():
    """MUST: ``athanor.json`` declares ``lfgLoop.consolidateCycles == false`` (D9).

    D9 (decisions.md) confirms per-cycle release as the default: each
    cycle ships its own PR + tag. ``consolidateCycles=true`` (single PR
    + final release) is the documented opt-in. The runtime config file
    must carry this default verbatim.
    """
    config = _load_json(ROOT_CONFIG)
    lfg_loop = config.get("lfgLoop")
    assert isinstance(lfg_loop, dict), (
        "athanor.json must declare a top-level 'lfgLoop' object; "
        f"got {type(lfg_loop).__name__}"
    )
    assert lfg_loop.get("consolidateCycles") is False, (
        f"athanor.json lfgLoop.consolidateCycles must equal false per D9; "
        f"got {lfg_loop.get('consolidateCycles')!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 -- athanor.json + templates/athanor.json parity for lfgLoop
# ---------------------------------------------------------------------------


def test_athanor_json_and_template_parity_for_lfg_loop():
    """MUST: root ``athanor.json`` and ``templates/athanor.json`` carry identical lfgLoop blocks.

    Per CLAUDE.md §Defense Mechanisms and the existing
    ``test_regression_setup_template_matches`` precedent, the two
    runtime config files must stay shape-identical so ``/athanor:setup``
    does not introduce silent drift between dev (root) and user-install
    (template) defaults. The lfgLoop block extends this lock.

    Both keys AND values must match.

    History: pre-S09 ``_doc`` inline-doc strings were also part of the
    parity contract. S09 (per user decision U3) hard-removed all
    ``_doc`` fields from both files, so the parity contract now covers
    only operational keys; documentation moved to the JSON Schema
    ``description`` fields under ``schemas/athanor-config.schema.json``.
    """
    root = _load_json(ROOT_CONFIG)
    template = _load_json(TEMPLATE_CONFIG)
    root_block = root.get("lfgLoop")
    template_block = template.get("lfgLoop")
    assert isinstance(root_block, dict), (
        "athanor.json must declare 'lfgLoop' as an object; "
        f"got {type(root_block).__name__}"
    )
    assert isinstance(template_block, dict), (
        "templates/athanor.json must declare 'lfgLoop' as an object; "
        f"got {type(template_block).__name__}"
    )
    assert set(root_block.keys()) == set(template_block.keys()), (
        "lfgLoop keys must match exactly between athanor.json and "
        f"templates/athanor.json; root={sorted(root_block.keys())!r} "
        f"template={sorted(template_block.keys())!r}"
    )
    for key in root_block.keys():
        assert root_block[key] == template_block[key], (
            f"lfgLoop[{key!r}] differs between athanor.json and "
            f"templates/athanor.json; root={root_block[key]!r} "
            f"template={template_block[key]!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 -- full schema validates athanor.json including the new block
# ---------------------------------------------------------------------------


def test_schema_validates_athanor_json_lfg_loop_block():
    """MUST: ``athanor.json`` validates against the extended schema.

    The extended schema (Subtask 5) plus the new runtime block
    (Subtask 6) must compose into a green validation pass. This test
    holds the full-instance contract that the existing
    ``test_regression_schema_validates_config`` precedent established
    for the rest of the config; the lfgLoop block must satisfy the same
    bar.

    Uses ``pytest.importorskip("jsonschema")`` so the suite degrades
    gracefully on CI images that omit the optional dependency, mirroring
    the precedent in ``test_regression_schema_validates_config.py``.

    Layered assertion (BOTH must hold for GREEN):

    1. The schema's ``properties.lfgLoop`` block is declared (locks
       Subtask 5's deliverable). Without this, the root schema's
       permissive ``additionalProperties: true`` would silently let an
       unknown ``lfgLoop`` runtime block validate as a no-op -- the
       contract would not actually be enforced.
    2. The runtime ``athanor.json`` instance validates against the full
       schema (locks Subtask 6's deliverable).
    """
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_json(SCHEMA_PATH)
    properties = schema.get("properties") or {}
    assert "lfgLoop" in properties, (
        "schema must declare a top-level 'lfgLoop' property block before this "
        "test can be considered a real contract lock; without it, the root "
        "schema's permissive additionalProperties=true would let any shape "
        "validate vacuously"
    )
    instance = _load_json(ROOT_CONFIG)
    jsonschema.validate(instance=instance, schema=schema)


# ---------------------------------------------------------------------------
# Test 6 -- lfg.maxFixRounds default = 3 (Step 3/8 fix-round cap, Phase 4)
# ---------------------------------------------------------------------------


def test_athanor_json_lfg_max_fix_rounds_default_3():
    """MUST: ``athanor.json`` declares ``lfg.maxFixRounds == 3``.

    Phase 4 of the verdict-anchor / lfg-fix-counter plan wires a real
    session-scoped fix-round counter (``scripts/loops/lfg_fix_round_counter.py``)
    that the leader branches on at /athanor:lfg Step 3 (review-fix) and
    Step 8 (CI-fix). The cap is config-driven; the runtime config file must
    carry the default 3 so the documented "up to 3 fix rounds" limit and the
    counter's ``max_rounds`` agree. Honesty label: ADVISORY (leader-bound
    exit-code) — NOT enforced.
    """
    config = _load_json(ROOT_CONFIG)
    lfg = config.get("lfg")
    assert isinstance(lfg, dict), (
        "athanor.json must declare a top-level 'lfg' object; "
        f"got {type(lfg).__name__}"
    )
    assert lfg.get("maxFixRounds") == 3, (
        f"athanor.json lfg.maxFixRounds must equal 3 (Step 3/8 fix-round cap "
        f"default); got {lfg.get('maxFixRounds')!r}"
    )


def test_template_json_lfg_max_fix_rounds_default_3():
    """MUST: ``templates/athanor.json`` declares ``lfg.maxFixRounds == 3``.

    Parity with the root config (cf. Test 4): the user-install template must
    ship the same Step 3/8 fix-round cap default so /athanor:setup does not
    introduce silent drift between dev and user-install defaults.
    """
    config = _load_json(TEMPLATE_CONFIG)
    lfg = config.get("lfg")
    assert isinstance(lfg, dict), (
        "templates/athanor.json must declare a top-level 'lfg' object; "
        f"got {type(lfg).__name__}"
    )
    assert lfg.get("maxFixRounds") == 3, (
        f"templates/athanor.json lfg.maxFixRounds must equal 3; got "
        f"{lfg.get('maxFixRounds')!r}"
    )


# ---------------------------------------------------------------------------
# Test 8 -- dead-config removal: userConfirmAfter must stay gone (C004-G4)
# ---------------------------------------------------------------------------


def test_user_confirm_after_is_removed():
    """MUST: ``lfgLoop.userConfirmAfter`` is absent from config + schema.

    Removed in C004-G4: the knob was schema-described ("pause for user
    confirmation after N cycles") but NEVER wired into skills/lfg-loop/SKILL.md
    — no loop step branches on it; the only live pause cadences are
    ``maxIterations``, the no-progress circuit breaker, scope-drift high
    severity, and Tier-3 ratification. A grep over scripts/skills/hooks found
    zero behavioral consumer, so the key was decorative config. This guard
    fails loud if it is re-introduced without a real consumer.
    """
    root = _load_json(ROOT_CONFIG)
    template = _load_json(TEMPLATE_CONFIG)
    schema = _load_json(SCHEMA_PATH)

    assert "userConfirmAfter" not in (root.get("lfgLoop") or {}), (
        "athanor.json lfgLoop must NOT re-introduce the dead 'userConfirmAfter' "
        "knob without wiring a real loop consumer (C004-G4 removal)."
    )
    assert "userConfirmAfter" not in (template.get("lfgLoop") or {}), (
        "templates/athanor.json lfgLoop must NOT re-introduce 'userConfirmAfter' "
        "(C004-G4 removal)."
    )
    lfg_schema_props = (
        ((schema.get("properties") or {}).get("lfgLoop") or {}).get("properties")
        or {}
    )
    assert "userConfirmAfter" not in lfg_schema_props, (
        "schema lfgLoop must NOT declare 'userConfirmAfter' (C004-G4 removal); "
        "re-add only alongside a real loop-step consumer."
    )


# ---------------------------------------------------------------------------
# Test 7 -- doc-consistency: the Step 3/8 honesty relabel is not stale
# ---------------------------------------------------------------------------


def test_lfg_skill_fix_round_relabel_not_stale():
    """MUST: ``skills/lfg/SKILL.md`` no longer claims "no programmatic counter"
    for the Step 3/8 fix-round loops, and the new counter protocol is wired.

    Phase 4 (d) doc-consistency lock: the relabel from *"prose guidance for the
    leader; there is no programmatic counter"* to the
    ``lfg_fix_round_counter.py ... exit 3 = cap`` protocol must actually have
    landed, so the honesty relabel in CLAUDE.md / the schema is not a stale
    claim. The Step 8.5 merge-readiness gate is the only place that may still
    carry the "no runtime hook" framing for ITSELF; the
    literal phrase "no programmatic counter" must be gone for the fix loops.
    """
    body = LFG_SKILL.read_text(encoding="utf-8")
    # The old admission must be gone entirely; the merge-gate row has its own
    # "no runtime hook" self-description, which does not use this exact phrase.
    assert "no programmatic counter" not in body, (
        "skills/lfg/SKILL.md still contains the stale 'no programmatic counter' "
        "admission — Phase 4 relabels the Step 3/8 fix-round loops to the real "
        "exit-code counter; this phrase must no longer appear."
    )
    # The real counter protocol must be wired into the fix loops.
    assert "lfg_fix_round_counter.py" in body, (
        "skills/lfg/SKILL.md must reference scripts/loops/lfg_fix_round_counter.py "
        "for the Step 3/8 fix-round loops (the real exit-code counter)."
    )
    assert "exit 3" in body, (
        "skills/lfg/SKILL.md must document 'exit 3 = cap reached' as the "
        "fix-round stop signal the leader branches on."
    )
    # The relabel must be honest: advisory / leader-bound, NOT claimed enforced.
    assert "advisory (leader-bound exit code)" in body, (
        "skills/lfg/SKILL.md must label the fix-round counter ADVISORY "
        "(leader-bound exit code), not enforced."
    )
