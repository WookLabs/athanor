# P24 Reactive Channel Fixture Design

Date: 2026-06-18
Branch: `feat/p24-reactive-channel-fixture`

## Context

After P23, Athanor has strong local harness control, deterministic evals,
operator-approved native runtime recipes, and external eval metadata. The
remaining sub-9.5 gap is reactive channel/event compatibility: CI and review
events are currently handled by polling or manual commands rather than by a
checked pushed-event contract.

The right next step is not a webhook listener. A listener would add secret,
network, retry, replay, and permission risk. The safer harness step is a
local-only fixture mapper that proves Athanor can understand pushed event
payloads and route them to existing manual actions.

## Design

`scripts/gates/reactive_channel_fixture.py` reads JSON fixtures under
`tests/fixtures/reactive_channels`. Each fixture contains a `channel`,
`event_type`, `delivery_id`, `payload`, and expected normalized action.

Supported fixture classes:

- GitHub Actions `workflow_run.completed`;
- GitHub pull request review `pull_request_review.submitted`.

The mapper emits:

- normalized event metadata;
- listener safety metadata;
- one or more recommended manual actions;
- evidence requirements;
- deterministic safety fields.

## Safety Properties

- no listener is registered;
- no webhook server is started;
- no network command is executed;
- `auto_execute` is always `false`;
- `external_network_default` is always `false`;
- `external_telemetry` is always `false`;
- `irreversible_actions` is always `0`;
- CI failure handling routes to `@athanor-ci-watcher` only as a manual command
  template.

## Score Impact

P24 is expected to move reactive channels/events from 8.9 to 9.55. It should
not add a default listener. A real listener should require a separate threat
model, secret handling design, replay defense, and opt-in deployment guide.

## Verification

```text
python -m pytest tests/test_regression_reactive_channel_fixture.py tests/test_regression_v019_release_story.py -q
python scripts/gates/reactive_channel_fixture.py --fixture-root tests/fixtures/reactive_channels --json
python scripts/gates/harness_decision_ledger.py --json
```

## Follow-Up

If local fake channel fixtures prove useful across real operations, a future
P25 can design an opt-in listener. That listener must stay off by default and
must authenticate payloads before mapping them to any action.
