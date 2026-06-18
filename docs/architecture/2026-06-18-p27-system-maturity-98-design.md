# P27 System Maturity 9.8 Design

Date: 2026-06-18

## Problem

P26 gave Athanor a company-like organization model, but the model alone does
not prove company-like operation. A mature organization also needs a durable
record of each work item: current stage, owner, artifacts, receipts, and stage
handoffs.

Without that record, the system can describe an organization but cannot reliably
answer:

- Which office owns this issue now?
- Which stage has completed?
- Which receipt proves the handoff?
- What must happen before the item advances?
- Which lessons should become policy or gates?

## Target

The target state is a 9.8/10 maturity score, where the organization model is
not just prose but an inspectable operating system. P27 does not claim 9.8 by
itself. It installs the first missing mechanism: a committed work-item registry
and a gate that validates stage state.

## Design

Add:

- `docs/organization-work-item-registry.md` as the operator contract.
- `docs/organization-work-items/*.json` as committed organization-memory work
  items.
- `scripts/gates/organization_work_item_registry.py` as a read-only gate.
- `schemas/organization-work-item-registry-report.schema.json` as the output
  contract.

The gate reads `docs/organization-operating-model.md`, then validates every
work item against the model's stage order and offices.

## Validation Rules

- Work item ids are unique.
- `current_stage` exists in the organization model.
- `owner_office` exists in the organization model.
- Active or blocked items have exactly one active/blocked stage-history entry.
- The active/blocked history entry matches `current_stage`.
- Stage history is ordered and gap-free from intake to the current stage.
- Completed stages require `receipt_ref`.
- Artifact refs and receipt refs resolve inside the repository.
- Safety fields remain read-only: no file mutation by default, no external
  telemetry, and zero irreversible actions.

## Score Impact

Expected score after P27:

- Organization operating model: 8.45 -> 9.15
- Company-like AI organization: 8.45 -> 9.05
- Knowledge lifecycle governance: 9.65 -> 9.75

Remaining gap to 9.8:

- Runtime emission of real stage receipts.
- Policy promotion lifecycle gate.
- Evidence-derived organization score gate.
- External benchmark execution profile.
