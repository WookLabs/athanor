# Package Knowledge Index

Last reviewed: 2026-06-18.

This is the short package-facing map for Athanor's current runtime and
operator surface. Use it first when a packaged worker needs current context
without scanning repo-local development history.

## Runtime Surface

- Root overview: [README](../README.md).
- Runtime instructions: [CLAUDE](../CLAUDE.md).
- User commands: `/athanor:plan`, `/athanor:work`, `/athanor:review`,
  `/athanor:lfg`, `/athanor:lfg-goal`, `/athanor:setup`,
  `/athanor:discuss`, `/athanor:analyze`, `/athanor:debug`.
- Registered agents: `learner`, `releaser`, `ci-watcher`,
  `codex-dispatcher`.

## Operator Gate Map

- Distribution smoke:
  [doc](distribution-smoke.md),
  [gate](../scripts/gates/distribution_smoke.py).
- Package footprint policy:
  [doc](package-footprint-policy.md),
  [gate](../scripts/gates/package_footprint_policy.py).
- Maintenance profile:
  [doc](maintenance-profile.md),
  [gate](../scripts/gates/maintenance_profile.py).
- Harness decision ledger:
  [doc](harness-decision-ledger.md),
  [gate](../scripts/gates/harness_decision_ledger.py).
- Native runtime probe:
  [doc](native-runtime-probe.md),
  [gate](../scripts/gates/native_runtime_probe.py).
- Native runtime playbook:
  [doc](native-runtime-playbook.md),
  [gate](../scripts/gates/native_runtime_playbook.py).
- Reactive channel fixtures:
  [doc](reactive-channel-fixtures.md),
  [gate](../scripts/gates/reactive_channel_fixture.py).

Run this index gate:

```text
python scripts/gates/package_knowledge_index.py --json
```

## Safety Contracts

- Default package-facing gates are read-only.
- `mutates_files_by_default` stays false for this index gate.
- `external_telemetry` stays false.
- `irreversible_actions` stays 0.
- Native runtime recipes and reactive channel actions are templates only until
  the operator explicitly approves execution.

## Ship Profile Boundary

The package-facing index links current runtime/operator docs and gates only.
Research notes, implementation planning records, regression suites, cloned
references, CI workflow files, and local runtime state remain repo-local
engineering memory rather than first-read packaged context.

## Freshness

Update this index when a new current operator gate, runtime surface, safety
contract, or package boundary is added. CI runs
`scripts/gates/package_knowledge_index.py` so stale links, missing back-links,
and development-history links fail before broad regression tests.
