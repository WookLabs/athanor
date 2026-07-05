# LFG Loop Receipt Validator

The receipt validator is a clean-context checker for one `/athanor:lfg` cycle.
It writes `.athanor/loops/<loop-id>/receipts/CNNN-lfg-receipt.md`.

The validator checks these rows:

| Step | Required Evidence | Verification Command |
|---|---|---|
| Step 1 plan | `plan.md` exists and is substantial | `test -s .athanor/sessions/<id>/plan.md` |
| Step 2 work | diff/commit exists; behavior work has tests or explicit no-test rationale | `git diff --stat HEAD~1..HEAD` or recorded dry-run evidence |
| Step 3 review | review artifact or PR review evidence exists | `test -s .athanor/sessions/<id>/review.md` |
| Step 4 review-fix commit | fix commit exists or no-op rule is recorded | `git log -1 --oneline` plus review-fix note |
| Step 5 residual handoff | PR body section or fallback residual file exists | `test -s .athanor/sessions/<id>/residual-handoff.md` or PR body evidence |
| Step 6 browser test | browser artifact exists or no-UI rule applies | `test -e .athanor/sessions/<id>/browser-test.md` or no-UI rationale |
| Step 7 commit-push-PR | PR exists or dry-run/null rule is explicit | `gh pr view --json number,url` or dry-run evidence |
| Step 8 CI watch | CI green or unresolved CI residual is durable | `gh pr checks --watch` or CI residual artifact |
| Step 9 DONE | result packet exists; dry-run/null handling is explicit | `test -s .athanor/sessions/<id>/result.md` |

Per-row statuses:

- `VALID`: command evidence supports the row.
- `INVALID`: evidence is missing, contradictory, or command-verified failure.
- `UNDETERMINED`: environment blocks verification, such as missing `gh`, auth,
  network, or sandbox access.

Aggregate statuses:

- `all_valid`: no invalid rows; undetermined rows are surfaced separately.
- `completed_with_residuals`: no invalid rows, but durable residuals remain.
- `invalid_steps_present`: at least one invalid row.

`UNDETERMINED` is non-blocking only when no step is `INVALID`: 8 `VALID` + 1
`UNDETERMINED` still aggregates as `all_valid`, provided no step is `INVALID`.

Rules:

- A bare `<promise>DONE</promise>` never closes a cycle.
- Free prose is not enough; each row needs command-shaped evidence or an explicit
  environment limitation.
- `UNDETERMINED` is visible, not silently converted into success.
