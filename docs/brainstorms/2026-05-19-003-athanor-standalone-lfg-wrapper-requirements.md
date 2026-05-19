---
date: 2026-05-19
topic: athanor-standalone-lfg-wrapper
origin: /athanor:discuss clarify mode (inline; lens 1-4 + scoping synthesis)
---

# athanor standalone LFG wrapper (v0.11.0)

## Summary

athanor v0.10.0 vendored 50 skills from compound-engineering + superpowers
under athanor namespace. But the LFG end-to-end pipeline in practice still
gets invoked via `/compound-engineering:lfg` (external plugin), with athanor
identity guards (Thin Leader, cross-model planner, Spec-then-TDD) layered
in only because the user happens to use athanor-native commands inside.
v0.11.0 introduces `/athanor:lfg` — an athanor-native wrapper that
explicitly invokes athanor commands at the identity-bearing steps (plan
+ work + review), reuses vendored CE flow for the remaining steps (commit
+ push + PR + CI watch). After v0.11.0, athanor stands alone: a user with
only athanor installed and no CE plugin can run the full pipeline through
`/athanor:lfg`.

---

## Problem Frame

The user is the sole maintainer + sole user today. The friction is not
present-day pain but a future-direction commitment: athanor was meant to
absorb CE/superpowers and stand alone as a vendored superset, yet the LFG
pipeline still requires `/compound-engineering:lfg` (the external CE
plugin's command). This means:

- v0.10.0's standalone narrative is technically incomplete — the LFG
  "killer flow" still routes through the upstream plugin.
- A new machine where athanor is installed but CE plugin is not would
  break the user's habit of invoking `/compound-engineering:lfg`.
- The honesty-arc commitment to "athanor stands alone" stays incomplete
  until LFG itself runs through athanor-native commands.

This is not urgent (current setup works), but it is the logical end-state
of the v0.10.0 absorption arc.

---

## Actors

- A1. **The user (athanor maintainer + primary operator)**: invokes the
  pipeline; expects athanor commands at the identity-bearing steps;
  values muscle-memory continuity with the v0.10.x LFG patterns used
  this session.

(External contributors / multi-user scenarios are out of scope for v0.11.0
— see Scope Boundaries.)

---

## Requirements

**Standalone capability (R1)**

- R1. athanor must be invokable end-to-end through `/athanor:*` commands
  without requiring `/compound-engineering:*` to be available on the
  user's machine.

**Wrapper skill shape (R2 — R3)**

- R2. A new `/athanor:lfg` skill (`skills/lfg/SKILL.md`) is created
  alongside the existing vendored `/athanor:ce-lfg`. Both coexist; the
  vendored copy stays at T2 provenance (body byte-identical to upstream).
- R3. The new wrapper's step 1 invokes `/athanor:plan` (cross-model
  adversarial — Planner A Claude + Planner B Codex + Critic). The
  wrapper's step 2 invokes `/athanor:work` (Spec-then-TDD discipline).
  athanor identity is the default for plan + work steps.

**Honesty arc continuity (R4)**

- R4. v0.11.0 release prose (CHANGELOG, STATE.md, README, CLAUDE.md)
  uses positive framing only — "athanor stands alone" / "athanor LFG
  invokes athanor-native commands at identity-bearing steps". It does
  NOT introduce phrases like "CE deprecated", "supersedes
  compound-engineering", "athanor replaces CE LFG", or any prose that
  colloquially marks CE as discouraged. The v0.10.0 commitment "does
  NOT deprecate upstream" is preserved verbatim through v0.11.0.

**Release shape (R5)**

- R5. v0.11.0 is a single release (one PR, one merge to main) — neither
  a long-running roadmap nor a multi-PR sequence.

---

## Acceptance Examples

- AE1. **Covers R1, R3.** When the user invokes `/athanor:lfg` in a
  Claude Code session with only athanor installed (no
  compound-engineering plugin), step 1 of the pipeline dispatches the
  cross-model adversarial planning flow (Planner A Claude + Planner B
  Codex + Critic) as in `/athanor:plan`, and step 2 dispatches the
  Spec-then-TDD execution as in `/athanor:work`. The pipeline reaches
  the commit/push/PR/CI steps successfully.
- AE2. **Covers R2.** After v0.11.0 ships, the file
  `skills/ce-lfg/SKILL.md` (vendored from compound-engineering 3.8.3)
  has the same body bytes as before the release (excluding the
  T2 provenance block which was already added at v0.10.0). The
  `tests/test_regression_v010_vendor_provenance.py` test stays green
  for ce-lfg.
- AE3. **Covers R4.** The v0.11.0 CHANGELOG entry, README banner,
  STATE.md Current Phase, and CLAUDE.md prose contain neither "CE
  deprecated", "athanor supersedes", nor "deprecate compound-engineering"
  phrases. A regression test pins this.

---

## Success Criteria

- **Human outcome**: The user has muscle memory `/athanor:lfg` and it
  works without needing the CE plugin installed. The user does not need
  to think about "which lfg" when starting a release pipeline.
- **Downstream agent handoff**: A future contributor reading
  `skills/lfg/SKILL.md` understands that the wrapper exists to inject
  athanor identity guards at plan + work steps, and that the vendored
  `/athanor:ce-lfg` continues to exist as the CE-default-flow option.
  CLAUDE.md §"Vendored Surface" identity commitment #2 + #3 stay
  pinned by tests.

---

## Scope Boundaries

- v0.11.0 wrapper step 3+ (review / commit / push / PR / CI) — these
  may reuse vendored CE skills (`ce-code-review`, `ce-commit-push-pr`,
  `ce-test-browser`) OR athanor-native equivalents (`/athanor:review`).
  The plan-write phase decides; user intent inferred toward
  athanor-first when an athanor-native equivalent exists.
- v0.11.0 does NOT remove or modify the vendored `/athanor:ce-lfg`
  skill (T2 provenance preserved).
- v0.11.0 does NOT change the v0.10.0 vendor-aware namespace policy
  (CE keeps `ce-*` prefix; superpowers keeps `sp-*`).
- v0.11.0 does NOT deprecate `/compound-engineering:lfg` direct invocation
  for users who prefer it. CE plugin compatibility is unchanged.
- v0.11.0 does NOT extend Stop hook coverage further (v0.10.3 boundary
  preserved).

### Deferred to Follow-Up Work

- **v0.11.1+ A4 closure**: superpowers `using-superpowers` skill-
  invocation-BEFORE-response cross-cutting integration with
  athanor-native skills. Separate brainstorm needed.
- **v0.11.2+ A5 closure**: native-vs-vendored deprecation decisions
  (e.g., `/athanor:discuss` synthesis mode vs `/athanor:ce-brainstorm`).
  Depends on A4 outcome.
- **v0.11.x LLM-class semantic similarity** (sec-003 last carry) and
  **transcript-event introspection** (sec-001 residual).
- **Mid-session profile mutation guard**.

---

## Key Decisions

- **D1 (carried from clarify lens 2)**: "athanor stands alone" is the
  user-environment definition. A new machine with only athanor (no CE
  plugin in `~/.claude/plugins/cache/`) must still run the full pipeline
  via `/athanor:lfg`.
- **D2 (carried from clarify lens 2)**: positive commitment only —
  "athanor stands alone" framing. CE direct invocation is not
  discouraged in any prose; the user chose framing explicitly.
- **D3 (carried from clarify lens 4)**: wrapper skill shape (option 3
  in attachment probe) — `/athanor:lfg` is a true wrapper, not just an
  alias. It encodes the athanor-first flow.

---

## Dependencies / Assumptions

- v0.10.3 already merged to main (5c56724); athanor namespace has
  `/athanor:plan`, `/athanor:work`, `/athanor:review`, etc., available.
- vendored `skills/ce-lfg/SKILL.md` continues to live at depth-1 in the
  skills tree with its T2 provenance block.
- Claude Code skill auto-discovery resolves a new `skills/lfg/SKILL.md`
  to `/athanor:lfg` automatically (depth-1 convention).
- The wrapper skill body referencing `/athanor:plan` / `/athanor:work`
  causes Claude Code to invoke those skills correctly when the user
  runs `/athanor:lfg` — i.e., athanor's own skill-to-skill chaining is
  the mechanism. (Plan-write may surface details about the chaining
  protocol if it needs refinement.)

---

## Outstanding Questions

### Resolve Before Planning

(none — clarify dialog answered all probe questions.)

### Deferred to Planning

- [Affects step 3+] Whether step 3 review should call `/athanor:review`
  (6-lens parallel, no autofix) or vendored `/athanor:ce-code-review`
  (18 personas, autofix mode). Default: athanor-first (`/athanor:review`).
  Plan-write commits the choice.
- [Affects steps 4–8] Remaining LFG steps (persist autofixes, residual
  handoff, browser test, commit/push/PR, CI watch). Plan-write decides
  the per-step routing — reuse vendored CE step body verbatim vs paraphrase
  in athanor voice. Default: reuse vendored prose for non-identity-bearing
  steps (avoid prose drift from upstream LFG flow).
