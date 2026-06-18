# Organization Work-Item Registry

The organization operating model defines the lifecycle. The work-item
registry records where concrete work is in that lifecycle.

This registry is the next maturity layer toward a 9.8/10 organization score:
it turns stage ownership from guidance into durable state that gates can
inspect. It remains read-only by default and does not add live listeners,
registered agents, external telemetry, or irreversible automation.

## Registry Location

Committed organization-memory work items live under:

```text
docs/organization-work-items/*.json
```

Local runtime work items may later use `.athanor/organization-work-items/`,
but the committed registry is the stable evidence surface for design,
release, postmortem, and policy promotion decisions. Stage receipt artifacts
use `docs/organization-stage-receipts/*.json` for committed evidence and
`.athanor/organization-stage-receipts/*.json` for local runtime emission.

## Required Work-Item Shape

Each work item is a JSON object with:

- stable `id`, `title`, `status`, `created_at`, and `updated_at`;
- `target_score` when the item is score-driven;
- `source_refs` and `acceptance_criteria`;
- `current_stage`, `owner_office`, and `owner_role`;
- `artifacts[]` with stage, path, kind, and status;
- ordered `stage_history[]`;
- completed stage receipts;
- read-only safety metadata.

## Stage History Contract

Stage history must be ordered according to
`docs/organization-operating-model.md`:

```text
intake -> triage -> requirements -> research -> planning -> design-review
-> execution -> verification -> release -> postmortem -> memory-update
```

An active item must have exactly one `active` or `blocked` history entry, and
that entry must match `current_stage`. Completed stages require a `receipt_ref`
that resolves inside the repository. This is the company-like handoff: a stage
cannot disappear just because the leader says it is done.

## 9.8 Maturity Design

The path from the current organization model to 9.8 is:

1. Work-item registry: durable stage state, owner, artifacts, and receipts.
2. Runtime receipt adapter: emit per-stage receipts from real LFG/LFG-goal runs.
3. Policy promotion gate: turn repeated lessons into candidate policy, policy,
   gate candidate, gate, or retired state.
4. Operational score gate: compute the organization score from evidence rather
   than prose.
5. External benchmark profile: run a sandboxed benchmark gate as normal
   operating evidence.

P27 implements item 1 as a read-only, schema-backed gate. P28 implements item
2 with `scripts/gates/organization_stage_receipt.py`; it writes only with
`--emit` and updates work items only with `--apply-work-item-update`. P29
implements item 3 with `scripts/gates/policy_promotion_ledger.py`, requiring
policy promotion records to carry evidence, rollback, gate tests, schemas, and
retirement state before they become operating policy. P30 implements item 4
with `scripts/gates/organization_score.py`, computing the 9.8 maturity target
from evidence inputs instead of preserving it as scorecard prose.
