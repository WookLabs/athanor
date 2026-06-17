# P20 Scheduled Maintenance Profile Design

Date: 2026-06-18
Status: planned

## Context

The post-P16 research report scored recurring maintenance at 8.7 because
entropy cleanup exists as a gate but there is no packaged maintenance profile
that an operator, CI job, or Claude `/loop` prompt can run consistently.

P20 adds that profile without creating a scheduler or enabling irreversible
cleanup. It composes already read-only gates into one operator report.

## Scope

Add `scripts/gates/maintenance_profile.py`.

The profile runs:

- entropy cleanup, including stale ref checks;
- distribution smoke;
- observability trend snapshot;
- native runtime probe;
- harness decision ledger.

It emits one JSON report with:

- step status;
- warnings and failures;
- command lines an operator can reuse;
- a suggested `/loop` prompt;
- `irreversible_actions: 0`.

## Non-Goals

- No automatic scheduled task registration.
- No worktree creation.
- No ref repository updates.
- No file deletion.
- No trend history append by default.
- No external telemetry.

## Architecture

The gate uses Python imports rather than shelling out for the default path:

- `scripts.gates.entropy_cleanup.build_report`
- `scripts.gates.distribution_smoke.build_report`
- `scripts.observability.collect_trend_snapshot.collect_snapshot`
- `scripts.gates.native_runtime_probe.build_live_profile` and `build_probe`
- `scripts.gates.harness_decision_ledger.build_report`

CLI flags keep local and CI use predictable:

- `--json`
- `--skip-claude` for environments without the Claude CLI
- `--samples`
- `--plan-warn-days`
- `--ref-warn-days`
- `--strict` to turn warnings into exit 1

## Score Movement

Expected score movement after P20:

- Recurring maintenance loop: 8.7 -> 9.55
- Live observability: 9.25 -> 9.45

P20 does not fully solve external benchmark/sandbox interop or package
footprint. Those remain separate candidates.

