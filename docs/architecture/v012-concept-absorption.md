---
title: "v0.12.0 Concept Absorption — Forward Architecture"
type: architecture
status: forward-looking
date: 2026-05-22
target_release: v0.12.0
authority: `.athanor/sessions/2026-05-22-001/decisions.md` (D3, D4, D8, D9, D13)
plan_of_record: `.athanor/sessions/2026-05-22-001/plan.md`
companion_archive: `docs/archive/v010-v011-vendoring-scope-correction.md`
---

# v0.12.0 Concept Absorption — Forward Architecture

## Purpose

This document is the Phase 0 forward-looking architecture note for the
v0.12.0 Concept Absorption Pivot. It describes the post-v0.12.0 shape:
the four athanor identity invariants that remain inviolable, the
`concepts/` inventory mechanism, the surviving vendored surface (3
retained items), and the LIFT pattern that moves persona / discipline /
discovery prose into athanor-native skills.

The backward-looking retrospective on the v0.10.0 plan-of-record misread
lives in the companion archive at
`docs/archive/v010-v011-vendoring-scope-correction.md`. This document
does not duplicate that material; references are by link only.

## Four athanor identity invariants

Four commitments survive the v0.12.0 pivot intact. Each is named, briefly
described, and cited to its codebase home.

### 1. Thin Leader contract

The leader (main session) does not perform implementation work directly.
It parses input, dispatches clean-context workers, and presents results.
All project file reading, analysis, code writing, and execution happens
in worker agents. Infrastructure / output exceptions
(`.athanor/sessions/` directory creation, `requirements.md` capture in
clarify mode) are explicit and documented.

- **Lives in:** `CLAUDE.md` §"Core Principle" + every athanor-native
  SKILL.md (the 10 Thin Leader skills) §Identity section.

### 2. Cross-model adversarial planning

`/athanor:plan` runs Planner A (Claude) + Planner B (Codex) + Critic in
parallel and produces an adversarially-reviewed plan-of-record. This is
athanor identity #2 and is the deliberate alternative to single-agent
planning flows.

- **Lives in:** `skills/plan/SKILL.md` (Planner A/B dispatch, Critic
  rubric, output format) + `CLAUDE.md` §"Commands" table row for
  `/athanor:plan`.

### 3. Spec-then-TDD discipline

`/athanor:work` applies Task Splitter `execution_note` classification
(`spec-then-tdd | test-aware | direct`) per subtask, then enforces a
conjunction-of-three Phase 3 gate (tests path touched + worker
self-reported `full_suite_passed: true` + consistent verification prose).
RED-first 5-step flow for spec-then-tdd subtasks; pending-then-gated
downgrade if RED is skipped. This is athanor identity #3.

- **Lives in:** `skills/work/SKILL.md` Step 0.5 (Splitter rules), Step 2a
  (3-branch dispatch packet), Step 2b (v0.8.0 result handler) +
  `CLAUDE.md` §"Spec-then-TDD Discipline".

### 4. Stop hook runtime gate

Every Claude Code `Stop` event invokes
`scripts/hooks/stop_verify_claims.py`. The script reads the transcript,
extracts the last main-session assistant message, detects material
claims via a multi-layer whitelist (paraphrase regex + NFKC + Cyrillic /
Greek / Armenian confusables fold + conditional / attribution
suppression + vendor-aware idioms + nonce sentinel), and exits 2 to
block Stop when a claim lacks fresh evidence. `hooks.profile: "off"`
in `athanor.json` is the per-project opt-out.

- **Lives in:** `scripts/hooks/stop_verify_claims.py` +
  `hooks/hooks.json` (with `${CLAUDE_PLUGIN_ROOT}` expansion since
  v0.11.4) + `CLAUDE.md` §"Completion-Claim Verification".

## The `concepts/` inventory (D3)

Per decision D3, `concepts/` is **inventory only — not runtime data.**

Each `concepts/*.md` file is a static traceability record. It documents:

- **Source attribution.** The upstream skill (e.g.,
  `compound-engineering:code-review` v3.8.3) and the SHA of the upstream
  source at the point of attribution.
- **Target athanor-native skill section.** Where the concept lives now
  in athanor-native code — typically a named subsection in a
  `skills/<native-skill>/SKILL.md`.
- **Commit SHA of the LIFT.** The athanor commit that landed the
  subsection in the target SKILL.md. This makes the LIFT auditable from
  either end (upstream attribution + athanor delivery).

`concepts/*.md` files are **not** read at runtime by any skill or hook.
No JSON-to-prompt rendering. No templating engine. No
`concepts/{name}.json` → `skills/<x>/SKILL.md` substitution path. The
concept prose itself lives directly inside the target athanor-native
SKILL.md as Markdown subsections — `concepts/` is the ledger that
records what was lifted, from where, and when.

This is the explicit decision over the Plan A alternative (concepts as a
JSON runtime data source) — athanor has no templating engine, and
introducing one would add infrastructure debt without solving a real
problem.

## Post-v0.12.0 vendored surface — 3 items total

Per decision D13, exactly **3 retained items** survive the v0.12.0
atomic cut. No THIN-ADAPTER stubs (decision D9). Aggregate surface
reduction from 94 vendored items to 3 retained: 97%.

### 1 KEEP skill (D8)

- **`/athanor:ce-test-browser`** — user opt-in browser automation. UI
  tooling that sits outside athanor's Thin-Leader orchestrator identity
  but provides real user value. T2 provenance block preserved verbatim.
  No athanor-native equivalent exists; rebuilding it natively was not in
  the v0.12.0 scope.

### 2 KEEP sub-agents (D12)

- **`ce-git-history-analyzer`** — generic git-log discovery dispatch
  target. Not user-invocable as a slash command; used as a worker-side
  dispatch target by `/athanor:debug` and `/athanor:analyze` when git
  history triage is needed.
- **`ce-repo-research-analyst`** — generic repo-research discovery
  dispatch target. Same shape: worker-side dispatch utility, not a
  user-invocable surface.

Both are justified in NOTICE.md and in the triage matrix as utility
agents not covered by the athanor-native lens architecture. The 47
other CE sub-agents are DROP per D12.

### Reasoning — why these 3 survive

- **`ce-test-browser` is user opt-in UI tooling** outside the
  Thin-Leader orchestrator identity. It does not interact with the four
  identity invariants; users invoke it explicitly when they want browser
  automation. Keeping it costs one skill surface; dropping it would
  require either rebuilding the browser automation natively (out of
  v0.12.0 scope) or removing the capability (which deletes user value).
- **The 2 sub-agents are utility dispatch targets**, not lenses. The
  athanor-native `/athanor:review` 6-lens architecture (D4 mechanism,
  below) covers code-review and parallel multi-lens analysis. The two
  surviving sub-agents fill discovery gaps (git history scanning, repo
  research) that the lens architecture does not address. Both are
  worker-side; neither inflates the user-invocable surface.

### What does NOT survive

Per decision D9, `/athanor:ce-plan`, `/athanor:ce-work`, and
`/athanor:ce-lfg` are full DROP. No THIN-ADAPTER one-release redirect
stubs. After the v0.11.8 deprecation warning cycle, invoking any of the
three in v0.12.0 produces an "unknown skill" error. Users migrate to
`/athanor:plan`, `/athanor:work`, `/athanor:lfg`. Migration
responsibility is the user's; the v0.11.8 deprecation preamble
(44 affected SKILL.md files per D14) is the one-cycle warning surface.

For the full retrospective on why these surfaces existed in the first
place — and why the v0.10.0 plan-of-record misread led there — see
`docs/archive/v010-v011-vendoring-scope-correction.md`.

## LIFT pattern

The LIFT pattern moves persona / discipline / discovery prose from a
vendored upstream skill into a subsection of a target athanor-native
SKILL.md. The vendored copy is then removed.

### Mechanism

1. Identify the concept-bearing prose in the upstream skill body (the
   multi-persona reviewer block, the Iron Law / Four Phases debugging
   discipline, the R/A/F/AE-IDs requirements template, the
   skill-discovery preamble pattern, etc.).
2. Lift the prose verbatim into a named subsection of the target
   athanor-native SKILL.md. Voice adjustment is allowed only where
   athanor-native conventions diverge (Thin Leader framing, bilingual
   short headers).
3. Record the LIFT in `concepts/<concept-name>.md` — source attribution
   + target SKILL.md section path + commit SHA.
4. Remove the vendored upstream skill (DROP class) and its directory.

### Worked example — `/athanor:review` (D4)

The multi-persona reviewer pattern lifts from
`compound-engineering:code-review` into `skills/review/SKILL.md` as
prose subsections **plus** `athanor.json` configuration:

- `athanor.json` adds `review.personas[]` — an array of lens
  identifiers (architecture, quality, security, performance, testing,
  documentation by default; user-extensible).
- `skills/review/SKILL.md` carries one prose subsection per lens. Each
  subsection states the lens's mandate, the questions it answers, and
  the output format. The skill body iterates over
  `review.personas[]` and dispatches one clean-context worker per
  configured lens.
- **No separate sub-agent files.** The lens prose lives as inline
  Markdown subsections, not as individual `agents/personas/*.agent.md`
  files. This is the explicit D4 mechanism choice over Plan A's
  hand-wave on the topic.
- `concepts/multi-persona-review.md` records the LIFT — source SHA from
  compound-engineering 3.8.3, target section anchor in
  `skills/review/SKILL.md`, athanor commit SHA of delivery.

### LIFT vocabulary (5 skills, per D14)

The v0.12.0 LIFT vocabulary covers 5 vendored skills:

- `ce-code-review` → `skills/review/SKILL.md` multi-persona subsections
- `ce-debug` discipline → `skills/debug/SKILL.md` Iron Law + Four Phases
  subsection
- `ce-brainstorm` patterns → `skills/discuss/SKILL.md` synthesis-mode
  subsection
- `sp-using-superpowers` preamble → `skills/setup/SKILL.md`
  skill-discovery subsection
- `sp-test-driven-development` → cross-reference into
  `skills/work/SKILL.md` Spec-then-TDD subsection (already partially
  present at v0.8.0; v0.12.0 completes the LIFT)

Each gets an entry in `concepts/`. Each upstream vendored skill is
removed after LIFT.

## Cross-references

- Companion archive (backward-looking retrospective):
  `docs/archive/v010-v011-vendoring-scope-correction.md`
- Pivot plan: `.athanor/sessions/2026-05-22-001/plan.md`
- Decisions log: `.athanor/sessions/2026-05-22-001/decisions.md`
- Durable plan inventory (Phase 1.4 target):
  `docs/plans/2026-05-22-001-feat-v0.12.0-concept-absorption-pivot-plan-INVENTORY.md`
- Identity guard layer (to be removed in v0.12.0 per archive doc):
  `CLAUDE.md` §"Vendored Surface — Identity Guard Layer"
