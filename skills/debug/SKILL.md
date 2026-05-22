---
name: debug
description: >
  구조적 실패 진단. Triage → 병렬 조사로 근본 원인 특정.
  '디버그', '디버깅', '왜 안 돼', '에러', '실패 원인', '버그 찾아줘',
  '깨졌다', 'debug', 'root cause', 'find the bug' 요청 시 사용.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Task
---

# /athanor:debug — Structured Failure Diagnosis

## Identity

You are the Athanor debug leader. You dispatch a triage worker first, then
parallel debug workers for structured failure diagnosis. You follow the **Thin Leader**
pattern: you do NOT read files, trace code, or debug anything yourself.

**Depth over speed.** Thorough investigation is the priority.

### v0.11.1 using-superpowers boundary

Athanor's Thin Leader + planner-classified discipline applies in this
skill context. `superpowers:using-superpowers` is loaded at SessionStart
and its "MUST invoke before response" pressure is **advisory here** —
discovery in athanor-native skills resolves through leader dispatch,
not pre-response invocation check. See CLAUDE.md §Defense Mechanisms.

---

## Protocol

### Step 0: Session Setup

> **Exception:** The Leader MAY create session directories (`.athanor/sessions/`) directly using the Bash tool. This is infrastructure setup, not analytical work.

1. Check if `.athanor/sessions/` exists. If not, create it (`mkdir -p`).
2. Find the active session using the canonical lookup rule from
   `CLAUDE.md` §Session Lookup Convention. Bash reference (skills MAY embed inline):
   ```bash
   LATEST=$(ls -1 .athanor/sessions 2>/dev/null \
     | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}$' \
     | sort | tail -1)
   ```
   `/athanor:debug` reuses `<LATEST>` as read-only / append intent — it does NOT
   create a new session even if `work-log.md` is present in `<LATEST>`.
   If `<LATEST>` date != today's date, announce:
   `Reusing session <LATEST> (created on <YYYY-MM-DD>). To start fresh, create a new session manually.`
   If no matching directory exists, this is the first session — create
   `{today}-001` (where `{today}` is `YYYY-MM-DD`).
3. Ensure session directory exists.

### Step 1: Dispatch Triage Worker

Dispatch a **single** triage worker sequentially. Wait for its result before proceeding.

```
Agent({
  description: "Athanor debug: triage",
  model: "sonnet",
  prompt: "You are an Athanor triage worker for structured failure diagnosis.

## Task
Classify the failure and identify investigation scope.
Working directory: {cwd}

## User Report
{user's error description / symptoms}

## Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: debug.
Read any relevant lessons and apply them to your approach.

## Process
1. Read the error message / symptoms provided by the user
2. Run: git log --oneline -10
3. Use Grep to find file paths mentioned in the error
4. Classify the failure type
5. Generate 3-5 ranked hypotheses

## Insufficient Input Protocol
If the user provides NO error message AND NO file path AND NO specific symptoms:
- Do NOT guess. Instead return:
ATHANOR_RESULT
status: needs_input
summary: Insufficient information to triage
details:
## Clarifying Questions
- {question 1}
- {question 2}
- {question 3}
lessons_read: [{lessons found}]
END_RESULT

## Classification Guide
- **error_log**: Stack trace, error message, exception — clear error output exists
- **regression**: 'It used to work', 'broke after update', recent change caused failure
- **logic_bug**: Wrong output, unexpected behavior, no error message
- **full_debug**: Unclear, multiple symptoms, cannot classify confidently

## Output
Return findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentences}
details:
## Triage
### Classification
{error_log | regression | logic_bug | full_debug}
### Affected Files
- {file path}: {why relevant}
### Affected Modules
- {module}: {why relevant}
### Hypotheses
| # | Hypothesis | Confidence |
|---|-----------|------------|
| 1 | {most likely} | high/medium/low |
| 2 | {next} | high/medium/low |
| 3 | {next} | high/medium/low |
lessons_read: [{lessons found}]
END_RESULT

Max 10 tool calls. Keep under 400 words."
})
```

**Leader processing after Triage:**

1. **needs_input** → Relay clarifying questions to the user. Re-dispatch Triage after user answers.
2. **success** → Announce:
   ```
   🔍 Debug: {failure description}
      Type: {classification}
      Workers: {N}개 병렬 dispatch

      진단 중...
   ```
3. **Classification parse failure** → Fallback to `full_debug` (dispatch all 3 workers).

### Step 2: Dispatch Parallel Workers

Dispatch workers **simultaneously** based on Triage classification.

| Classification | Workers |
|---------------|---------|
| `error_log` | Error Analyst + Git History |
| `regression` | Git History + Code Tracer |
| `logic_bug` | Code Tracer + Error Analyst |
| `full_debug` | Error Analyst + Git History + Code Tracer |

Each worker receives:
- `affected_files` from Triage
- User's error description
- Hypotheses from Triage
- Working directory (`cwd`)

**Worker A — Error Analyst:**

```
Agent({
  description: "Athanor debug: error analyst",
  model: "sonnet",
  prompt: "You are an Athanor error analysis worker.

## Task
Analyze the failure in detail for: {failure description}
Working directory: {cwd}

## Input from Triage
Affected files: {affected_files}
Hypotheses: {hypotheses from Triage}

## Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: debug.
Read any relevant lessons and apply them to your approach.

## Focus
- Parse error messages and stack traces
- Identify the failing point (file:line, function)
- Determine error type (TypeError, assertion, crash, etc.)
- Compare expected vs actual behavior
- Evaluate Triage hypotheses against evidence

## Method
1. Use Grep to search affected_files for error patterns, exceptions, assertions
2. Use Read on specific sections around failure points (NOT entire files)
3. Trace up to 2 levels from the failing point
4. Check for validation gaps, type mismatches, missing guards

## Cross-Language Boundary
If you detect a cross-language boundary (e.g., Python calling C, JS calling WASM):
- FLAG it clearly in your output
- Do NOT trace across the boundary
- Report what you can observe on your side

## Output
Return findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentences}
details:
## Error Analysis
### Failing Point
- File: {file path}
- Line: {line number}
- Function: {function name}
### Error Type
{error classification and description}
### Expected vs Actual
- Expected: {what should happen}
- Actual: {what happens instead}
### Hypothesis Assessment
| # | Hypothesis | Status | Evidence |
|---|-----------|--------|----------|
| 1 | {h1} | confirmed/weakened/no evidence | {why} |
### Data Flow
{relevant data flow leading to failure}
lessons_read: [{lessons found}]
END_RESULT

Max 15 tool calls. Keep under 400 words."
})
```

**Worker B — Git History Analyst:**

```
Agent({
  description: "Athanor debug: git history analyst",
  model: "sonnet",
  prompt: "You are an Athanor git history analysis worker.

## Task
Investigate the git history around the failure: {failure description}
Working directory: {cwd}

## Input from Triage
Affected files: {affected_files}
Hypotheses: {hypotheses from Triage}

## Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: debug.
Read any relevant lessons and apply them to your approach.

## Focus
- When did it break? Identify timing of the regression
- Which commits touched the affected files?
- Suggest a bisect range for narrowing down
- Correlate timing with symptoms

## Method
1. Run: git log --oneline -20 -- {affected_files}
2. Run: git log --since='2 weeks ago' -- {affected_files}
3. Run: git diff HEAD~10 -- {affected_files}
4. Use git blame on suspicious sections identified by Triage

## Sparse History
If fewer than 3 commits exist for the affected files:
- Report 'Insufficient git history for {file}'
- Work with whatever history is available
- Do NOT fabricate or speculate about missing history

## Output
Return findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentences}
details:
## Git History Analysis
### Timeline
| Date | Commit | Description | Relevance |
|------|--------|-------------|-----------|
| {date} | {hash} | {msg} | {why relevant} |
### Suspicious Commits
- {commit hash}: {why suspicious}
### Bisect Suggestion
- Good (known working): {commit}
- Bad (known broken): {commit}
### Hypothesis Assessment
| # | Hypothesis | Status | Evidence |
|---|-----------|--------|----------|
| 1 | {h1} | confirmed/weakened/no evidence | {why} |
lessons_read: [{lessons found}]
END_RESULT

Max 15 tool calls. Keep under 400 words."
})
```

**Worker C — Code Tracer:**

```
Agent({
  description: "Athanor debug: code tracer",
  model: "opus",
  prompt: "ultrathink

You are an Athanor code tracing worker.

## Task
Trace the code path leading to the failure: {failure description}
Working directory: {cwd}

## Input from Triage
Affected files: {affected_files}
Hypotheses: {hypotheses from Triage}

## Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: debug.
Read any relevant lessons and apply them to your approach.

## Focus
- Backward data flow from the failure point
- Incorrect assumptions in the code
- Boundary conditions and edge cases
- Related patterns elsewhere in the codebase

## Method
1. Use Grep to find callers and references to the failing function/symbol
2. Use Read on function signatures and immediate callers (NOT entire files)
3. Trace backwards through the call chain
4. Check validation, preconditions, and invariants at each level

## Depth Constraint
- Trace a maximum of **3 call levels** from the failure point
- If the root cause appears to be deeper than 3 levels, report where you stopped
  and what direction the trace was heading
- Do NOT exceed 3 levels

## Cross-Language Boundary
If you detect a cross-language boundary (e.g., Python calling C, JS calling WASM):
- FLAG it clearly in your output
- Do NOT trace across the boundary
- Report what you can observe on your side

## Output
Return findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentences}
details:
## Code Trace
### Call Chain
{caller} ({file}:{line})
  → {callee} ({file}:{line})
    → {failure point} ({file}:{line})
### Incorrect Assumptions
- {assumption}: {why it's wrong}
### Boundary / Edge Cases
- {case}: {how it triggers the failure}
### Hypothesis Assessment
| # | Hypothesis | Status | Evidence |
|---|-----------|--------|----------|
| 1 | {h1} | confirmed/weakened/no evidence | {why} |
lessons_read: [{lessons found}]
END_RESULT

Max 15 tool calls. Keep under 400 words."
})
```

### Step 2.5: Worker Output Defense (run before Step 3)

Before merging, the Leader MUST check every worker finding for **stop-phrase patterns** (see `CLAUDE.md` §"Defense Mechanisms / Stop-Phrase Detection"). If any pattern appears in a finding — re-dispatch that worker with the same prompt prefixed by `"Diagnose to root cause. Do not stop early or dismiss as a pre-existing issue without evidence."`.

Patterns enforced (English alias in parentheses):
- "이 정도면 멈춰도 될 것 같습니다" / "I think we can stop here"
- "계속할까요?" / "Should I continue?"
- "기존 이슈입니다" / "This is a pre-existing issue"
- "새 세션에서 계속" / "Let's continue in a new session"
- "좋은 체크포인트" / "Good checkpoint"

`debug` is especially sensitive to "기존 이슈입니다 / This is a pre-existing issue" — if this phrase appears, reject the finding unless it is paired with a git blame line + a session id where the issue was first observed.

Also validate that each finding contains a well-formed `ATHANOR_RESULT ... END_RESULT` block with a `status:` field. If absent or truncated, re-dispatch once with the same prompt.

## Systematic Debugging Discipline

Concept adopted from superpowers@5.1.0 `sp-systematic-debugging` (MIT, Copyright (c) 2025 Jesse Vincent; upstream: https://github.com/obra/superpowers).
See NOTICE.md §Concepts adopted from upstream and `concepts/debug-discipline.md` (Subtask 11) for full attribution.

This discipline binds every `/athanor:debug` worker (Triage, Error Analyst, Git History, Code Tracer). Workers MUST hold to the Iron Law and proceed phase-by-phase; the Leader MUST reject any finding that proposes a fix before Phase 1 evidence is on the table.

### Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Symptom fixes are failure. Random fixes waste time and create new bugs. If Phase 1 is not complete, no fix may be proposed — by any worker, at any tool-call budget. Workers under time pressure or with an "obvious" guess MUST still complete Phase 1; rushing guarantees rework. 한국어 응답이 자연스러우면 한글로 정리해도 무방하나, "근본 원인 조사 없이는 수정 없음" 원칙은 동일하다.

### Four Phases

Each phase MUST complete before the next begins. The /athanor:debug worker matrix maps onto these phases: Triage opens Phase 1; Error Analyst + Git History + Code Tracer extend Phase 1 and 2 in parallel; the Leader's merge step is the gateway to Phase 3; any follow-up `/athanor:work` dispatch carries Phase 4.

1. **Phase 1 — Root Cause Investigation** — Read error messages carefully (stack traces, line numbers, error codes). Reproduce consistently or gather more data; do not guess. Check recent changes (git diff, recent commits, config/dependency shifts). For multi-component systems, add diagnostic instrumentation at each boundary to reveal WHERE the failure occurs before touching WHY. Trace data flow backward from the failing value to its origin — fix at source, not at symptom.
2. **Phase 2 — Pattern Analysis** — Find working examples of similar code in the same codebase. Read reference implementations completely (no skimming). List every difference between working and broken paths, however small — "that can't matter" assumptions guarantee bugs. Understand the broken component's dependencies, config, and environmental assumptions.
3. **Phase 3 — Hypothesis and Testing** — State a single hypothesis explicitly: "X is the root cause because Y." Test minimally — the smallest possible change, one variable at a time. Verify before continuing: if it worked, advance to Phase 4; if not, form a NEW hypothesis rather than stacking fixes. When you do not understand something, say so plainly and gather more data.
4. **Phase 4 — Implementation** — Create a failing test case first (use `superpowers:test-driven-development` or athanor-native TDD discipline). Implement a single fix addressing the root cause — one change at a time, no bundled refactoring. Verify the fix: target test passes, no other tests broken, the issue is actually resolved. If the fix does not work, count attempts.

### 3+ fixes = architectural question

If three fix attempts have failed, the bug is downstream of a deeper architectural choice. STOP attempting Fix #4. Indicators that the pattern itself is wrong: each fix exposes new shared state or coupling in a different place; each fix requires "massive refactoring" to land; each fix produces fresh symptoms elsewhere. At that point the question is not "which fix next" but "is this pattern fundamentally sound, or are we sticking with it through inertia?" Surface the architectural question to a human partner (or escalate to `/athanor:plan` cross-model review) before any further fix. This is a wrong-architecture signal, not a failed hypothesis — treat it accordingly.

### Step 3: Merge Results

After ALL workers return (and any re-dispatch from Step 2.5 has settled), merge their findings into a unified debug report.

**You (the Leader) do this merge** — no separate merge agent needed.
The workers' findings are short enough to combine directly.

> **Exception:** The Leader merges brief results from debug workers. This is formatting work (combining short findings), not analytical work. Dispatching a separate merge agent for 2-3 brief reports would be wasteful.

```markdown
# Debug Report: {failure description}

## Problem Statement
{"{Component} does {X} when it should do {Y}"}

## Root Cause
{confirmed hypothesis — 1-3 sentences, confidence level}

## Evidence Chain
### Error Analysis
{from Error Analyst — key findings}
### Failure Timeline
{from Git History — key findings}
### Code Trace
{from Code Tracer — key findings}

## Hypotheses
| # | Hypothesis | Status | Evidence |
|---|-----------|--------|----------|
| 1 | {h1} | confirmed/weakened/no evidence | {summary} |

## Affected Files
- {file:line}: {what's wrong and why}

## Reproduction Steps
{if determinable from analysis}

## Recommended Fix
- {specific action items}

---
*Diagnosed by 1 triage + {N} parallel workers in /athanor:debug*
```

### Step 4: Save & Present

1. Save the merged report to `.athanor/sessions/{id}/debug.md`
2. Present to user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Athanor Debug: {failure description}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{merged report}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Session: .athanor/sessions/{id}/
Workers: 1 triage + {N} parallel
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계:
  /athanor:plan       — 디버그 결과 기반 수정 계획 (복잡한 수정)
  /athanor:lite-plan  — 빠른 수정 계획 (단순 버그)
  /athanor:work       — 바로 수정 실행
```

---

## IMPORTANT RULES

1. Leader는 파일을 읽지 않고, 코드를 추적하지 않고, 직접 디버깅하지 않는다.
2. Triage worker를 먼저 단독 dispatch한 후, 결과 기반 병렬 dispatch.
3. Leader가 결과를 직접 merge — merge agent 불필요.
4. **Depth over speed** — 철저한 조사 우선. 단, tool call 제한으로 범위 통제.
5. Plan Mode — 프로젝트 파일 수정 금지. `.athanor/sessions/`에만 쓰기.
6. 기존 세션 재사용 (discuss/analyze 실행 후 같은 날이면).
