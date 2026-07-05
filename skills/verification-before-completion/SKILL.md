---
name: verification-before-completion
description: Use when about to make a material claim about edits, tests, releases, migrations, deployments, or verification output. Requires fresh commands and explicit evidence before any success or completion claim.
allowed-tools: Bash, Read
---

<!-- Provenance:
  upstream: ref/superpowers/skills/verification-before-completion/SKILL.md
  source-commit: unknown-local-vendored-copy
  license: MIT
  modifications:
    - Adapted for Athanor explicit evidence gates after Stop hook removal.
    - Replaced runtime completion-claim hook dependency with workflow artifact evidence.
-->

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonest. Athanor no longer
uses a Stop completion-claim hook to police this at runtime; quality comes from
explicit evidence gates in the active workflow artifacts.

Core principle: evidence before claims, always.

## Gate Function

Before making any material success, completion, readiness, release, migration,
or deployment claim:

1. Identify the command or artifact that proves the claim.
2. Run the full command freshly, or read the exact artifact freshly.
3. Inspect the output, exit code, and failure count.
4. Report the actual result, including failures or partial coverage.
5. Only then make the claim, and only to the extent the evidence supports it.

If verification cannot be run, say that directly and do not present the work as
fully verified.

## Structured Verdict Block

Use one block per check when reporting verification evidence:

```text
### Check: <what is being proven>
Command: <exact command run, or Artifact: <path> for a read-only check>
Output: <real output, important lines, and exit code>
VERDICT: PASS | FAIL | PARTIAL
```

Rules:

- `PASS` means the cited command or artifact directly supports the claim.
- `FAIL` means the proof failed; continue working or report the blocker.
- `PARTIAL` means the proof covers only part of the claim or could not run fully.
- Do not paraphrase output as a substitute for checking it.
- Do not use old command output, agent reports, or expectations as evidence.

## Red Flags

- "Should pass", "probably", "seems fixed", or equivalent wording.
- A positive status claim before running the relevant check.
- Trusting another agent's completion report without inspecting the diff and
  verifying the behavior.
- Treating a lint pass as proof that tests, schemas, hooks, or packaging pass.
- Reporting completion when any required check is `FAIL` or materially `PARTIAL`.

## Common Claim Mapping

| Claim | Required Evidence |
| --- | --- |
| Tests pass | Exact test command, exit code 0, and failure count |
| Linter clean | Exact lint command, exit code 0 |
| Build succeeds | Build command exit code 0 |
| Bug fixed | A check that reproduces the original symptom and now passes |
| Migration complete | Active-surface scan plus touched regression tests |
| Requirements met | Requirement checklist mapped to evidence |

## Bottom Line

Run the check. Read the output. Then state the evidence-backed status.
