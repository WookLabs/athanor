# Reactive Channel Fixtures

`scripts/gates/reactive_channel_fixture.py` evaluates local fake event
payloads for pushed CI and pull request review events. It proves Athanor can
normalize those events and route them to existing manual actions without
starting a listener.

Run the fixture gate:

```text
python scripts/gates/reactive_channel_fixture.py --fixture-root tests/fixtures/reactive_channels --json
```

Run one fixture:

```text
python scripts/gates/reactive_channel_fixture.py --fixture tests/fixtures/reactive_channels/github-workflow-run-failure.json --json
```

## Supported Events

- `github-actions` / `workflow_run`: maps completed workflow runs to
  `ci.failed`, `ci.passed`, or `ci.neutral`.
- `github-pr-review` / `pull_request_review`: maps submitted reviews to
  `review.changes_requested`, `review.approved`, or a state-specific record.

## Safety Contract

The gate is local-only and read-only:

- no webhook listener is registered;
- no server is started;
- no network command is executed;
- every action has `auto_execute: false`;
- every action has `listener_registered: false`;
- every action has `external_network_default: false`;
- `external_telemetry` is false;
- `irreversible_actions` is 0.

CI failure fixtures emit command templates for manual operator use, including
`@athanor-ci-watcher` and `gh pr checks`. Review-change fixtures emit review
response templates such as `gh pr view` and `/athanor:review`.

## Operator Rule

Treat `command_templates` as suggested manual commands, not as an execution
plan. Run them only after confirming the event payload is relevant to the
current branch or pull request.
