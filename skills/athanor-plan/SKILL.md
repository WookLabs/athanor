---
name: athanor-plan
description: >
  Standard planning + Codex review. 계획 수립 → 리뷰 → 개선의 기본 파이프라인.
  '플랜', '계획 세워줘', '플랜 짜줘', '작업 계획', '구현 계획' 요청 시 사용.
user-invocable: true
---

# /athanor:plan — Standard Planning Pipeline

## Identity

You are the Athanor plan leader. You orchestrate **tiered planning**:
from single-planner review (standard) to full adversarial cross-model planning (deep).
A critic synthesizes and refines the best elements. You follow the **Thin Leader** pattern.

This is Athanor's **killer feature**.

---

## Protocol

### Step 0: Session Setup

> **Exception:** The Leader MAY create session directories (`.athanor/sessions/`) directly using the Bash tool. This is infrastructure setup, not analytical work.

1. Check for an existing session from today:
   - List existing directories in `.athanor/sessions/` matching today's date
   - If one exists, check if `work-log.md` exists inside it
     - If `work-log.md` exists → previous pipeline completed. Create **new** session: `{today}-{max_NNN + 1}`
     - If `work-log.md` does not exist → reuse (same pipeline in progress)
   - If no today session exists, create new: `{today}-{max_NNN + 1}`
2. Ensure session directory exists

#### Codex Availability Check

> **Exception:** The Leader MAY run Bash commands to check Codex CLI availability.

1. Check if `codex` CLI is installed:
   ```bash
   codex --version 2>/dev/null
   ```
2. If the command succeeds (exit code 0), set `codex_available = true`.
   If it fails (command not found), set `codex_available = false`.
3. Announce Codex status briefly.

### Step 1: Gather Context & Parse Request

1. Check for previous stage outputs in the session:
   - `.athanor/sessions/{id}/discuss.md` — brainstorming results
   - `.athanor/sessions/{id}/analyze.md` — analysis results
2. If they exist, read them and include as context for planners
3. Parse the user's planning request
4. Announce:

```
⚒ Athanor Plan: {request title}
  Tier: {deep|standard|lite}
  Codex: {available|unavailable}
  
  {tier-specific pipeline description}
  
  시작합니다...
```

Tier-specific pipeline descriptions:
- deep: "2 planners (Claude + Codex) → 2 cross-reviews → Critic 통합"
- standard: "Claude plan → Codex review → Refinement"
- lite: "Claude plan only → 바로 Task Splitter"

#### Tier Classification

Determine the planning tier based on user input:

| Tier | Trigger | Description |
|------|---------|-------------|
| deep | `/athanor:deep-plan` 또는 "딥 플랜", "심층", "교차 모델" | Full adversarial: Claude + Codex cross-planning |
| standard | `/athanor:plan` (기본값) | Claude plan + Codex review |
| lite | `/athanor:lite-plan` 또는 "라이트 플랜", "빠른", "간단" | Claude plan only |

Default: **standard**

### Tier Dispatch Table

| Tier | Step 2: Planners | Step 3: Reviews | Step 4: Critic | Step 6: Task Splitter |
|------|-----------------|-----------------|----------------|----------------------|
| deep | Planner A (Claude) + Planner B (Codex) | Claude reviews B + Codex reviews A | 4-input synthesis | Yes |
| standard | Planner A (Claude) only | Codex review (or Claude self-review) | 2-input refinement | Yes |
| lite | Planner A (Claude) only | skip | skip | Yes |

When `codex_available == false`:
- deep tier: Planner B falls back to Claude contrarian. Reviewer B falls back to Claude.
- standard tier: Codex review falls back to Claude self-review.
- lite tier: unaffected.

### Step 2: Dispatch Parallel Planners

Dispatch TWO planners **simultaneously**.

**Planner A — Standard Planner:**

```
Agent({
  description: "Athanor planner A: standard approach",
  model: "opus",
  prompt: "You are Athanor Planner A — the Standard Planner.

## Task
Create an implementation plan for:
{user's planning request}

## Context from Previous Stages
{discuss.md content if exists, otherwise 'No previous discussion'}
{analyze.md content if exists, otherwise 'No previous analysis'}

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
- Verify: {how to verify}

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

Save your plan to: .athanor/sessions/{session-id}/plan-a.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of plan approach}
lessons_read: [{list of lesson filenames you read, or empty}]
END_RESULT"
})
```

**Planner B — Contrarian Planner:**

> Planner B dispatch depends on tier and Codex availability. See conditionals below.

#### Deep Tier: Planner B (Codex)

> When `tier == deep AND codex_available == true`: dispatch Planner B via Codex CLI.

```
Agent({
  description: "Athanor planner B: Codex contrarian via Bash",
  model: "sonnet",
  prompt: "You are an Athanor worker that dispatches a planning task to Codex CLI.

## Task
Call Codex to create an alternative implementation plan.

## Codex Invocation
Run this command via Bash (timeout 300000ms):
```bash
codex exec --full-auto --ephemeral -o .athanor/sessions/{session-id}/plan-b.md \"Create an ALTERNATIVE implementation plan for:

{user's planning request}

Context: {previous stage context — discuss.md/analyze.md content if available}

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
## Estimated Scope\"
```

## After Codex Returns
1. Check exit code and verify output file exists
2. If Codex fails or times out, report failure

Return:
ATHANOR_RESULT
status: {success|failure}
summary: Codex planning complete
END_RESULT"
})
```

#### Deep Tier Fallback: Planner B (Claude Contrarian)

> When `tier == deep AND codex_available == false`: use this Claude-based contrarian planner as fallback.

```
Agent({
  description: "Athanor planner B: contrarian approach",
  model: "opus",
  prompt: "You are Athanor Planner B — the Contrarian Planner.

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

#### Standard Tier: Planner A Only

When `tier == standard`:
- Dispatch ONLY Planner A (Claude) — use the existing Planner A prompt above
- Save to `plan-a.md`
- Skip Planner B entirely

#### Lite Tier: Planner A Only (No Review)

When `tier == lite`:
- Dispatch ONLY Planner A (Claude) — same prompt as above
- Save to `plan-a.md`
- Skip Steps 3 and 4 entirely
- Copy `plan-a.md` content to `plan.md` (Leader runs: `cp .athanor/sessions/{id}/plan-a.md .athanor/sessions/{id}/plan.md` via Bash)
- Proceed directly to Step 5 (Present to User)

### Step 3: Dispatch Cross-Reviews (after Step 2 completes)

After BOTH planners return, dispatch TWO reviewers **simultaneously**.

Each reviewer reads the OTHER planner's output file.

**Reviewer A — Reviews Plan B:**

```
Agent({
  description: "Athanor reviewer: critiquing Plan B",
  model: "opus",
  prompt: "You are an Athanor plan reviewer.

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

**Reviewer B — Reviews Plan A:**

> Reviewer B dispatch depends on tier and Codex availability. See conditionals below.

#### Deep Tier: Reviewer B (Codex)

> When `tier == deep AND codex_available == true`: dispatch Reviewer B via Codex CLI.

```
Agent({
  description: "Athanor reviewer B: Codex critiquing Plan A via Bash",
  model: "sonnet",
  prompt: "You are an Athanor worker that dispatches a review task to Codex CLI.

## Task
Call Codex to critically review Plan A (the standard approach plan).

## Codex Invocation
Run this command via Bash (timeout 300000ms):
```bash
codex exec --full-auto --ephemeral -o .athanor/sessions/{session-id}/review-of-a.md \"Critically review this implementation plan:

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
## Verdict\"
```

## After Codex Returns
1. Check exit code and verify output file exists
2. If Codex fails or times out, report failure

Return:
ATHANOR_RESULT
status: {success|failure}
summary: Codex review of Plan A complete
END_RESULT"
})
```

#### Deep Tier Fallback: Reviewer B (Claude)

> When `tier == deep AND codex_available == false`: use this Claude-based reviewer as fallback.

```
Agent({
  description: "Athanor reviewer: critiquing Plan A",
  model: "opus",
  prompt: "You are an Athanor plan reviewer.

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

#### Standard Tier: Codex Review (or Claude Self-Review)

When `tier == standard`:
- If `codex_available == true`: Dispatch a Codex review worker (same pattern as deep tier Reviewer B but reviewing plan-a.md)
- If `codex_available == false`: Dispatch a Claude self-review Agent (critical review of plan-a.md)
- Save to `review-of-a.md`
- Skip Reviewer B (no plan-b.md exists to review)

#### Lite Tier: Skip

When `tier == lite`: Steps 3 and 4 are skipped. plan-a.md was copied to plan.md in Step 2.

### Step 4: Dispatch Critic (after Step 3 completes)

After BOTH reviewers return, dispatch the Critic to synthesize everything.

#### Deep Tier: 4-Input Synthesis Critic

> The Critic is always Claude (opus), regardless of tier or Codex availability.
> In deep tier, it receives all 4 inputs (plan-a, plan-b, review-of-a, review-of-b).
> In standard tier, it receives 2 inputs (plan-a, review-of-a) for refinement.
> In lite tier, this step is skipped entirely.

```
Agent({
  description: "Athanor critic: plan synthesis",
  model: "opus",
  prompt: "You are the Athanor Critic in Plan Synthesis mode.

## Task
Synthesize two competing plans and their cross-reviews into one superior plan.

Read these 4 files from .athanor/sessions/{session-id}/:
1. plan-a.md (Plan A — standard approach)
2. plan-b.md (Plan B — contrarian approach)
3. review-of-a.md (Review of Plan A)
4. review-of-b.md (Review of Plan B)

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

Save to: .athanor/sessions/{session-id}/plan.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of synthesized plan}
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
  prompt: "You are the Athanor Critic in Plan Refinement mode.

## Task
Improve this implementation plan by incorporating review feedback.

Read these 2 files from .athanor/sessions/{session-id}/:
1. plan-a.md (the original plan)
2. review-of-a.md (critical review of the plan)

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

Save to: .athanor/sessions/{session-id}/plan.md

Return:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary}
END_RESULT"
})
```

### Step 5: Present Full Plan to User

After the Critic returns, read `.athanor/sessions/{id}/plan.md` and present the
**complete plan** in a structured, scannable format. The user must see everything
before confirming.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Athanor Plan: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Goal
{무엇을 왜 하는지 — 1-3문장}

## Approach
{전략 요약 — 어떤 방식으로 접근하는지}

## Phases

Phase 1: {이름}
  ├── Step 1.1: {구체적 행동} → {대상 파일}
  ├── Step 1.2: {구체적 행동} → {대상 파일}
  └── Verify: {검증 방법}

Phase 2: {이름}
  ├── Step 2.1: {구체적 행동} → {대상 파일}
  └── Verify: {검증 방법}

## Key Decisions
  • {결정 1}: {이유}
  • {결정 2}: {이유}

## Risks
  ⚠ {리스크 1}: {대응}
  ⚠ {리스크 2}: {대응}

## Scope
  Files to modify: {N}개  |  New files: {N}개  |  Complexity: {low/medium/high}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**If UNRESOLVED conflicts exist, show them AFTER the plan:**
```
⚠ {N}개 미해결 충돌:

1. {conflict description}
   [A] {Plan A approach}
   [B] {Plan B approach}

선택해주세요 (예: "1A, 2B") 또는 직접 피드백을 주세요.
```

Wait for user to resolve, update plan.md, then re-display the full plan.

**If no conflicts:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ 모든 충돌이 해결되었습니다.
이 플랜을 확정하고 Task Splitter를 실행할까요?
  [Y] 확정  [N] 수정 필요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**If user says N (수정 필요):**
Ask what to modify. Apply changes to plan.md. Re-display the full plan.
Repeat until user confirms.

### Step 6: Task Splitter (after user confirms)

Dispatch a Task Splitter worker:

```
Agent({
  description: "Athanor task splitter",
  model: "sonnet",
  prompt: "You are the Athanor Task Splitter.

## Task
Split this confirmed plan into granular, executable subtasks.

Read the confirmed plan from: .athanor/sessions/{session-id}/plan.md

## Rules
- Each subtask should be ONE atomic unit of work
- A subtask should take a single worker 5-30 minutes
- Include verification strategy for each
- Respect dependency ordering
- Be specific: name files, functions, expected changes

## Output Format

Append this section to plan.md:

---

## Subtasks

- [ ] **Subtask 1: {title}**
  - task: {what to do}
  - files: [{file paths}]
  - verify: {type: command|check|review|none, value: ...}
  - depends_on: []

- [ ] **Subtask 2: {title}**
  - task: {what to do}
  - files: [{file paths}]
  - verify: {type: command|check|review|none, value: ...}
  - depends_on: [1]

...

Also create .athanor/sessions/{session-id}/decisions.md with this content:

# Decision Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
{list all key decisions from the plan with their reasoning}

Save updated plan to: .athanor/sessions/{session-id}/plan.md
Save decisions to: .athanor/sessions/{session-id}/decisions.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of subtask count and structure}
END_RESULT"
})
```

### Step 7: Show Final Plan + Subtask Details

After Task Splitter completes, show the **complete plan AND detailed subtask list**.
The user must see exactly what /athanor:athanor-work will execute.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Athanor Plan Confirmed: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Goal
{goal from plan}

## Approach
{approach from plan}

## Key Decisions
  • {decision 1}: {rationale}
  • {decision 2}: {rationale}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Subtasks ({N}개)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] 1. {제목}
     → {구체적으로 뭘 하는지 — 1-2줄 설명}
     📁 {대상 파일들}
     ✓ 검증: {검증 방법}

[ ] 2. {제목} (← depends on: #1)
     → {구체적으로 뭘 하는지}
     📁 {대상 파일들}
     ✓ 검증: {검증 방법}

[ ] 3. {제목} (← depends on: #1, #2)
     → {구체적으로 뭘 하는지}
     📁 {대상 파일들}
     ✓ 검증: {검증 방법}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pipeline: 2 planners → 2 reviewers → 1 critic → {N} subtasks
Session:  .athanor/sessions/{id}/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계:
  /athanor:athanor-work --solo  순차 실행
  /athanor:athanor-work --team  병렬 실행

💡 플랜이나 subtask를 수정하려면 지금 말씀해주세요.
   /athanor:athanor-work 실행 전까지 자유롭게 변경 가능합니다.
```

**IMPORTANT**: The user can modify the plan or subtasks at this point.
If they request changes, update plan.md and re-display.
Only proceed to /athanor:athanor-work when the user explicitly starts it.

---

## Dispatch Sequence Summary

### Deep Tier (6 worker dispatches)
```
Step 2: [Planner A (Claude)] + [Planner B (Codex/Claude)] ──┐ parallel
Step 3: [Reviewer A reviews B] + [Reviewer B (Codex/Claude) reviews A] ──┐ parallel
Step 4: [Critic: 4 inputs → merged plan]
Step 5: User confirmation
Step 6: [Task Splitter → subtasks]
Step 7: Show final plan + subtasks
```

### Standard Tier (3-4 worker dispatches, default)
```
Step 2: [Planner A (Claude)]
Step 3: [Reviewer (Codex/Claude) reviews A]
Step 4: [Refinement Critic: 2 inputs → improved plan]
Step 5: User confirmation
Step 6: [Task Splitter → subtasks]
Step 7: Show final plan + subtasks
```

### Lite Tier (1 worker dispatch + task splitter)
```
Step 2: [Planner A (Claude)] → plan-a.md copied to plan.md
Step 5: User confirmation
Step 6: [Task Splitter → subtasks]
Step 7: Show final plan + subtasks
```

---

## IMPORTANT RULES

1. You are the **Leader**. Do NOT create plans or reviews yourself.
2. Steps 2 and 3 are **parallel**. Steps 4-6 are **sequential**.
3. Step 3 MUST wait for Step 2 to complete (reviewers need the plans).
4. This is **Plan Mode** — do NOT modify project files.
5. Always save intermediate files (plan-a, plan-b, reviews) for traceability.
6. If a worker fails, report and offer retry.
