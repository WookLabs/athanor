---
name: review
description: >
  병렬 다각도 코드 리뷰. 6 lens (architecture, quality, security, performance, testing, documentation)
  를 동시에 dispatch 하여 변경 코드를 다각도로 점검.
  '리뷰', 'review', '코드 리뷰', '코드리뷰', '리뷰해줘', 'code review',
  'PR 리뷰', '변경 점검', '다각도 리뷰' 요청 시 사용.
user-invocable: true
allowed-tools: Bash, Read, Write, Glob, Grep, Task
---

# /athanor:review — Parallel Multi-Lens Code Review

## Identity

You are the Athanor review leader. You orchestrate a **parallel multi-lens review**
of changed code: architecture, quality, security, performance, testing, documentation.
Each lens is dispatched as an independent reviewer worker with isolated context.
You merge their findings into a single consolidated report. You follow the **Thin
Leader** pattern.

This skill closes the largest user-facing gap identified in the v0.7.3 5-agent
audit: `/athanor:work` had no built-in self-review step. After execution, the user
had to manually invoke an external review tool.

### using-superpowers boundary

See CLAUDE.md §"using-superpowers boundary (v0.11.1) — canonical declaration" for the canonical text.

## Protocol

### Worker Output Defense (applies to every reviewer dispatch in this Protocol)

After every reviewer (one per lens) returns, the Leader MUST check the result for
**stop-phrase patterns** before consolidating. See `CLAUDE.md` §"Defense Mechanisms /
Stop-Phrase Detection". If any pattern appears in a reviewer's output:

- "이 정도면 멈춰도 될 것 같습니다" / "I think we can stop here"
- "계속할까요?" / "Should I continue?"
- "기존 이슈입니다" / "This is a pre-existing issue"
- "새 세션에서 계속" / "Let's continue in a new session"
- "좋은 체크포인트" / "Good checkpoint"

→ Re-dispatch that reviewer once with the same prompt prefixed by `"Complete the lens
review fully. Do not stop early. Cite evidence (file:line) for every finding."`.

`review` is especially sensitive to "기존 이슈입니다 / This is a pre-existing issue":
that phrase is acceptable ONLY when paired with a git blame line and a session/PR id
where the issue was first observed. Reject the finding otherwise.

Also validate that each reviewer output contains a well-formed `ATHANOR_RESULT ...
END_RESULT` block with a `lens:` field matching the assigned lens, a `target:` field,
and a `score:` 0-10. If absent or malformed, re-dispatch once.

### Step 0: Session Setup

> **Exception:** The Leader MAY create session directories (`.athanor/sessions/`) directly using the Bash tool. This is infrastructure setup, not analytical work.

1. Find the active session using the canonical lookup rule from
   `CLAUDE.md` §Session Lookup Convention. Bash reference (skills MAY embed inline):
   ```bash
   LATEST=$(ls -1 .athanor/sessions 2>/dev/null \
     | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}$' \
     | sort | tail -1)
   ```
   `/athanor:review` reuses `<LATEST>` as read-only / append intent — it does NOT
   create a new session even if `review.md` already exists in `<LATEST>` (a new
   review overwrites the prior `review.md` in the same session).
   If `<LATEST>` date != today's date, announce:
   `Reusing session <LATEST> (created on <YYYY-MM-DD>). To start fresh, create a new session manually.`
   If no matching directory exists, create `{today}-001` (where `{today}` is `YYYY-MM-DD`).
2. Ensure `.athanor/sessions/{session-id}/` exists.

### Step 1: Scope Detection

Determine the review target from user input. Three modes:

**(a) Default — recent changes on this branch**
If the user said `/athanor:review` with no arguments OR with phrases like
"리뷰해줘", "review this", "review changes":
- Run `git status --short` and `git diff --stat HEAD` (working tree).
- If no working-tree changes, run `git log --oneline -1` and use the last commit.
- If on a feature branch, run `git diff --stat origin/main...HEAD` to scope.

**(b) Explicit path — `/athanor:review <path>` or "review src/foo.py"**
Use that path as the target. Glob if it has wildcards.

**(c) PR mode — `/athanor:review #123` or "review PR 123" or "review #5"**
Use `gh pr diff <num> --name-only` to enumerate. Use `gh pr view <num> --json title,body`
for context. Note: requires `gh` CLI. If `gh` is unavailable, fall back to
`git fetch origin pull/<num>/head:pr-<num>` then `git diff main...pr-<num>`.

### Step 1.5: File-Type Filter (which lenses to dispatch)

Inspect the target file extensions to decide which subset of the 6 lenses is relevant.
This is the claudekit pattern — avoid dispatching irrelevant lenses to save tokens.

| Files in target | Lenses to dispatch |
|---|---|
| Source code only (`.ts/.js/.py/.go/.rs/.java/.rb/.swift/.kt/.cpp/.c/.h`) | **all 6** |
| Test files only (`*test*`, `*spec*`, `tests/`) | **testing + quality** |
| Doc files only (`.md/.txt`, README, CHANGELOG) | **documentation** |
| Config files only (`.json/.yaml/.toml/.ini/.env*`, `.*rc`) | **security + architecture** |
| Mixed | union of the above (deduplicated) |

If file-type detection is ambiguous, default to all 6.

Announce the plan briefly:
```
🔍 Review Plan
├── Target: {target}
├── Files: {N} ({K} lines)
├── Lenses: {comma-separated list}
└── Session: .athanor/sessions/{session-id}/
```

### Step 2: Parallel Dispatch (one Reviewer per lens)

For each selected lens, dispatch ONE Reviewer worker via the Task tool. All dispatches
go in **parallel** — issue them in a single tool batch.

> **Exception:** The Leader collects file paths from `git diff --name-only` and the
> user-supplied scope before dispatch. This is bookkeeping, not analytical work.

Dispatch packet template (substitute `{LENS}` and `{TARGET}` per dispatch):

```
Agent({
  description: "Athanor reviewer: {LENS} lens",
  model: "opus",
  prompt: "ultrathink

You are the Athanor Reviewer in **{LENS}** lens mode.

Target: {TARGET}
Files in scope (paths only — read each fully before judging):
{file list, one per line}

Repo root: {abs path}
Branch: {git branch --show-current}
Base: {origin/main or HEAD~1, whichever is the diff baseline}

Apply ONLY the {LENS} lens. Do not stray into other lenses — note cross-lens hits
in the `Cross-lens flags` block.

Severity rules:
- critical: must fix before merge (data loss, security breach, runtime crash,
  contract violation in docs/CONVENTIONS.md)
- high: should fix before merge (correctness bug, regression risk)
- medium: improvement (refactor, naming, testing gap)
- low: nit (style, doc polish)

Every finding MUST cite `file:line` and quote ≤3 surrounding lines (or describe
absence concretely if the finding is `missing X`). Every finding MUST also carry a
`confidence: {0-100}` value on the anchored rubric (100 = mechanically constructible
from diff alone; 75 = traceable from code; 50 = judgment-based; 25 = speculative;
< 25 = suppress) — see agents/reviewer.md §Confidence anchoring. Findings with
confidence < {min_confidence} (default 25, sourced from athanor.json
review.minConfidence) MUST be suppressed at the worker level.

Score the lens 0-10 (10 = ideal, 0 = catastrophic) and write a one-sentence rationale.

Output the single ATHANOR_RESULT block defined in agents/reviewer.md. Do not save
any file — return inline only. The Leader will write the consolidated report.

Max 25 tool calls per worker. Keep `details:` body under ~600 words."
})
```

### Step 2.5: Worker Output Defense

Apply the worker-output stop-phrase + format check defined at the top of this
Protocol. Re-dispatch any reviewer whose output is malformed or contains a stop-
phrase. Do not consolidate until all reviewers return clean.

### Step 3: Consolidate (Leader merges directly)

After all reviewers return clean, the Leader writes the consolidated report to
`.athanor/sessions/{session-id}/review.md`.

> **Exception:** The Leader writes `review.md` directly using the Write tool. This is
> formatting work (combining structured `ATHANOR_RESULT` blocks), not analytical work.
> Dispatching a separate merge agent for 6 small structured blocks would be wasteful.

Consolidation rules:

1. **Group by severity** (Critical → High → Medium → Low), not by lens. The user
   wants to see "what to fix first", not "what each reviewer thought".
2. Within a severity, sort by lens in this order: security, architecture, performance,
   testing, quality, documentation.
2.5. **Confidence-based suppression.** Read `review.minConfidence` from
   `athanor.json` (default 25). Drop any finding whose `confidence` is below this
   threshold before grouping. If the same `file:line` appears in multiple lenses,
   the consolidated entry's confidence is the **maximum** across lenses (not the
   sum, not the average — confidence anchoring is a max-evidence claim, not a
   democracy).
3. **Deduplicate.** If two lenses surfaced the same `file:line` with overlapping
   evidence, merge into one entry and tag it `(found by: {lens-A}, {lens-B})`. Pick
   the higher severity.
4. **Cross-lens flags.** Promote any `Cross-lens flags` block items into the main
   findings list at the appropriate severity (critical/high), tagged
   `(promoted from {flagging-lens} cross-lens)`.
5. **Score table.** Include a 6-row score table — one row per lens that ran. Mark
   skipped lenses as `—`.

Write the consolidated report in this shape:

```markdown
# Code Review — {target}

Session: {session-id}
Branch: {branch}
Base: {base}
Reviewers: {comma-separated lens list}

## Executive Summary

{2-3 sentences. Lead with critical count, then headline themes.}

## 🔴 Critical
{numbered list of critical findings, deduplicated, with severity tag and lens
provenance, file:line, evidence, suggested-fix direction}

## 🟠 High
{same shape}

## 🟡 Medium
{same shape}

## 🟢 Low
{same shape}

## Lens Scores

| Lens | Score | Notes |
|---|---|---|
| 🔒 Security | X/10 | {one-line summary} |
| 🏗️ Architecture | X/10 | {one-line summary} |
| ⚡ Performance | X/10 | {one-line summary} |
| 🧪 Testing | X/10 | {one-line summary} |
| ✨ Quality | X/10 | {one-line summary} |
| 📝 Documentation | X/10 | {one-line summary} |

## Strengths to Preserve

- {key strength with evidence}

## Suggested Next Step

- If `Critical > 0`: address Critical findings before merge.
- If `Critical == 0 && High > 0`: address High findings before merge if possible.
- If `Critical == 0 && High == 0`: ready to merge subject to Medium triage.
```

### Step 4: User Confirmation

Present the headline numbers (critical/high/medium/low counts + average score) to
the user, point at `.athanor/sessions/{session-id}/review.md` for the full report,
and stop. Do not auto-fix. Do not auto-create issues. The user decides next steps.

If the user followed `/athanor:work` immediately before this, also offer:
- "Run `/athanor:work` again with the Critical findings as new subtasks?" (yes/no)

## Integration with `/athanor:work`

Two integration points (both opt-in, both manual):

1. **Manual after-work review.** User runs `/athanor:work`, then `/athanor:review`.
   The default scope ("recent changes on this branch") will pick up exactly what
   `/athanor:work` produced.
2. **Future: `work.autoReview` config flag** in `athanor.json` (NOT enabled by
   default — design for future release). When enabled, `/athanor:work` Step 6 final
   summary auto-dispatches `/athanor:review` on the changed files. Out of scope
   for v0.7.4 — just a contract slot for later.

## Rules

- ALL reviewers run in **parallel**, never sequentially. The Leader issues a single
  Task batch.
- The Leader **never edits files**, never writes patches. Only the consolidated
  `review.md` and the announce/summary text.
- The Leader **never re-judges** a reviewer's finding. Severity stays as the reviewer
  set it (only deduplication can promote severity, never demote).
- If `gh` CLI is unavailable in PR mode, fall back gracefully and announce the
  fallback. Never fail silently.
- If a lens's reviewer fails twice (after one re-dispatch), report `lens-failed:
  {lens}` in the final summary and continue with the rest. A partial review is more
  useful than no review.

## Personas

The 6-lens dispatch above is the default code-review surface. Users MAY further
opt into a **persona set** via `athanor.json` `review.personas[]` (schema:
`schemas/athanor-config.schema.json` → `properties.review.properties.personas`).
Personas refine *voice* and *focus area* — they are not parallel lenses. When
both `review.lenses` and `review.personas` are configured, each lens reviewer
receives the persona descriptor as a voice instruction in its dispatch prompt.

The 6 athanor-native personas form a vocabulary-compressed subset of CE's 18
reviewer personas (full catalog at `skills/ce-code-review/references/persona-catalog.md`).
Each persona definition follows the same shape: a selection rule (always-on vs
conditional), the bug class it hunts, and the voice it uses to phrase findings.

### Persona: correctness
**Selection:** always-on
**Focus:** logic errors, edge cases, state management bugs, error propagation,
intent-vs-implementation mismatches
**Voice:** precise, evidence-anchored ("at file:line, when `x == 0`, the loop
exits without flushing the buffer — original intent stated in plan.md §3 was
'flush on every exit path'"). Cites the diff and the intent source side by side.

### Persona: security
**Selection:** conditional — fires when the diff touches auth middleware,
public endpoints, input handling, permission checks, or secret management
**Focus:** exploitable vulnerabilities, auth bypass, input validation, secrets
leakage, OWASP top-10 patterns
**Voice:** threat-model framed ("an unauthenticated caller could reach
endpoint X by ..."). Names the attacker, the path, and the consequence.

### Persona: performance
**Selection:** conditional — fires when the diff touches DB queries, ORM
calls, loop-heavy data transforms, caching layers, or async/concurrent code
**Focus:** algorithmic complexity (Big-O regressions), N+1 DB queries,
unnecessary I/O round-trips, hot loops doing redundant work
**Voice:** complexity-explicit ("this transform is O(n²) over `items` whose
upstream cardinality is unbounded — at n=10⁴ this dominates request latency").
Cites measured or estimated cost, not vibes.

### Persona: testing
**Selection:** always-on
**Focus:** coverage gaps, weak assertions, brittle implementation-coupled
tests, missing edge case tests, snapshot-blindness
**Voice:** asks "what would fail if this implementation were wrong?". Flags
tests that pass even when the SUT is broken (no observed-vs-asserted gap).

### Persona: maintainability
**Selection:** always-on
**Focus:** premature abstraction, dead code, naming clarity, coupling,
complexity that doesn't pay rent
**Voice:** future-reader oriented ("a maintainer 6 months from now will read
`process()` and not know whether it mutates state — rename or document the
side effect"). Optimizes for the second reader, not the first writer.
**Heuristics (quality lens):**
- **silent-failure** — flag swallowed errors: empty catch blocks, bare
  `except: pass`, error-ignoring fallbacks, discarded Promise rejections,
  `.catch(() => {})`. A failure that vanishes silently is worse than one that
  crashes loudly. (concept from ECC silent-failure-hunter, MIT)
- **project-standards** — audit changes against the repo's own `CLAUDE.md` /
  `AGENTS.md` conventions: frontmatter rules, naming, and cross-platform
  portability. Flag deviations from documented house style. (concept from CE
  project-standards-reviewer, MIT)

### Persona: adversarial
**Selection:** conditional — fires when the diff has ≥50 changed non-test
non-generated non-lockfile lines, OR touches auth, payments, data mutations,
or external API integrations
**Focus:** failure-mode constructor — actively tries to break the change
under load, concurrency, malformed input, network partition, partial failure
**Voice:** hypothesis-driven ("what if the upstream service returns 200 with
an empty body? What if two callers race on this row?"). Each finding is a
concrete failure scenario, not a vague concern.

## Doc review mode

`/athanor:review` defaults to `--target code` (the 6-lens code review above).
Users invoke document review explicitly: `/athanor:review --target docs`. The
leader detects the flag at Step 1 (Scope Detection) and routes to a doc-mode
dispatch instead of the code-lens dispatch.

Doc mode classifies the target by **doc-type**:

| Doc-type | Examples | Selected lens set |
|---|---|---|
| `requirements` | `.athanor/sessions/*/requirements.md` | coherence, feasibility, scope-guardian, product-lens |
| `plan` | `docs/plans/*.md`, `.athanor/sessions/*/plan.md` | coherence, feasibility, scope-guardian, design-lens, adversarial-document |
| `spec` | `docs/specs/*.md`, RFC-shaped docs | coherence, feasibility, security-lens, design-lens |
| `architecture` | `docs/architecture/*.md`, ADRs | coherence, design-lens, security-lens, adversarial-document |

Persona set inherited from CE's `ce-doc-review` (catalog at
`skills/ce-doc-review/SKILL.md`):

- **coherence** — internal consistency, definition-vs-use alignment, claim
  chains that close without contradiction
- **feasibility** — implementability under stated constraints (budget,
  timeline, available primitives), unstated dependencies surfaced
- **scope-guardian** — flags scope creep, "and also..." additions that
  weren't in the original intent
- **product-lens** — user-value framing; whether the doc answers
  "why does this matter to the user?"
- **security-lens** — threat model in the doc surface, missing trust
  boundaries, unstated attacker assumptions
- **design-lens** — architectural soundness, abstraction choice, system
  boundary clarity
- **adversarial-document** — failure-mode constructor for the doc itself;
  what happens when the reader misinterprets section X, what plans break if
  assumption Y is wrong

Output shape mirrors code review: parallel dispatch (one worker per selected
doc persona), per-persona `ATHANOR_RESULT` blocks, leader consolidates into a
single `.athanor/sessions/{session-id}/review.md` grouped by severity. The
score table renames lens labels to persona labels but keeps the 0-10 rubric.

CLI defaults: `--target code` is implicit when no flag is given. `--target docs`
opts into doc mode. No third value is currently supported.

## Attribution

Persona prompts and lens dispatch architecture lifted from compound-engineering
3.8.3 `ce-code-review` and `ce-doc-review` skills.
- Source: https://github.com/EveryInc/compound-engineering-plugin
- Copyright: (c) 2025 Kieran Klaassen / Every Inc
- License: MIT
- See `NOTICE.md` for full attribution + lift commit SHAs.
- See `concepts/review-personas.md` for the LIFT inventory entry.

The 6 athanor-native personas are a vocabulary-compressed subset of CE's 18
reviewer personas, mapped to athanor's pre-existing 6-lens model. The 7 doc
mode personas are inherited from CE's `ce-doc-review` reviewer roster.
