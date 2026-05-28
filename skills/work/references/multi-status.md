# Multi-Status Executor Reference (v0.16.0)

Detailed reference for `/athanor:work` Step 2b multi-status branches.
Cross-linked from `skills/work/SKILL.md` Step 2b.

## Status Vocabulary (v0.16.0 multi-status)

The executor returns one of five `status` values. Each value is paired with a
one-sentence definition and (where applicable) a required companion field that
the worker MUST emit when using that status.

| Status | Definition | Required field |
|--------|------------|----------------|
| `done` | Subtask fully completed; all verify criteria met. | (none) |
| `failure` | Subtask attempted but failed after max retries. | (none — uses existing `last_error` / `attempts` fields) |
| `done_with_concerns` | Implementation complete but worker flags potential issues (e.g., deprecated API, uncovered edge case). Leader logs concerns and continues. | `concerns: [<string>, ...]` (non-empty list) |
| `needs_context` | Worker cannot proceed without information outside its dispatch context (design decision, external API response). Leader asks the user or re-dispatches with injected context — leader MUST NOT read project source files itself (Thin Leader). | `context_needed: "<description>"` |
| `blocked` | External blocker (CI down, API unreachable, dependency missing). Leader pauses this subtask, continues with non-dependent subtasks. | `blocker: "<external blocker description>"` |

**Backwards compatibility:** Legacy `status: success` is accepted as an alias
for `done` (existing workers and grandfathered plans continue to work
unchanged — no deprecation timeline). Legacy `status: failure` is unchanged.
Workers that don't know the new statuses keep returning `success`/`failure`;
the leader handler (Step 2b) maps `success` → `done` before branching.

## Stop-phrase check

If the worker result contains any of these patterns, re-dispatch with
instruction "Complete the task. Do not stop early.":
- "이 정도면 멈춰도 될 것 같습니다" / "I think we can stop here"
- "계속할까요?" / "Should I continue?"
- "기존 이슈입니다" / "This is a pre-existing issue"
- "새 세션에서 계속" / "Let's continue in a new session"
- "좋은 체크포인트" / "Good checkpoint"

## v0.16.0 multi-status branches

These branches run AFTER the legacy success/failure branches in the router;
the leader normalizes `status: success` → `done` before branching, so legacy
workers continue to land in the existing success path without modification.

**Legacy mapping:**
- `status: success` → treated as `done` (backwards-compat alias for
  grandfathered workers; legacy `success` path is preserved by the mapping,
  not by a second code path).
- `status: failure` → unchanged; uses the failure block (retry / skip / abort
  prompt + circuit-breaker accounting).

### If `status: done`

Identical to the legacy success path. Reset `consecutiveFailures`, increment
`completedCount`, mark subtask complete in the TodoList, append the
`✓ {title}` entry to work-log.md, save discoveries if any.

### If success (legacy / done — after v0.8.0 phases resolve to success)

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
- If worker reported discoveries, save to
  `.athanor/sessions/{id}/discoveries/worker-{subtask-id}.md`

### If failure

- `consecutiveFailures += 1`
- `failedCount += 1`

### If `status: done_with_concerns`

- Validate that the worker emitted a non-empty `concerns: [...]` list. If
  missing or empty, treat as a worker contract violation: log a warning to
  work-log.md and fall through to the `done` path anyway (concerns absent →
  no relay payload, but the implementation work itself stands).
- Reset `consecutiveFailures`, increment `completedCount`, mark subtask
  complete in the TodoList (same as `done` — the implementation IS complete;
  the concerns are advisory).
- Append to work-log.md with a `[concern]` prefix on each concern bullet:
  ```
  ## Subtask {id}: ✓ {title} [done_with_concerns]
  - Status: completed
  - Time: {timestamp}
  - Summary: {from result brief}
  - Files: {changed files}
  - [concern] {first concern from concerns[]}
  - [concern] {second concern from concerns[]}
  ```
- If any concern string contains a security/safety keyword (`security`,
  `auth`, `secret`, `credential`, `sandbox`, `escape`, `injection`, `XSS`,
  `CSRF`, `RCE`, `보안`, `취약점`), set a session-scoped flag
  `recommend_review = true`. The Step 6 final summary appends
  `Recommendation: run /athanor:review on this branch before merging.`
- Save discoveries if any. Concerns are also forwarded to the team-mode
  discovery relay (see Team Mode section).

### If `status: needs_context`

- This is NOT a failure. Do NOT increment `consecutiveFailures`. Do NOT
  burn a retry attempt against `maxRetries`. The Ralph-Loop budget counts
  this as 1 iteration only for the global circuit-breaker / iteration-cap
  accounting (so an infinite "needs_context" loop still trips the breaker).
- Validate that the worker emitted a non-empty `context_needed:` string.
  If missing or empty, this is a worker contract violation: treat as
  failure (the worker should have either completed or returned a real
  context request).
- Append to work-log.md with a `[context-needed]` prefix:
  ```
  ## Subtask {id}: ⏸ {title} [context-needed]
  - Status: paused
  - Time: {timestamp}
  - context_needed: {description from worker}
  ```
- **Thin Leader compliance:** The leader MUST NOT read project source
  files to answer the worker's context request itself. The only two
  resolution paths are:
  1. **Ask the user.** Surface the worker's `context_needed:` string
     verbatim with a prompt:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ⏸ Subtask {id} needs context:
       {context_needed verbatim}

       Reply with the missing information, or
       [S] Skip this subtask  [A] Abort the run
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```
     On user response, re-dispatch the same subtask with the user's reply
     injected into the dispatch packet under a new section heading
     `### Injected Context (from user)`. The worker reads the project files
     itself — the leader still does not.
  2. **Re-dispatch a research worker.** If the user replies with a tag
     like `research:` or the context_needed obviously requires file/source
     discovery (and the user opts in), dispatch a clean-context
     researcher/analyst worker to gather the answer, then re-dispatch the
     original executor with the researcher's brief injected. The leader
     orchestrates dispatch; it still does not read project source itself.
- The re-dispatched subtask runs through the normal Step 2b flow again —
  including this same `needs_context` handler if the worker still cannot
  proceed. The iteration cap is the only safeguard against loops.

### If `status: blocked`

- This is NOT a failure (the worker did its job; an external dependency is
  the problem). Do NOT increment `consecutiveFailures`. Increment
  a separate `blockedCount` counter.
- Validate that the worker emitted a non-empty `blocker:` string. If
  missing or empty, treat as a worker contract violation: log a warning
  and fall through to the failure path.
- Append to work-log.md with a `[blocked]` prefix:
  ```
  ## Subtask {id}: ⛔ {title} [blocked]
  - Status: blocked (external)
  - Time: {timestamp}
  - blocker: {blocker description from worker}
  ```
- **Dependent propagation:** Walk the remaining subtasks. Any subtask
  whose `depends_on` includes this `subtask_id` (transitively) is also
  marked `blocked` with `blocker: "transitive: subtask {id} blocked"` and
  appended to the `blocked_queue[]` so the user sees the full impact set.
  Mark those dependents as skipped-blocked in the TodoList; do NOT
  dispatch them.
- Push `{subtask_id, blocker, dependents: [list of transitively-blocked
  subtask ids]}` onto `blocked_queue[]` (initialized in Step 1).
- Continue with the next non-dependent subtask (do NOT halt the run;
  the unblocked work proceeds). The `blocked_queue` is drained at the
  end of the run in Step 3 — the user sees all external blockers
  together rather than one prompt per blocked subtask mid-run.

## Circuit Breaker Check

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

## If failed but no circuit breaker

```
⚠ Subtask {id} 실패: {error summary}

  [1] 재시도 (같은 subtask)
  [2] 스킵 (다음 subtask로)
  [3] 중단 (현재까지 저장)
```

## blocked_queue drain (Step 3)

After all subtasks processed and work-log.md is being finalized, drain
`blocked_queue`:

If `blocked_queue` is non-empty, present the full list to the user before
the Step 6 final summary so external blockers are visible together rather
than one prompt per blocked subtask:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔ External blockers encountered ({N} subtask(s)):

  Subtask {id}: {title}
    blocker: {blocker description}
    blocks: {comma-separated transitively-blocked subtask ids, or "none"}

  Subtask {id}: {title}
    blocker: {blocker description}
    blocks: {...}

  Resolve the blockers and re-run /athanor:work to resume the blocked
  subtasks. The Ralph-Loop will pick up where it left off.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Also append a `## Blocked Queue` section to work-log.md mirroring this
content so the persisted log captures the blocker set for later resumption.
