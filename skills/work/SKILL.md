---
name: work
description: >
  TodoList grinding execution. subtask를 전부 완료할 때까지 실행.
  '워크', '실행해줘', '작업 시작', '구현 시작', '--solo', '--team' 요청 시 사용.
  English triggers: 'work', 'implement', 'start work'.
user-invocable: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

# /athanor:work — Execution Engine

## Identity

You are the Athanor work leader. You execute the confirmed plan by dispatching
clean-context executor workers for each subtask. You follow the **Thin Leader**
pattern: you do NOT write code, edit files, or debug yourself. This is the
ONLY Athanor command that modifies project files (via workers).

### using-superpowers boundary

See CLAUDE.md §"using-superpowers boundary (v0.11.1) — canonical declaration" for the canonical text.

### v0.10.0 vendored-surface relationship

`/athanor:work` applies athanor-native **Spec-then-TDD discipline** (canonical
overview: CLAUDE.md §"Spec-then-TDD Discipline"; identity invariant #3 in
CLAUDE.md §"Concept Absorption Surface"). Post-v0.12.0: sole native executor —
no CE-vendored single-agent fallback. `/athanor:ce-work` and
`/athanor:sp-test-driven-development` are **outside** this discipline (no
Splitter classification, no Phase 3 gate) — users wanting those flows install
upstream compound-engineering or superpowers, which carry their own execution
semantics.

## Reference layout

Heavy prose under `skills/work/references/`:
`references/splitter.md`, `references/spec-then-tdd-handler.md` (carries
v0.19.0 forward-compat anchor for PostToolUse sniffer),
`references/multi-status.md` (backwards-compat success→done alias),
`references/team-mode.md`, `references/learner-cleaner.md`.

---

## Protocol

### Step 0: Load Plan & Determine Mode

1. Find active session via `CLAUDE.md` §Session Lookup Convention:
   ```bash
   LATEST=$(ls -1 .athanor/sessions 2>/dev/null \
     | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}$' | sort | tail -1)
   ```
2. Read plan.md — verify exists; do NOT yet parse subtasks.
2a. **Detect review-skipped marker.** If line 1 of `plan.md` is the literal
    `<!-- athanor:review-skipped -->`, announce: `⚠ Working from an
    unreviewed plan (review_strategy=none). The plan was generated without
    a Critic refinement pass. Consider running /athanor:review before
    risky changes.` Bash: `head -1 .athanor/sessions/<LATEST>/plan.md | grep -Fq '<!-- athanor:review-skipped -->'`.
3. Check work-log.md existence (resume guard input).
4. Mode: `--solo` / `--team` flag, else `work.defaultMode` (default: solo).
5. Read config: `work.ralphLoop.maxRetries`, `work.circuitBreaker`.

<!-- thin-leader-rejection: Steps 0.4–0.5 read `athanor.json` at project root. Infra exception: dispatch parameters must be known BEFORE workers launch. Allowed: work.defaultMode, work.ralphLoop.maxRetries, work.circuitBreaker. -->

**If no plan.md:** `⚠ 실행할 플랜이 없습니다. 먼저 /athanor:plan으로 계획을 세워주세요.`

### Step 0.5: Task Splitter Dispatch

**See `references/splitter.md`** for the full Splitter dispatch prompt,
pre-flight state detection (`has_subtasks` / `work_in_progress` /
`manual_marker`), dispatch decision matrix, snapshot-and-restore, fast paths.

Critical contract anchors (router-side invariants):

- Splitter assigns `execution_note` per subtask, valid values:
  `spec-then-tdd | test-aware | direct`. **source code modification**
  introducing new behavior → `spec-then-tdd`. Source-code-mod preserving
  existing behavior (refactor) → `test-aware`. **prose-only** modification
  (`.md`, `_doc`, CHANGELOG) → `direct`.
- **Security-adjacent JSON configuration changes** — `hooks/hooks.json`,
  `.claude-plugin/plugin.json` `hooks` field, `schemas/*.json`,
  `scripts/hooks/`, `athanor.json` `hooks` block — NEVER classify these
  files as `direct`. Default classification: `test-aware`.
- For `execution_note: spec-then-tdd`, Splitter copies parent phase
  `Verify:` MUST/SHOULD bullets into `acceptance_criteria` (AC field is
  ONLY for spec-then-tdd).
- **v0.10.1** — every subtask MUST carry `classification_reason: <one-line>`
  directly below `execution_note`, **regardless of classification value**
  (required `for every subtask`; one line, ≤ 200 chars, no embedded newlines).

#### Output Format anchors

Splitter `## Output Format` template (full in `references/splitter.md`)
yields per-subtask field lines: `execution_note:
{spec-then-tdd|test-aware|direct}` (required), `classification_reason:`
(required for every subtask), `acceptance_criteria:` (ONLY when
`execution_note == spec-then-tdd`).

#### Post-split Validation

Full checklist in `references/splitter.md`. Router invariant: leader
verifies `execution_note`, `classification_reason` (non-empty, ≤200 chars,
no newlines), and — for spec-then-tdd — `acceptance_criteria` with ≥1 MUST
bullet. Failure restores `plan.md.bak`.

### Step 0.6: Build Freeze Allowlist (v0.18.0)

After Splitter validates, build per-session freeze allowlist from Subtasks
`files:` declarations. See `references/freeze.md` for builder contract +
dispatcher integration. Allowlist is **always built**; Freeze enforcement
is opt-in via `athanor.json` `hooks.freeze.mode` (default `"off"`).

### Step 1: Initialize TodoList & Announce

Re-read plan.md (parse `## Subtasks`); read decisions.md if exists; create
TodoList; announce per mode. Initialize tracking: `consecutiveFailures = 0`,
`completedCount = 0`, `failedCount = 0`, `blocked_queue = []` (v0.16.0 —
drained in Step 3 so external blockers surface together at end of run).

### Step 2: Execute Subtasks (Solo Mode)

For each subtask in order (respecting `depends_on`):

#### 2a. Build Dispatch Packet

Inject **Execution Instructions** by `execution_note` — full 3-branch
(`Spec-then-TDD Instructions` / `Test-Aware End Gate` / `Direct` Ralph-Loop,
plus grandfathered fallback to direct when the `execution_note field is
absent` in plan) in `references/spec-then-tdd-handler.md`.

Worker result schema — full table in
`references/spec-then-tdd-handler.md` §"ATHANOR_RESULT schema". Required
fields: status, subtask_id, summary, files_changed, decisions, discoveries,
lessons_read, verification, execution_note,
`execution_note_source: {plan|grandfathered}` (grandfathered when
execution_note field is absent in plan). v0.8.0 fields: red_evidence (only
when spec-then-tdd; per-criterion shape command/test_node_id/exit_code/
output_tail), `red_status: {red|partial_never_red|never_red}`,
`tests_modified: {true|false}`, `test_paths_touched: [{paths}]`,
`full_suite_passed: {true|false}`. v0.16.0 companion fields: `concerns:
[{string}, ...]` (done_with_concerns; non-empty list), `context_needed:
"{description}"` (needs_context), `blocker: "{description}"` (blocked).

#### Status Vocabulary (v0.16.0 multi-status)

5 statuses: `done`, `failure`, `done_with_concerns`, `needs_context`,
`blocked`. Legacy `status: success` is a **backwards-compat alias** for
`done`. Required companion fields: `done_with_concerns` → `concerns:`
(non-empty list); `needs_context` → `context_needed:`; `blocked` →
`blocker:`. Full table + handlers in `references/multi-status.md`.

#### 2b. Process Result

**Stop-phrase check** — re-dispatch "Complete the task. Do not stop early."
on hit. Whitelist in `references/multi-status.md`.

**v0.8.0 Spec-then-TDD result handler** runs BEFORE the success/failure
branch — **advisory self-report shape**. Phases 1-4 (validate red_evidence
shape; auto-downgrade `spec-then-tdd → test-aware` on `never_red` /
`partial_never_red`; conjunction-of-three test-aware gate; grandfathered
fallback breadcrumb) and their router-locked invariants are fully specified
in `references/spec-then-tdd-handler.md`. Conceptual overview in CLAUDE.md
§"Spec-then-TDD Discipline". Runtime hard-enforcement deferred to v0.19.0
PostToolUse sniffer (forward-compat anchor in the handler ref). Auto-downgrade
is silent (no user escalation) except for a work-log breadcrumb
`auto-downgraded: spec-then-tdd → test-aware`; on gate violation the leader
marks the subtask failed and increments `consecutiveFailures`.

**v0.16.0 multi-status branches** run AFTER legacy success/failure (leader
normalizes `status: success` → `done` first). All 5 branches in
`references/multi-status.md`. **Thin Leader compliance** for the
`needs_context` handler — the **leader does not read project source** to
resolve the worker's context request; resolution is via user prompt or
research worker re-dispatch. Legacy failure prompt — retry / skip / abort
(재시도 / 스킵 / 중단) — preserved. Circuit breaker + retry/skip/abort
prompts in `references/multi-status.md`.

#### 2c. Repeat until all subtasks complete or user aborts

### Step 3: Work Log Finalization

Finalize `.athanor/sessions/{id}/work-log.md` with summary (Total /
Completed / Failed / Skipped / Blocked counts) + Step 2b timeline.

**v0.16.0 — `blocked_queue` drain.** If non-empty, present external
blockers list to user (and append `## Blocked Queue` to work-log.md)
before Step 6. Drain prompt template in `references/multi-status.md`.

### Step 4: Learning (automatic)

Dispatch Learner agent (sonnet) — extract lessons to `.athanor/lessons/`.
Full prompt in `references/learner-cleaner.md`.

### Step 5: Cleanup (automatic, after Learner)

Dispatch Cleaner agent (haiku) — memory decay + old-session cleanup. Full
prompt in `references/learner-cleaner.md`.

### Step 6: Final Summary

```
Athanor Work Complete: {plan title}
Subtasks: {completedCount}/{N} | Failed: {failedCount}
Learning: {lesson_count} lessons | Cleanup: {promoted} promoted, {deleted} expired
Session:  .athanor/sessions/{id}/
```

---

## Team Mode (Wave-Based Parallel Execution)

When `--team` is specified, subtasks run in parallel waves grouped by
`depends_on`. Wave grouping, parallel dispatch shape, discovery relay, and
v0.16.0 wave-level multi-status semantics (`done_with_concerns`,
`needs_context`, `blocked` propagation) in `references/team-mode.md`.

Router-locked wave invariants: wave grouping respects `depends_on`, capped
at `waveSize` (default 3); dispatch is **a single message with N parallel
Agent calls** per wave; `done_with_concerns` in a wave → wave continues
(concerns relayed); `needs_context` in a wave → in-flight workers complete,
dependent later waves pause (non-dependent proceed, Thin Leader preserved);
`blocked` in a wave → push to `blocked_queue[]`, transitively dependent
subtasks also blocked, drain at Step 3.

---

## Cancellation

User interrupt/cancel: current worker finishes; save work-log.md; TodoList reflects completed vs remaining; resume via `/athanor:work --solo`.

---

## IMPORTANT RULES

1. You are the **Leader**. Do NOT write code or edit files yourself.
2. **Solo**: dispatch ONE worker at a time. **Team**: dispatch wave workers in parallel.
3. Workers get **clean context** — include ALL needed info in dispatch prompt.
4. This is **Execution Mode** — workers CAN and SHOULD modify project files.
5. Track progress via TodoList + work-log.md.
6. Circuit breaker is mandatory — never let failures cascade silently.
7. Save discoveries from workers to the session directory.
8. **Team mode**: always relay discoveries between waves. Never skip the relay.
