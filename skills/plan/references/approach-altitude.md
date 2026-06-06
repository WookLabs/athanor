# Approach-Altitude Gate (Step 1)

Concept adopted from compound-engineering v3.11.1 `/ce-plan` Phase 0.1a
"Recognize Approach-Altitude Requests" (MIT, Kieran Klaassen / Every Inc).

## What it is

Before `/athanor:plan` parses a request as a **deliverable plan** (the
concrete artifact to build), recognize when the user instead wants a **plan
for the approach** — a grounded, methodology-level plan of *how* something
will be made, held above the deliverable, before zero-shotting it.

## Two entry gates

### 1. Explicit (ungated — always honor)

Trigger phrases (EN/KO), case-insensitive:

- "plan the approach", "plan how", "don't build yet — just plan how",
  "방법부터 계획", "어떻게 할지부터 정하자", "아직 만들지 말고 계획만".

When matched: enter approach-altitude mode. Do NOT dispatch deliverable
planners yet — the subject of planning is the method, not the artifact.

### 2. Proactive (conservative — offer, don't force)

Offer a single dismissible line ONLY when BOTH hold:

- **method uncertainty is high** — multiple competing approaches, ≥3 heavy
  sources to synthesize, long/unknown research, or a risky/irreversible
  change; AND
- **cost of getting the approach wrong is high**.

Never offer for obvious tasks (simple feature, bug fix, rename, single-file
change) or answer-seeking questions. One line, not a blocking prompt.

## What it produces

A method-level plan (not the deliverable): candidate approaches, the chosen
one + why, key risks/unknowns, and the validation strategy. Cross-model
adversarial planning still applies (Planner A + Planner B + Critic) — the
*subject* is the approach, not the artifact.

## Re-anchor to the deliverable

Approach-altitude is a detour, not the destination. After the approach is
agreed, explicitly **re-anchor**: resume the normal `/athanor:plan`
deliverable pipeline (Tier dispatch → planners → review → Critic) with the
chosen approach as a locked constraint. Record the approach decision in
`.athanor/sessions/{id}/decisions.md` so downstream `/athanor:work` inherits
it.

## Fit with athanor invariants

- **Thin Leader**: recognition is leader-side parsing; the method-plan
  itself is still produced by dispatched planners.
- **Cross-model adversarial planning**: reinforced — the approach plan runs
  the same Planner A/B + Critic loop.
- **Spec-then-TDD**: reinforced — settling the approach early reduces Phase 3
  scope surprises.
