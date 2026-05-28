# Critic Dispatch Variants (Step 4 Detail)

This reference holds the full Critic Agent dispatch packets. The SKILL.md
router carries the per-tier orchestration logic and points here for the
actual prompt text.

Variant selection recap (full text in SKILL.md):

- **Deep tier:** Critic reads `plan-a.md`, `plan-b.md`, `review-of-a.md`,
  `review-of-b.md` and produces `plan.md`. (If `review_strategy=none`,
  reviews are absent; Critic reads only the two plans — use the 2-input
  synthesis variant.)
- **Standard tier:** Critic reads `plan-a.md` + `review-of-a.md` and
  produces `plan.md`. (If `review_strategy=none`, Critic is a trivial
  pass-through: copies `plan-a.md` to `plan.md` with a prepended
  `<!-- athanor:review-skipped -->` HTML header comment so downstream
  `/athanor:work` can detect that review was skipped.)
- **Lite tier:** Step 4 skipped; `plan-a.md` is copied directly to
  `plan.md`.

#### Critic Dispatch Gate Checkpoint

Before dispatching the Critic, the Leader MUST announce:

```
Critic dispatch: model=opus, inline-prompt mode, tier={deep|standard}, review_strategy={codex|claude-self-review|none}
  Expect: inline-prompt behavior, NOT registered athanor-critic agent behavior
```

> **COLLISION GUARD**: The Critic MUST use the inline prompt from this skill, NOT the registered `athanor-critic` agent's system prompt. The inline prompt contains specific session file paths (plan-a.md, plan-b.md, review files) that the registered agent does not know about.

> **Pass-through case:** If `tier == standard AND review_strategy == none`, do NOT dispatch the Critic Agent at all. Instead, the Leader uses Bash to prepend the `<!-- athanor:review-skipped -->` header to `plan-a.md` and write the result to `plan.md`, e.g.:
> ```bash
> { printf '<!-- athanor:review-skipped -->\n'; cat .athanor/sessions/{id}/plan-a.md; } > .athanor/sessions/{id}/plan.md
> ```
> Then announce: "Review skipped per codex.fallback=skip; plan-a.md copied to plan.md with review-skipped header."

#### Deep Tier: 4-Input Synthesis Critic (when review_strategy != none)

> The Critic is always Claude (opus), regardless of tier or Codex availability.
> In deep tier with reviews present, it receives all 4 inputs (plan-a, plan-b,
> review-of-a, review-of-b). For the `review_strategy == none` case, use the
> 2-input variant below instead — do NOT dispatch this 4-input block with
> empty or missing review files.
> In standard tier, see §"Standard Tier: 2-Input Refinement Critic" below.
> When `review_strategy == none` in standard tier, the Critic step is replaced
> by the Bash pass-through above; no Agent is dispatched.
> In lite tier, this step is skipped entirely.

```
Agent({
  description: "Athanor critic: plan synthesis",
  model: "opus",
  prompt: "ultrathink

You are the Athanor Critic in Plan Synthesis mode.

## Task
Synthesize two competing plans and their cross-reviews into one superior plan.

Read these 4 files from .athanor/sessions/{session-id}/:
1. plan-a.md (Plan A — standard approach)
2. plan-b.md (Plan B — contrarian approach)
3. review-of-a.md (Review of Plan A)
4. review-of-b.md (Review of Plan B)

Conditional v0.9.0 input — also read if present:
5. requirements.md (clarify-mode origin requirements doc with R-IDs /
   A-IDs / F-IDs / AE-IDs). When present, axis (C) R-ID traceback
   coverage fires — verify each phase's MUST/SHOULD Verify bullets in
   plan-a.md / plan-b.md cite-back the origin IDs.

## Process
1. Read all 4 documents
2. Identify where both plans AGREE — these are high-confidence choices
3. Identify where they DISAGREE — evaluate both reviews
4. For each conflict:
   - If one side has stronger evidence/feasibility → resolve in their favor
   - If genuinely ambiguous → mark as UNRESOLVED
5. Merge the best elements into a unified plan

## Output Format

# Final Plan: {title}

## Merged Elements (both plans agreed)
- {element}: {why it's high-confidence}

## Resolved Conflicts
- {conflict}: chose {approach} because {reasoning}

## UNRESOLVED — User Decision Required
### Conflict 1: {description}
- **Option A** (from Plan A): {approach} — {reasoning}
- **Option B** (from Plan B): {approach} — {reasoning}
- **Critic's lean**: {slight preference if any}

## Unified Implementation Plan

### Goal
{merged goal}

### Approach
{synthesized strategy}

### Phases
{merged phases — best steps from both plans}

### Risks & Mitigations
{comprehensive risk list from both plans + reviews}

### Estimated Scope
{merged scope estimate}

## Rules
- Account for EVERY element from both plans — don't silently drop anything
- Be explicit about WHY you chose one approach over another
- UNRESOLVED conflicts must present both options fairly

## v0.8.0 Critic Rubric — Spec-then-TDD Readiness (REQUIRED)

In addition to the general rules above, apply the three-axis Spec-then-TDD
readiness rubric to the synthesized plan (acceptance_criteria coverage +
execution_note classification appropriateness + R-ID traceback coverage) —
full text in `skills/plan/references/critic-rubric.md` (also referenced from
`skills/plan/SKILL.md` §\"v0.8.0 Critic Rubric — Spec-then-TDD
Readiness\").

Axis (A) — acceptance_criteria coverage: for every behavior-bearing phase
in the synthesized plan, ensure the Verify field is written as MUST/SHOULD
observable assertions (not free-form prose). At least one MUST per behavior
phase. Reformulate prose Verify fields where needed.

Axis (B) — classification appropriateness: predict the likely execution_note
value for each phase. Flag over-classification (CHANGELOG-only / _doc-only
phase forced into MUST/SHOULD) and under-classification (source code
modification with prose-only Verify). Adjust phase scope or Verify formality
to match.

Axis (C) — R-ID traceback coverage (v0.9.0; gated on requirements.md presence):
when `.athanor/sessions/{id}/requirements.md` exists in the same session,
verify that each phase's MUST/SHOULD Verify bullets cite-back the relevant
origin R-IDs / A-IDs / F-IDs / AE-IDs. Flag any behavior-bearing phase that
silently fails to trace back to a stated requirement. When requirements.md
is absent, axis (C) is skipped (backwards compat).

Save to: .athanor/sessions/{session-id}/plan.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of synthesized plan}
END_RESULT"
})
```

#### Deep Tier: 2-Input Synthesis Critic (when review_strategy == none)

When `tier == deep AND review_strategy == none`: no review files exist, but
the deep-tier Synthesis Critic is still useful because two contrarian plans
(plan-a + plan-b) need merging. Dispatch this 2-input variant instead of the
4-input block above. The output `plan.md` MUST be prepended with the
`<!-- athanor:review-skipped -->` HTML header comment so `/athanor:work` can
detect that no review pass ran.

```
Agent({
  description: "Athanor critic: plan synthesis (review-skipped)",
  model: "opus",
  prompt: "ultrathink

You are the Athanor Critic in Plan Synthesis mode (review-skipped variant).

## Task
Synthesize two competing plans into one superior plan. Reviews were skipped
this session (codex.fallback=skip); rely on the plans themselves.

Read these 2 files from .athanor/sessions/{session-id}/:
1. plan-a.md (Plan A — standard approach)
2. plan-b.md (Plan B — contrarian approach)

Conditional v0.9.0 input — also read if present:
3. requirements.md (clarify-mode origin requirements doc with R-IDs /
   A-IDs / F-IDs / AE-IDs). When present, axis (C) R-ID traceback
   coverage fires — verify each phase's MUST/SHOULD Verify bullets in
   plan-a.md / plan-b.md cite-back the origin IDs.

## Process
1. Read both plans
2. Identify where they AGREE — these are high-confidence choices
3. Identify where they DISAGREE — note both options and which has stronger
   internal evidence (cite-back specificity, test scenarios, risk treatment)
4. For each conflict, lean toward the option with more concrete grounding;
   mark genuinely ambiguous conflicts as UNRESOLVED for the user to decide
5. Merge into a unified plan

## Output Format

Begin the output file with this exact line (so /athanor:work detects the skipped review):
<!-- athanor:review-skipped -->

# Final Plan: {title}

## Merged Elements (both plans agreed)
- {element}: {why it's high-confidence}

## Resolved Conflicts (deep tier — no external reviews to lean on)
- {conflict}: chose {approach} because {reasoning grounded in plan content alone}

## UNRESOLVED — User Decision Required
### Conflict 1: {description}
- **Option A** (from Plan A): {approach}
- **Option B** (from Plan B): {approach}
- **Critic's lean** (no external review evidence): {note that this is plan-only}

## Unified Implementation Plan
{... same shape as 4-input variant ...}

## v0.8.0 Critic Rubric — Spec-then-TDD Readiness (REQUIRED)

Apply the same three-axis Spec-then-TDD readiness rubric as the 4-input
variant: (A) acceptance_criteria coverage — every behavior-bearing phase's
Verify field must be MUST/SHOULD observable assertions; reformulate prose
Verify fields where needed. (B) classification appropriateness — predict
each phase's likely execution_note value and flag over-/under-classification.
(C) R-ID traceback coverage (v0.9.0; gated on requirements.md presence) —
when `.athanor/sessions/{id}/requirements.md` exists, verify each phase's
MUST/SHOULD Verify bullets cite-back the origin R-IDs / A-IDs / F-IDs /
AE-IDs. Skip axis (C) when requirements.md is absent (backwards compat).
Full rubric text in `skills/plan/references/critic-rubric.md` (also
referenced from `skills/plan/SKILL.md` §\"v0.8.0 Critic Rubric —
Spec-then-TDD Readiness\").

Save to: .athanor/sessions/{session-id}/plan.md (with the header comment as line 1)

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary, note review-skipped tier}
END_RESULT"
})
```

#### Lite Tier: Skip

When `tier == lite`: Steps 3 and 4 are skipped. plan-a.md was copied to plan.md in Step 2.

#### Standard Tier: 2-Input Refinement Critic

When `tier == standard`:

```
Agent({
  description: "Athanor critic: plan refinement",
  model: "opus",
  prompt: "ultrathink

You are the Athanor Critic in Plan Refinement mode.

## Task
Improve this implementation plan by incorporating review feedback.

Read these 2 files from .athanor/sessions/{session-id}/:
1. plan-a.md (the original plan)
2. review-of-a.md (critical review of the plan)

Conditional v0.9.0 input — also read if present:
3. requirements.md (clarify-mode origin requirements doc with R-IDs /
   A-IDs / F-IDs / AE-IDs). When present, axis (C) R-ID traceback
   coverage fires — verify each phase's MUST/SHOULD Verify bullets in
   plan-a.md cite-back the origin IDs.

## Process
1. Read both documents
2. For each piece of feedback in the review:
   - If valid and actionable → incorporate into the plan
   - If disagree → explain why you're not incorporating it
3. Produce an improved plan that addresses the review's concerns

## Output Format

# Final Plan: {title}

## Changes from Review
- {feedback point}: {how addressed OR why not}

## Improved Implementation Plan
{the full plan with improvements incorporated}

## Rules
- Incorporate ALL valid feedback — don't ignore any
- If you disagree with feedback, state why explicitly
- Maintain the original plan's structure and specificity
- This is refinement, not synthesis — one plan in, one plan out

## v0.8.0 Critic Rubric — Spec-then-TDD Readiness (REQUIRED)

In addition to the rules above, apply the three-axis Spec-then-TDD readiness
rubric to the refined plan: (A) acceptance_criteria coverage — every
behavior-bearing phase's Verify field must be MUST/SHOULD observable
assertions; reformulate prose Verify fields where needed. (B) classification
appropriateness — predict each phase's likely execution_note value and flag
over-classification (CHANGELOG-only / _doc-only phase with MUST/SHOULD)
and under-classification (source code with prose-only Verify). (C) R-ID
traceback coverage (v0.9.0; gated on requirements.md presence) — when
`.athanor/sessions/{id}/requirements.md` exists, verify each phase's
MUST/SHOULD Verify bullets cite-back the origin R-IDs / A-IDs / F-IDs /
AE-IDs. Skip axis (C) when requirements.md is absent (backwards compat).
Full rubric text in `skills/plan/references/critic-rubric.md` (also
referenced from `skills/plan/SKILL.md` §\"v0.8.0 Critic Rubric —
Spec-then-TDD Readiness\"). This rubric applies whether the upstream review
came from Codex or from Claude self-review (claude-self-review fallback).

Save to: .athanor/sessions/{session-id}/plan.md

Return:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary}
END_RESULT"
})
```

#### End of Refinement variants

(Marker heading — the prose-level regression parsers anchor on `#### ...`
section transitions whose heading text contains the section-key word; this
marker resets `section_active` after the Standard Tier Refinement block
so adjacent companion files [`planner-dispatch.md`,
`reviewer-dispatch.md`] don't bleed into the variant scan.)
