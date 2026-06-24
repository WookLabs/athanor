---
name: lfg
description: >
  Run the full autonomous engineering pipeline end-to-end through
  athanor-native commands at identity-bearing steps (cross-model
  adversarial planner / Spec-then-TDD work / parallel multi-lens review),
  then commit, push, open PR, watch CI until green. athanor stands alone:
  no compound-engineering plugin required.
  '진행해', '전체 파이프라인', '배포해', '커밋 푸시 PR', 'ship this',
  'release this end-to-end', '/athanor:lfg', 'athanor lfg'.
user-invocable: true
allowed-tools: Bash, Read, Write, Task, Skill
---

# /athanor:lfg — Athanor-native LFG Pipeline

## Identity

You are the Athanor LFG leader. You orchestrate the full ship pipeline by
dispatching to athanor-native commands at the identity-bearing steps and
reusing vendored CE step shape for the non-identity-bearing steps. You
follow the **Thin Leader** pattern: you parse, dispatch, and verify — you
do NOT write code or run tests directly. See CLAUDE.md §"Concept
Absorption Surface" identity commitment #1.

This is the athanor-native end-to-end pipeline. It is invoked when the
user says "진행해", "ship this", "release this", "/athanor:lfg" — i.e.,
hands-off execution of a software task where the user provides a feature
description or names an in-progress branch.

### using-superpowers boundary

See CLAUDE.md §"using-superpowers boundary (v0.11.1) — canonical declaration" for the canonical text.

## When NOT to invoke

- For casual conversation or exploratory questions — use `/athanor:discuss`
  instead.
- For one-off planning without execution — use `/athanor:plan`
  (optionally `--depth=lite`) directly.
- For one-off review without commit/push/PR — use `/athanor:review`
  directly.

## Historical note (post-v0.12.0)

`/athanor:ce-lfg` was vendored from compound-engineering v3.8.3 in v0.10.0
and removed in the v0.12.0 atomic cut. `/athanor:lfg` is the sole
end-to-end pipeline. Users wanting CE's single-agent LFG flow should
install the upstream compound-engineering plugin directly. See
`docs/v0.12.0-migration.md` for the migration path.

---

## Protocol

CRITICAL: You MUST execute every step below IN ORDER. Do NOT skip any
required step. Do NOT jump ahead to coding or implementation. The plan
phase (step 1) MUST be completed and verified BEFORE any work begins.
Violating this order produces bad output.

When invoking any skill referenced below, resolve its name against the
available-skills list the host platform provides and use that exact
entry. Some platforms list skills under a plugin namespace (e.g.,
`compound-engineering:ce-test-browser`); others list the bare name.
Invoking a short-form guess that isn't in the list will fail — always
match a listed entry verbatim before calling the Skill/Task tool.

### P13 Live Trace Emission: `scripts/evals/emit_workflow_trace.py` emits `workflow.started` and `workflow.finished`; see `docs/workflow-trace-evals.md`.

### v0.18.0 honesty residual — Codex stage NOT freeze-gated

If the user has enabled `athanor.json` `hooks.freeze.mode = "session"`,
the v0.18.0 Freeze guard gates Claude file-tool writes (Edit / Write /
MultiEdit + conservative Bash patterns) against the per-session
allowlist. **Codex subprocess writes invoked during this LFG run
(`/athanor:plan` Step 1 Codex dispatches, any `codex exec ...` worker
calls) are NOT gated by Freeze** — those writes happen inside a
subprocess whose destination paths are not visible to the PreToolUse
dispatcher. This is the documented D2 residual; see
`skills/work/references/freeze.md` §"D2 residual — subprocess writes
NOT gated" and `docs/v0.18.0-migration.md` §"D2 Honesty Residual".

The leader does not warn the user about this on every invocation
(noise); the residual is documented in CHANGELOG, ROADMAP, and the
migration guide. LFG users with strong scope-lock requirements should
be aware that Codex stage writes are on the honour system within this
release line.

### P26 Organization Operating Model Overlay

Before Step 1, align the run with `docs/organization-operating-model.md`.
The LFG leader routes the existing 9-step pipeline through that P26
office/stage graph: intake, requirements, research, planning,
design-review, execution, verification, release, postmortem, and
memory-update. This overlay does not add a default live listener,
registered agents, or external telemetry; it clarifies accountable
owner roles and keeps the existing receipt obligations explicit.

When a run needs an organization-stage handoff artifact, use
`scripts/gates/organization_stage_receipt.py` after the relevant LFG evidence
exists. Preview without writes by omitting `--emit`; write only with `--emit`,
and update a work item only with `--apply-work-item-update`.

When a postmortem lesson should become operating policy or a gate, record it in
`docs/policy-promotions/*.json` and validate it with
`scripts/gates/policy_promotion_ledger.py` before treating it as policy.

### Step 1 — Invoke `/athanor:plan` (cross-model adversarial)

Invoke the `/athanor:plan` skill with the user's feature description.

`/athanor:plan` runs the tiered planning pipeline — Standard (single
Planner A Claude + Codex review) or Deep (Planner A Claude + Planner B
Codex + cross-review + Critic synthesis). The tier is decided inside
`/athanor:plan` based on user signals; LFG callers do not override the
tier choice.

**GATE: STOP.** Verify that the `/athanor:plan` workflow produced
`.athanor/sessions/<id>/plan.md`. If no plan file was created, re-invoke
`/athanor:plan` with the same description. Do NOT proceed to step 2
until a written plan exists. **Record the plan file path** — it will
be passed to step 3 (review) if the review skill accepts a plan
reference.

### Step 2 — Invoke `/athanor:work --team` (Spec-then-TDD)

Invoke the `/athanor:work --team` skill.

v0.15.1: LFG defaults to team mode (`--team`) because most plans produce
subtasks with parallelizable dependency graphs. Users may override with
`--solo` if sequential execution is preferred.

`/athanor:work` applies athanor v0.8.0 Spec-then-TDD discipline:
Splitter Step 0.5 classifies each subtask as `execution_note:
spec-then-tdd | test-aware | direct` and the executor follows the
red-first 5-step flow per classification. The conjunction-of-three
Phase 3 gate (tests touched + full_suite_passed self-report +
verification line consistency) prevents subtle test-bypass. See
CLAUDE.md §"Spec-then-TDD Discipline" for mechanism details.

**GATE: STOP.** Verify that implementation work was performed — files
were created or modified beyond the plan. Do NOT proceed to step 3 if
no code changes were made.

### Step 3 — Invoke `/athanor:review` (parallel multi-lens)

Invoke the `/athanor:review` skill against the current branch.

`/athanor:review` dispatches parallel reviewer workers across the
default 6 lenses configured in `athanor.json` `review.lenses`
(architecture, quality, security, performance, testing, documentation;
file-type filtering may narrow this). Each lens produces findings
above the `review.minConfidence` threshold (default 25). The Leader
consolidates findings and surfaces blockers + recommendations.

If `/athanor:review` surfaces merge-blocker findings, the LFG leader
re-dispatches `/athanor:work` with a focused subtask scoped to the merge-blocker findings.
Iterate up to **3 fix rounds** (the iteration limit is prose guidance
for the leader; there is no programmatic counter enforced by the Stop
hook or any runtime gate), then stop and proceed to step 4 with any
unresolved blockers recorded.

`/athanor:review` does NOT auto-apply fixes (athanor identity choice).
Users wanting CE's autofix behavior should install the upstream
compound-engineering plugin — see §"Historical note (post-v0.12.0)".

### Step 4 — Persist review fixes (REQUIRED after step 3, before residual handoff)

Check `git status --short`. If review-driven fixes changed files in
step 3, stage only those files, commit them with `fix(review): apply
review feedback`, and push the current branch before continuing.

If an upstream exists, run `git push`. If no upstream exists, resolve
a writable remote dynamically: prefer `origin` when present, otherwise
use `git remote` and choose the first configured remote. Then run
`git push --set-upstream <remote> HEAD`.

If `git remote` returns no remotes, skip the push and note: "No remote
configured — review fixes committed locally only. Push manually when a
remote is available."

Do not proceed to step 5, run browser tests, or output DONE while review
fix edits remain only in the working tree. If no files changed,
explicitly note that there were no review fixes to persist.

### Step 5 — Residual review findings handoff

(Skip when step 3 reported no actionable findings.)

If `/athanor:review` reported unresolved blocker or recommendation
findings, record them durably:

1. Compose a `## Residual Review Findings` markdown section listing
   each finding with severity, file:line, title, and recommendation.
2. Detect the current branch's open PR without prompting:
   ```bash
   gh pr view --json number,url,body,state
   ```
3. If an open PR exists, append the section to the PR body via
   `gh pr edit PR_NUMBER --body-file BODY_FILE`.
4. If no open PR exists yet, create a fallback file at
   `docs/residual-review-findings/<branch-or-head-sha>.md` containing
   the composed section. Stage only that file, commit it with
   `docs(review): record residual review findings`, and push.

Never block DONE on residuals once they are durably recorded.

### Step 6 — Browser test (optional)

If the branch touches UI surfaces (`*.tsx`, `*.html`, `*.css`,
`templates/*.html`, etc.), invoke `ce-test-browser` (vendored CE skill)
with `mode:pipeline`. Otherwise skip this step.

The browser test is vendored CE-tooling; athanor does not maintain a
native browser-test runner. (`/athanor:ce-test-browser` is the same
skill via athanor namespace if the user prefers.)

### Step 7 — Commit, push, open PR

Commit any remaining changes, push the branch, and open a pull request.
If step 5 already opened a PR (check with `gh pr view --json
number,url,state 2>/dev/null`), skip PR creation but still commit and
push any uncommitted changes.

Use a value-first PR title and a description that summarizes:
- What changed (high-level — link to the plan file from step 1)
- Why it changed (problem frame from plan)
- Work summary (subtask counts — completed / failed / skipped — from
  `.athanor/sessions/<id>/work-log.md`; the session tree is gitignored, so
  the PR body is how the work record survives in git)
- Review summary (per-lens scores + any residual findings from
  `.athanor/sessions/<id>/review.md`)
- Test plan (verification steps)
- Migration / breaking-change notes (if any)

If `git push` fails (non-zero exit), diagnose the error (authentication,
diverged history, protected branch). Report the push failure as a residual
finding and proceed to Step 8 only if a PR was already opened by a prior
step. If no PR exists and push failed, skip Steps 8-9 and emit the failure
as the pipeline outcome.

> **v0.14.0:** The `athanor-releaser` agent (`agents/releaser.md`) can automate
> the version bump + CHANGELOG + STATE rotation ceremony. Invoke via worker
> dispatch when the release involves mechanical version bumps.

### Step 8 — CI watch and autofix loop

(Only when an open PR exists for the current branch.)

Detect the PR; if none exists or `gh` is unavailable, skip this step
entirely and proceed to step 9.

```bash
gh pr view --json number,url,state
```

For up to **3 fix iterations** (the iteration limit is prose guidance
for the leader; there is no programmatic counter enforced by the Stop
hook or any runtime gate), repeat:

1. Wait for CI to complete:
   ```bash
   timeout 600s gh pr checks --watch
   ```
   If the command exits 0, all checks passed. Break out of the loop and
   proceed to step 9.
   If the `timeout` wrapper expires (exit 124), treat the cycle as
   CI-still-pending and continue to step (2) failure handling. The shell
   `timeout` command wraps the unbounded `--watch` flag; `gh pr checks`
   itself has no native `--timeout` flag.
   If it exits non-zero, one or more checks failed. Continue to (2).
2. Identify failing checks and pull failure logs:
   ```bash
   BRANCH=$(git branch --show-current)
   run_id=$(gh run list --branch "$BRANCH" --status failure --limit 1 \
     --json databaseId --jq '.[0].databaseId')
   if [ -n "$run_id" ]; then
     gh run view "$run_id" --log-failed
   else
     echo "No failed run found for branch $BRANCH"
   fi
   ```
3. Dispatch a worker (via `athanor-ci-watcher` agent or `/athanor:work` focused subtask)
   with the failure logs as context. The worker identifies root cause and applies
   the fix. Do NOT weaken, skip, or mock the failing assertion — repair the actual
   issue. If the failure is a flaky test with no fix path, the worker documents it
   as a residual outcome.
4. After the worker completes, verify files were changed, then stage, commit, push:
   ```bash
   git add <changed-files>
   git commit -m "fix(ci): <one-line summary of the failure repaired>"
   git push
   ```
5. Return to iteration (1) with the next attempt counter.

**GATE: STOP** iterating after 3 failed attempts. If CI is still red
after 3 fix cycles, compose a `## CI Failures Unresolved` markdown
section in the PR body and proceed to step 9. The autopilot contract is
"make residuals durable, then exit."

> **v0.14.0:** The `athanor-ci-watcher` agent (`agents/ci-watcher.md`)
> encapsulates this CI watch + autofix loop. **v0.15.0:** Worker dispatch
> (item 3 above) is now the canonical form — the leader MUST NOT apply
> fixes directly (Thin Leader contract).

### Step 8.5 — Merge-readiness gate + optional merge

(Runs after Step 8 reports CI green, before the Step 9 sentinel.)

**Honesty label: advisory (leader-prose-enforced).** This gate is leader
prose-driven git/gh plumbing, the same enforcement class as the Step 5/7/8
lfg steps — there is **no PreToolUse/Stop runtime hook** that programmatically
prevents the merge or enforces the conjunction. It is **advisory**, NOT
enforced (cf. the Step 3/Step 8 iteration limits: "prose guidance for the
leader; no programmatic counter"). The §Defense Mechanisms "lfg merge-readiness
gate" row carries the same advisory scope and is deliberately kept distinct
from the **enforced** Stop-hook row.

This step runs inside the documented Thin-Leader lfg git/gh plumbing exception
(CLAUDE.md §Core Principle). It does exactly two things on success — `gh pr
merge --rebase` + `--delete-branch` (best-effort). It **never** version-bumps,
git-tags, or edits CHANGELOG/STATE.md — that stays the `athanor-releaser`
ceremony (`agents/releaser.md`). See §"Post-merge boundary" below.

#### Opt-out resolution (merge is ON by default)

`/athanor:lfg` auto-merges a green PR by default, but still only through the
fail-loud conjunctive readiness gate below — merging to a base branch is
consequential and effectively irreversible, so disabling it stays a one-flag
**opt-out**. Resolution precedence (the fail-safe *disable* direction wins ties):

1. `--unmerge` invocation flag (**highest precedence**) → **hard-disables** the
   merge even when config enables it — the fail-safe direction wins ties.
2. else `--merge` invocation flag → explicitly **enables**, overriding a config
   that is `false`.
3. else `athanor.json` `lfg.autoMerge` (boolean, **default `true`**).
4. else **on**.

If merge is **disabled** (`--unmerge`, or `lfg.autoMerge: false` with no
`--merge`), Step 8.5 is a **no-op** that records `merge: skipped-merge-disabled`
and proceeds to Step 9. Do not run the gate.

#### The merge-readiness gate (ordered conjunction, fail-loud)

Merge proceeds **iff ALL** clauses G1–G5 hold (after the G0 entry check). The
word **ALL** governs the conjunction: the merge action is reachable **iff every
clause passes**. Evaluate clauses **top-to-bottom, fail-fast**; on the first
FAIL, do NOT merge, leave the PR open, and report **that first failing clause**.
Each clause emits a one-line `PASS`/`FAIL` trace. `mergeStateStatus` (G4) is the
**single source of truth** for "is GitHub's merge machine happy"; no second
authority votes against it.

**G0 — Entry / re-entry state (runs FIRST, before the conjunction).** Resolve
the PR once, sharing Step 8's exact `2>/dev/null` skip guard:
```bash
gh pr view --json number,url,state,isDraft,mergeable,mergeStateStatus,headRefName,baseRefName 2>/dev/null
```
- `gh` unavailable / unauthenticated / no PR for the branch (command non-zero or
  empty) → `merge: skipped-no-pr` (the same clean skip as Step 8, NOT an
  unhandled error). Do NOT run the conjunction.
- `state == "MERGED"` → `merge: already-merged` (+ the merged SHA if resolvable).
  Report **merged — NEVER `blocked-by-gate`**. This is the most likely re-run
  outcome after a mid-merge crash (merge succeeded server-side, the leader died
  before writing the result packet). Do NOT run the conjunction.
- `state == "CLOSED"` (closed un-merged) → `merge: skipped-pr-closed`. Do NOT
  run the conjunction.
- `headRefName == baseRefName` (head == base — misconfigured same-branch PR, or
  the pipeline ran directly on the default branch) → `merge:
  skipped-head-equals-base`. Nothing to merge; skip cleanly, never attempt the
  merge. Do NOT run the conjunction.
- Else `state == "OPEN"` with distinct head/base → proceed to G1.

**G1 — Draft check.** `isDraft == false`. `isDraft` is the **authoritative,
primary** draft signal (self-documenting in the FAIL trace, and decoupled from
the merge-state machine, which can momentarily report `UNKNOWN` while a PR is
still a draft). `isDraft == true` → `FAIL` ("PR is a draft"). This is a distinct
clause from the `DRAFT` row in G4 — `isDraft` is primary, `mergeStateStatus ==
DRAFT` is the backstop.

**G2 — No review merge-blockers (BOTH sources).** Step 5 records residual review
findings in **one of two places**: appended to the **PR body**
(`## Residual Review Findings`) when a PR existed, OR written to the **fallback
file** `docs/residual-review-findings/<branch-or-head-sha>.md` when no PR existed
yet at Step 5 time. The gate **MUST check BOTH**; a blocker in *either* location
→ `FAIL`. Parse for a **structured machine token**, not freeform prose: a line
matching `^[-*] *severity: *blocker` (case-insensitive) within a
`## Residual Review Findings` section (PR body) **or** in the fallback file.
```bash
# (a) PR body
BODY=$(gh pr view "$PR" --json body --jq .body)
# (b) fallback file (may or may not exist)
BRANCH=$(git branch --show-current)
HEADSHA=$(git rev-parse HEAD)
FALLBACK1="docs/residual-review-findings/${BRANCH}.md"
FALLBACK2="docs/residual-review-findings/${HEADSHA}.md"
# FAIL iff (BODY in a Residual Review Findings section) OR (either fallback file)
#   contains a line matching ^[-*] *severity: *blocker  (case-insensitive)
```
A recommendation line that merely *mentions* the word "blocker" in prose is NOT
a `^severity: blocker` line and does not false-FAIL. A blocker present only in
the fallback file FAILs the gate even though the PR body has no such section
(this closes the body-only false-PASS hole).

**G3 — No unresolved-CI section.** The PR body contains **no
`## CI Failures Unresolved`** header (Step 8 writes that header only when it
exhausted 3 fix cycles still-red). Present → `FAIL`.

**G4 — GitHub merge-state disposition (the safety crux, single authority).**
Using the G0-resolved `mergeable` + `mergeStateStatus`, apply the **exhaustive
disposition tables below**.

`mergeable` field (`MERGEABLE | CONFLICTING | UNKNOWN`, or JSON `null`
immediately post-push):

| `mergeable` | Disposition |
|---|---|
| `MERGEABLE` | continue to the `mergeStateStatus` table |
| `CONFLICTING` | **BLOCK** — `merge: blocked-by-gate` clause G4 (conflicts with base; resolve manually) |
| `UNKNOWN` or `null` | **RE-POLL** (see below); GitHub is still computing mergeability async post-push |

`mergeStateStatus` field — **EXHAUSTIVE disposition (all 8 GitHub enum
values)**. `CLEAN` is the **only** MERGE-OK state:

| `mergeStateStatus` | Verdict | Action / FAIL trace |
|---|---|---|
| `CLEAN` | **MERGE-OK** | proceed to G5 then merge |
| `UNKNOWN` | **RE-POLL** | transient; re-poll per the budget below, then BLOCK on exhaustion |
| `BEHIND` | **BLOCK** | "PR base is behind; merge would integrate against a stale base — rebase/update the branch, then re-run." (Conservative; see the stale-CI caveat.) |
| `BLOCKED` | **BLOCK** | "merge blocked by branch protection / required reviews / required status checks — human approval required; merge manually after approval." (Never `--admin`.) |
| `DIRTY` | **BLOCK** | "merge conflict with base — resolve manually." |
| `DRAFT` | **BLOCK** | "PR is a draft (mergeStateStatus=DRAFT)." (G1's `isDraft` is the primary signal; this is the backstop.) |
| `HAS_HOOKS` | **BLOCK** | "a pre-receive/server hook is configured; merge may be rejected mid-flight server-side — merge manually so a hook rejection is visible to a human." Do not attempt a merge a server hook may reject. |
| `UNSTABLE` | **BLOCK** | "a non-required check is failing or pending (required checks are green, but `mergeStateStatus` is not CLEAN) — merge manually or wait for the optional check." |

**G1/G4 overlap resolution (single authority, no contradiction).**
`mergeStateStatus` (G4) is the **single authority** for check/merge readiness.
An optional `gh pr checks` CI re-check is **demoted to a cheap diagnostic
pre-check** that only informs the FAIL trace — it does **not** vote
independently. If `gh pr checks` shows red, report "CI red" early (friendlier
than a bare `UNSTABLE`/`BLOCKED`), but the **binding verdict is always G4's
`mergeStateStatus`**. This removes the latent "pre-check PASS but G4 FAIL, why
won't it merge?" contradiction — one authority cannot disagree with itself.
**`UNSTABLE` is NOT mergeable in v1** (conservative): required checks may be
green, but a non-required check is failing/pending, so BLOCK *with the
explanatory trace* above (auto-merging on `UNSTABLE` — "required-green is
enough" — is an explicit possible future opt-in, out of scope for v1).

**G4 re-poll (bounded, async-mergeability transient).** The transient that needs
re-polling is **`mergeable ∈ {UNKNOWN, null}`** (the field GitHub computes
asynchronously after a push — a freshly-pushed PR reports `mergeable: null`
until GitHub schedules the check) **OR** `mergeStateStatus == UNKNOWN`. Re-poll
while either holds: **up to 3 attempts × ~5s wait** between polls (re-run the G0
`gh pr view` query each attempt). On **exhaustion** (still `mergeable ∈ {UNKNOWN,
null}` or `mergeStateStatus == UNKNOWN` after 3×5s) → `merge: blocked-by-gate`
clause G4, trace "GitHub mergeability did not settle after 3×5s — do not merge;
re-run later." **Exhaustion is BLOCK, never merge.** `CONFLICTING` and all
non-`CLEAN` *settled* states do NOT re-poll — they go straight to BLOCK per the
G4 table (re-polling a settled conflict is pointless).

**G5 — Merge-queue detection (do not fight the queue).** Detection is fail-loud
**at merge time**: attempt the merge (below) and if `gh pr merge` exits non-zero
with output citing a required merge queue (e.g. matches `merge queue` /
`required.*queue`, case-insensitive), classify as `merge: blocked-merge-queue` —
leave the PR open, instruct manual enqueue (`gh pr merge --auto` / the repo's
queue UI), and **never** `--admin` past it. Merge-queue auto-enqueue from lfg is
out of scope for v1; the queue is **detected and respected**, not silently
fought.

#### Merge command (only when G1–G5 all PASS)

Repo live convention is rebase, so:
```bash
gh pr merge "$PR" --rebase --delete-branch
```
We hardcode `--rebase` (a configurable `lfg.mergeMethod` is out of scope for v1).
`delete_branch_on_merge` is `false` at the repo level, so `--delete-branch` is
passed explicitly for autopilot hygiene.

**Branch-delete is best-effort.** If `--delete-branch` fails (branch is a base
of another open PR, deletion restricted) the **merge already succeeded** — treat
the delete failure as a **non-fatal post-merge note**: report `merge: merged`
with `branch-deleted: no`, **never** as a merge failure.

#### Never bypass branch protection

The merge **MUST NOT** bypass branch protection or required human approvals:
**no `--admin`**, no `gh api ... merge` force path, no protection-rule mutation.
If protection blocks the merge (`mergeStateStatus == BLOCKED`, or `gh pr merge`
exits non-zero citing protection / pending approvals), this is **"leave PR open
+ report", NOT a pipeline error to force past**. We rely on GitHub's own
`BLOCKED` state as the source of truth (we do NOT probe
`branches/<base>/protection`). Report: "PR #N left open — merge blocked by branch
protection / required approvals (mergeStateStatus=BLOCKED). Human approval
required; merge manually after approval."

#### Stale-CI honest caveat (documented residual)

v1 trusts GitHub's `CLEAN`. A PR can be `CLEAN`+`MERGEABLE` with green CI that
**ran against an older base commit** when the repo does **not** require
up-to-date branches (the common default); GitHub reports `CLEAN` (not `BEHIND`)
in that configuration, and we do NOT re-run CI against the merged result. So **if
the repo does not enable branch-protection "require branches to be up to date", a
green-but-stale-base merge is possible** — enable that setting for full safety. A
stricter "require up-to-date / rebase-and-wait" mode is explicit out-of-scope
(it re-introduces a CI wait loop). This residual is surfaced honestly, not
silently swallowed.

#### Post-merge boundary vs releaser

lfg-merge merges (+ best-effort branch delete) **only**. It does **NOT**
version-bump, git-tag, edit CHANGELOG/STATE.md, or run `check_release_ready.py` —
the `athanor-releaser` agent (`agents/releaser.md`) owns the version bump +
CHANGELOG prepend + STATE.md rotation + test-pin updates + readiness check.
Merging a feature PR ≠ cutting a release. Merging a feature PR that added a
`## [Unreleased]` CHANGELOG entry leaves that entry on the base branch
**un-tagged**, which is expected ("Unreleased" means exactly that); auto-merge
deliberately leaves `[Unreleased]` accumulation for the **next releaser pass** to
reconcile — it is not lfg-merge's job to roll it.

#### Result outcome

Record exactly one `merge:` outcome line for Step 9 (see the Step 9 result
packet for the full 8-state list). Whatever the outcome — merged, blocked, or
any skip — proceed to Step 9 and emit `<promise>DONE</promise>`: a
gated/blocked/already-done merge is a **normal terminal outcome, not a pipeline
failure**. Keep the `merge:` key and the `G1..G5` clause IDs in English (like
`## Residual Review Findings` / `## CI Failures Unresolved` / `GATE: STOP`); only
the user-facing explanation prose follows the resolved `output.language`.

### Step 9 — Output `<promise>DONE</promise>` when complete

Emit the result packet (below), then the completion sentinel, so caller
workflows can detect end-of-pipeline. `<promise>DONE</promise>` fires in **every**
terminal case (merged, blocked, or any skip) — a gated/blocked/already-done
merge is a normal terminal outcome, not a pipeline failure.

**Result packet (machine-parsable).** Emit a `merge:` outcome line carrying
exactly one of these 8 states (the `merge:` key and the values stay English):

```
merge: <one of>
  merged                   # merged successfully (+ merged SHA + branch-deleted: yes|no)
  already-merged           # G0 re-entry found state == MERGED (honest merged report, never blocked)
  blocked-by-gate          # a G1..G5 clause failed (+ failing clause + one-line reason)
  blocked-merge-queue      # repo uses a merge queue; left for the queue/human (G5)
  skipped-merge-disabled   # merge disabled (--unmerge, or lfg.autoMerge=false with no --merge)
  skipped-no-pr            # no open PR / gh unavailable (shares Step 8's skip guard)
  skipped-pr-closed        # G0 found state == CLOSED (closed un-merged)
  skipped-head-equals-base # headRefName == baseRefName; nothing to merge
<promise>DONE</promise>
```

The `merge:` key, the 8 state tokens, and the `G1..G5` clause IDs are
machine-parsed and **stay English** — only the user-facing explanation prose
follows the resolved language.

Language directive (best-effort advisory): 단계·최종 보고는 해석된
`output.language`에 맞춘다; 커밋 메시지/PR 본문/센티널/GATE 키워드는 영어;
완료-주장 어조(`완료했습니다`) 회피 — 사실 서술 사용. The DONE 센티널 above,
the `merge:` result line + `G1..G5` clause IDs, the `fix(review):` /
`fix(ci):` commit templates, the `## Residual Review Findings` /
`## CI Failures Unresolved` PR body labels, and `GATE: STOP` keywords are
machine-parsed and stay English; only user-facing explanation prose follows
the resolved language. Resolve the value per `skills/setup/SKILL.md`
§`output.language 해석 (canonical)` (Present-to-User 직전 해석; 파일
부재·malformed·미지원 값 → en).

---

## Athanor identity invariants

This pipeline preserves all four v0.10.0 athanor identity commitments:

1. **Thin Leader** — every step dispatches to a worker skill or runs the
   git/gh plumbing permitted by CLAUDE.md §Core Principle exceptions; the
   LFG leader never authors code itself.
2. **Cross-model adversarial planning** — step 1 invokes `/athanor:plan`,
   whose tier is set by `--depth=` (or trigger keywords) per its Tier
   Dispatch Table (`skills/plan/SKILL.md`); `codex.enabled` controls only
   the in-tier Codex fallback, not which tier runs.
3. **Spec-then-TDD discipline** — step 2 invokes `/athanor:work`, which
   applies Splitter `execution_note` classification and the Phase 3 gate.
4. **Stop hook runtime gate** — every Stop event during this pipeline
   passes through `scripts/hooks/stop_verify_claims.py` (v0.10.3-level
   coverage: NFKC + Cyrillic/Greek/Armenian fold + paraphrase regex +
   vendor-aware whitelist + conditional/attribution suppression).

If a worker output violates one of these invariants, the leader flags
the violation and re-dispatches the worker rather than letting the
pipeline proceed.
