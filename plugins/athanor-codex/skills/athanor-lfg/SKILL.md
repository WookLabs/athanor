---
name: athanor-lfg
description: "Run an Athanor-style end-to-end ship pipeline in Codex: plan, work, review, persist fixes, test, commit, push, open PR, watch CI, and verify completion."
---

# Athanor LFG

Use this when the user wants hands-off end-to-end delivery rather than a
single plan, implementation pass, or review.

## Pipeline

Run the steps in order. Do not skip forward to implementation before planning
is written and accepted.

### Step 1 — Plan

Invoke or follow `athanor-plan` for the user's feature or branch goal. Gate:
record the plan source, preferably `.athanor/sessions/<id>/plan.md`.

### Step 2 — Work

Invoke or follow `athanor-work`. Default to team-style decomposition when
subtasks are independent, but only use Codex sub-agents if the user explicitly
authorized parallel agent work. Gate: implementation changed files beyond the
plan or the pipeline stops with a clear no-op reason.

### Step 3 — Review

Invoke or follow `athanor-review` against the current diff. If merge-blocking
findings appear, run focused `athanor-work` fix rounds, then re-review. Keep a
hard cap of three review-fix rounds unless the user explicitly extends it.

### Step 4 — Persist Review Fixes

Check `git status --short`. Commit review-driven fixes separately when they
exist. Push if a writable remote is configured; otherwise record that review
fixes are local only.

### Step 5 — Residual Handoff

If blockers or recommendations remain, record them durably in a PR body when a
PR exists, otherwise in `docs/residual-review-findings/<branch-or-sha>.md`.

### Step 6 — Browser Test

If UI files changed, run the available browser-test skill or a project-native UI
smoke test. If no UI files changed, record the skip reason.

### Step 7 — Commit, Push, PR

Commit remaining changes, push the branch, and open or update a PR. The PR body
must include what changed, why it changed, test plan, and migration notes.
For Athanor release work, invoke or follow `athanor-release` before tagging or
publishing release claims.

### Step 8 — CI Watch

If a PR exists and `gh` is available, watch CI. For up to three iterations, pull
failing logs, fix the real issue, commit, push, and watch again. If CI is still
red, write a durable `CI Failures Unresolved` section instead of hiding it.
Use `athanor-ci-watch` for the bounded watch/fix/retry loop.

### Step 9 — Completion

Run `athanor-verify` against the final material claim. Emit
`<promise>DONE</promise>` only after concrete evidence supports the pipeline
outcome.

## Codex Constraints

- Do not claim Claude Stop hook enforcement, Claude PreToolUse enforcement,
  Freeze enforcement, or Claude Task isolation.
- Do not fabricate PR, push, CI, or test status. If credentials, remotes, `gh`,
  or CI are unavailable, record that as the pipeline outcome.
- Do not weaken failing tests or CI checks to make the pipeline green.
