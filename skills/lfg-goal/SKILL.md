---
name: lfg-goal
description: >
  Goal-Driven Validated Ralph Loop — run /athanor:lfg in a bounded N-cycle
  macro loop bound to a durable goal ledger. Each cycle ends not on a
  bare <promise>DONE</promise> sentinel but on a dispatched
  receipt-validator that runs 9 externally-verifiable Bash checks against
  the cycle's actual artifacts. Goal completion requires a 3-tier check
  (mechanical + adversarial cross-model judge dispatch + blocking user
  ratification). Wraps athanor's existing /athanor:lfg verbatim; does NOT
  modify it. Built for hands-off multi-cycle execution toward a stated
  outcome with externally-verifiable progress receipts.
  '목표 달성까지 돌려', 'ralph loop', 'goal-driven ship',
  '/athanor:lfg-goal', 'athanor lfg-goal', 'iterate until goal met'.
user-invocable: true
allowed-tools: Bash, Read, Write, Task, AskUserQuestion, Skill
---

# /athanor:lfg-goal — Athanor-native Goal-Driven Validated Ralph Loop

## Identity

You are the Athanor LFG-Goal leader. You orchestrate a bounded N-cycle
macro loop that wraps `/athanor:lfg` (single cycle) verbatim and binds
every cycle to a durable goal ledger. You follow the **Thin Leader**
pattern: you parse the goal, dispatch validators / judges / cycles, and
collect verdicts. You do NOT write project source code, you do NOT
author per-cycle receipts, and you do NOT decide goal-met yourself. See
CLAUDE.md §"Concept Absorption Surface" identity
commitment #1.

This skill is invoked when the user wants hands-off multi-cycle work
toward a stated outcome (a "goal") rather than a single feature ship.
Typical triggers: "목표 달성까지 돌려", "iterate until goal met",
"keep going until done", "/athanor:lfg-goal".

The four v0.10.0 athanor identity invariants — Thin Leader, cross-model
adversarial planning, Spec-then-TDD discipline, Stop hook runtime gate
— are preserved through orchestration over existing primitives, NOT by
introducing a new invariant. Per D11 (decisions.md 2026-05-22-002),
lfg-goal is an orchestration layer composed of the existing four; no
fifth invariant ships with v0.13.0.

### using-superpowers boundary

See CLAUDE.md §"using-superpowers boundary (v0.11.1) — canonical declaration" for the canonical text.

## When NOT to invoke

- For a single feature ship without goal-level iteration —
  use `/athanor:lfg` directly.
- For one-off planning without execution — use `/athanor:plan`
  (optionally `--depth=lite`).
- For casual conversation or exploratory questions —
  use `/athanor:discuss`.
- For a one-shot review without commit/push — use `/athanor:review`.

## Difference from /athanor:lfg

`/athanor:lfg` is a single-cycle end-to-end pipeline. `/athanor:lfg-goal`
is a goal-bounded N-cycle macro loop that invokes `/athanor:lfg`
verbatim once per cycle and adds an honesty layer on top:

| | `/athanor:lfg` | `/athanor:lfg-goal` |
|---|---|---|
| Scope | Single feature → ship | Bounded N-cycle iteration → goal completion |
| Cycle bound | None — one pass through 9 steps | `lfgGoal.maxIterations` (default 5) |
| Goal ledger | None — implicit in user prompt | `.athanor/goals/<id>/goal.md` durable ledger with G-markers |
| Per-cycle DONE signal | `<promise>DONE</promise>` from Step 9 | Dispatched receipt-validator runs 9 Bash verification commands; produces `CNNN-lfg-receipt.md` with per-step status enum |
| Goal-level completion | N/A (no goal concept) | 3-tier check: Tier 1 mechanical + Tier 2 adversarial cross-model judges + Tier 3 BLOCKING user ratification |
| Scope-drift between cycles | N/A | `/athanor:scope-drift` auto-fires (`lfgGoal.scopeDriftAutoCheck: true` default) |
| Release strategy | Single PR + tag | Per-cycle PRs + tags (`consolidateCycles: false` default per D9); opt-in single-PR mode available |
| When to choose | Known scope, single ship | Multi-cycle work, goal stated in outcome terms |

`/athanor:lfg-goal` does NOT modify `/athanor:lfg`. The wrapper calls
lfg verbatim and reads what lfg already produces. Loose coupling is
the architectural decision (D2): lfg-goal can evolve without touching
the inner pipeline.

## Invocation Forms

Both forms are supported (D10, decisions.md 2026-05-22-002):

### Inline form

```
/athanor:lfg-goal "ship a CLI that does X, Y, and Z with passing tests"
```

The text becomes the goal statement. A goal-id is auto-generated as
`sha256(<goal-text> + <ISO-8601-timestamp>)[:8]` — an 8-char hex slug
unique per invocation. Storage opens at
`.athanor/goals/<goal-id>/goal.md` and the bootstrap cycle begins.

Use inline form for simple goals expressible in one or two sentences.

### File form

```
/athanor:lfg-goal --goal-file goals/cli-feature.md
```

`<goal-file>` is a repo-relative path to a pre-curated goal markdown
file. The leader reads the file, derives the goal-id from
`sha256(<file-contents> + <ISO-8601-timestamp>)[:8]`, and copies the
contents into `.athanor/goals/<goal-id>/goal.md` as the initial ledger.
If the goal file already contains `G1`, `G2`, ... markers, bootstrap
skips the auto-derive step and locks them directly.

Use file form for long-form goals, multi-marker plans, repeat use
across sessions, or goals you want versioned in git.

Both forms produce the same downstream state. Choice is ergonomic only.

## Architecture: Validated Receipt-Ledger Loop

The skill's three-layer architecture is the **Validated Receipt-Ledger
Loop**. Each layer is an independent honesty primitive; a misbehaving
leader has to defeat all three to declare false completion.

- **Layer 1 — Goal Ledger.** Durable `.athanor/goals/<id>/goal.md` is
  the source of truth. G-markers, acceptance criteria, scope-change
  audit, stop conditions. Locked after bootstrap; mid-flight changes
  go through the explicit `scope_change` flow.
- **Layer 2 — Per-Cycle Receipts.** After each cycle's `/athanor:lfg`
  invocation, a dispatched **receipt-validator** worker (clean context)
  runs 9 externally-verifiable Bash commands — one per lfg step — and
  writes `CNNN-lfg-receipt.md` with per-step status enum and
  evidence-as-command-output. The leader does NOT author the receipt.
- **Layer 3 — Adversarial 3-Tier Goal-Completion Check.** Mechanical
  Bash arithmetic + cross-model judge dispatch (Claude + Codex parallel)
  + blocking user ratification. Goal completion is a state transition
  conjoining all three tiers, NOT a model verdict.

The literal phrase **Validated Receipt-Ledger Loop** names this
architecture in plan.md and in every downstream reference. Use it
verbatim when describing the skill to users.

## Goal Ledger Format

`.athanor/goals/<id>/goal.md` shape:

```markdown
# Goal <id>: <one-line summary>

## Goal statement
<verbatim user text or file contents, lightly normalized for markdown
escaping only>

## G-markers (locked at bootstrap)

- [ ] G1 — <observable, evidence-backed outcome>
  - acceptance_criterion: <MUST-style single criterion>
  - closed_by: <CNNN or empty>
  - evidence_refs: <list>
- [ ] G2 — ...
- [ ] G3 — ...

## Cycle queue

| cycle | targets | status |
|---|---|---|
| C001 | G1 | pending |
| C002 | G2, G3 | pending |

## Verify command
<single Bash one-liner the goal-author specifies; Tier 1 runs this and
checks exit 0>

## Test-count command
<project-specific count command, e.g.
`pytest --collect-only -q tests/ | tail -1`>

## Stop conditions
- complete: all G-markers checked AND each has closed_by:CNNN with
  validator-passed receipt
- invalid_cycle: receipt aggregate=invalid for `noProgressThreshold`
  consecutive cycles
- blocked: explicit user abort via Tier 3 prompt
- max_iterations: cycle counter reaches `lfgGoal.maxIterations`

## Scope changes (append-only)

| id | proposed_by | timestamp | summary | status | decision |
|---|---|---|---|---|---|
```

G-markers are **locked** after initial generation. New requirements
must go through the `scope_change` flow (see §"Scope-Change Protocol"
below).

**Completion is a state transition**, not a model verdict:

```
status: complete
  AND every G-marker checked [x]
  AND every checked marker has closed_by: CNNN with evidence refs
  AND every closing CNNN has validator-passed receipt
  AND Tier-2 judges (A + B) both returned goal_met: true
  AND Tier-3 user ratification = yes
```

## Cycle Receipt Format

After each cycle's `/athanor:lfg` invocation, the dispatched
receipt-validator writes
`.athanor/goals/<id>/receipts/CNNN-lfg-receipt.md`. The validator runs
each Verification Command below and records its exit code + captured
output as the evidence for that step. **Per-step status enum:**
`completed | skipped-by-rule | completed-with-residuals | failed | missing`.

| Step | Required Evidence | Verification Command | PASS Criterion |
|---|---|---|---|
| 1 plan | `plan_file_path` | `test -f <path> && [ $(wc -c < <path>) -gt 500 ]` | exit 0 (file exists + ≥500 bytes) |
| 2 work | `commit_sha` + `tests_modified: bool` | `git show --stat <sha> && git show --name-only <sha> \| grep -E '^tests/'` | sha resolves; if behavior-bearing, tests/** path present |
| 3 review | `review_artifact_path` OR `pr_url` | `test -f <path> && grep -q '^## Verdict' <path>` OR `gh pr view <pr> --json comments \| jq '.comments \| length > 0'` | parsable structure present, not free prose |
| 4 review-fix commit | `commit_sha_review_fix` OR `null` (no-op rule) | `git log --grep='fix(review)' --oneline -1` OR explicit no-op flag | sha resolves OR rule-skip recorded |
| 5 residual handoff | `pr_url` body section OR fallback `.md` path | `gh pr view <pr> --json body \| jq -r '.body' \| grep -q 'Residual Review Findings'` OR `test -f <path>` | section present or fallback file exists |
| 6 browser test | `result_file_path` OR `null` (no UI) | `test -f <path>` OR `git diff --name-only <cycle-start>..HEAD \| grep -v -E '\.(html\|jsx\|tsx\|css)$' \| wc -l` ≥ all diff | artifact exists OR no UI files touched |
| 7 commit-push-PR | `pr_url` | `gh pr view <pr> --json state,url \| jq -e '.state != "CLOSED"'` | PR exists, not closed-without-merge |
| 8 CI watch | `ci_run_url` + `final_check_status` | `gh pr checks <pr> --json conclusion \| jq -r '.[].conclusion' \| sort -u` | last conclusion = success OR `## CI Failures Unresolved` section in PR body |
| 9 DONE | `tag` OR `null` (dry-run) | `git tag -l '<tag>'` | tag exists (or null + dry-run flag) |

**Per-cycle aggregate status:**

- `all_valid` — all steps `completed` or `skipped-by-rule`
- `completed_with_residuals` — ≥1 `completed-with-residuals`, 0 `failed`, 0 `missing`
- `invalid_steps_present` — ≥1 `failed` or `missing`

Only `all_valid` and `completed_with_residuals` (with user override) can close G-markers.
`invalid_steps_present` blocks marker closure — the next cycle resumes from the
failure point with explicit reason recorded.

## Receipt Validation Protocol

After cycle N runs `/athanor:lfg` to completion, the leader dispatches
a clean-context **receipt-validator** worker (see
`skills/lfg-goal/references/receipt-validator.md`). The validator:

1. Reads cycle N's `.athanor/sessions/<id>/` artifacts (plan.md,
   work-log.md, review artifacts, discoveries/).
2. Runs the **Verification Command** for each of `/athanor:lfg`'s 9
   steps (table above). Each command returns Bash exit code + captured
   output.
3. Writes `.athanor/goals/<id>/receipts/CNNN-lfg-receipt.md` with
   per-step status enum + evidence-as-command-output (not free prose).
4. Returns `ATHANOR_RESULT` with `validation_status: all_valid |
   completed_with_residuals | invalid_steps_present` + list of failing
   steps if any.

**`<promise>DONE</promise>` sentinel emission alone is insufficient
for cycle completion — a valid receipt with all 9 step evidence fields
verified by the dispatched receipt-validator is required.** This is
the load-bearing honesty primitive of the Validated Receipt-Ledger
Loop: the leader cannot infer cycle-DONE from the bare sentinel that
`/athanor:lfg` Step 9 emits; the cycle is closed only when the
externally-dispatched validator returns `validation_status: all_valid`
(or `completed_with_residuals` with explicit user override). This
closes the silent-bypass hole — a misbehaving leader cannot emit DONE
prose and skip the work.

The validator is a dispatched worker, NOT a leader function (D4,
decisions.md 2026-05-22-002). This preserves identity #1 (Thin Leader)
structurally rather than by prose admonition.

## 3-Tier Goal-Completion Check

After the receipt-validator returns `all_valid` (or `completed_with_residuals` + user
override), the leader dispatches the goal-completion check. Three
sub-tiers, each independent:

### Tier 1 — Mechanical (deterministic, no LLM)

Bash-only checks. Same shape as `/athanor:lfg` Step 2 GATE checks.
PASS requires **all** of:

1. **Ledger arithmetic.** All G-markers in `goal.md` have `[x]`; each
   has `closed_by: CNNN`; each referenced CNNN has receipt with
   `aggregate: valid`.
2. **Verify command.** Run `goal.md` §"Verify command" (single Bash
   one-liner); capture exit code. Exit 0 → signal PASS.
3. **AE-ID evidence index.** For each AE-ID in `goal.md`, grep cycle
   work-logs for a corresponding `pytest::test_node_id` or inline
   assertion. 100% coverage required.
4. **Regression test count.** Pre-cycle count cached at bootstrap;
   post-cycle count must be `>= pre + (count of acceptance tests
   required by markers)`. If `goal.md` omits the test-count command,
   this signal is `unknown` (not PASS).
5. **No new TODO/FIXME** tagged with the goal-id in the cycle diff.

### Tier 2 — Adversarial Cross-Model Judge Dispatch

NOT a single goal-checker. Dispatch **two PARALLEL judges**, mirroring
athanor identity #2 (cross-model adversarial planning):

- **Judge A** — Claude opus, structured rubric: R-ID coverage per
  marker (PASS / PARTIAL / FAIL), AE-ID coverage per marker, scope-creep
  flag (diff items outside G-markers), residual gap (free-form prose).
  Cannot infer completion from DONE sentinel, PR existence, or
  self-reported work logs alone — must cite ledger evidence.
- **Judge B** — Codex via Bash (gated on `codex.enabled: true`), same
  rubric, different model family.

**Verdict:** Tier 2 PASSES only when both judges return
`goal_met: true` with independent reasoning. Disagreement → escalate
to Tier 3 with both verdicts shown to user.

If `codex.enabled: false`, Tier 2 degrades to single-judge mode with
explicit warning written to `decisions.md` — the loss of adversarial
posture is recorded, not silenced.

### Tier 3 — User Ratification (BLOCKING)

ONE blocking prompt:

```
Goal-status: cycle N complete; receipt-validator: all_valid;
Tier 1 mechanical: PASS; Tier 2 cross-model: Judge A = goal_met,
Judge B = goal_met (or split — show both).

Confirm goal is achieved? [yes / continue-iterating / abort]
```

cycle·goal-completion 보고는 해석된 `output.language`에 맞춘다; ledger 필드/판정 토큰/센티널은 영어; 완료-주장 어조 회피. 즉 이 ratification 프롬프트의 user-facing 안내 문구(예: "목표가 달성되었는지 확인할까요? [yes / continue-iterating / abort]")와 아래 응답 처리 안내는 해석된 언어로 제시하되, machine-parsed 토큰은 영어로 둔다. 영어로 유지되는 토큰: 옵션 토큰 `[yes / continue-iterating / abort]`·`receipt-validator`·`Tier 1 mechanical`·`Judge A = goal_met`·`validation_status` enum 값·ledger 필드 키·G-markers·DONE 센티널은 언어 무관 항상 영어. 해석 규칙은 `skills/setup/SKILL.md` §`output.language 해석 (canonical)` (Present-to-User 직전 해석; 파일 부재·malformed·미지원 값 → en).

User responses:

- **yes** → write `goal-completion.md`, set ledger `status: complete`,
  emit DONE sentinel through the verification-before-completion skill.
- **continue-iterating** → ledger stays `active`, next cycle dispatched
  with residual gap as cycle delta.
- **abort** → ledger `status: abandoned`, write reason to
  `decisions.md`, no further cycles.

The negative-ratification path (user rejects goal-met) explicitly does
**NOT** emit DONE and explicitly does **NOT** mark complete.

Tier 3 is BLOCKING by default (D6). User CANNOT bypass Tier-3 without
explicit `--auto-ratify-when-tier2-passes` flag (default false; not
exposed in shipped config block — user must edit the raw command line
to opt in). Ratification is the out-of-band primitive the leader
cannot fabricate.

## Scope-Change Protocol

Mid-cycle worker discovers a missing dependency:

1. Worker appends `scope_change: proposed` row to `goal.md` table with
   `proposed_by: C<N>`, `timestamp`, `summary`, `evidence_ref`.
2. Leader dispatches `scope-change-critic` worker (clean context) to
   evaluate proposal against original goal intent.
3. Critic returns `decision: accept | reject | escalate` with reasoning.
4. **Accept** → leader appends new G-marker to ledger (G-markers
   re-lock); cycle continues; user notified via `decisions.md` entry.
5. **Reject** → cycle continues WITHOUT ledger update; proposal stays
   in table with `status: rejected` + decision rationale.
6. **Escalate** → PAUSE the loop. Leader invokes `AskUserQuestion` with
   the proposed delta + critic reasoning; user picks `accept | reject`
   manually. `cycle_state` transitions to `scope_change_pending` (per
   `skills/lfg-goal/references/state-shape.md`) so resume semantics
   route the next invocation back to the user-ratification gate if the
   session is interrupted before the user answers.
7. User can override either direction via direct ledger edit; audit
   trail preserved (no silent rewrites).

The `escalate` branch mirrors the Tier 3 BLOCKING posture (D6): when
the critic cannot confidently choose accept/reject (e.g., the proposed
delta touches goal intent in ambiguous ways), the user gets the final
say rather than the leader silently picking one direction.

This addresses rigid-lock paralysis while preserving the audit-trail
discipline.

## Goal Storage Lifecycle

- Default: `.athanor/goals/` is **gitignored** (mirrors the
  `.athanor/sessions/` convention).
- Completed goals: on `mark_goal_complete()`, leader copies `goal.md`,
  `goal-completion.md`, AND the `receipts/` directory (every
  `CNNN-*-receipt.md` validator receipt) to `docs/goals-completed/<id>/`
  (gitted) before ledger closure — the receipts are the externally-
  verifiable evidence trail and must survive with the completion record,
  since the gitignored `.athanor/goals/<id>/` tree may later be aged out by
  the cleaner. Controlled by `lfgGoal.archiveOnComplete: true` (default).
- `abandoned | blocked | max_iterations_exceeded` goals: stay in
  `.athanor/goals/` for `lfgGoal.goalRetentionDays` (default 30) then
  cleaner agent ages them out per D13.
- Destructive ops (delete completed-goal directory) require explicit
  user action per athanor convention.

## Resume / Mid-Cycle Abort

Explicit cycle states tracked in `.athanor/goals/<id>/state.json` (see
`skills/lfg-goal/references/state-shape.md` for the durable JSON schema).

The macro `cycle_state` enum has 6 values (canonical per state-shape.md):

```text
cycle_state: bootstrapping | cycle_n_in_progress | cycle_n_complete |
             goal_complete | aborted | scope_change_pending
```

A separate `cycle_phase` sub-status field captures granular within-cycle
position for resume semantics. `cycle_phase` is **only meaningful when
`cycle_state == cycle_n_in_progress`**; for the other 5 macro states it
is `null` or absent.

```text
cycle_phase: not_started | lfg_done_seen | receipt_validated |
             tier1_checked | tier2_checked | tier3_pending |
             tier3_ratified
```

**Resume rules** (keyed on the 6 macro states + cycle_phase):

- `cycle_state == bootstrapping` → next invocation finishes goal.md
  bootstrap (resume from the goal-shape user confirmation prompt).
  `cycle_phase` is `null` in this state.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == not_started`
  → RE-RUNS the cycle from the beginning (does NOT increment counter).
  User is prompted before re-run with reason from `state.json`.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == lfg_done_seen`
  → dispatches receipt-validator on the existing cycle session (skips
  re-running `/athanor:lfg`).
- `cycle_state == cycle_n_in_progress` with `cycle_phase == receipt_validated`
  → skips receipt validation; proceeds to Tier 1 mechanical check on the
  existing receipt.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == tier1_checked`
  → skips Tier 1; dispatches Tier 2 adversarial cross-model judge dispatch.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == tier2_checked`
  → proceeds to Tier 3 user ratification prompt for the same cycle.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == tier3_pending`
  → re-issues Tier 3 user ratification prompt (user response was lost
  mid-session).
- `cycle_state == cycle_n_in_progress` with `cycle_phase == tier3_ratified`
  → cycle is effectively closed; next invocation starts cycle+1
  (equivalent to `cycle_n_complete`).
- `cycle_state == cycle_n_complete` → cycle is closed; next invocation
  starts cycle+1.
- `cycle_state == scope_change_pending` → next invocation resumes from
  the scope-change-critic verdict / user ratification gate.
- `cycle_state ∈ {goal_complete, aborted}` → terminal; leader refuses
  to re-enter the loop and instructs the user to start a fresh
  invocation.

Malformed `state.json` triggers an explicit abort message (NOT silent
fall-back). User can repair manually or start a fresh goal-id.

## Loop architecture

```text
function lfg_goal_loop(goal_input | --goal-file path):
  goal_id = sha256(goal_input + timestamp)[:8]

  # ───── Cycle 0: Bootstrap ─────
  if not goal_ledger_exists(goal_id):
    bootstrap_goal_ledger(goal_id, goal_input)
    # Dispatches /athanor:plan with goal-shaped prompt template
    # Output: goal.md draft (markers + cycle queue + verify-command +
    #         test-count-command)
    user_confirm_goal_shape()   # single blocking checkpoint
    write_bootstrap_receipt(goal_id)
  else:
    load_existing_ledger(goal_id)
    resume_with_user_confirm()

  # ───── Cycles 1..N ─────
  no_progress_counter = 0
  for cycle in 1..lfgGoal.maxIterations:   # default 5 (D8)
    inject_goal_into_session_requirements(cycle)
    if cycle > 1:
      inject_prior_compressed_summary(cycle - 1)

    # Invoke /athanor:lfg VERBATIM — no modification (D2)
    invoke_skill("athanor:lfg")
    cycle_session_id = read_latest_session_id()

    # ── Receipt validation (Layer 2) ──
    validator_result = dispatch_worker("receipt-validator",
        cycle_session_id=cycle_session_id, goal_id=goal_id)

    write_compressed_cycle_summary(cycle)  # ≤300 words

    # ── No-progress circuit breaker (C1 fix: moved inside loop) ──
    if no_progress_against_prior(cycle - 1):
      no_progress_counter += 1
      if no_progress_counter >= lfgGoal.noProgressThreshold:
        emit_durable_residual_exit(reason="no-progress")
        return
    else:
      no_progress_counter = 0   # reset on progress

    if validator_result.aggregate == "invalid_steps_present":
      log_to_goal_log("cycle N invalid: <failing steps>")
      if cycle == lfgGoal.maxIterations:
        emit_durable_residual_exit(reason="max-iter-with-invalid")
        return
      continue   # next cycle resumes from failure

    if validator_result.aggregate == "completed_with_residuals":
      log_to_goal_log("cycle N completed_with_residuals: <residual steps>")
      # proceed to tier checks with user-override gate at tier 3

    # else: all_valid — proceed to tier checks directly

    # ── Auto scope-drift between cycles ──
    if cycle < lfgGoal.maxIterations AND lfgGoal.scopeDriftAutoCheck:
      drift = invoke_skill("athanor:scope-drift", target=goal.md)
      if drift.severity == "high":
        record_to_decisions("drift detected: <summary>")
        user_confirm_continue_or_abort()

    # ── Tier 1 mechanical ──
    tier1 = run_tier1_mechanical(goal_id, cycle)
    if not tier1.pass:
      log "tier 1 fail: <signal>"
      continue

    # ── Tier 2 adversarial cross-model ──
    judges = parallel_dispatch(
        ("judge-A", model="claude-opus"),
        ("judge-B", model="codex" if codex.enabled else "claude-sonnet"))

    if not (judges.A.goal_met AND judges.B.goal_met):
      record_to_decisions("tier 2 split: A=<v>, B=<v>")
      if cycle == lfgGoal.maxIterations:
        escalate_to_user_with_both_verdicts()
        break
      continue

    # ── Tier 3 user ratification (BLOCKING — D6) ──
    user_verdict = block_for_user(format_tier3_prompt(cycle, judges))
    if user_verdict == "yes":
      mark_goal_complete(goal_id, cycle)
      write_goal_completion_md(goal_id)
      emit_done_sentinel_through_verification_skill()
      return
    elif user_verdict == "continue-iterating":
      continue
    elif user_verdict == "abort":
      mark_goal_abandoned(goal_id, cycle)
      return

  # ───── Hit max-iter ─────
  emit_durable_residual_exit(reason="max-iterations")
```

**Key invariants:**

- Every `invoke_skill(...)` and `dispatch_worker(...)` starts in **clean
  context** (Thin Leader preserved).
- The leader writes ONLY goal-loop infrastructure files
  (`.athanor/goals/<id>/*` contents that are NOT receipts — receipts
  are validator-authored). No project source.
- Stop hook fires on every Stop event regardless of which skill produced
  it — all 5 companion-fix arc layers (v0.11.3 → v0.11.7) protections
  remain.
- `/athanor:lfg` is **unchanged**. The wrapper does not couple to the
  inner pipeline. Receipt-validator reads what lfg already produces.

## Auto Scope-Drift Between Cycles

Between cycle N completion and cycle N+1 start, the leader auto-dispatches
the existing `/athanor:scope-drift` skill when
`lfgGoal.scopeDriftAutoCheck: true` (default per D12,
decisions.md 2026-05-22-002). The on-demand skill becomes
auto-invoked in the goal-loop context only — the underlying scope-drift
skill itself is unchanged. See `skills/scope-drift/SKILL.md` for the
upstream skill body, intent-source contract, and SELF_REFERENCE_EXCLUDES
list (claude-octopus-vendored, T2 provenance preserved).

**Input contract.** The scope-drift worker receives two inputs:

- **Canonical scope artifact:** `.athanor/goals/<id>/goal.md` ledger
  — the locked G-markers + acceptance criteria define the goal's
  intent surface. This replaces the per-session `plan.md` that
  scope-drift normally consumes from `INTENT_SOURCE_GLOB`; in
  goal-loop context, the goal ledger IS the plan-of-record.
- **Latest work product:** cycle N's
  `.athanor/goals/<id>/receipts/CNNN-lfg-receipt.md` plus the cycle's
  resolved `git diff` (commit SHAs are recorded in the receipt's
  step-2 evidence). The worker compares actual diff against ledger
  intent.

**Decision rubric.** The scope-drift worker returns a severity verdict:

- **low** or **medium** → log the finding to
  `.athanor/goals/<id>/goal-log.md` with summary + diff items flagged,
  continue to cycle N+1 without interruption. Intentional drift
  ("I saw a bug while working on the feature") is normal and recorded
  as audit-trail only.
- **high** → PAUSE the loop. Leader presents the drift summary to
  the user in a BLOCKING ratification prompt (mirrors the Tier 3
  posture per D6); the user must explicitly confirm continue / abort /
  scope-change before cycle N+1 dispatches. NOT autopilot-bypassable
  even if `--auto-ratify-when-tier2-passes` is set — that flag governs
  goal-completion Tier 3, not mid-loop drift escalation.

**Honesty note on enforcement scope.** scope-drift is itself an
advisory skill — it is informational, NOT a runtime gate. The
high-severity pause is enforced by leader prose discipline (this
SKILL.md contract + Thin Leader dispatch protocol), NOT by the Stop
hook or any equivalent runtime hard-enforcement. A misbehaving leader
that suppresses scope-drift findings between cycles is an
adversarial-forgery scenario named in §"Honesty note on physical
enforcement scope" below; runtime hard-enforcement is deferred to
v0.13.x+ per the same residual list. Until then, the layer is honest
about catching mechanical drift (diff items outside ledger markers)
and not catching adversarial suppression (leader skips the dispatch
entirely). Users encountering false positives can set
`lfgGoal.scopeDriftAutoCheck: false` as an escape hatch; the choice
is recorded to `decisions.md` so the loss of posture is auditable,
not silent.

## Configuration Defaults (D8 / D9 / D10)

Baked into `athanor.json` and `templates/athanor.json`:

```json
"lfgGoal": {
  "_doc": "Configuration for /athanor:lfg-goal — goal-driven macro Ralph loop wrapping /athanor:lfg with dispatched receipt validation + adversarial 3-tier goal-completion check. See skills/lfg-goal/SKILL.md.",
  "maxIterations": 5,
  "noProgressThreshold": 2,
  "userConfirmAfter": 3,
  "tier2Adversarial": true,
  "tier3UserRatification": true,
  "scopeDriftAutoCheck": true,
  "consolidateCycles": false,
  "archiveOnComplete": true,
  "goalRetentionDays": 30,
  "goalsDir": ".athanor/goals",
  "dryRun": false
}
```

Confirmed defaults per user dialog (2026-05-22 decisions.md):

- **`maxIterations: 5`** (D8, default 5) — sufficient single-session
  runway; circuit breaker trips at 5; user re-invocation available for
  longer goals.
- **`consolidateCycles: false`** (D9, per-cycle release default) —
  honest history. Each cycle ships its own PR + tag
  (v0.13.0 → v0.13.1 → ...). `consolidateCycles: true` available as
  opt-in for users who prefer condensed release history.
- **Both invocation forms supported** (D10) — inline goal text
  (auto-id) OR `--goal-file <path>` (file-based, explicit).

Other defaults:

- `noProgressThreshold: 2` — two consecutive no-progress cycles trips
  the no-progress circuit breaker.
- `tier2Adversarial: true` — Tier 2 dispatches cross-model judges by
  default (degrades to single-judge with explicit warning when
  `codex.enabled: false`).
- `tier3UserRatification: true` — Tier 3 blocks on user input by
  default (D6). The opt-out `--auto-ratify-when-tier2-passes` flag is
  NOT exposed in the shipped config block; the user must edit the raw
  invocation to bypass.
- `scopeDriftAutoCheck: true` — `/athanor:scope-drift` auto-fires
  between cycles (D12). The on-demand skill becomes auto-invoked in
  the goal-loop context.
- `goalsDir: ".athanor/goals"` — storage location per D7.
- `goalRetentionDays: 30` — cleaner ages out abandoned / blocked /
  max-iter goal directories after 30 days (D13).

## Per-cycle commit / release strategy (D9)

Per D9, each cycle ships its own PR + patch release. Honest history:
v0.13.0 → v0.13.1 → v0.13.2 → ... with one tag per cycle that closes
≥1 G-marker. Version-space inflation is the accepted honesty-arc cost.

- **Default** (`lfgGoal.consolidateCycles: false`, per D9): per-cycle
  PRs, one release tag per cycle. Each cycle's `/athanor:lfg` Step 9
  emits its own DONE sentinel and tag. Goal-completion adds a final
  `goal-completion.md` index pointing at all cycle tags but does NOT
  introduce an extra "goal-complete-only" release.
- **Override** (`lfgGoal.consolidateCycles: true`): all cycles
  accumulate into a single goal-PR; only goal-completion ships a
  release. Available as opt-in for users who prefer condensed release
  history.

`goal-completion.md` indexes all cycle PRs + tags back to the goal
regardless of mode.

## 4 Athanor Identity Invariants — Survival Check

This skill preserves all four v0.10.0 athanor identity commitments
through orchestration over existing primitives. No new identity
invariant is introduced (D11):

1. **Thin Leader** — the lfg-goal leader dispatches receipt-validator,
   judge-A, judge-B, scope-change-critic, and user-block prompts. It
   NEVER authors receipts, judgments, or scope decisions directly.
   The leader only writes goal-loop infrastructure (state file +
   compressed summaries + decisions log + bootstrap goal.md draft
   awaiting user confirmation). Per-cycle receipts are validator-
   authored.
2. **Cross-model adversarial planning** — preserved at two layers:
   (a) each cycle's `/athanor:plan` runs whichever tier its `--depth=`
   selects per the Tier Dispatch Table (`skills/plan/SKILL.md`), with
   `codex.enabled` gating only the in-tier Codex fallback; (b) Tier-2
   goal-check ALSO runs cross-model judge-A (Claude) + judge-B (Codex).
   The goal-loop EXTENDS cross-model adversarial coverage to goal-level
   judgment, not just per-cycle planning.
3. **Spec-then-TDD discipline** — each cycle's `/athanor:work`
   invocation continues to apply Splitter `execution_note`
   classification + conjunction-of-three Phase 3 gate. The goal-loop
   injects goal MUST/SHOULD bullets into Planner A via
   `requirements.md` so the discipline runs against goal-cited
   acceptance criteria.
4. **Stop hook runtime gate** — every Stop event in every cycle
   passes through `scripts/hooks/stop_verify_claims.py` with all 5
   companion-fix arc layers (v0.11.3 input-layer fix + v0.11.4
   plugin-root deployment fix + v0.11.5 documentation honesty
   hardening + v0.11.6 sentinel body-hash binding + v0.11.7 scanner
   extension + Residual reclassification). Goal-completion write
   itself is a material claim and goes through the
   verification-before-completion skill emission.

**NO new identity invariant required** (D11). The four invariants are
sufficient to characterize what athanor is; lfg-goal is an
orchestration layer composed of them.

## Honesty note on physical enforcement scope

The receipt-arithmetic + validator dispatch + 3-tier check are
**advisory / orchestration layers**, NOT runtime gates like the Stop
hook. The Validated Receipt-Ledger Loop achieves trust through
structural enforcement — clean-context worker dispatch + externally-
verifiable Bash commands + blocking user ratification — but it does
NOT physically prevent a misbehaving leader from:

- Skipping `/athanor:lfg` steps and fabricating a receipt entry
  (the validator runs Bash commands against artifacts; if the leader
  forges commit SHAs or PR URLs, the Bash checks would still detect
  the forgery via `git show` / `gh pr view` non-zero exit — but a
  truly adversarial leader that forges artifacts too would defeat
  the layer).
- Falsifying goal-completion by mutating `goal.md` directly before
  Tier 3 ratification.
- Suppressing scope-drift findings between cycles.

These adversarial-forgery scenarios require runtime hard-enforcement
that is deferred to v0.13.x+ (transcript-event introspection + hook-
level evidence ratification). Until then, the layer is honest about
its enforcement posture:

- It makes false completion **externally-detectable** via dispatched
  validation (clean-context worker reading actual artifacts).
- It makes false completion **non-completing** via ledger arithmetic
  (goal.md state transition requires real receipts).
- It does NOT physically prevent the leader from emitting prose that
  *claims* false completion (Stop hook handles that fraction of the
  attack surface; lfg-goal does not duplicate it).

This honest-scope voice mirrors the v0.11.x companion-fix arc
(v0.11.3 → v0.11.7): the mechanism is shipped, the scope is named,
and the residual is recorded as deferred. The label
"advisory (planner-classified)" in CLAUDE.md §Defense Mechanisms
applies analogously to this skill — the receipt-arithmetic is honest
about what it catches (mechanical step-skipping, receipt evidence
shape mismatches) and what it does not (adversarial artifact forgery,
LLM-class semantic forgery). Users encountering false positives can
set `lfgGoal.tier2Adversarial: false` or `lfgGoal.tier3UserRatification:
false` as escape hatches; both choices are recorded to `decisions.md`
so the loss of posture is auditable, not silent.
