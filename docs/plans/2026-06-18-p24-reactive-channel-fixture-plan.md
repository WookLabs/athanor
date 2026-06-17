# P24 Reactive Channel Fixture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-only fake channel/event fixture gate that normalizes pushed CI and review events into safe Athanor action recommendations without registering a default listener or auto-executing networked commands.

**Architecture:** Introduce a read-only mapper for fixture payloads shaped like GitHub Actions `workflow_run` and pull request review events. The mapper emits normalized event metadata plus recommended manual actions such as `dispatch-ci-watcher`, `record-ci-pass`, or `plan-review-response`. All actions remain templates with `auto_execute: false`, `listener_registered: false`, `external_network_default: false`, and `irreversible_actions: 0`.

**Tech Stack:** Python stdlib, JSON fixtures, JSON schemas, pytest, existing `ci-watcher` agent contract.

---

## File Structure

- Create `scripts/gates/reactive_channel_fixture.py`: read-only event fixture mapper and CLI.
- Create `schemas/reactive-channel-fixture-report.schema.json`: fixture report and reactive plan schema.
- Create `tests/fixtures/reactive_channels/*.json`: local fake payload fixtures for CI failure, CI pass, and review changes requested.
- Create `tests/test_regression_reactive_channel_fixture.py`: RED/GREEN coverage for schema validity, action mapping, blocked auto-execution, and invalid payload handling.
- Modify `.github/workflows/validate-plugin.yml`: add named reactive channel fixture gate.
- Modify `tests/test_regression_v019_release_story.py`: assert CI and changelog mention P24.
- Modify `CHANGELOG.md`: document the fixture gate in Unreleased.
- Create `docs/reactive-channel-fixtures.md`: operator usage and safety notes.
- Create `docs/architecture/2026-06-18-p24-reactive-channel-fixture-design.md`: architecture rationale and score impact.
- Create `docs/harness-decisions/2026-06-18-p24-reactive-channel-fixture.json`: decision ledger entry.

## Task 1: RED Tests

- [ ] Add tests that call:

```text
python scripts/gates/reactive_channel_fixture.py --fixture-root tests/fixtures/reactive_channels --json
```

- [ ] Assert the report has `schema_version: 1`, `status: "pass"`, three fixtures, zero auto listeners, zero auto-executed actions, and zero irreversible actions.
- [ ] Assert a failed `workflow_run` maps to `normalized_type: "ci.failed"` and action `dispatch-ci-watcher` with `@athanor-ci-watcher` and `gh pr checks` command templates.
- [ ] Assert a successful `workflow_run` maps to `record-ci-pass` with no network command templates.
- [ ] Assert a `pull_request_review` changes-requested payload maps to `plan-review-response`.
- [ ] Assert malformed payloads return exit code 2.
- [ ] Assert schema, docs, architecture note, CI gate, and changelog tokens exist.
- [ ] Run the focused tests and confirm they fail because the mapper does not exist yet.

## Task 2: Event Mapper

- [ ] Add `normalize_payload(raw_fixture_or_payload)` with support for:
  - `github.workflow_run`;
  - `github.pull_request_review`.
- [ ] Require repository, event type, delivery id, and pull request number where the action needs a PR.
- [ ] Emit a reactive plan with deterministic fields:
  - `event.source`
  - `event.event_type`
  - `event.normalized_type`
  - `event.repository`
  - `event.pr_number`
  - `listener.default_enabled`
  - `actions[]`
  - `safety`
- [ ] Keep every action descriptive only: no command execution, no listener registration, no network by default, no telemetry.
- [ ] Add fixture root expectation matching for normalized type and action ids.

## Task 3: Schema, CI, Docs, Ledger

- [ ] Add `schemas/reactive-channel-fixture-report.schema.json`.
- [ ] Add CI step:

```text
Reactive channel fixture gate
python scripts/gates/reactive_channel_fixture.py --fixture-root tests/fixtures/reactive_channels --json
```

- [ ] Update release-story tests, changelog, operator docs, architecture note, and harness decision ledger.
- [ ] Update the current workflow/loop/harness comparison so reactive channel compatibility is recorded as >=9.5 after P24.

## Task 4: Verification

- [ ] Run:

```text
python -m pytest tests/test_regression_reactive_channel_fixture.py tests/test_regression_v019_release_story.py -q
python scripts/gates/reactive_channel_fixture.py --fixture-root tests/fixtures/reactive_channels --json
python scripts/gates/harness_decision_ledger.py --json
python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json
python -m pytest tests/ -q
git diff --check
```

- [ ] Commit, merge to `main`, push, and mark the active optimization goal complete only if the scorecard has no sub-9.5 dimensions.

## Self-Review

- Spec coverage: P24 covers fake pushed event fixtures, CI/review action mapping, CI visibility, docs, and ledger.
- Placeholder scan: no TBD/TODO/fill-in-later placeholders.
- Type consistency: `reactive_channel_fixture`, `normalized_type`, `listener.default_enabled`, `auto_execute`, and `external_network_default` names are consistent across tests, implementation, schema, and docs.

