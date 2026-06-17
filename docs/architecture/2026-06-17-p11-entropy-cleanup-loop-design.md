# P11 Entropy Cleanup Loop Design

Date: 2026-06-17
Branch: `feat/p11-entropy-cleanup-loop`
Status: design for implementation

## Goal

Add an executable local cleanup sensor that makes Athanor's accumulating
harness entropy visible before P12 adds more live orchestration surfaces.

The P11 loop is intentionally read-only. It does not delete stale files, edit
plans, prune refs, or rewrite generated mirrors. Its job is to report actionable
cleanup work as structured JSON, support CI smoke coverage, and give future
agents a stable source of truth for where entropy is accumulating.

## Why This Comes Before P12

P12 will likely add dynamic workflow, agent-team, and worktree adapters. Those
surfaces increase fanout, generated artifacts, background state, and docs that
can drift. OpenAI's harness write-up and Fowler's harness model both point to
the same ordering: keep the cleanup sensors close to the work before increasing
autonomy.

P11 therefore creates the recurring "garbage collection" layer first.

## Design Choices

### Approach A: Strong Fail Gate For All Stale Items

This would fail CI whenever an old plan, ref, capture-only hook candidate, or
mirror appears stale.

Rejected for P11. Athanor already carries historical plans, archived state, and
reference clones. Failing on age alone would force churn instead of producing a
useful cleanup queue.

### Approach B: Manual Checklist Document

This would document cleanup rules and ask agents to inspect them during release
work.

Rejected. Athanor's strongest pattern is executable evidence. A prose-only
cleanup checklist would not raise the maintainability score enough.

### Approach C: Structured Read-Only Entropy Report

Selected. A CLI emits a typed report with `pass`, `warn`, and `fail` findings.
Structural defects fail. Age/freshness issues warn unless `--strict` is used.
CI can run the non-strict gate now, while release or scheduled jobs can run
strict mode later.

## Architecture

Add one new gate script:

- `scripts/gates/entropy_cleanup.py`

Add one report schema:

- `schemas/entropy-cleanup-report.schema.json`

Add one focused regression test file:

- `tests/test_regression_entropy_cleanup.py`

Add one operator document:

- `docs/entropy-cleanup.md`

Update release story and CI:

- `.github/workflows/validate-plugin.yml`
- `CHANGELOG.md`
- `tests/test_regression_v019_release_story.py`

The script follows the existing gate pattern:

- stdlib only;
- read-only by default;
- `--json` for machine-readable output;
- exit `0` on pass or warn in non-strict mode;
- exit `1` on fail, and on warn when `--strict` is set;
- exit `2` for invalid input or CLI usage.

## Report Shape

Top-level report:

```json
{
  "schema_version": 1,
  "status": "pass",
  "summary": {
    "checks": 0,
    "warnings": 0,
    "errors": 0,
    "actions": 0
  },
  "generated_at": "2026-06-17T00:00:00Z",
  "categories": {
    "plans": {},
    "hook_candidates": {},
    "refs": {},
    "mirrors": {}
  },
  "checks": [],
  "actions": []
}
```

Each check has:

- `id`: stable machine id;
- `category`: `plans`, `hook_candidates`, `refs`, or `mirrors`;
- `status`: `pass`, `warn`, or `fail`;
- `message`: human-readable summary;
- optional `path`, `age_days`, `threshold_days`, `details`.

Each action has:

- `id`: stable action id;
- `severity`: `info`, `warn`, or `fail`;
- `category`;
- `target`;
- `recommendation`.

## Sensors

### Plan Age Sensor

Inputs:

- `docs/plans/*.md`

Logic:

- Parse leading date from filenames shaped `YYYY-MM-DD-*`.
- Count checked and unchecked checkbox lines.
- If a dated plan has unchecked boxes older than `--plan-warn-days`, emit a
  warning action.
- Missing date prefix is a warning, not a failure, because some historical docs
  may not follow the newest naming convention.

Default threshold:

- `--plan-warn-days 30`

Reasoning:

Plans are allowed to be historical, but unfinished dated plans should be visible
to cleanup agents.

### Hook Candidate Age Sensor

Inputs:

- `hooks/catalog.json`

Logic:

- For `runtime_default: "capture-only"` entries, require:
  - `candidate_since`: ISO date `YYYY-MM-DD`;
  - `review_after_days`: non-negative integer;
  - non-empty `source_refs`.
- Missing required candidate metadata is a failure. The catalog cannot manage
  candidate aging without it.
- Candidate age greater than `review_after_days` is a warning action.

Reasoning:

Capture-only candidates are useful, but they should not live forever without a
review date.

### Ref Freshness Sensor

Inputs:

- direct children of `ref/`

Logic:

- If `ref/` is absent, pass with zero refs.
- For each child that is a git repo, report:
  - path;
  - current HEAD;
  - active branch if available;
  - last commit date;
  - age in days.
- If a git repo's last commit age exceeds `--ref-warn-days`, emit a warning
  action.
- Non-git children under `ref/` are warnings, not failures.

Default threshold:

- `--ref-warn-days 45`

Reasoning:

Refs are external research inputs. Staleness is not a correctness failure, but
it must be visible before a future analysis relies on old references.

### Mirror/Conformance Sensor

Inputs:

- `docs/runtime-surface-contract.json`
- `plugins/athanor-codex/`
- root Claude plugin surface

Logic:

- Reuse `scripts.gates.runtime_conformance.build_report`.
- If conformance reports fail, P11 reports a `mirrors.runtime_conformance`
  failure.
- If it passes, P11 records the conformance check count and status.

Reasoning:

P9 already owns detailed mirror drift checks. P11 should not duplicate all of
that logic; it should include the conformance result in the entropy report so a
cleanup run has one place to look.

## Candidate Metadata Migration

P11 adds candidate lifecycle metadata to each capture-only hook catalog entry:

```json
"candidate_since": "2026-06-16",
"review_after_days": 30
```

This is metadata only. It does not enable new hooks, change runtime policy, or
alter installation behavior.

## CI Integration

Add a named CI step after the observability trend snapshot gate:

```yaml
- name: Entropy cleanup report gate
  shell: bash
  run: python scripts/gates/entropy_cleanup.py --json
```

Non-strict mode is deliberate. The gate fails structural report defects but
does not fail on stale age warnings yet. A future scheduled cleanup or release
job can add `--strict` after the team has normalized the warning queue.

## Error Handling

- Invalid JSON input: exit `2`.
- Missing required files for core sensors, such as `hooks/catalog.json` or
  `docs/runtime-surface-contract.json`: exit `2`.
- Runtime conformance failure: report status `fail`, exit `1`.
- Candidate lifecycle metadata missing: report status `fail`, exit `1`.
- Age warnings only: report status `warn`, exit `0` unless `--strict`.

## Testing Strategy

Use TDD with focused tests:

1. Current repo CLI emits schema-valid JSON and exits `0`.
2. Capture-only candidate missing `candidate_since` fails.
3. Capture-only candidate older than `review_after_days` emits a warning action.
4. Old plan with unchecked boxes emits a warning action.
5. Runtime conformance failure is surfaced as a mirror failure.
6. CI and changelog release story mention P11.

The test fixtures should construct temporary miniature repos for behavior that
would be hard to trigger safely in the real repo.

## Non-Goals

- No automatic deletion.
- No network fetch or `git pull` for refs.
- No scheduled task creation.
- No external telemetry.
- No replacement for P9 runtime conformance.
- No P12 dynamic workflow or worktree execution behavior.

## Architecture Review

The selected design keeps P11 as a sensor, not an actor. That is the right
boundary because cleanup suggestions are safe to run in CI and easy for future
agents to consume, while edits/deletions require judgment. The gate composes
existing P9 conformance instead of cloning it, which keeps responsibilities
clear. The main risk is warning fatigue; the mitigation is stable action ids,
threshold flags, and `--strict` only for contexts that intentionally want a
zero-warning queue.

## Self-Review

- Placeholder scan: no unresolved placeholders.
- Scope check: one CLI/report/schema/docs change; P12 runtime adapters are out
  of scope.
- Consistency check: report status and exit semantics are aligned across design
  and testing strategy.
- Risk check: default mode is read-only and non-strict; no user settings or
  external refs are mutated.

