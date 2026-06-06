# v0.8.0 Critic Rubric — Spec-then-TDD Readiness (Shared)

This rubric is **advisory** — there is no runtime gate enforcing the
Critic's evaluation. The Critic's output `plan.md` is what `/athanor:work`
consumes; missed evaluations degrade the spec-then-tdd discipline silently
but do not break the pipeline. Canonical discipline overview: CLAUDE.md
§"Spec-then-TDD Discipline".

It is referenced from every Critic dispatch variant under
`references/critic-variants.md`: deep-tier 4-input synthesis, deep-tier
2-input synthesis (review-skipped), standard-tier 2-input refinement, and
standard-tier self-critic / claude-self-review fallback. The Critic MUST
evaluate the input plan along the axes below in addition to existing
criteria (clarity, completeness, risk treatment).

**v0.9.0 NOTE:** the rubric below is referenced from each Critic
Agent({prompt: ...}) block via the inline injection added in v0.9.0. The
injection text now lists four axes (A, B, C, D — axis C added in v0.9.0 for
R-ID traceback coverage; axis D simplicity/fail-loud added in v0.18.4). See
`docs/plans/2026-05-19-002-feat-v0.9.0-discuss-clarify-mode-plan.md` §U5.

## (A) Acceptance criteria coverage (`acceptance_criteria coverage`)

- For each behavior-bearing phase in `plan-a.md` (or `plan-b.md`), is the
  `Verify:` field written as MUST/SHOULD bullets rather than free-form prose?
- Do MUST bullets describe observable outcomes (exit codes, file state, schema
  validation, test count, error references) rather than abstract goals?
- Is there at least one MUST bullet per behavior phase?

## (C) R-ID traceback coverage (v0.9.0, gated on requirements.md presence)

- This axis fires ONLY when `.athanor/sessions/{id}/requirements.md` exists
  in the same session (clarify-mode upstream artifact from `/athanor:discuss`).
- For each phase in the plan, verify that the `Verify:` MUST/SHOULD bullets
  cite-back the relevant origin R-IDs (and A/F/AE-IDs where applicable) from
  requirements.md. Example acceptable cite-back: `MUST exit 2 when material
  claim detected (covers R3, AE1)`.
- Flag phases that introduce behavior obviously tied to a stated requirement
  but lack any R-ID cite-back — these silently break the trace between
  user-stated intent and implementation.
- When requirements.md is absent, axis (C) is skipped (backwards compat —
  pre-v0.9.0 sessions and grandfathered plans run unchanged).

## (B) Classification appropriateness (`execution_note` predictability)

- For each phase, predict the likely `execution_note` value (the
  `/athanor:work` Task Splitter will eventually assign one) based on its
  files and approach:
  - Phase touches `.py` / `.js` / `.ts` / etc. source code introducing new
    behavior or contract → expect `spec-then-tdd`. If the `Verify:` field is
    prose-only or absent, flag as **under-classification** (false-negative
    risk).
  - Phase modifies source preserving existing behavior (refactor, narrow bug
    fix without contract change) → expect `test-aware`.
  - Phase modifies only `.md` / `_doc` strings / CHANGELOG / version strings
    → expect `direct`. If MUST/SHOULD bullets are forced onto such a phase
    (a CHANGELOG-only phase with elaborate MUST/SHOULD), flag as
    **over-classification** (false-positive risk).
- Flag any phase where the planner's stated intent contradicts the file-set
  signal (e.g., "Add new feature X" but the `files:` list only touches
  CHANGELOG.md or `_doc` strings).

## (D) Simplicity & fail-loud readiness (v0.18.4, advisory)

Applies CLAUDE.md §Core Principle "Engineering quality" to the plan:

- **Unjustified complexity / scope** — does a phase add complexity or scope
  beyond what its acceptance criteria require? If a simpler approach meets the
  same MUST bullets, flag it (premature abstraction, needless generalization,
  "and also..." scope-creep). Works is the floor, not the goal.
- **Fail-loud over silent fallback** — does the design swallow a
  should-be-fixed error into a fallback / silent-degrade path (hard to find
  later)? Prefer surfacing the error (fail-loud). Flag fallbacks that mask real
  failures; deliberate fallbacks must be logged/announced.
- **Advisory** — like (A)/(B)/(C), no runtime gate; surface as a plan-body
  note ("SIMPLICITY/FAIL-LOUD — …") for the Splitter/executor to weigh.

## Corrective behavior when violations are found

- **Reformulate prose Verify fields** into MUST/SHOULD bullets where the
  phase is behavior-bearing (axis A).
- Add missing observable assertions to phases that have MUST/SHOULD bullets
  but lack at least one observable MUST.
- **Adjust phase scope or Verify formality** where classification is
  mismatched (axis B) — if a phase is too broad and conflates source-code
  work with doc-only work, split it; if a `_doc`-only phase has forced
  MUST/SHOULD, demote the Verify to prose.
- Flag any phase the Critic cannot reformulate (insufficient detail from
  planner) — leave it but emit an "UNRESOLVED — classification risk" note
  in the plan body so the downstream Splitter (which cannot see the
  Critic's reasoning) is aware of the uncertainty.

## Scope

The rubric applies identically to **Codex-driven** dispatches
(`review_strategy=codex`), **Claude self-review fallback** dispatches
(`review_strategy=claude-self-review` — a.k.a. `codex.fallback=self-critic`),
and the **review-skipped** Critic pass-through (which is a copy operation,
not a true Critic — but its presence in this skill is what the
`claude-self-review` path also takes when reviews exist).
