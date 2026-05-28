# Planner Dispatch Packets (Step 2 Detail)

This reference holds the full Planner A + Planner B prompt bodies. The
SKILL.md router carries the per-tier orchestration (which planner to
dispatch) and points here for the actual prompt text.

Dispatch matrix recap (full text in SKILL.md):

- **Deep tier:** Planner A (Claude) + Planner B (Codex if available, Claude
  contrarian fallback otherwise) in parallel.
- **Standard tier:** Planner A (Claude) only.
- **Lite tier:** Planner A (Claude) only — `plan-a.md` copied directly to
  `plan.md`; Steps 3 and 4 skipped.

## Dispatch Gate Checkpoint (mandatory)

Before dispatching planners, the Leader MUST announce its dispatch decision:

```
Planner B dispatch: {codex|claude-fallback|none}
  Reason: codex_available={true|false}, review_strategy={codex|claude-self-review|none}, tier={deep|standard|lite}
```

This checkpoint makes the branch decision visible in the transcript.

> Planner B selection still branches on `codex_available` alone (Codex CLI
> present → Codex contrarian; CLI absent → Claude contrarian fallback).
> `review_strategy` is logged here for traceability and consumed by Step 3 /
> Step 4 reviewer dispatch.

## Planner A — Standard Planner

```
Agent({
  description: "Athanor planner A: standard approach",
  model: "opus",
  prompt: "ultrathink

You are Athanor Planner A — the Standard Planner.

## Task
Create an implementation plan for:
{user's planning request}

## Context from Previous Stages

Read these files from `.athanor/sessions/{session-id}/` in order (each
optional — if absent, note it as 'not present this session'). Order
matters per `/athanor:plan` Step 1 v0.9.0 ordering rule:

1. `analyze.md` (code-grounded analysis, if `/athanor:analyze` ran)
2. `requirements.md` (NEW v0.9.0 — clarify-mode origin requirements doc
   with R-IDs / A-IDs / F-IDs / AE-IDs, if `/athanor:discuss` ran in
   clarify mode)
3. `discuss.md` (synthesis-mode discussion output, if `/athanor:discuss`
   ran in synthesis mode)

When `requirements.md` is present, your phase `Verify:` MUST/SHOULD
bullets MUST cite-back the relevant origin R-IDs / A-IDs / F-IDs /
AE-IDs in your plan output (Critic Rubric axis (C) will check this).
Example acceptable cite-back: `MUST exit 2 when material claim detected
(covers R3, AE1)`.

### Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: plan.
Read any relevant lessons and apply them to your approach.
**Report which lesson files you read** in your ATHANOR_RESULT under a `lessons_read:` field.
Example: lessons_read: [plan-2026-04-01-001.md, plan-2026-04-05-002.md]

## Plan Structure
Write a structured implementation plan:

# Plan A: {title}

## Goal
{what we're trying to achieve and why}

## Approach
{high-level strategy — the most natural, straightforward approach}

## Phases

### Phase 1: {name}
- Step 1.1: {action} → files: {paths}
- Step 1.2: {action} → files: {paths}
- Verify (MUST/SHOULD for behavior-bearing phases; prose for non-behavior):
  - MUST <observable assertion — exit code, file state, schema validation, ...>
  - MUST <observable assertion>
  - SHOULD <quality / performance / non-blocking assertion>

### Phase 2: {name}
...

## Risks
- {risk}: {mitigation}

## Estimated Scope
- Files to modify: {count}
- New files: {count}
- Complexity: {low/medium/high}

## Rules
- Be specific: name actual files, functions, line ranges
- Use Grep/Glob to verify file existence before referencing
- Each step should be independently verifiable
- Include verification criteria per phase

## Verify field format guidance (v0.8.0+)
- **Behavior-bearing phase** (source code modification introducing or changing
  observable behavior: .py / .js / .ts / .rb / .go / etc. that produces a new
  contract): write the `Verify:` field as MUST/SHOULD bullets where each MUST
  describes an observable assertion (exit code, file content, schema validation
  outcome, test count, error reference). At least one MUST bullet per phase.
- **Non-behavior phase** (doc-only edits, CHANGELOG bumps, version-string
  changes, `_doc` inline-schema rewrites, prose-only refactors): a free-form
  prose `Verify:` field is acceptable; MUST/SHOULD format is not required.
- The MUST/SHOULD format feeds the v0.8.0 Spec-then-TDD discipline downstream:
  the `/athanor:work` Task Splitter copies these bullets into per-subtask
  `acceptance_criteria` fields, and the Executor uses them as red-first
  criteria. Writing free-form prose Verify in a behavior-bearing phase
  silently degrades the spec-then-tdd discipline (the Splitter cannot extract
  acceptance criteria from prose).
- This guidance is **advisory** — there is no runtime hook enforcing MUST/SHOULD
  format. The Critic at Step 4 will flag misclassifications during refinement.

Save your plan to: .athanor/sessions/{session-id}/plan-a.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of plan approach}
lessons_read: [{list of lesson filenames you read, or empty}]
END_RESULT"
})
```

## Planner B — Contrarian Planner

> Planner B dispatch depends on tier and Codex availability. See conditionals below.

### Deep Tier: Planner B (Codex)

> When `tier == deep AND codex_available == true`: dispatch Planner B via Codex CLI.

> **COLLISION GUARD**: Do NOT dispatch Planner B as a registered Claude plugin agent when `codex_available == true`. The Codex path MUST use the Bash tool to run `codex exec` — it is a sonnet-model wrapper, not a direct planner. If you see `athanor:athanor-planner` in the dispatch log or the worker uses tools like Grep/Read instead of a single Bash call, the dispatch has been intercepted by a registered agent — this is the WRONG behavior. Re-dispatch using the exact Agent() call below.

```
Agent({
  description: "Athanor planner B: Codex contrarian via Bash",
  model: "sonnet",
  prompt: "You are an Athanor worker that dispatches a planning task to Codex CLI.

## Task
Call Codex to create an alternative implementation plan.

## Codex Invocation
Per `codex --help` (CLI 0.133.0+): `-a/--ask-for-approval` and `-s/--sandbox`
are TOP-LEVEL options preceding the `exec` subcommand. `never` is the
documented noninteractive approval policy. `--full-auto` is deprecated (removed in 0.133.0).

Run this command via the Bash tool. The Worker bash block computes
`CODEX_TIMEOUT_S` inline from `athanor.json` with clamping (1-600s,
default 300). The shell-level `timeout ${CODEX_TIMEOUT_S}s` prefix is the
hard wall-clock fence. Additionally pass `timeout: ${CODEX_TIMEOUT_MS}` as
a Bash tool parameter (belt-and-suspenders). If Bash returns non-zero or
`timeout` exits with 124, report failure (do NOT retry inside the worker —
leader handles codex.fallback enum).
<!-- stdin redirected to prevent readFileSync(0) hang (GitHub codex#20919) -->
```bash
CODEX_TIMEOUT_S=$(jq -r '(.codex.timeoutMs // 300000) / 1000 | floor | if . < 1 then 300 elif . > 600 then 600 else . end' athanor.json 2>/dev/null || echo 300) && \
timeout ${CODEX_TIMEOUT_S}s codex -a never -s workspace-write exec --ephemeral -o .athanor/sessions/{session-id}/plan-b.md \"Create an ALTERNATIVE implementation plan for:

{user's planning request}

Context: {previous stage context from .athanor/sessions/{session-id}/ — read in order: analyze.md (code-grounded), requirements.md (NEW v0.9.0 — clarify-mode origin requirements with R/A/F/AE-IDs, if present), discuss.md (synthesis-mode output, if present). When requirements.md is present, your phase Verify MUST/SHOULD bullets MUST cite-back origin R-IDs / A-IDs / F-IDs / AE-IDs (Critic Rubric axis (C)).}

Requirements:
- Find a fundamentally different approach than the obvious one
- Be specific: name actual files, functions
- Include verification criteria per phase
- Output as structured markdown

Format your plan as:
# Plan B: [title] — Alternative Approach
## Goal
## Approach (explain WHY this alternative)
## Phases (with Steps, files, verify)
## Risks
## Why This Alternative?
## Estimated Scope\" < /dev/null
```

> **v0.14.0:** The `athanor-codex-dispatcher` agent (`agents/codex-dispatcher.md`)
> encapsulates the codex invocation pattern above — timeout computation, stdin
> redirect, and flag management. Skills dispatching Codex MAY use the agent
> directly instead of inline bash. The inline form is preserved here as the
> canonical reference implementation.

## After Codex Returns
1. Check exit code and verify output file exists
2. If Codex fails or times out, report failure
3. If shell `timeout` exits with code 124, or Bash tool returns
   timeout, report status: timeout and let the leader route via
   codex.fallback enum.

Return:
ATHANOR_RESULT
status: {success|failure}
summary: Codex planning complete
END_RESULT"
})
```

### Deep Tier Fallback: Planner B (Claude Contrarian) — ONLY IF codex_available == false

> When `tier == deep AND codex_available == false`: use this Claude-based contrarian planner as fallback.

> **FALLBACK ONLY**: This Claude-based contrarian dispatch is the fallback path. Use it ONLY when `codex --version` check failed at Step 0. If Codex is available, you MUST use the Codex path above instead.

```
Agent({
  description: "Athanor planner B: contrarian approach",
  model: "opus",
  prompt: "ultrathink

You are Athanor Planner B — the Contrarian Planner.

## Task
Create an ALTERNATIVE implementation plan for:
{user's planning request}

## Context from Previous Stages
{same context as Planner A}

### Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: plan.
Read any relevant lessons and apply them to your approach.
**Report which lesson files you read** in your ATHANOR_RESULT under a `lessons_read:` field.
Example: lessons_read: [plan-2026-04-01-001.md, plan-2026-04-05-002.md]

## Your Role
You MUST find a fundamentally different approach than the obvious one.
- If the obvious approach is top-down, go bottom-up
- If the obvious approach modifies existing code, consider creating new modules
- If the obvious approach is incremental, consider a larger refactor
- Challenge assumptions about the 'right' way to do this

## Plan Structure
Same format as standard plan:

# Plan B: {title} — Alternative Approach

## Goal
{same goal, different path}

## Approach
{fundamentally different strategy — explain WHY this alternative}

## Phases
...

## Risks
...

## Why This Alternative?
{explicit reasoning for why this approach deserves consideration}

## Estimated Scope
...

## Rules
- Be genuinely different, not just reordered
- Explain WHY your approach might be better
- Be realistic — this is a serious alternative, not a strawman

Save your plan to: .athanor/sessions/{session-id}/plan-b.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of alternative approach}
lessons_read: [{list of lesson filenames you read, or empty}]
END_RESULT"
})
```

### Standard Tier: Planner A Only

When `tier == standard`:
- Dispatch ONLY Planner A (Claude) — use the existing Planner A prompt above
- Save to `plan-a.md`
- Skip Planner B entirely

### Lite Tier: Planner A Only (No Review)

When `tier == lite`:
- Dispatch ONLY Planner A (Claude) — same prompt as above
- Save to `plan-a.md`
- Skip Steps 3 and 4 entirely
- Copy `plan-a.md` content to `plan.md` (Leader runs: `cp .athanor/sessions/{id}/plan-a.md .athanor/sessions/{id}/plan.md` via Bash)
- Proceed directly to Step 5 (Present to User)

<!--
  review_strategy contract (set in Step 0):
    - codex              → dispatch Codex reviewer(s) (original behavior)
    - claude-self-review → dispatch Claude reviewer(s) (no cross-model)
    - none               → skip Step 3 entirely AND make Step 4 a pass-through
                           (standard tier emits plan-a.md content as plan.md with
                            a `<!-- athanor:review-skipped -->` HTML header comment
                            prepended so downstream /athanor:work can detect it)
  Tier × review_strategy together determine reviewer count and direction.
-->
