# Work-Item Stage Transitions

This gate validates a small, file-local work-item stage machine. It is the
bounded version of the broader organization registry: no MCP server, daemon,
listener, dashboard, or automatic agent generation.

## Inputs

The validator reads a fixture root containing:

```text
work-items.json
transitions.jsonl
```

`work-items.json` declares each work item with stable `id`, `owner`, current
`stage`, dependency blockers, required evidence, approval state, and
intervention state. `transitions.jsonl` is an append-only audit log with one
JSON object per stage move.

Run:

```text
python scripts/gates/work_item_stage.py --fixture-root tests/fixtures/work_items/valid --json
```

## Stage Contract

Allowed transitions are deliberately small:

- `queued -> work`
- `queued -> blocked`
- `work -> review`
- `work -> blocked`
- `review -> done`
- `review -> work`
- `review -> blocked`
- `blocked -> work`

The report reconstructs final item state from the audit log and fails when the
declared item stage does not match the reconstructed stage.

## Evidence And Dependency Rules

- Dependency blockers must point to known work items.
- Dependencies must be in `done` before a dependent item advances.
- Required evidence paths must resolve inside the fixture root.
- Transitions into `review` or `done` require `evidence_refs[]`.
- The JSONL audit sequence must be gap-free and append-only shaped.

The gate cannot prove historical file append-only integrity by itself; it
validates the audit shape that makes append-only review possible.

## Approval And Intervention States

Approval states are:

- `not_required`
- `requested`
- `approved`
- `denied`

Intervention states use the human-in-the-loop vocabulary:

- `none`
- `proceed`
- `deny`
- `guide`
- `interrupt`
- `transform`

`review -> done` requires `approved`. A denied approval cannot advance work
except to `blocked`. `deny` and `interrupt` interventions must also route the
item to `blocked`.

## Safety

The gate is read-only by default:

- no external telemetry;
- no runtime launch;
- no file mutation;
- `irreversible_actions` stays `0`.

This keeps work-item/stage control as an auditable harness layer rather than a
new registered agent or always-on control plane.
