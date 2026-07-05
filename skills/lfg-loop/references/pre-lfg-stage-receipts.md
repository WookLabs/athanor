# Pre-LFG Stage Receipts

Before `/athanor:lfg-loop` starts the first `/athanor:lfg` delivery cycle, deep
research, planning, and architecture/design work must leave explicit receipt
evidence. These receipts keep pre-cycle reasoning visible to the durable loop
controller, later judges, and resume operators.

## Receipt Locations

- research receipt: `.athanor/loops/<loop-id>/receipts/R000-research-receipt.md`
- planning receipt: `.athanor/loops/<loop-id>/receipts/P000-planning-receipt.md`
- architecture receipt: `.athanor/loops/<loop-id>/receipts/A000-architecture-receipt.md`

If a stage is intentionally skipped, write the receipt with `status: skipped`
and a concrete reason. Do not replace the receipt with hidden context or chat
summary.

## Required Evidence

| Stage | Required Evidence |
| --- | --- |
| research receipt | Source files, external references if any, unresolved facts, and findings that shape `loop.md`. |
| planning receipt | Accepted plan path, acceptance markers, verification commands, cycle boundaries, and known risks. |
| architecture receipt | Public contracts, cross-module design decisions, rejected alternatives, and follow-up constraints. |

Each receipt must reference `loop.md` and any session artifact that supplied the
stage input. The later `/athanor:lfg` cycle receipt starts after these receipts;
it does not need to restate their full contents.

Readiness check:

```bash
python scripts/loops/check_pre_lfg_stage_receipts.py --loop-dir .athanor/loops/<loop-id> --json
```
