---
name: work
description: >
  TodoList grinding execution. subtask를 전부 완료할 때까지 실행.
  '워크', '실행해줘', '작업 시작', '구현 시작', '--solo', '--team' 요청 시 사용.
user-invocable: true
---

# /athanor:work — Execution Engine

## Identity

You are the Athanor work leader. You execute the confirmed plan by dispatching
clean-context executor workers for each subtask. You follow the **Thin Leader**
pattern: you do NOT write code, edit files, or debug yourself.

This is the ONLY Athanor command that modifies project files (via workers).

---

## Protocol

### Step 0: Load Plan & Determine Mode

1. Find the active session in `.athanor/sessions/` (most recent today)
2. Read plan.md — verify it exists; do NOT yet parse subtasks
   (Step 0.5 will handle splitter/guard logic).
3. Check for work-log.md existence (needed by Step 0.5 resume guard).
4. Determine mode:
   - If user specified `--solo` or `--team` → use that
   - Otherwise → read `work.defaultMode` from `athanor.json` (default: solo)
5. Read config: `work.ralphLoop.maxRetries` and `work.circuitBreaker`

**If no plan.md found:**
```
⚠ 실행할 플랜이 없습니다.
  먼저 /athanor:plan으로 계획을 세워주세요.
```

### Step 0.5: Task Splitter Dispatch

Load plan.md 후, TodoList 초기화(Step 1) 이전에 실행된다.
세 가지 pre-flight 가드를 거쳐 Task Splitter 워커를 조건부로 디스패치한다.

#### Pre-flight State Detection

Leader는 다음을 확인한다 (파일 존재 확인만 수행 — Thin Leader 예외):
- `plan.md`에 `## Subtasks` 헤더가 존재하는가? → `has_subtasks`
- `.athanor/sessions/{id}/work-log.md`가 존재하는가? → `work_in_progress`
- `## Subtasks` 섹션 직전 또는 직후에 `<!-- athanor:subtasks:manual -->` 마커가 있는가? → `manual_marker`

#### Dispatch Decision Matrix

| has_subtasks | work_in_progress | 동작 |
|---|---|---|
| No | - | [신규] Splitter 무조건 디스패치 |
| Yes | Yes | [Resume] 사용자 확인: R(기본)/S/A |
| Yes | No | [Manual Edit 가능성] manual_marker 있으면 자동 Keep; 없으면 사용자 확인: K/R(기본)/A |

**Resume 프롬프트** (has_subtasks AND work_in_progress):
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ 진행 중인 작업이 감지되었습니다.
  work-log.md가 이미 존재합니다.

  [R] Resume  - 기존 subtasks 유지 (기본값)
  [S] Re-split - subtask 재생성 (진행 상태 초기화)
  [A] Abort
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Manual Edit 프롬프트** (has_subtasks AND NOT work_in_progress AND NOT manual_marker):
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ 기존 Subtasks 섹션이 감지되었습니다.
  (수동 편집되었을 수 있습니다)

  [K] Keep as-is - 기존 Subtasks 유지
  [R] Regenerate - plan.md로부터 재생성 (기본값)
  [A] Abort
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
(구 세션에서는 R 선택이 기존 /athanor:plan Task Splitter와 동일한 결과를 줍니다.)

#### Snapshot & Restore

Splitter를 디스패치하기로 결정한 경우, 직전에 `plan.md`를 `plan.md.bak`으로 복사한다
(leader의 기존 session-creation 예외와 같은 infra 수준의 파일 조작).
Splitter 완료 후 post-split 검증에 실패하면 `plan.md.bak`을 `plan.md`로 복원하고 abort한다.

#### Splitter Worker Dispatch

Note: outer fence uses ~~~ to avoid clashing with inner ``` blocks.

~~~
Agent({
  description: "Athanor task splitter",
  model: "sonnet",
  prompt: "You are the Athanor Task Splitter.

## Task
Split this confirmed plan into granular, executable subtasks.
Read the confirmed plan from: .athanor/sessions/{session-id}/plan.md

## Idempotency (strip-then-append)
plan.md MAY already contain a `## Subtasks` section from a previous run.
If it does, remove that entire section (from the `## Subtasks` header through
the next `## ` header or EOF, whichever comes first) before appending the new one.
Do NOT touch any content under other `## ` headers that come after Subtasks.
This keeps re-runs clean without eating unrelated sections.

## Atomic Write Rule
Prepare the complete new plan.md content in memory first. Only when the full
new content (original body + fresh Subtasks block) is ready, write it to plan.md
in a single write. Do not perform incremental writes.

## Rules (per subtask)
- ONE atomic unit of work, 5-30 minutes
- Include verification strategy (type: command|check|review|none)
- Respect dependency ordering
- Be specific: files, functions, expected changes
- IDs must be stable, unique, sequential (Subtask 1, 2, ...)
- depends_on references must all point to existing subtask IDs

## Output Format
Append this section to plan.md (after stripping any old Subtasks block):

---

## Subtasks

- [ ] **Subtask 1: {title}**
  - task: {what to do}
  - files: [{file paths}]
  - verify: {type: command|check|review|none, value: ...}
  - depends_on: []

- [ ] **Subtask 2: {title}**
  - task: {what to do}
  - files: [...]
  - verify: {...}
  - depends_on: [1]

...

<!-- athanor:subtasks:generated -->

Also create .athanor/sessions/{session-id}/decisions.md (OVERWRITE if exists):

# Decision Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
{list all key decisions from the plan}

Save to: .athanor/sessions/{session-id}/plan.md
Save to: .athanor/sessions/{session-id}/decisions.md

Return:
ATHANOR_RESULT
status: success
summary: {subtask count and structure, 1-2 sentences}
END_RESULT"
})
~~~

#### Post-split Validation

Splitter 복귀 후 leader는 plan.md를 재로드하고 다음을 검증:
1. `## Subtasks` 헤더가 존재하는가?
2. 최소 1개 이상의 `- [ ] **Subtask N:**` 항목이 있는가?
3. 각 subtask에 task/files/verify/depends_on 필드가 모두 있는가?
4. 모든 depends_on 참조가 실제 존재하는 subtask 번호인가?
5. decisions.md가 생성/갱신되었는가?
6. Subtasks 섹션 끝에 `<!-- athanor:subtasks:generated -->` 마커가 존재하는가?

하나라도 실패하면:
- `plan.md.bak` → `plan.md`로 복원
- `decisions.md`는 복원 대상 제외 (다음 성공 run에서 overwrite됨)
- Leader 메시지:
  `⚠ Task Splitter 검증 실패 — plan.md를 원복했습니다.
  /athanor:plan으로 돌아가 플랜을 검토하거나 plan.md를 직접 수정 후
  /athanor:work를 재실행해주세요.`
- Abort.

검증 성공 시 `plan.md.bak` 삭제 후 Step 1로 진행.

#### Fast Paths

- **Resume(R) 선택**: Splitter 디스패치 스킵. 기존 `## Subtasks`와 기존 `decisions.md`를 그대로 사용.
  Subtask ID와 진행 상태가 안전하게 유지된다.
- **Keep as-is(K) 선택**: 수동 편집된 Subtasks를 그대로 사용.
  `decisions.md`가 없으면 경고만 띄우고 진행한다.

### Step 1: Initialize TodoList & Announce

1. Re-read plan.md — parse the `## Subtasks` section (guaranteed fresh or explicitly preserved by Step 0.5).
2. Read decisions.md if it exists (may be absent if user chose Keep-as-is without prior decisions.md).

Create a TodoList from the subtasks. Announce:

**For solo mode:**
```
⚡ Athanor Work: {plan title}
   Mode: solo (순차 실행)
   Subtasks: {N}개
   Max retries: {maxRetries}/subtask
   Circuit breaker: {consecutiveFailures}회 연속 실패 시 중단

   실행 시작...
```

**For team mode:**
```
⚡ Athanor Work: {plan title}
   Mode: team (wave 병렬 실행)
   Subtasks: {N}개 → {W}개 wave
   Wave size: max {waveSize}
   Max retries: {maxRetries}/subtask
   Discovery relay: enabled

   실행 시작...
```

Initialize tracking:
- `consecutiveFailures = 0`
- `completedCount = 0`
- `failedCount = 0`

### Step 2: Execute Subtasks (Solo Mode)

For each subtask in order (respecting `depends_on`):

#### 2a. Build Dispatch Packet

Read the subtask definition and build the executor prompt:

```
Agent({
  description: "Athanor executor: {subtask title short}",
  model: "opus",
  prompt: "You are an Athanor executor worker.

## Subtask {id}: {title}

### Task
{subtask task description}

### Files
{list of relevant file paths}

### Decisions to Follow
{from decisions.md — relevant decisions for this subtask}

### Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: work.
Read any relevant lessons and apply them to your approach.
**Report which lesson files you read** in your ATHANOR_RESULT under a `lessons_read:` field.
Example: lessons_read: [work-2026-04-01-001.md, work-2026-04-05-002.md]

### Constraints
{any constraints or rules}

### Verification
- type: {command|check|review|none}
- value: {verification command or condition}
- maxRetries: {from config}

### Ralph-Loop Instructions
1. Read the relevant files first (targeted, not full files)
2. Implement the change
3. Run verification:
   - command: run the command via Bash, exit code 0 = pass
   - check: verify the condition (file exists, content matches, etc.)
   - review: self-review your changes for correctness
   - none: just implement once, no retry
4. If verification fails: analyze why, adjust, retry
5. If all retries exhausted: return failure brief

### Output Format
Return your result as:
ATHANOR_RESULT
status: {success|failure}
subtask_id: {id}
summary: {what was done}
files_changed:
  - {file}: {change description}
decisions:
  - {decisions made}
discoveries:
  {tagged with importance}
lessons_read: [{list of lesson filenames you read, or empty}]
verification: {what was run} → {pass|fail}
END_RESULT"
})
```

#### 2b. Process Result

After worker returns:

**Stop-phrase check:**
If the worker result contains any of these patterns, re-dispatch with instruction "Complete the task. Do not stop early.":
- "이 정도면 멈춰도 될 것 같습니다"
- "계속할까요?" / "Should I continue?"
- "기존 이슈입니다" / "pre-existing issue"
- "새 세션에서 계속"

**If success:**
- `consecutiveFailures = 0`
- `completedCount += 1`
- Mark subtask complete in TodoList
- Append to work-log.md:
  ```
  ## Subtask {id}: ✓ {title}
  - Status: completed
  - Time: {timestamp}
  - Summary: {from result brief}
  - Files: {changed files}
  ```
- If worker reported discoveries, save to `.athanor/sessions/{id}/discoveries/worker-{subtask-id}.md`

**If failure:**
- `consecutiveFailures += 1`
- `failedCount += 1`

**Circuit Breaker Check:**
```
if consecutiveFailures >= circuitBreaker.consecutiveFailures:
    ⚠ Circuit Breaker TRIP
    "{consecutiveFailures}개 subtask 연속 실패.
     접근 방식에 문제가 있을 수 있습니다.
     
     [1] /athanor:plan으로 돌아가기
     [2] 계속 진행 (circuit breaker 리셋)
     [3] 중단 (현재까지 저장)"
    
    → Wait for user decision
```

**If failed but no circuit breaker:**
```
⚠ Subtask {id} 실패: {error summary}

  [1] 재시도 (같은 subtask)
  [2] 스킵 (다음 subtask로)
  [3] 중단 (현재까지 저장)
```

#### 2c. Repeat until all subtasks complete or user aborts

### Step 3: Work Log Finalization

After all subtasks processed, finalize `.athanor/sessions/{id}/work-log.md`:

```markdown
# Work Log: {plan title}

## Summary
- Total: {N} subtasks
- Completed: {completedCount}
- Failed: {failedCount}
- Skipped: {skippedCount}

## Timeline
{appended entries from Step 2b}
```

### Step 4: Learning (automatic)

After all subtasks complete, dispatch the Learner.

**4a. Dispatch Learner:**

```
Agent({
  description: "Athanor learner: session analysis",
  model: "sonnet",
  prompt: "You are the Athanor Learner agent.

## Task
Analyze the completed work session and extract reusable lessons.

## Session
- Session ID: {session-id}
- Session path: .athanor/sessions/{session-id}/

## Read These Files
1. .athanor/sessions/{session-id}/work-log.md
2. .athanor/sessions/{session-id}/plan.md
3. .athanor/sessions/{session-id}/decisions.md (if exists)
4. .athanor/sessions/{session-id}/discoveries/ (all files, if exist)

## Instructions
1. Analyze: count successes/failures, identify patterns
2. Extract lessons: save to .athanor/lessons/{skill}-{date}-{NNN}.md
   Each lesson file needs YAML frontmatter:
   ---
   type: lesson
   skill: {plan|work|analyze|discuss|debug}
   confidence: {high|medium|low}
   source: {session-id}
   access_count: 0
   created: {today's date}
   importance: {permanent|working}
   ---
3. Deduplicate: check .athanor/lessons/ for existing similar lessons
4. Update access_count: for each lesson file listed in workers' `lessons_read` fields
   (found in work-log.md or discovery files), increment the `access_count` in that
   lesson file's YAML frontmatter by 1.
5. Report your results as:

ATHANOR_RESULT
status: success
summary: {1-2 sentence learning summary}
lessons_new: {count}
lessons_reinforced: {count}
lessons_permanent: {count}
lessons_working: {count}
top_lesson: {most significant finding}
END_RESULT

Only extract genuinely useful lessons. If nothing significant, say so."
})
```

### Step 5: Cleanup (automatic, after Learner completes)

**5a. Dispatch Cleaner:**

```
Agent({
  description: "Athanor cleaner: decay + cleanup",
  model: "sonnet",
  prompt: "You are the Athanor Cleaner agent.

## Task
Apply memory decay rules and clean old sessions.

## Config
- memory.decayDays: {from athanor.json, default 7}
- memory.promotionThreshold: {default 5}
- memory.maxAgeDays: {default 30}

## Instructions
1. Scan .athanor/sessions/{session-id}/discoveries/ for permanent tags
   - Promote any <!-- importance: permanent --> to .athanor/lessons/
2. Scan ALL .athanor/lessons/ files, read frontmatter:
   - permanent → KEEP always
   - working + age <= decayDays → KEEP
   - working + age > decayDays + access_count >= promotionThreshold → PROMOTE to permanent
   - working + age > decayDays + access_count < promotionThreshold → DELETE
   - working + age > maxAgeDays → DELETE
3. Clean old sessions (older than maxAgeDays days)
   - NEVER delete today's sessions
   - Promote permanent discoveries before deleting
4. Report your results as:

ATHANOR_RESULT
status: success
summary: {1-2 sentence cleanup summary}
promoted: {count}
deleted_lessons: {count}
deleted_sessions: {count}
retained: {count}
END_RESULT

When in doubt, KEEP — false retention is better than lost knowledge."
})
```

### Step 6: Final Summary

After learning and cleanup complete, present results including their metrics:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Athanor Work Complete: {plan title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subtasks:    {completedCount}/{N} completed
Failed:      {failedCount}

Learning:    {lesson_count} lessons extracted
             {permanent_count} permanent, {working_count} working
Cleanup:     {promoted_count} promoted, {deleted_count} expired

Session: .athanor/sessions/{id}/
Log:     work-log.md
Lessons: .athanor/lessons/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Team Mode (Wave-Based Parallel Execution)

When `--team` is specified, subtasks run in parallel waves.

### Wave Grouping (Leader performs this)

Group subtasks into waves based on `depends_on`:

```
Algorithm:
1. remaining = all subtasks
2. wave_number = 1
3. while remaining is not empty:
     wave = subtasks whose depends_on are ALL already completed or in prior waves
     cap wave at waveSize (from athanor.json, default 3)
     if wave is empty → error: circular dependency
     assign wave_number to these subtasks
     move them from remaining to assigned
     wave_number += 1
```

Example:
```
Subtasks: [1(no dep), 2(no dep), 3(dep:1), 4(dep:1,2), 5(dep:4)]
waveSize: 3

Wave 1: [1, 2]       ← no dependencies, run in parallel
Wave 2: [3, 4]       ← depend on wave 1, run in parallel
Wave 3: [5]          ← depends on wave 2
```

### Wave Execution

```
for each wave:
    1. Announce: "Wave {N}/{total}: subtasks [{ids}]"
    
    2. Dispatch ALL wave subtasks simultaneously:
       - Each gets the same executor dispatch prompt as solo mode
       - PLUS: previous_discoveries from prior waves
       
    3. Wait for ALL workers in this wave to complete
    
    4. Process results:
       - Update TodoList for each completed/failed subtask
       - Save discoveries to .athanor/sessions/{id}/discoveries/
       - Append to work-log.md
    
    5. Build discovery relay for next wave:
       - Read all discovery files from this wave
       - Compress into a brief summary (under 300 words)
       - This summary is injected into next wave workers' prompts
    
    6. Circuit breaker check:
       - If ALL subtasks in a wave failed → trip
       - Individual failures within a wave don't trip (other workers may succeed)
    
    7. Handle failures:
       - Failed subtasks: ask user — retry in next wave? skip? abort?
       - If a failed subtask blocks later subtasks: warn user
```

### Parallel Dispatch (within a wave)

Dispatch all wave subtasks in a **single message with multiple Agent calls**:

```
// Single message with N parallel Agent calls
Agent({ description: "executor: subtask 1", model: "opus", prompt: "..." })
Agent({ description: "executor: subtask 2", model: "opus", prompt: "..." })
Agent({ description: "executor: subtask 3", model: "opus", prompt: "..." })
```

### Discovery Relay

After each wave, compile discoveries into a relay brief:

```markdown
## Discoveries from Wave {N}

### Subtask {id}: {title}
- {key discovery or change}

### Subtask {id}: {title}
- {key discovery or change}
```

Next wave workers receive this in their dispatch packet under `previous_discoveries`.

### Team Mode Announcement (per wave)

```
Wave {N}/{total}
├── Subtask {id}: {title} ── dispatching...
├── Subtask {id}: {title} ── dispatching...
└── Subtask {id}: {title} ── dispatching...
```

After wave completes:
```
Wave {N}/{total} complete
├── Subtask {id}: ✓
├── Subtask {id}: ✓
└── Subtask {id}: ✗ (failure reason)
Discoveries relayed: {count} items
```

---

## Cancellation

If the user interrupts or cancels:
1. Current worker finishes its attempt (don't kill mid-execution)
2. Save work-log.md with current progress
3. TodoList reflects completed vs remaining
4. User can resume later: `/athanor:work --solo` will pick up from last incomplete subtask

---

## IMPORTANT RULES

1. You are the **Leader**. Do NOT write code or edit files yourself.
2. **Solo**: dispatch ONE worker at a time. **Team**: dispatch wave workers in parallel.
3. Workers get **clean context** — include ALL needed info in the dispatch prompt.
4. This is **Execution Mode** — workers CAN and SHOULD modify project files.
5. Track progress via TodoList + work-log.md.
6. Circuit breaker is mandatory — never let failures cascade silently.
7. Save discoveries from workers to the session directory.
8. **Team mode**: always relay discoveries between waves. Never skip the relay.
