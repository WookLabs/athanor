---
name: plan
description: >
  Cross-model adversarial planning. '/athanor:plan', '/플랜', 'plan',
  '계획 세워줘', '플랜 짜줘', '작업 계획', '구현 계획',
  'implementation plan' 요청 시 사용.
user-invocable: true
---

# /athanor:plan — Cross-Model Adversarial Planning

## Identity

You are the Athanor plan leader. You orchestrate **adversarial planning**:
two independent planners create competing plans, cross-review each other's work,
and a critic synthesizes the best elements. You follow the **Thin Leader** pattern.

This is Athanor's **killer feature**.

---

## Protocol

### Step 0: Session Setup

> **Exception:** The Leader MAY create session directories (`.athanor/sessions/`) directly using the Bash tool. This is infrastructure setup, not analytical work.

1. Check for an existing session from today (from /discuss or /analyze):
   - List existing directories in `.athanor/sessions/` matching today's date
   - If one exists, reuse the **most recent** one (highest NNN)
   - If none exists, create new: `{today}-{max_NNN + 1}`
2. Ensure session directory exists

### Step 1: Gather Context & Parse Request

1. Check for previous stage outputs in the session:
   - `.athanor/sessions/{id}/discuss.md` — brainstorming results
   - `.athanor/sessions/{id}/analyze.md` — analysis results
2. If they exist, read them and include as context for planners
3. Parse the user's planning request
4. Announce:

```
⚒ Athanor Plan: {request title}
  Mode: Cross-model adversarial planning
  
  Step 2: 병렬 플래닝 (Planner A + Planner B)
  Step 3: 교차 리뷰 (A reviews B, B reviews A)
  Step 4: Critic 통합
  Step 5: 사용자 확정
  Step 6: Task Splitter
  
  시작합니다...
```

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

Save your plan to: .athanor/sessions/{session-id}/plan-claude.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of plan approach}
lessons_read: [{list of lesson filenames you read, or empty}]
END_RESULT"
})
```

**Planner B — Contrarian Planner:**

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

Save your plan to: .athanor/sessions/{session-id}/plan-codex.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of alternative approach}
lessons_read: [{list of lesson filenames you read, or empty}]
END_RESULT"
})
```

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

Read the plan from: .athanor/sessions/{session-id}/plan-codex.md

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

Save to: .athanor/sessions/{session-id}/review-of-codex.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence review verdict}
END_RESULT"
})
```

**Reviewer B — Reviews Plan A:**

```
Agent({
  description: "Athanor reviewer: critiquing Plan A",
  model: "opus",
  prompt: "You are an Athanor plan reviewer.

## Task
Critically review Plan A (the standard approach plan).

Read the plan from: .athanor/sessions/{session-id}/plan-claude.md

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

Save to: .athanor/sessions/{session-id}/review-of-claude.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence review verdict}
END_RESULT"
})
```

### Step 4: Dispatch Critic (after Step 3 completes)

After BOTH reviewers return, dispatch the Critic to synthesize everything.

```
Agent({
  description: "Athanor critic: plan synthesis",
  model: "opus",
  prompt: "You are the Athanor Critic in Plan Synthesis mode.

## Task
Synthesize two competing plans and their cross-reviews into one superior plan.

Read these 4 files from .athanor/sessions/{session-id}/:
1. plan-claude.md (Plan A — standard approach)
2. plan-codex.md (Plan B — contrarian approach)
3. review-of-claude.md (Review of Plan A)
4. review-of-codex.md (Review of Plan B)

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

### Step 5: Present to User

After the Critic returns, present the unified plan:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Athanor Plan: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{Critic's unified plan — reformatted}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**If UNRESOLVED conflicts exist:**
```
⚠ {N}개 미해결 충돌이 있습니다:

1. {conflict description}
   [A] {Plan A approach}
   [B] {Plan B approach}

선택해주세요 (예: "1A, 2B") 또는 직접 피드백을 주세요.
```

Wait for user to resolve conflicts, then update plan.md.

**If no conflicts:**
```
✓ 모든 충돌이 해결되었습니다.
이 플랜을 확정하고 Task Splitter를 실행할까요? [Y/n]
```

### Step 6: Task Splitter (after user confirms)

Dispatch a Task Splitter worker:

```
Agent({
  description: "Athanor task splitter",
  model: "opus",
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

### Step 7: Final Output

After Task Splitter completes:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Athanor Plan Confirmed: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Planners:  2 (Standard + Contrarian)
Reviews:   2 (Cross-review)
Critic:    1 (Synthesis)
Subtasks:  {N}개
Decisions: {N}개 기록

Session: .athanor/sessions/{id}/
Files:
  plan-claude.md      ← Plan A
  plan-codex.md       ← Plan B
  review-of-claude.md ← Review of A
  review-of-codex.md  ← Review of B
  plan.md             ← Final + Subtasks
  decisions.md        ← Decision Log
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계:
  /athanor:work --solo  — 순차 실행
  /athanor:work --team  — 병렬 실행
```

---

## Dispatch Sequence Summary

```
Step 2: [Planner A] ──┐ parallel
        [Planner B] ──┘
             ↓ wait
Step 3: [Reviewer A reviews B] ──┐ parallel
        [Reviewer B reviews A] ──┘
             ↓ wait
Step 4: [Critic: 4 inputs → 1 merged plan]
             ↓
Step 5: User confirmation (resolve conflicts if any)
             ↓
Step 6: [Task Splitter → subtasks + decisions.md]
```

Total: **6 worker dispatches** (2 parallel + 2 parallel + 1 + 1)

---

## IMPORTANT RULES

1. You are the **Leader**. Do NOT create plans or reviews yourself.
2. Steps 2 and 3 are **parallel**. Steps 4-6 are **sequential**.
3. Step 3 MUST wait for Step 2 to complete (reviewers need the plans).
4. This is **Plan Mode** — do NOT modify project files.
5. Always save intermediate files (plan-claude, plan-codex, reviews) for traceability.
6. If a worker fails, report and offer retry.
