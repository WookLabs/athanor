# Ref-Driven Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the full `ref/` analysis into concrete Athanor optimizations while preserving the 11-command, 4-registered-agent Thin Leader surface.

**Architecture:** Implement improvements as local-first gates, scripts, internal skill support, and durable artifacts. Do not add registered agents or broad new command families. Each task must preserve package safety: read-only by default, no external telemetry by default, no irreversible action without explicit operator approval.

**Tech Stack:** Python standard library, pytest, existing Athanor gate/report patterns, Markdown docs, JSON schemas, existing Claude/Codex plugin manifests.

**Scope update 2026-06-20:** The analysis source set is now 346 local `ref/`
repositories, not the earlier 29-, 64-, or 190-repository snapshots. The
expanded pass keeps the no-new-registered-agent decision, but raises the
priority of contract/admission gates, trace replay/search/stats/diff,
file-local work-item/stage transitions, Codex mirror parity, and reference
radar governance.

**Execution update 2026-06-20:** Task 9 was implemented early because the
ref expansion made catalog admission a prerequisite for any further absorption.
Task 6 is now implemented as a read-only Codex mirror parity source map and
gate. Task 10 is now implemented as local trace query tooling plus a
fixture-backed memory retrieval eval.

---

## File Structure

- Create `docs/architecture/2026-06-20-ref-full-optimization-analysis.md`
  - Completed source analysis and priority decision record.

- Create `docs/memory-index.md`
  - Operator-facing contract for local memory search and handoff behavior.

- Create `scripts/gates/memory_index.py`
  - Read-only CLI that indexes committed fixtures or local `.athanor` sources
    when explicitly pointed at them.

- Create `schemas/memory-index-report.schema.json`
  - JSON report schema for memory indexing and retrieval quality.

- Create `tests/test_regression_memory_index.py`
  - Tests for indexing, deduplication, progressive disclosure, and budget caps.

- Modify `agents/learner.md`
  - Add memory-index export rules without creating a new registered agent.

- Modify `skills/work/references/learner-cleaner.md`
  - Keep worker-facing Learner guidance aligned.

- Modify `skills/lfg-goal/SKILL.md`
  - Add loop-run-log, budget, lock, and min-attempt expectations.

- Modify `skills/lfg-goal/references/state-shape.md`
  - Add state fields for `acting_on`, budgets, and run-log references.

- Create `scripts/loops/loop_run_log.py`
  - Append-only helper for goal loop run records.

- Create `schemas/loop-run-log-record.schema.json`
  - Single-record schema for loop run logs.

- Create `tests/test_regression_loop_run_log.py`
  - Tests for append-only shape, lock conflict detection, and budget reports.

- Modify `docs/workflow-trace-evals.md`
  - Document scorer/reducer naming and provenance.

- Modify `scripts/evals/run_workflow_scenarios.py`
  - Add reducer metadata and sample-level limit reporting.

- Create or modify `docs/hook-catalog.md`
  - Add hook UX and promotion-stage guidance if missing.

- Modify `scripts/hooks/safety_patterns.py`
  - Add observe-first pattern ids from hook refs.

- Create `tests/test_regression_hook_safety_patterns_ref_expansion.py`
  - Fixtures for new observe-first safety patterns.

- Modify `plugins/athanor-codex/README.md` and parity tests
  - Document or enforce the source-of-truth mirror mapping.

- Modify `docs/package-footprint-policy.md`
  - Record package reduction candidates and ship-profile strategy.

- Create `docs/package-footprint-reduction.md`
  - Record explicit ship-profile exclusions for dev-only and reference-radar
    buckets without deleting repo-local evidence.

---

### Task 1: Memory Index Contract

**Files:**
- Create: `docs/memory-index.md`
- Create: `scripts/gates/memory_index.py`
- Create: `schemas/memory-index-report.schema.json`
- Create: `tests/test_regression_memory_index.py`

- [x] **Step 1: Write RED tests**

Create tests that expect:

- the gate script exists;
- the schema exists;
- the doc exists;
- indexing supports lesson, trace, goal, and completed-goal records;
- records contain `id`, `kind`, `source_path`, `content_hash`, `title`,
  `summary`, and `tokens_estimate`;
- duplicate `content_hash` values collapse;
- search returns summary rows first, not full content;
- detail lookup by id returns the full record;
- generated context blocks obey a token budget;
- report declares `external_telemetry: false`, `mutates_files_by_default:
  false`, and `irreversible_actions: 0`.

Run:

```text
python -m pytest tests/test_regression_memory_index.py -q
```

Expected: FAIL until the script, schema, docs, and fixtures are added.

- [x] **Step 2: Implement minimal read-only indexer**

Implement `scripts/gates/memory_index.py` using only the standard library.
Use SQLite FTS when available through `sqlite3`; otherwise fall back to simple
case-insensitive token matching with the same report shape.

The CLI should support:

```text
python scripts/gates/memory_index.py --fixture-root tests/fixtures/memory_index --json
python scripts/gates/memory_index.py --source .athanor --json
python scripts/gates/memory_index.py --query "release evidence" --limit 5 --json
python scripts/gates/memory_index.py --detail <id> --json
```

Expected behavior:

- default mode is read-only;
- no daemon;
- no network;
- no vector dependency;
- no automatic context injection.

- [x] **Step 3: Document memory policy**

`docs/memory-index.md` must state:

- progressive disclosure order: search, context, detail;
- no default transcript ingestion;
- no external telemetry;
- token budget requirements;
- retention and stale result warnings;
- relationship to `learner`, `.athanor/lessons`, workflow traces, and
  `lfg-goal`.

- [x] **Step 4: Verify**

Run:

```text
python scripts/gates/memory_index.py --fixture-root tests/fixtures/memory_index --json
python -m pytest tests/test_regression_memory_index.py -q
```

Expected: direct CLI status `pass`, focused tests pass.

### Task 2: Learner And Handoff Integration

**Files:**
- Modify: `agents/learner.md`
- Modify: `skills/work/references/learner-cleaner.md`
- Modify: `skills/lfg-goal/SKILL.md`
- Create: `docs/handoff-artifact.md`
- Create: `tests/test_regression_memory_learner_handoff.py`

- [x] **Step 1: Write RED tests**

Tests should require:

- Learner mentions memory-index export without adding a new registered agent;
- Work reference mentions searchable lesson ids;
- `lfg-goal` mentions a compact handoff artifact;
- no new file appears under `agents/` with `name: memory-indexer`;
- `docs/agent-topology-contract.json` still lists exactly 4 registered agents.

Run:

```text
python -m pytest tests/test_regression_memory_learner_handoff.py tests/test_regression_agent_effort_level.py -q
```

Expected: FAIL until docs are updated.

- [x] **Step 2: Update Learner guidance**

Add a short Learner section that emits memory-indexable fields:

- stable id;
- source artifact path;
- summary;
- evidence refs;
- confidence;
- stale-after hint;
- safe-to-inject summary.

- [x] **Step 3: Add handoff artifact contract**

Document a small handoff artifact containing:

- current goal;
- recent decisions;
- active plan or work item;
- latest run-log reference;
- relevant memory ids;
- resume command;
- open risks.

Do not add a `/handoff` command in this task.

- [x] **Step 4: Verify**

Run the focused tests and:

```text
python scripts/gates/agent_topology.py --json
```

Expected: tests pass and topology still reports 4 registered agents.

### Task 3: `lfg-goal` Run Log, Budget, And Lock

**Files:**
- Modify: `skills/lfg-goal/SKILL.md`
- Modify: `skills/lfg-goal/references/state-shape.md`
- Create: `scripts/loops/loop_run_log.py`
- Create: `schemas/loop-run-log-record.schema.json`
- Create: `tests/test_regression_loop_run_log.py`
- Modify: `docs/durable-loop-controller.md`

- [x] **Step 1: Write RED tests**

Tests should cover:

- valid loop run record schema;
- append-only JSONL writer;
- lock conflict report when `acting_on` differs from requested goal id;
- budget warnings for max cycles, max wall time, or token estimate;
- min-attempt gate for risky or high-score-target tasks;
- no irreversible action in the helper.

Run:

```text
python -m pytest tests/test_regression_loop_run_log.py -q
```

Expected: FAIL until helper/schema/docs exist.

- [x] **Step 2: Implement append-only helper**

`scripts/loops/loop_run_log.py` should expose pure helpers plus a CLI:

```text
python scripts/loops/loop_run_log.py append --goal-dir tests/fixtures/loop_run_log/goal --event cycle_started --json
python scripts/loops/loop_run_log.py inspect --goal-dir tests/fixtures/loop_run_log/goal --json
```

The helper must not delete or rewrite existing records.

- [x] **Step 3: Update `lfg-goal` state shape**

Add fields:

- `acting_on`;
- `loop_run_log`;
- `budget.max_cycles`;
- `budget.max_wall_minutes`;
- `budget.max_token_estimate`;
- `min_attempts`;
- `last_evaluator_role`;
- `lock_status`.

- [x] **Step 4: Verify**

Run:

```text
python scripts/loops/loop_run_log.py inspect --goal-dir tests/fixtures/loop_run_log/goal --json
python -m pytest tests/test_regression_loop_run_log.py -q
python scripts/gates/runtime_conformance.py --json
```

Expected: focused tests pass; runtime conformance still passes.

### Task 4: Scorer/Reducer Eval Profile

**Files:**
- Modify: `docs/workflow-trace-evals.md`
- Modify: `scripts/evals/run_workflow_scenarios.py`
- Modify: `schemas/workflow-trace-scenario.schema.json` if present
- Create: `tests/test_regression_workflow_scorer_reducer.py`

- [x] **Step 1: Write RED tests**

Tests should require:

- each grader result has `scorer_id`;
- scenario output has reducer metadata;
- reducer records `method`, `sample_limit`, and `score_provenance`;
- retry/resume identifiers are accepted in scenario metadata;
- old scenario fixtures still pass.

Run:

```text
python -m pytest tests/test_regression_workflow_scorer_reducer.py tests/test_regression_workflow_trace_evals.py -q
```

Expected: FAIL until scenario runner/report shape is extended.

- [x] **Step 2: Extend scenario runner**

Keep existing output backward-compatible. Add optional fields rather than
renaming existing ones.

- [x] **Step 3: Document eval profile**

Add a section mapping Athanor terms to `Task`, `Trace Fixture`, `Scorer`, and
`Reducer`. State that model-graded evals are optional and not required for
default local gates.

- [x] **Step 4: Verify**

Run:

```text
python -m pytest tests/test_regression_workflow_scorer_reducer.py tests/test_regression_workflow_trace_evals.py -q
python scripts/gates/maintenance_profile.py --skip-claude --json
```

Expected: focused tests and maintenance profile pass or retain only existing
bounded warnings.

### Task 5: Hook Rule Pack UX And Safety Corpus Expansion

**Files:**
- Modify: `scripts/hooks/safety_patterns.py`
- Modify: `docs/hook-safety-pattern-corpus.md`
- Modify: `docs/hook-catalog.md`
- Create: `tests/test_regression_hook_safety_patterns_ref_expansion.py`
- Modify: `scripts/gates/hook_install_dry_run.py` only if list/info output is implemented there

- [x] **Step 1: Write RED tests**

Tests should require:

- new pattern ids for dangerous shell deletion variants and secret-path reads;
- stage is `observe` by default;
- fixtures do not block by default;
- each pattern has `source_ref`, `risk`, and `promotion_condition`;
- hook catalog exposes list/info metadata.

Run:

```text
python -m pytest tests/test_regression_hook_safety_patterns_ref_expansion.py -q
```

Expected: FAIL until patterns/docs are added.

- [x] **Step 2: Add observe-first patterns**

Use ref-derived ideas from Karanb, Hookify, and Disler, but do not enable new
default blockers.

- [x] **Step 3: Add hook UX documentation**

Document the intended operator flow:

```text
list -> info -> preview -> dry-run install -> explicit apply
```

If a CLI subcommand is added, it must remain read-only unless the existing
installer apply path is explicitly invoked.

- [x] **Step 4: Verify**

Run:

```text
python -m pytest tests/test_regression_hook_safety_patterns_ref_expansion.py tests/test_regression_hook_safety_patterns.py -q
python scripts/gates/hook_install_dry_run.py --json
```

Expected: focused tests pass; dry-run remains read-only.

### Task 6: Codex Mirror Source-Of-Truth

**Files:**
- Modify: `tests/test_regression_codex_companion.py`
- Modify: `plugins/athanor-codex/README.md`
- Create: `docs/codex-mirror-source-map.md`
- Optional create: `scripts/gates/codex_mirror_parity.py`

- [x] **Step 1: Write RED parity tests**

Tests should require a single source map listing every Claude skill and Codex
mirror skill, including `assess` and `prompt-gen`.

Run:

```text
python -m pytest tests/test_regression_codex_companion.py -q
```

Expected: FAIL if the source map/gate does not exist.

- [x] **Step 2: Add source map or parity gate**

Prefer a read-only parity gate before adding a generator. The gate should
report:

- missing mirror skills;
- stale version references;
- unmatched descriptions;
- unsupported Claude-only hooks.

- [x] **Step 3: Verify**

Run:

```text
python scripts/gates/codex_mirror_parity.py --json
python -m pytest tests/test_regression_codex_companion.py -q
```

Expected: gate passes and focused tests pass.

### Task 7: Package Footprint Reduction Plan

**Files:**
- Modify: `docs/package-footprint-policy.md`
- Modify: `scripts/gates/package_footprint_policy.py` only if supported by the existing design
- Create: `docs/package-footprint-reduction.md`
- Create: `tests/test_regression_package_footprint_reduction.py`

- [x] **Step 1: Write RED tests**

Tests should require a documented action for each current dev-only candidate
bucket:

- docs/plans;
- docs/archive;
- tests;
- docs/architecture;
- ref.

Run:

```text
python -m pytest tests/test_regression_package_footprint_reduction.py -q
```

Expected: FAIL until the reduction doc exists and links current gate output.

- [x] **Step 2: Document ship-profile strategy**

Do not delete historical files in this task. Define what should be excluded
from marketplace packages when packaging supports it.

- [x] **Step 3: Verify**

Run:

```text
python scripts/gates/package_footprint_policy.py --json
python -m pytest tests/test_regression_package_footprint_reduction.py -q
```

Expected: gate remains warn or better, with documented bounded candidates.

### Task 8: Release Story And Composite Verification

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/STATE.md`
- Modify: `.github/workflows/validate-plugin.yml` only for new stable gates
- Modify: `tests/test_regression_v019_release_story.py`

- [x] **Step 1: Add release story tests**

Tests should require changelog/state mentions for implemented tasks and CI
coverage for any new stable gate.

- [x] **Step 2: Run focused verification**

Run:

```text
git diff --check
python scripts/gates/agent_topology.py --json
python scripts/gates/package_knowledge_index.py --json
python scripts/gates/runtime_conformance.py --json
python scripts/gates/organization_score.py --json
python -m pytest tests -q
```

Expected: no whitespace errors; gates pass; test suite passes or only existing
expected skips/xpasses remain.

### Task 9: Contract And Admission Gates

**Files:**
- Create: `docs/catalog-admission-policy.md`
- Create: `schemas/catalog-entry.schema.json`
- Create: `scripts/gates/catalog_admission.py`
- Optional create: `scripts/gates/plugin_manifest_contract.py`
- Create: `tests/test_regression_catalog_admission.py`

- [x] **Step 1: Write RED tests**

Tests should require source-reference entries to declare `id`, `category`,
`url`, `local_ref`, `why_included`, `license`, `last_reviewed`,
`adoption_status`, `runtime_surface_delta`, and `sunset_condition`.

- [x] **Step 2: Implement read-only admission report**

The report should classify refs as `adopt`, `adapt`, `observe`, `reject`, or
`sunset`, with the weakest scored dimension capping the recommendation.

- [x] **Step 3: Verify**

Run:

```text
python scripts/gates/catalog_admission.py --json
python -m pytest tests/test_regression_catalog_admission.py -q
```

Expected: report is read-only and rejects runtime surface growth without
evidence.

### Task 10: Trace Replay And Retrieval Quality

**Files:**
- Modify: `docs/workflow-trace-evals.md`
- Create: `docs/memory-retrieval-eval.md`
- Create: `scripts/evals/workflow_trace_query.py`
- Create: `scripts/gates/memory_retrieval_eval.py`
- Create: `schemas/memory-retrieval-eval-report.schema.json`
- Create: `tests/test_regression_workflow_trace_query.py`
- Create: `tests/test_regression_memory_retrieval_eval.py`

- [x] **Step 1: Write RED tests**

Tests should require timeline, stats, search, and diff modes for local trace
fixtures, plus memory retrieval metrics for query/gold-id fixtures.

- [x] **Step 2: Implement local read-only scripts**

No live listeners, no exporters, no dashboards, no external telemetry.

- [x] **Step 3: Verify**

Run:

```text
python scripts/evals/workflow_trace_query.py --trace-path tests/fixtures/workflow_trace_query/base.jsonl --mode stats --json
python scripts/evals/workflow_trace_query.py --trace-path tests/fixtures/workflow_trace_query/base.jsonl --compare-path tests/fixtures/workflow_trace_query/candidate.jsonl --mode diff --json
python scripts/gates/memory_retrieval_eval.py --fixture-root tests/fixtures/memory_index --queries tests/fixtures/memory_retrieval_eval/queries.json --json
python -m pytest tests/test_regression_workflow_trace_query.py tests/test_regression_memory_retrieval_eval.py -q
```

Expected: scripts report deterministic local metrics.

### Task 11: Work-Item Stage Transition Gate

**Files:**
- Create: `docs/work-item-stage-transitions.md`
- Create: `schemas/work-item-stage-report.schema.json`
- Create: `scripts/gates/work_item_stage.py`
- Create: `tests/test_regression_work_item_stage.py`

- [x] **Step 1: Write RED tests**

Tests should require file-local work items with actor, owner, stage,
dependencies, required evidence, transition reason, approval/intervention
state, and append-only audit entries.

- [x] **Step 2: Implement read-only validator**

Validate state transitions such as `queued -> work -> review -> done`,
`work -> blocked`, and `review -> work`, without running an MCP server or
mutating state.

- [x] **Step 3: Verify**

Run:

```text
python scripts/gates/work_item_stage.py --fixture-root tests/fixtures/work_items/valid --json
python -m pytest tests/test_regression_work_item_stage.py -q
```

Expected: invalid transitions fail with actionable missing-evidence messages.

## Non-Goals

- Do not add registered agents.
- Do not add broad language/domain/SaaS skill packs.
- Do not enable new lifecycle hooks by default.
- Do not add a daemon, vector DB, web viewer, remote prompt policy, or memory
  MCP surface to the core plugin.
- Do not delete historical docs or tests as part of this plan.
- Do not make model-graded external evals mandatory for local verification.

## Completion Criteria

- The full ref analysis document exists and covers all 346 repositories through
  curated analysis plus the read-only catalog admission gate.
- New implementation work preserves 11-command and 4-agent topology unless a
  separate topology decision explicitly proves otherwise.
- New memory/loop/eval/hook/package changes are covered by read-only gates or
  focused regression tests.
- Package footprint warning count is either reduced or bounded with a
  documented ship-profile decision.
- No default external telemetry or irreversible actions are introduced.
