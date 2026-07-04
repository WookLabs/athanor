# Honesty note on physical enforcement scope

Relocated from `skills/lfg-goal/SKILL.md` (session 2026-07-03-004 Phase 2.2,
pure-relocation diet). The `advisory (planner-classified)` label is kept
inline in the SKILL.md body so the dispatch-time posture is visible; this
file holds the full reasoning for operators tracing the enforcement scope.

The receipt-arithmetic + validator dispatch + 3-tier check are
**advisory / orchestration layers**, NOT runtime gates like the Stop
hook. The Validated Receipt-Ledger Loop achieves trust through
structural enforcement — clean-context worker dispatch + externally-
verifiable Bash commands + blocking user ratification — but it does
NOT physically prevent a misbehaving leader from:

- Skipping `/athanor:lfg` steps and fabricating a receipt entry
  (the validator runs Bash commands against artifacts; if the leader
  forges commit SHAs or PR URLs, the Bash checks would still detect
  the forgery via `git show` / `gh pr view` non-zero exit — but a
  truly adversarial leader that forges artifacts too would defeat
  the layer).
- Falsifying goal-completion by mutating `goal.md` directly before
  Tier 3 ratification.
- Suppressing scope-drift findings between cycles.

These adversarial-forgery scenarios require runtime hard-enforcement
that is deferred to v0.13.x+ (transcript-event introspection + hook-
level evidence ratification). Until then, the layer is honest about
its enforcement posture:

- It makes false completion **externally-detectable** via dispatched
  validation (clean-context worker reading actual artifacts).
- It makes false completion **non-completing** via ledger arithmetic
  (goal.md state transition requires real receipts).
- It does NOT physically prevent the leader from emitting prose that
  *claims* false completion (Stop hook handles that fraction of the
  attack surface; lfg-goal does not duplicate it).

This honest-scope voice mirrors the v0.11.x companion-fix arc
(v0.11.3 → v0.11.7): the mechanism is shipped, the scope is named,
and the residual is recorded as deferred. The label
"advisory (planner-classified)" in CLAUDE.md §Defense Mechanisms
applies analogously to this skill — the receipt-arithmetic is honest
about what it catches (mechanical step-skipping, receipt evidence
shape mismatches) and what it does not (adversarial artifact forgery,
LLM-class semantic forgery). Users encountering false positives can
set `lfgGoal.tier2Adversarial: false` or `lfgGoal.tier3UserRatification:
false` as escape hatches; both choices are recorded to `decisions.md`
so the loss of posture is auditable, not silent.
