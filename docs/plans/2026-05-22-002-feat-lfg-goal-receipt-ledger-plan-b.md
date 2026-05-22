---
title: "Plan B: /athanor:lfg-goal - Receipt-Gated Goal Ledger"
type: feat
status: draft
date: 2026-05-22
depth: deep
origin: user request for alternative-perspective /athanor:lfg-goal plan after v0.12.0 concept absorption pivot
approach: durable goal ledger plus per-cycle nine-step receipt validation
---

# Plan B: /athanor:lfg-goal - Receipt-Gated Goal Ledger

## Goal

Create `/athanor:lfg-goal`, a new athanor-native skill that lets a user state a
larger goal and then advances that goal through repeated `/athanor:lfg` cycles
until the goal is complete.

The non-negotiable design goal is not "add a while loop." It is to make macro
LFG progress auditable. A goal run must leave durable evidence of:

- what the user asked for,
- which acceptance markers define completion,
- which cycle attempted which marker,
- whether every `/athanor:lfg` step actually ran,
- what evidence closed each marker,
- why the process stopped.

This plan directly addresses the known failure mode from this session:
`/athanor:lfg` can be skipped by leader discretion even though
`skills/lfg/SKILL.md:68-70` says all steps are mandatory. `/athanor:lfg-goal`
must not amplify that loophole. It must make skipped LFG steps visible and
non-completing.

## Approach (explain WHY this beats the safe while-loop wrap)

Use a **receipt-gated goal ledger**.

The goal is not an in-memory loop condition. It is a durable artifact under
`.athanor/goals/<goal-id>/goal.md`. The macro process advances a finite set of
acceptance markers and cycle cards recorded in that ledger. Each cycle invokes
the existing `/athanor:lfg` pipeline, but `/athanor:lfg-goal` does not trust
`<promise>DONE</promise>` by itself. It requires a per-cycle receipt proving
that LFG steps 1 through 9 were either completed with artifact references or
explicitly skipped by the rules of `skills/lfg/SKILL.md`.

This beats the obvious while-loop wrap for four reasons:

1. **Completion becomes artifact-based, not model-opinion-based.** A hallucinated
   "the goal is done" cannot close the ledger unless the required acceptance
   marker has evidence.
2. **History is not fragmented into unrelated releases.** Each LFG cycle remains
   a release candidate, but all cycles point back to the same `goal.md`, with
   marker IDs and cycle IDs tying PRs, commits, reviews, and residuals together.
3. **Scope drift is constrained by the ledger.** A new marker cannot silently
   appear mid-loop. It must be recorded as `scope_change: proposed`, reviewed,
   and either accepted into the ledger or rejected as drift.
4. **The existing skipped-step loophole becomes detectable.** The current
   `/athanor:lfg` contract has strong prose gates (`skills/lfg/SKILL.md:80-240`)
   but no durable receipt. `/athanor:lfg-goal` adds a caller-side receipt
   requirement that marks a cycle invalid if Step 1, Step 2, Step 3, or any
   required ship step lacks evidence.

This is closest to alternative 1, "Goal as durable artifact," but with a harder
answer to the user's actual concern: the ledger alone is not enough. It must be
paired with a nine-step receipt that treats LFG's `DONE` sentinel as a signal to
verify, not as proof.

## Goal-completion detection mechanism (deep dive)

### Completion Is a Ledger State Transition

`/athanor:lfg-goal` creates or resumes:

```text
.athanor/goals/<goal-id>/
  goal.md
  cycles/
    C001.md
    C002.md
  receipts/
    C001-lfg-receipt.md
    C002-lfg-receipt.md
  decisions.md
```

`goal.md` is the source of truth. It contains:

```markdown
# Goal: <human title>

goal_id: <YYYY-MM-DD-NNN-slug>
status: active | complete | blocked | abandoned
created_at: <ISO-8601>
source_session: .athanor/sessions/<id>

## User Goal

<verbatim user goal, lightly normalized only for markdown escaping>

## Completion Markers

- [ ] G1: <observable result>
  - evidence_required: <file path, command result, PR state, UI behavior, doc state>
  - source: user | planner | accepted-scope-change
  - closed_by: -
- [ ] G2: ...

## Cycle Queue

- [ ] C001: Close G1 and only G1 unless implementation discovers a dependency.
- [ ] C002: Close G2.

## Scope Changes

| id | proposed_by | summary | status | decision |
|---|---|---|---|---|

## Stop Conditions

- complete_when: all G markers checked and each has evidence.
- invalid_cycle_when: any required LFG step receipt is missing or contradicted.
- blocked_when: same marker fails twice, or CI remains red after the LFG step-8 cap.
```

Completion is only:

```text
status: complete
AND every G marker checked
AND every checked marker has closed_by: Cnnn with evidence refs
AND every closing Cnnn has a valid nine-step LFG receipt
```

There is no free-form "goal check" model judgment. The leader may summarize
progress, but it may not mark completion without ledger evidence.

### Acceptance Markers Are Generated Once, Then Locked

On first invocation, `/athanor:lfg-goal` dispatches `/athanor:plan` in a
goal-decomposition mode. That worker writes the initial `goal.md` marker list
and cycle queue. The plan must produce observable markers, not vague intentions.

Example good marker:

```markdown
- [ ] G1: `/athanor:lfg-goal` appears in the command table and is depth-1
  discoverable at `skills/lfg-goal/SKILL.md`.
  - evidence_required: regression test asserts file exists and `CLAUDE.md`
    command table includes `/athanor:lfg-goal`.
```

Example rejected marker:

```markdown
- [ ] G1: The feature feels robust.
```

After the initial ledger is written, markers are locked. If a cycle discovers
that a missing dependency is necessary, it writes a scope-change proposal. The
leader cannot silently add work to the goal. That protects against macro-loop
scope drift.

### Per-Cycle LFG Receipt Is Mandatory

Every cycle has a receipt:

```markdown
# LFG Receipt: C001

cycle_id: C001
goal_id: <goal-id>
target_markers: [G1]
status: valid | invalid | blocked

## Step Receipts

1. Step 1 - /athanor:plan
   - status: completed
   - evidence: .athanor/sessions/2026-05-22-002/plan.md
   - required_by: skills/lfg/SKILL.md:80-96
2. Step 2 - /athanor:work
   - status: completed
   - evidence: .athanor/sessions/2026-05-22-002/work-log.md
   - required_by: skills/lfg/SKILL.md:98-112
3. Step 3 - /athanor:review
   - status: completed
   - evidence: .athanor/sessions/2026-05-22-002/review-of-branch.md
   - required_by: skills/lfg/SKILL.md:114-133
4. Step 4 - Persist review fixes
   - status: completed | no-op
   - evidence: git status output or commit hash
   - required_by: skills/lfg/SKILL.md:135-148
5. Step 5 - Residual review findings handoff
   - status: skipped-by-rule | completed
   - evidence: review had no actionable findings OR PR/body/fallback file ref
   - required_by: skills/lfg/SKILL.md:150-170
6. Step 6 - Browser test
   - status: skipped-by-rule | completed
   - evidence: no UI files touched OR browser-test artifact
   - required_by: skills/lfg/SKILL.md:172-180
7. Step 7 - Commit, push, open PR
   - status: completed
   - evidence: commit hash + PR URL
   - required_by: skills/lfg/SKILL.md:182-193
8. Step 8 - CI watch and autofix loop
   - status: completed | skipped-by-rule | blocked-after-cap
   - evidence: PR checks output, CI green, or unresolved CI section
   - required_by: skills/lfg/SKILL.md:195-236
9. Step 9 - DONE sentinel
   - status: completed
   - evidence: transcript excerpt or captured final sentinel
   - required_by: skills/lfg/SKILL.md:238-240

## Marker Closure

- G1: closed | not_closed
  - evidence: tests/test_regression_lfg_goal_skill.py::...
```

The receipt has two jobs:

- Catch a leader that jumped from planning to `DONE`.
- Let future invocations resume without rereading the entire transcript.

### Why This Closes the Discretion Loophole

Current `/athanor:lfg` has a mandatory prose protocol but no machine-checkable
cycle ledger. Existing tests check for step anchors and identity-bearing command
references (`tests/test_regression_v011_athanor_lfg_wrapper.py:69-120`), not
runtime proof that all steps ran.

`/athanor:lfg-goal` cannot make Claude Code physically incapable of skipping
steps inside `/athanor:lfg`. But it can close the macro-level loophole:

- A skipped step makes the cycle receipt invalid.
- An invalid cycle cannot close any goal marker.
- A goal with invalid or missing receipts cannot become complete.
- The invalid receipt names the missing step, so the next invocation resumes
  from the failure instead of pretending success.

This deliberately avoids a false guarantee. The design does not claim that the
leader cannot misbehave. It makes misbehavior non-completing and durable.

## Loop architecture

### Not a While Loop; a Ledger State Machine

`/athanor:lfg-goal` runs this state machine:

```text
resolve_goal()
  if no goal exists:
    initialize_goal_ledger()

load_goal()
  if status == complete:
    report completion with evidence refs; stop
  if status == blocked:
    report blocker and recovery choices; stop

select_next_cycle()
  choose first unchecked Cnnn whose dependencies are closed

run_cycle(Cnnn)
  invoke /athanor:lfg with:
    - target marker IDs
    - exact non-goal scope
    - required receipt path
    - instruction that DONE is not sufficient without receipt

validate_receipt(Cnnn)
  if receipt valid and marker evidence present:
    close marker(s), append decision, continue to next open cycle
  if receipt invalid:
    mark Cnnn invalid and stop; do not loop blindly
  if LFG returns blocked after its own caps:
    mark goal blocked and stop

repeat only while:
  - there is an open cycle,
  - the previous cycle produced a valid receipt,
  - no scope-change proposal is pending,
  - maxCycles not exceeded.
```

This still "runs lfg cycles until the goal is reached" in the happy path, but
the loop condition is a durable state transition. If the system hits ambiguity,
scope change, invalid receipt, or blocked CI, it stops with evidence rather than
asking a model whether the goal is done.

### Macro Ralph Loop Semantics

Reuse the Ralph pattern from `/athanor:work`, but change the retry unit.
`skills/work/SKILL.md:391-401` defines a per-subtask retry loop for verification
failures, and `skills/work/SKILL.md:567-604` documents the Phase 3 test-aware
gate with known self-report limits. `/athanor:lfg-goal` applies the same
philosophy at cycle scale:

- `maxCycles`: default 5, read from `athanor.json` as
  `lfgGoal.maxCycles` when present.
- `maxInvalidReceipts`: default 1. If one cycle claims done but lacks required
  step receipts, stop instead of retrying autonomously.
- `maxBlockedCyclesPerMarker`: default 2. If the same marker cannot close after
  two valid cycles, mark `blocked`.
- `consecutiveFailures`: default 2. Invalid receipt, blocked CI, and missing
  marker evidence count as failures.

This is intentionally stricter than the micro Ralph loop. A macro cycle can
commit, push, and open PRs; a blind retry can create real repository churn.

### Relationship to Existing `/athanor:lfg`

`/athanor:lfg-goal` is not a replacement for `/athanor:lfg`.

- `/athanor:lfg` remains the single-cycle release pipeline.
- `/athanor:lfg-goal` is a goal ledger coordinator that repeatedly invokes
  `/athanor:lfg` against one cycle card at a time.
- `/athanor:lfg-goal` owns goal state and receipt validation.
- `/athanor:lfg` owns the actual plan -> work -> review -> ship flow.

This respects the v0.12.0 surface correction. Post-v0.12.0, the vendored
`ce-lfg` directory is gone and users migrate to native `/athanor:lfg`
(`tests/test_regression_v012_no_vendored_surface.py:126-139`). The new skill
builds on the native surface only.

## Phases (Steps with files + MUST/SHOULD Verify)

### Phase 1 - Add Goal Ledger Contract Tests

Files:

- Create: `tests/test_regression_lfg_goal_skill.py`

Implementation notes:

- Test for `skills/lfg-goal/SKILL.md` at depth 1.
- Test frontmatter `name: lfg-goal`, `user-invocable: true`, and allowed tools.
- Test the skill body contains `Receipt-Gated Goal Ledger`.
- Test it names `.athanor/goals/` and `goal.md`.
- Test it requires receipt entries for Step 1 through Step 9.
- Test it says `<promise>DONE</promise>` is insufficient without a valid receipt.

Verify:

- MUST `pytest tests/test_regression_lfg_goal_skill.py -v` fail before the skill
  exists.
- MUST the test assert all nine LFG step receipt labels exist in
  `skills/lfg-goal/SKILL.md`.
- MUST the test reject a body that contains a plain `while goal not met`
  architecture without receipt validation.
- SHOULD the test use regexes tolerant of heading changes but strict about
  required contract phrases.

### Phase 2 - Create `/athanor:lfg-goal` Skill

Files:

- Create: `skills/lfg-goal/SKILL.md`

Skill frontmatter:

```yaml
---
name: lfg-goal
description: >
  Run goal-level Athanor LFG cycles through a durable goal ledger. Creates or
  resumes .athanor/goals/<goal-id>/goal.md, invokes /athanor:lfg for the next
  cycle card, validates a nine-step LFG receipt, and repeats only while ledger
  state advances safely. '/athanor:lfg-goal', 'goal until done', 'run lfg cycles
  until this goal is reached'.
user-invocable: true
allowed-tools: Bash, Read, Write, Skill, Grep, Glob
---
```

Required sections:

- Identity: Thin Leader, no implementation work.
- When to invoke / when not to invoke.
- Goal ledger format.
- Cycle receipt format.
- Protocol:
  1. Resolve or initialize goal.
  2. Lock completion markers.
  3. Select next cycle card.
  4. Invoke `/athanor:lfg`.
  5. Validate nine-step receipt.
  6. Close markers or mark invalid/blocked.
  7. Repeat only on valid ledger advancement.
  8. Emit final summary with goal evidence.
- Identity invariants.
- Honesty note: cannot prevent `/athanor:lfg` from skipping internally, but
  makes skipped steps non-completing.

Verify:

- MUST `skills/lfg-goal/SKILL.md` explicitly states the leader does not code and
  only edits `.athanor/goals/**` infrastructure artifacts directly.
- MUST it invokes `/athanor:lfg` rather than duplicating the 9-step pipeline.
- MUST it treats `skills/lfg/SKILL.md:238-240` DONE sentinel as insufficient
  without Step 1-9 receipt evidence.
- MUST it defines invalid receipt behavior: invalid cycle cannot close markers;
  stop with missing-step report.
- SHOULD it keep the protocol under 250 lines so the skill remains readable.

### Phase 3 - Add Goal Config Schema Support

Files:

- Modify: `athanor.json`
- Modify: `templates/athanor.json`
- Modify: `schemas/athanor-config.schema.json`
- Create: `tests/test_regression_lfg_goal_config.py`

Add optional config:

```json
"lfgGoal": {
  "maxCycles": 5,
  "maxInvalidReceipts": 1,
  "maxBlockedCyclesPerMarker": 2,
  "consecutiveFailures": 2
}
```

Defaults must be documented in `skills/lfg-goal/SKILL.md` so the skill works
when older projects lack the new config block.

Verify:

- MUST schema accepts `lfgGoal.maxCycles`, `maxInvalidReceipts`,
  `maxBlockedCyclesPerMarker`, and `consecutiveFailures` as positive integers.
- MUST repo `athanor.json` and `templates/athanor.json` both validate against
  `schemas/athanor-config.schema.json`.
- MUST absence of `lfgGoal` is valid for backward compatibility.
- SHOULD config docs explain that macro retries are stricter than
  `work.ralphLoop.maxRetries` because each LFG cycle can create commits and PRs.

### Phase 4 - Add Receipt-Aware `/athanor:lfg` Caller Contract

Files:

- Modify: `skills/lfg/SKILL.md`
- Modify: `tests/test_regression_v011_athanor_lfg_wrapper.py`
- Create: `tests/test_regression_lfg_receipt_contract.py`

Do not rewrite `/athanor:lfg` as a goal loop. Add a small caller-contract
section:

- If invoked by `/athanor:lfg-goal`, the caller may pass a receipt path.
- On every step, `/athanor:lfg` must append or instruct the leader to append
  step status to that receipt path.
- Step 9 may emit `<promise>DONE</promise>` only after receipt status is valid
  or after explicitly marking the receipt invalid/blocked.

This is the one place where `/athanor:lfg-goal` closes the loophole at the
source. The caller-side validator is still required, but the callee should be
told to produce the artifact.

Verify:

- MUST `skills/lfg/SKILL.md` contains a `Receipt contract for goal callers`
  section.
- MUST each of Step 1 through Step 9 is mentioned in the receipt contract.
- MUST the contract says missing required receipt entries make the cycle invalid.
- MUST existing lfg wrapper tests still pass.
- SHOULD the new prose be additive and avoid changing the existing
  single-cycle `/athanor:lfg` behavior for normal callers.

### Phase 5 - Document Command Surface and Goal Storage

Files:

- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/CONVENTIONS.md`
- Modify: `docs/STATE.md`
- Modify: `CHANGELOG.md`

Documentation changes:

- Add `/athanor:lfg-goal` to the native command table in `CLAUDE.md`, next to
  `/athanor:lfg`.
- Add `.athanor/goals/{goal-id}/` to the session/storage convention.
- Document that `.athanor/sessions/{id}/` remains cycle-local, while
  `.athanor/goals/{goal-id}/` is goal-level state.
- State that `/athanor:lfg-goal` is not autopilot without checkpoints; it stops
  on invalid receipt, pending scope change, blocked CI, or max cycle cap.

Verify:

- MUST `CLAUDE.md` command table includes `/athanor:lfg-goal`.
- MUST docs distinguish `.athanor/sessions/` from `.athanor/goals/`.
- MUST docs preserve all four identity invariants already listed for Athanor:
  Thin Leader, cross-model adversarial planning, Spec-then-TDD discipline, and
  Stop hook runtime gate.
- SHOULD `CHANGELOG.md` include the honesty note that this feature adds a
  receipt gate because `/athanor:lfg` step order was previously prose-enforced.

### Phase 6 - Add End-to-End Text Fixture Tests

Files:

- Create: `tests/fixtures/lfg_goal/valid_goal.md`
- Create: `tests/fixtures/lfg_goal/valid_receipt.md`
- Create: `tests/fixtures/lfg_goal/invalid_missing_step_3_receipt.md`
- Create: `tests/test_regression_lfg_goal_receipt_fixtures.py`

These are not runtime parser tests unless a parser is introduced. They are
contract fixtures that keep the skill's documented formats concrete.

Verify:

- MUST valid fixture includes every Step 1-9 receipt.
- MUST invalid fixture omits Step 3 and is named accordingly.
- MUST tests assert `skills/lfg-goal/SKILL.md` references the fixture shape or
  embeds an equivalent example.
- SHOULD tests stay string/regex-based unless a real parser is added. Do not
  invent a parser only to test prose.

### Phase 7 - Release Readiness

Files:

- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `CHANGELOG.md`
- Modify: `docs/STATE.md`

If this ships as v0.12.1 or v0.13.0, bump the version consistently. The plan
does not choose the release number; the maintainer should choose based on
whether it is treated as a minor feature or a major orchestration addition.

Verify:

- MUST `python3 scripts/check_release_ready.py` exits 0.
- MUST `pytest tests/test_regression_lfg_goal_skill.py tests/test_regression_lfg_receipt_contract.py tests/test_regression_lfg_goal_config.py -v` exits 0.
- MUST full `pytest tests/` exits 0 before release.
- SHOULD manually invoke `/athanor:lfg-goal` on a doc-only toy goal in a scratch
  repo and verify it creates `.athanor/goals/<goal-id>/goal.md` and refuses to
  mark completion when a receipt is incomplete.

## Risks (>= 6 with mitigations)

1. **Risk: Receipt validation becomes another prose promise.**
   Mitigation: add regression tests that scan `skills/lfg-goal/SKILL.md` and
   `skills/lfg/SKILL.md` for all nine required receipt entries. Keep fixtures
   concrete. Do not claim runtime enforcement beyond what exists.

2. **Risk: `/athanor:lfg` still skips steps internally.**
   Mitigation: `/athanor:lfg-goal` treats missing receipts as invalid and
   non-closing. Add the receipt contract to `/athanor:lfg` so the callee is
   prompted to produce evidence, then validate from the caller side.

3. **Risk: Goal marker generation is hallucination-prone.**
   Mitigation: markers must be observable and evidence-backed. Vague markers
   are rejected during ledger initialization. Scope changes require explicit
   ledger entries instead of silent mutation.

4. **Risk: Multiple cycles create branch or PR clutter.**
   Mitigation: each cycle targets one marker or a declared marker group.
   Macro caps are low by default. A blocked cycle stops instead of blindly
   retrying.

5. **Risk: The ledger duplicates session state and confuses users.**
   Mitigation: document the separation: `.athanor/sessions/` is one pipeline
   run; `.athanor/goals/` is cross-cycle state. Receipts reference session
   artifacts rather than copying them.

6. **Risk: The design violates Thin Leader by writing files.**
   Mitigation: classify `.athanor/goals/**` writes as infrastructure/session
   artifact writes, analogous to the documented session-file exception in
   `CLAUDE.md:11-14`. The leader still must not edit project source files or
   implement code directly.

7. **Risk: Acceptance tests become too synthetic.**
   Mitigation: use regression tests for skill contract shape and one manual
   scratch invocation before release. Do not overbuild a parser unless the
   skill actually consumes machine-readable files.

8. **Risk: User expects true autopilot, but the design stops on invalid receipt
   or pending scope change.**
   Mitigation: be explicit in the skill description and docs. This is
   autonomous while state advances safely, not autonomous through ambiguity.

9. **Risk: Stop hook gives a false sense of completion safety.**
   Mitigation: document that the Stop hook only gates material claims at Stop
   time. It does not validate every LFG step. The receipt ledger is the
   goal-specific gate.

10. **Risk: Post-v0.12.0 concept absorption makes adding another command feel
    like surface creep.**
    Mitigation: justify `/athanor:lfg-goal` as a native orchestration command
    that composes existing native identity commands. It does not reintroduce
    CE or superpowers command surfaces.

## Why This Alternative?

The obvious while-loop plan fails exactly where this feature matters most:
trust. It says "run LFG, ask if goal is done, repeat." That puts the weakest
part of the system, leader discretion, in charge of the most consequential
decision.

This alternative moves trust to artifacts:

- Goal intent is durable.
- Completion markers are durable.
- Scope changes are durable.
- Per-cycle LFG step evidence is durable.
- Invalid cycles are durable.

It also fits Athanor's identity better than a generic loop:

- **Thin Leader survives.** The leader orchestrates, creates infrastructure
  artifacts, invokes skills, and validates receipts. It does not code.
- **Cross-model adversarial planning survives.** Initial marker decomposition
  and every cycle's plan step still route through `/athanor:plan`, whose
  identity is declared in `skills/plan/SKILL.md:14-17` and whose tier table is
  in `skills/plan/SKILL.md:168-179`.
- **Spec-then-TDD survives.** Cycle implementation still goes through
  `/athanor:work`, including Splitter `execution_note` classification and the
  Phase 3 gate described in `skills/work/SKILL.md:271-287` and
  `skills/work/SKILL.md:567-604`.
- **Stop hook runtime gate survives.** Every Stop event still passes through
  the command hook registered in `hooks/hooks.json:1-13`, with the script's
  material-claim gate documented in `scripts/hooks/stop_verify_claims.py:5-31`.

The design is adversarial toward `/athanor:lfg` itself. It does not assume the
single-cycle pipeline obeyed its own mandatory prose. It demands receipts. That
is the difference between "wrap the pipeline" and "make a goal-level controller
that can survive an untrusted cycle result."

## Estimated Scope

Estimated implementation size:

- New skill: `skills/lfg-goal/SKILL.md`, about 180-250 lines.
- Tests: 3-4 new regression files, about 250-450 lines total.
- Config/schema/docs: 5-7 modified files.
- Optional fixtures: 3 markdown fixtures.

Estimated engineering time:

- 0.5 day for skill + tests if kept prose-contract-only.
- 1 day including schema, docs, fixtures, and release readiness.
- 2+ days only if a real parser/validator is introduced. This plan recommends
  avoiding that unless the first prose-contract version proves insufficient.

Recommended release shape:

- Ship as one focused feature PR.
- Do not combine with unrelated v0.12.0 cleanup.
- Treat it as v0.12.1 if the current release line accepts new native commands;
  otherwise hold for v0.13.0.
