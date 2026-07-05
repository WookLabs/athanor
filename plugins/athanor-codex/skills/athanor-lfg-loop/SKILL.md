---
name: athanor-lfg-loop
description: Run a bounded Athanor loop from a natural-language objective through research, planning, design, implementation, assessment/review, verification, persistence, and next-loop decisioning.
---

# Athanor LFG Loop

Use this when the user wants Codex to drive bounded iteration toward an
outcome, not just ship one cycle.

## Contract

`athanor-lfg-loop` mirrors `/athanor:lfg-loop`:

1. accept a natural-language objective;
2. create durable loop state under `.athanor/loops/<loop-id>/`;
3. perform deep research/discovery when context is incomplete;
4. run deep planning and architecture/design before implementation when needed;
5. invoke `athanor-lfg` for each delivery cycle;
6. validate each cycle with per-cycle receipts;
7. run `athanor-assess` and/or `athanor-review` as configured gates;
8. convert evidence into controller input;
9. persist the controller decision and decide the next-loop action.

Codex is an implementation runtime, not Claude Code. Do not claim Claude hook,
Claude Task, Freeze, or PreToolUse enforcement. No hidden completion hook is
part of this command; the removed Stop completion claim hook is not part of
loop quality. Quality comes from explicit artifacts: loop ledger, receipts,
assessment/review reports, controller decisions, and human escalation.

This is the Validated Receipt-Ledger Loop. It keeps G-markers in `loop.md`,
stores `CNNN-lfg-receipt.md` under `.athanor/loops/<loop-id>/receipts/`, and
uses a receipt-validator plus 3-tier completion check. Tier 1 checks receipt
structure, Tier 2 judges evidence and score/review gates, and Tier 3 asks the
user for final ratification. `<promise>DONE</promise>` is insufficient without
validated receipts and controller evidence. Honor `maxIterations`.
Do not claim hook-backed enforcement.

## Durable State Summary

Durable state lives at `.athanor/loops/<loop-id>/state.json`. Keep the compact
field vocabulary visible in Codex runs:

- lifecycle: `cycle_state`, `cycle_phase`, `current_cycle`,
  `cycle_n_in_progress`, `tier3_pending`, `tier3_ratified`
- ownership/logging: `acting_on`, `loop_run_log`, `lock_status`, `updated_at`
- limits/progress: `max_iterations`, `budget`, `no_progress_count`,
  `stop_reason`
- evidence pointers: `last_receipt_path`, `last_validator_status`,
  `last_evaluator_role`, `tier2_last_verdict`

Controller decisions must be derived from `state.json` plus
`evidence/latest.json`; assistant prose is not controller evidence.

## Pre-LFG Stage Receipts

Before the first `athanor-lfg` delivery cycle, preserve pre-cycle reasoning as
explicit receipts under `.athanor/loops/<loop-id>/receipts/`:

- research: `R000-research-receipt.md`
- planning: `P000-planning-receipt.md`
- architecture/design: `A000-architecture-receipt.md`

If a stage is intentionally skipped, write its receipt with `status: skipped`
and a concrete reason. Do not replace the receipt with hidden context or a chat
summary.

Required compact evidence:

- research receipt: Source files, external references if any, unresolved facts,
  and findings that shape `loop.md`.
- planning receipt: Accepted plan path, acceptance markers, verification
  commands, cycle boundaries, and known risks.
- architecture receipt: Public contracts, cross-module design decisions,
  rejected alternatives, and follow-up constraints.

Each pre-LFG receipt references `loop.md` and any session artifact that supplied
the stage input.

## Evidence Vocabulary

Use the 9-step verification command table from the parent receipt validator:

- Step 1 plan
- Step 2 work
- Step 3 review
- Step 4 review-fix commit
- Step 5 residual handoff
- Step 6 browser test
- Step 7 commit-push-PR
- Step 8 CI watch
- Step 9 DONE

Receipt rows use:

- `VALID`
- `INVALID`
- `UNDETERMINED`

`aggregate_status` uses:

- `all_valid`: no invalid rows; undetermined rows are surfaced separately.
- `completed_with_residuals`: no invalid rows, but durable residuals remain.
- `invalid_steps_present`: at least one invalid row.

`UNDETERMINED` is non-blocking only when no step is `INVALID`: 8 `VALID` + 1
`UNDETERMINED` still aggregates as `all_valid`, provided no step is `INVALID`.
`UNDETERMINED` is non-blocking for aggregate status only under that no-invalid
condition.

A bare `<promise>DONE</promise>` does not close a cycle.

## Score-Target Mode

Use forms such as:

```text
athanor-lfg-loop --score-target 95 --min-dimension 90 "raise release readiness"
```

Codex must run `athanor-assess` for baseline and post-cycle score evidence when
score-target mode is selected. It tracks `target_overall_score`,
`target_min_dimension_score`, and `max_allowed_regression`, then drives the next
cycle from the lowest-scoring dimensions. Weighted-average gains are not enough;
inflated scores or waived blockers must be surfaced as residuals.

## Controller Actions

The loop controller may emit `run_baseline_assess`, `run_delta_assess`,
`run_lfg_cycle`, `require_receipt_validation`, `require_assessment_evidence`,
`run_scope_drift`, `prompt_tier3_user`, `stop_no_progress`,
`stop_max_iterations`, `refuse_terminal_state`, or `complete_loop`.

Forward actions exit `0`; halt/refuse actions exit `1`; malformed input exits
`2`.

## Human Escalation

Escalate for destructive operations, product ambiguity, repeated invalid
receipts, high scope drift, contradictory assessment/review evidence,
max-cycle terminal exits, or final ratification. The expected choices are
`yes`, `continue-iterating`, `abort`, and `revise-scope` where applicable.

## Terminal Artifacts

Completed loops write `.athanor/loops/<loop-id>/loop-completion.md`.
Blocked, max-iteration, no-progress, or aborted loops write
`.athanor/loops/<loop-id>/loop-residual-exit.md`.
