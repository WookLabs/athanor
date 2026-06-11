---
name: athanor-lfg-goal
description: Run bounded goal-driven Athanor LFG cycles in Codex using a durable goal ledger, per-cycle receipts, and 3-tier completion verification.
---

# Athanor LFG Goal

Use this when the user wants repeated LFG cycles until an outcome-level goal is
met, not just a single feature shipped.

## Validated Receipt-Ledger Loop

This skill adapts Athanor's Validated Receipt-Ledger Loop for Codex. It wraps
`athanor-lfg` cycles with durable goal state and external evidence checks.
`<promise>DONE</promise>` from one cycle is insufficient by itself; completion
requires a validated receipt and user-visible goal decision.

## Goal Bootstrap

1. Accept either inline goal text or a `--goal-file` path.
2. Create or update `.athanor/goals/<goal-id>/goal.md`.
3. Define locked G-markers with observable acceptance criteria.
4. Record `maxIterations` from `athanor.json` `lfgGoal.maxIterations` when
   available; default to 5 if absent.
5. Initialize a cycle queue and state file if the goal is new.

## Cycle Flow

For each cycle `CNNN`:

1. Select target G-markers.
2. Run `athanor-scope-drift` before starting when previous cycles exist.
3. Run `athanor-lfg` for the cycle target.
4. Dispatch or perform a receipt-validator pass that writes
   `.athanor/goals/<goal-id>/receipts/CNNN-lfg-receipt.md`.
5. The receipt must cover the LFG steps: plan, work, review, review-fix,
   residual handoff, browser test, commit-push-PR, CI watch, and DONE.
6. Mark G-markers closed only when receipt evidence supports them.

## Receipt Validator Contract

The receipt-validator is a verification pass over disk and GitHub artifacts,
not a trust step over model prose. It must execute or explicitly mark every
row in the 9-step verification command table.

| Step | Required evidence | Verification command shape | Pass criterion |
| --- | --- | --- | --- |
| Step 1 plan | `plan_file_path` for a real `plan.md` | `test -f "$PLAN_FILE_PATH" && [ "$(wc -c < "$PLAN_FILE_PATH")" -gt 500 ]` | Plan artifact exists and is substantial. |
| Step 2 work | `commit_sha` and whether tests changed | `git show --stat "$COMMIT_SHA"` plus changed-file inspection | Commit resolves; behavior work has test evidence or explicit no-test reason. |
| Step 3 review | `review_artifact_path` or `pr_url` | `test -f "$REVIEW_ARTIFACT_PATH"` or `gh pr view "$PR_URL"` | Structured review evidence exists. |
| Step 4 review-fix commit | review-fix commit or no-op rule | `git log --grep='fix(review)' --oneline -1` | Fix commit exists or receipt records no blocking findings. |
| Step 5 residual handoff | PR body section or fallback file | `gh pr view "$PR_URL" --json body` or `test -f "$RESIDUAL_HANDOFF_PATH"` | Residual Review Findings are durable. |
| Step 6 browser test | UI test artifact or no-UI rule | `test -f "$RESULT_FILE_PATH"` | Browser test evidence exists or no UI files changed. |
| Step 7 commit-push-PR | `pr_url` | `gh pr view "$PR_URL" --json state,url` | PR exists and is not closed without merge. |
| Step 8 CI watch | final CI status or residual section | `gh pr checks "$PR_URL"` | CI is green or `CI Failures Unresolved` is recorded. |
| Step 9 DONE | tag or dry-run rule | `git tag -l "$TAG"` | Tag exists, or receipt records null tag with dry-run mode. |

Each row receives one status:

- `VALID`: command evidence supports the receipt row.
- `INVALID`: command evidence contradicts the row, the artifact is missing, or
  the command fails with a real verification failure.
- `UNDETERMINED`: command cannot be reached because `gh`, network, auth, or a
  sandbox restriction prevents verification. This is surfaced but does not
  equal success.

After all rows, compute `aggregate_status`:

- `all_valid`: every row is `VALID`, or `VALID` with `UNDETERMINED` rows mixed
  in, provided no row is `INVALID`. `UNDETERMINED` is **non-blocking for
  aggregate**: a cycle with 8 `VALID` + 1 `UNDETERMINED` still aggregates as
  `all_valid` provided no step is `INVALID`. Environmental failures (missing
  `gh`, no network) must not force a re-cycle on an otherwise honest receipt;
  the `undetermined_count` is surfaced separately, not treated as a blocker.
- `completed_with_residuals`: no row is `INVALID`, but durable residuals such
  as review findings or unresolved CI are present.
- `invalid_steps_present`: at least one row is `INVALID`.

The receipt must record per-step command, exit code when available, evidence,
status, `undetermined_count`, and `aggregate_status`.

## 3-tier Completion Check

Completion is a 3-tier check, not a model assertion:

- Tier 1 mechanical: ledger arithmetic, verify command, test evidence, no
  unresolved required markers.
- Tier 2 adversarial: independent review of ledger, receipts, diff, and tests.
  Use Codex sub-agents only when explicitly authorized; otherwise run a local
  adversarial pass and label it as non-parallel.
- Tier 3 user ratification: ask the user to choose `yes`,
  `continue-iterating`, or `abort` when evidence says the goal may be complete.

Only `yes` writes `goal-completion.md` and marks the ledger complete.
`continue-iterating` starts the next cycle with residual gaps. `abort` records
the reason and stops without declaring success.

## Scope Changes

If a cycle discovers new required scope, append a scope-change entry to
`goal.md`, evaluate it as `accept`, `reject`, or `escalate`, and preserve the
decision trail. Do not silently rewrite locked G-markers.

## Codex Constraints

- Do not claim Claude Stop hook enforcement, Claude PreToolUse enforcement,
  Freeze enforcement, or Claude Task isolation.
- Do not let a bare `<promise>DONE</promise>` close a cycle.
- Do not mark the goal complete from model confidence alone; require ledger,
  receipt, and ratification evidence.
