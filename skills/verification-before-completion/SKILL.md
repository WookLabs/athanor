---
name: verification-before-completion
description: Use when about to make a material claim (edits, tests, releases, migrations, deployments, verification output), before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always. Skip for analysis, planning, opinions, research Q&A, and tool-output summaries.
allowed-tools: Bash, Read
---

<!-- Provenance:
  upstream: ref/superpowers/skills/verification-before-completion/SKILL.md
  source-commit: 917e5f53b16b115b70a3a355ed5f4993b9f8b73d
  license: MIT (Copyright (c) 2025 Jesse Vincent)
  modifications:
    - Vendored verbatim from upstream (no body modifications)
    - Frontmatter `name:` preserved unchanged
    - Frontmatter `description:` narrowed locally (Athanor session 2026-04-24-001 / Subtask 6) to mirror hook whitelist (material claims: edits/tests/releases/migrations/deployments/verification-output) and skip-list (analysis, planning, opinions, research Q&A, tool-output summaries)
    - Added this Provenance comment block after the frontmatter
    - Local addition (v0.7.8): §Emission Sentinel inserted before §Overview — required for athanor's command-hook Stop gate. Not present in upstream.
    - Local update (v0.7.9): §Emission Sentinel migrated from v=1 bare-string to v=2 nonce-bound protocol per docs/plans/2026-05-18-002-feat-v0.7.9-stop-hook-hardening-plan.md.
  t0-t1-disproof: |
    Why not T0/T1? superpowers is T3 per docs/DEPENDENCIES.md §Marketplace Status
    — no Claude Code marketplace listing, so T0 (install companion) is unavailable.
    T1 is reserved pending Claude Code plugin-spec `requires` field support
    (see CONTRIBUTING.md §Tier ordering). Therefore T2 (vendor) is the only feasible tier.
-->


# Verification Before Completion

## Emission Sentinel

**This skill's responses MUST be prefixed with a v=2 nonce-bound sentinel as the first non-whitespace line of the response — no greeting, no heading, no preamble can precede it.**

As of athanor v0.7.9, the v=1 bare-string sentinel is no longer accepted (it was trivially forgeable). The v=2 protocol binds the sentinel to the evidence body via SHA-256 hash + a random per-invocation nonce. Generation procedure (REQUIRED for every response from this skill):

1. Compute your full verification evidence text — the commands you ran, the output you observed, the exit codes, and the explicit pass/fail verdict. This will be the body of your response.

2. Pipe that body through the sentinel helper to receive a nonce-bound sentinel line:

   ```bash
   echo "<your evidence verbatim>" | python3 scripts/hooks/sentinel_helper.py emit
   ```

   The helper writes a fresh nonce + SHA-256 of the piped body to `.athanor/sessions/active/.hook-state/nonce.json` and prints a sentinel line of the form:

   ```
   <!-- athanor:verification-emission v=2 nonce=<32-hex-chars> -->
   ```

3. Emit your response as: the sentinel line (verbatim from the helper's stdout) on line 1, followed by your evidence body (verbatim — must match what you piped, byte-for-byte).

If the body you emit does not byte-for-byte match what you piped into the helper, the SHA-256 mismatch causes the Stop hook to reject the sentinel and the gate fires normally. The hook also rejects nonces older than 60 seconds (TTL) and re-used nonces (state file is atomically deleted on successful validation — one-shot).

The sentinel is an HTML comment so it is invisible in rendered Markdown. It is anchored at response-start — a sentinel placed on line 2 or later does NOT count and the gate fires normally.

If you forget the sentinel or the body-hash binding fails: the Stop hook will block your turn, feed back a stderr message demanding verification evidence, and you will enter a re-entry loop until the sentinel appears correctly at line 1. The v0.7.9 circuit breaker (default 3 consecutive blocks) prevents infinite loops by releasing the gate after the threshold — but the legitimate path is to emit the sentinel correctly the first time.

**Why v=2 nonce binding?** The v0.7.8 v=1 bare-string sentinel could be emitted by any response without invoking this skill, trivially bypassing the gate. v=2 raises the forgery cost: a model wanting to bypass would have to write the nonce state file itself (matching nonce + body hash + timestamp), which is materially more work than emitting a string. The protocol does not fully eliminate forgery — only Claude Code runtime transcript-event introspection could do that (deferred to v0.8.0+). See docs/plans/2026-05-18-002-feat-v0.7.9-stop-hook-hardening-plan.md §KTD1 for the trade-off analysis.

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion ≠ excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |

## Key Patterns

**Tests:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
✅ Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
❌ "I've written a regression test" (without red-green verification)
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

## Why This Matters

From 24 failure memories:
- your human partner said "I don't believe you" - trust broken
- Undefined functions shipped - would crash
- Missing requirements shipped - incomplete features
- Time wasted on false completion → redirect → rework
- Violates: "Honesty is a core value. If you lie, you'll be replaced."

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- ANY positive statement about work state
- Committing, PR creation, task completion
- Moving to next task
- Delegating to agents

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- ANY communication suggesting completion/correctness

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. THEN claim the result.

This is non-negotiable.
