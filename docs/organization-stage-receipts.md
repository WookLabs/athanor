# Organization Stage Receipts

Organization work items record where work sits in the lifecycle. Stage
receipts record what proved a stage handoff.

P28 adds a local-only adapter for creating and validating those receipts. The
default gate is read-only; it validates committed receipts under:

```text
docs/organization-stage-receipts/*.json
```

Local runtime emissions default to:

```text
.athanor/organization-stage-receipts/*.json
```

The adapter writes only when `--emit` is passed. It updates a work item only
when `--apply-work-item-update` is also passed with a concrete work-item path.

## Receipt Contract

Each receipt records:

- stable `id`, `work_item_id`, `stage`, `owner_office`, and `owner_role`;
- `decision`: `completed`, `blocked`, `skipped`, or `handoff`;
- `source`: `lfg`, `lfg-goal`, `manual`, or `gate`;
- `evidence_refs[]` that resolve inside the repository;
- `source_receipts[]` for LFG or LFG-goal-backed evidence;
- command evidence with exit code and short result text;
- safety metadata proving no default mutation, telemetry, runtime launch, or
  irreversible action.

For `lfg-goal` sources, the source receipt must look like validator output: it
must contain `## Step Receipts` and `validator_status:`.

## Operating Rules

- Validate committed receipts:

  ```text
  python scripts/gates/organization_stage_receipt.py --json
  ```

- Preview a local receipt without writing:

  ```text
  python scripts/gates/organization_stage_receipt.py --json --work-item-id <id> --stage <stage> --decision completed --summary "<summary>" --source lfg-goal --source-receipt <path> --evidence-ref <path>
  ```

- Emit a local receipt:

  ```text
  python scripts/gates/organization_stage_receipt.py --json --emit --work-item-id <id> --stage <stage> --decision completed --summary "<summary>" --source lfg-goal --source-receipt <path> --evidence-ref <path>
  ```

- Emit and explicitly update the work item:

  ```text
  python scripts/gates/organization_stage_receipt.py --json --emit --apply-work-item-update --work-item-path docs/organization-work-items/<id>.json --next-stage <next-stage> --work-item-id <id> --stage <stage> --decision completed --summary "<summary>" --source lfg-goal --source-receipt <path> --evidence-ref <path>
  ```

This closes the P27 gap: stage state no longer relies only on a leader-written
work-item record. A stage can now have a standalone receipt artifact that the
registry can reference.
