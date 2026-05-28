# Reviewer Dispatch Packets (Step 3 Detail)

This reference holds the full Reviewer A + Reviewer B prompt bodies and
fallback variants. The SKILL.md router carries the per-tier orchestration
(which reviewer to dispatch, in what direction) and points here for the
actual prompt text.

Tier × `review_strategy` recap (full text in SKILL.md):

- **Deep tier:**
  - `review_strategy=codex`: TWO reviewers run in parallel — Reviewer A
    (Claude) reviews Plan B; Reviewer B (Codex) reviews Plan A.
  - `review_strategy=claude-self-review`: TWO reviewers, both Claude —
    Reviewer A reviews Plan B; Reviewer B reviews Plan A (no cross-model).
  - `review_strategy=none`: skip Step 3 entirely; both plans flow to Step 4
    Critic as-is.
- **Standard tier:**
  - `review_strategy=codex` (requires `codex_available == true`): ONE
    reviewer (Codex) reviews Plan A; output `review-of-a.md`.
  - `review_strategy=claude-self-review`: ONE reviewer (Claude self-review)
    reviews Plan A; output `review-of-a.md`.
  - `review_strategy=none`: skip Step 3.
- **Lite tier:** Step 3 skipped entirely regardless of `review_strategy`.

When two reviewers are dispatched (deep tier), they run **simultaneously**
and each reviewer reads the OTHER planner's output file.

## Reviewer A — Reviews Plan B

```
Agent({
  description: "Athanor reviewer: critiquing Plan B",
  model: "opus",
  prompt: "ultrathink

You are an Athanor plan reviewer.

## Task
Critically review Plan B (the contrarian/alternative plan).

Read the plan from: .athanor/sessions/{session-id}/plan-b.md

## Review Criteria
1. **Feasibility**: Can this actually be implemented as described?
2. **Completeness**: Are there missing steps or unconsidered scenarios?
3. **Risks**: What could go wrong that the plan doesn't address?
4. **Strengths**: What does this plan do BETTER than a standard approach?
5. **Weaknesses**: Where does this plan fall short?

## Output Format

# Review of Plan B

## Strengths
- {what this plan does well}

## Weaknesses
- {where it falls short}

## Missing Steps
- {anything the plan forgot}

## Risk Assessment
- {risks not addressed}

## Verdict
{1-2 sentences: overall assessment}

Save to: .athanor/sessions/{session-id}/review-of-b.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence review verdict}
END_RESULT"
})
```

## Reviewer Dispatch Gate Checkpoint

Before dispatching Reviewer B, the Leader MUST announce:

```
Reviewer B dispatch: {codex|claude-fallback|skipped}
  Reason: codex_available={true|false}, review_strategy={codex|claude-self-review|none}, tier={deep|standard}
```

Dispatch matrix:
- `codex_available=true AND review_strategy=codex` → Codex Reviewer B
- `review_strategy=claude-self-review` → Claude Reviewer B (fallback prompt below)
- `review_strategy=none` → skip Reviewer B entirely (do not dispatch)

## Reviewer B — Reviews Plan A

> Reviewer B dispatch depends on tier and Codex availability. See conditionals below.

### Deep Tier: Reviewer B (Codex)

> When `tier == deep AND codex_available == true`: dispatch Reviewer B via Codex CLI.

> **COLLISION GUARD**: Same rule as Planner B — do NOT let a registered plugin agent intercept this dispatch. Reviewer B Codex path MUST use Bash tool to run `codex exec`. If the worker uses Grep/Read instead of Bash, it was intercepted.

```
Agent({
  description: "Athanor reviewer B: Codex critiquing Plan A via Bash",
  model: "sonnet",
  prompt: "You are an Athanor worker that dispatches a review task to Codex CLI.

## Task
Call Codex to critically review Plan A (the standard approach plan).

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
timeout ${CODEX_TIMEOUT_S}s codex -a never -s workspace-write exec --ephemeral -o .athanor/sessions/{session-id}/review-of-a.md \"Critically review this implementation plan:

$(cat .athanor/sessions/{session-id}/plan-a.md)

Review Criteria:
1. Feasibility: Can this actually be implemented as described?
2. Completeness: Are there missing steps or unconsidered scenarios?
3. Risks: What could go wrong that the plan doesn't address?
4. Strengths: What does this plan do BETTER than an alternative approach?
5. Weaknesses: Where does this plan fall short?
6. Convention: Does it play it too safe? Could a bolder approach be better?

Output as structured markdown:
# Review of Plan A
## Strengths
## Weaknesses
## Missing Steps
## Risk Assessment
## Verdict\" < /dev/null
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
summary: Codex review of Plan A complete
END_RESULT"
})
```

### Deep Tier Fallback: Reviewer B (Claude) — ONLY IF codex_available == false

> When `tier == deep AND codex_available == false`: use this Claude-based reviewer as fallback.

```
Agent({
  description: "Athanor reviewer: critiquing Plan A",
  model: "opus",
  prompt: "ultrathink

You are an Athanor plan reviewer.

## Task
Critically review Plan A (the standard approach plan).

Read the plan from: .athanor/sessions/{session-id}/plan-a.md

## Review Criteria
1. **Feasibility**: Can this actually be implemented as described?
2. **Completeness**: Are there missing steps or unconsidered scenarios?
3. **Risks**: What could go wrong that the plan doesn't address?
4. **Strengths**: What does this plan do BETTER than an alternative approach?
5. **Weaknesses**: Where does this plan fall short?
6. **Convention**: Does it play it too safe? Could a bolder approach be better?

## Output Format

# Review of Plan A

## Strengths
- {what this plan does well}

## Weaknesses
- {where it falls short — be tough}

## Missing Steps
- {anything the plan forgot}

## Risk Assessment
- {risks not addressed}

## Verdict
{1-2 sentences: overall assessment}

Save to: .athanor/sessions/{session-id}/review-of-a.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence review verdict}
END_RESULT"
})
```

### Standard Tier: Codex Review (or Claude Self-Review, or Skip)

When `tier == standard`, branch on `review_strategy` (resolved in Step 0):
- `review_strategy == codex` (requires `codex_available == true`): Dispatch a Codex review worker (same pattern as deep tier Reviewer B but reviewing plan-a.md). Save to `review-of-a.md`.
- `review_strategy == claude-self-review`: Dispatch a Claude self-review Agent (critical review of plan-a.md). Save to `review-of-a.md`.
- `review_strategy == none`: **Skip Step 3 entirely.** Do not produce `review-of-a.md`. Step 4 Critic also becomes a trivial pass-through (see Step 4 standard-tier block).

In all three branches: skip Reviewer B (no `plan-b.md` exists in standard tier).

### Lite Tier: Skip

When `tier == lite`: Steps 3 and 4 are skipped. plan-a.md was copied to plan.md in Step 2.
