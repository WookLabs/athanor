# Athanor System Maturity 9.8 Scorecard

Date: 2026-06-18

## Current Evidence

Implemented evidence as of P30:

- P26 organization operating model:
  `docs/organization-operating-model.md`
- P26 organization gate:
  `scripts/gates/organization_operating_model.py`
- P27 work-item registry:
  `docs/organization-work-item-registry.md`
- P27 registry gate:
  `scripts/gates/organization_work_item_registry.py`
- P28 organization stage receipt contract:
  `docs/organization-stage-receipts.md`
- P28 stage receipt adapter gate:
  `scripts/gates/organization_stage_receipt.py`
- P28 committed release receipt:
  `docs/organization-stage-receipts/p28-runtime-stage-receipt-adapter-release.json`
- P29 policy promotion ledger:
  `docs/policy-promotion-ledger.md`
- P29 policy promotion gate:
  `scripts/gates/policy_promotion_ledger.py`
- P29 promotion records:
  `docs/policy-promotions/p29-policy-promotion-gate.json`
  and
  `docs/policy-promotions/legacy-prose-only-policy-notes.json`
- P30 organization score gate:
  `scripts/gates/organization_score.py`
- P30 organization score contract and schema:
  `docs/organization-score.md`
  and
  `schemas/organization-score-report.schema.json`
- Current 9.8-target work item:
  `docs/organization-work-items/p27-system-maturity-98.json`
- P28 work item:
  `docs/organization-work-items/p28-runtime-stage-receipt-adapter.json`
- P29 work item:
  `docs/organization-work-items/p29-policy-promotion-gate.json`
- P30 work item:
  `docs/organization-work-items/p30-organization-score.json`
- Harness decision records:
  `docs/harness-decisions/2026-06-18-p26-organization-operating-model.json`
  `docs/harness-decisions/2026-06-18-p27-organization-work-item-registry.json`
  `docs/harness-decisions/2026-06-18-p28-organization-stage-receipt.json`
  `docs/harness-decisions/2026-06-18-p29-policy-promotion-ledger.json`
  and
  `docs/harness-decisions/2026-06-18-p30-organization-score.json`

## Score After P30

`scripts/gates/organization_score.py` now computes the target score from
read-only input gates. The current weighted score is expected to be at least
9.8 when:

- organization operating model passes;
- work-item registry passes;
- stage receipts pass;
- policy promotion ledger passes;
- harness decision ledger passes;
- package knowledge index passes;
- package footprint has only bounded warnings;
- CI contains all required score inputs.

Composite current score: **computed by
`python scripts/gates/organization_score.py --json` and targeted at 9.8+**.

P30 closes the measurement gap: the 9.8 claim is no longer scorecard prose.
Residual gaps remain visible and scored, but they are not blocking the 9.8
target unless the score gate reports below target.

## Residual Design After 9.8

### P31 External Sandboxed Benchmark Profile

Run one first-class external sandboxed benchmark profile as normal operating
evidence. The existing external eval adapter exports shapes; this adds a
controlled execution profile with explicit sandbox and no default network.

Expected score impact: harden beyond 9.8 by raising external benchmark evidence.

### P32 Runtime Integration Hardening

Promote native runtime playbook recipes from dry-run/manual to controlled
operator-approved execution only where receipts, work item state, cleanup, and
rollback are already available.

Expected score impact: harden beyond 9.8 while preserving safety.

## Removal / Reduction Candidates

- Do not add more registered agents for organization offices. P27 proves that
  office ownership can be modeled without expanding the live agent surface.
- Do not add a default event listener yet. Reactive fixture coverage exists,
  but runtime listener promotion should wait until policy promotion and score
  gates agree it is justified.
- Reduce package footprint warnings next; current maturity is strong but still
  carries package-boundary entropy.

## Next Best Step

Next best hardening is P31 or package-footprint warning reduction. P30 makes
the 9.8 target auditable; the remaining work is quality margin, not the core
score claim.
