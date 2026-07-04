# Difference from /athanor:lfg

Relocated from `skills/lfg-goal/SKILL.md` (session 2026-07-03-004 Phase 2.4,
pure-relocation diet). The SKILL.md body keeps the 3-line loose-coupling (D2)
summary so the architectural posture is visible at the dispatch site; this
file holds the full comparison table for operators deciding which skill to
invoke.

`/athanor:lfg` is a single-cycle end-to-end pipeline. `/athanor:lfg-goal`
is a goal-bounded N-cycle macro loop that invokes `/athanor:lfg`
verbatim once per cycle and adds an honesty layer on top:

| | `/athanor:lfg` | `/athanor:lfg-goal` |
|---|---|---|
| Scope | Single feature → ship | Bounded N-cycle iteration → goal completion |
| Cycle bound | None — one pass through 9 steps | `lfgGoal.maxIterations` (default 5) |
| Goal ledger | None — implicit in user prompt | `.athanor/goals/<id>/goal.md` durable ledger with G-markers |
| Score-target loop | N/A | Optional `/athanor:assess` scorecard loop; repeat until `target_overall_score` and `target_min_dimension_score` pass |
| Per-cycle DONE signal | `<promise>DONE</promise>` from Step 9 | Dispatched receipt-validator runs 9 Bash verification commands; produces `CNNN-lfg-receipt.md` with per-step status enum |
| Goal-level completion | N/A (no goal concept) | 3-tier check: Tier 1 mechanical + optional score-target arithmetic + Tier 2 adversarial cross-model judges + Tier 3 BLOCKING user ratification |
| Scope-drift between cycles | N/A | `/athanor:scope-drift` auto-fires (`lfgGoal.scopeDriftAutoCheck: true` default) |
| Release strategy | Single PR + tag | Per-cycle PRs + tags (`consolidateCycles: false` default per D9); opt-in single-PR mode available |
| When to choose | Known scope, single ship | Multi-cycle work, goal stated in outcome terms |

`/athanor:lfg-goal` does NOT modify `/athanor:lfg`. The wrapper calls
lfg verbatim and reads what lfg already produces. Loose coupling is
the architectural decision (D2): lfg-goal can evolve without touching
the inner pipeline.
