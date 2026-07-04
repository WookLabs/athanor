# Per-cycle commit / release strategy (D9)

Relocated from `skills/lfg-goal/SKILL.md` (session 2026-07-03-004 Phase 2.3,
pure-relocation diet). The SKILL.md body keeps the canonical `consolidateCycles`
default and the per-cycle release-rule summary; this file holds the full
per-cycle vs consolidated-override reasoning for operators tracing the D9
strategy.

Per D9, each cycle ships its own PR + patch release. Honest history:
each cycle adds one tag that closes ≥1 G-marker. Version-space inflation
is the accepted honesty-arc cost.

- **Default** (`lfgGoal.consolidateCycles: false`, per D9): per-cycle
  PRs, one release tag per cycle. Each cycle's `/athanor:lfg` Step 9
  emits its own DONE sentinel and tag. Goal-completion adds a final
  `goal-completion.md` index pointing at all cycle tags but does NOT
  introduce an extra "goal-complete-only" release.
- **Override** (`lfgGoal.consolidateCycles: true`): all cycles
  accumulate into a single goal-PR; only goal-completion ships a
  release. Available as opt-in for users who prefer condensed release
  history.

`goal-completion.md` indexes all cycle PRs + tags back to the goal
regardless of mode.
