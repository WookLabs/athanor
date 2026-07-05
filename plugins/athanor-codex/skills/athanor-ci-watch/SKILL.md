---
name: athanor-ci-watch
description: Watch GitHub Actions for an Athanor PR, fix concrete CI failures, commit, push, and retry within a bounded loop.
---

# Athanor CI Watch

Use this for the CI watch and autofix stage of `athanor-lfg` or
`athanor-lfg-loop`, or when the user explicitly asks to monitor a PR's CI.

## Preconditions

1. A pull request number or URL is available.
2. `gh` is installed and authenticated.
3. The current branch is writable and has a normal push remote.
4. `maxIterations` is known from the user, the pipeline, or defaults to `3`.

If any precondition is missing, report the missing condition and stop. Do not
fabricate CI status.

## Watch-Fix Loop

For each iteration from `1` through `maxIterations`:

1. Watch checks:

```bash
gh pr checks <pr-number-or-url> --watch
```

If `--watch` is unavailable, poll with:

```bash
gh pr checks <pr-number-or-url>
```

2. If every terminal check passes, report success with the final command
   evidence.
3. For each failed check, collect structured metadata:

```bash
gh pr checks <pr-number-or-url> --json name,state,link
```

4. Open the failed run and retrieve logs:

```bash
gh run view <run-id> --log-failed
```

5. Classify the root cause:
   - Test failure: failing test name, assertion, and touched code path.
   - Lint or type failure: file, line, rule, and minimal fix.
   - Build failure: first real build error and owning source/config file.
   - Timeout: step that timed out and whether it is likely infrastructure.
   - Infrastructure failure: network, cache outage, rate limit, runner outage,
     or flaky external service.
6. For real code failures, apply the smallest fix, run the relevant local
   verification, commit, and push:

```bash
git add <changed-files>
git commit -m "fix(ci): <concise root cause>"
git push
```

7. For an infrastructure failure, do not edit code. Re-run the failed job:

```bash
gh run rerun <run-id> --failed
```

8. If the same check fails twice with the same root cause, stop the autofix
   loop and write a residual failure summary.

## Output

On success, include the PR, iteration count, failures fixed, commits pushed,
and final `gh pr checks` evidence.

On failure, include `CI Failures Unresolved`, the checks still failing, the
root cause summary, what was already attempted, and the next manual action.

## Codex Constraints

- Do not fabricate CI status, PR status, logs, run IDs, commits, or push
  results.
- Do not force-push.
- Do not weaken tests, remove assertions, or disable checks to make CI green.
- Do not edit `.github/workflows/` unless the failing log points to workflow
  configuration as the root cause.
- Do not claim Claude Task dispatch, hidden hook verification, Claude
  PreToolUse enforcement, or Freeze enforcement.
