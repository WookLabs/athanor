<!-- Provenance:
  upstream: compound-engineering/ce-brainstorm references/requirements-capture.md
  source-commit: compound-engineering@3.8.2 skills/ce-brainstorm/references/requirements-capture.md
                 (vendored at athanor v0.9.0 release time; verified still present
                 at compound-engineering@3.8.3 during v0.10.0 absorption).
                 SHA pin not available from plugin-cache distribution; version-tag
                 fallback per CLAUDE.md §"Vendored Surface" drift policy
                 (v0.10.1 correction).
  license: MIT (Copyright (c) 2025 Every Inc / compound-engineering authors)
  modifications:
    - Vendored verbatim with athanor-specific adaptations:
      - Output path retargeted to `.athanor/sessions/{id}/requirements.md`
        (clarify mode artifact) instead of `docs/brainstorms/<date>-<topic>-
        requirements.md` (ce-brainstorm's pattern)
      - Bilingual prose adapted to athanor project voice; structural content
        (section list, ID conventions, frontmatter, tier matrix) unchanged
      - Removed Deep-product tier guidance (athanor v0.9.0 supports
        Standard tier only — Deep-product durability lens is v0.9.1+ work)
    - All section purposes and template structure preserved
  t0-t1-disproof:
    Why not T0/T1? compound-engineering is a Claude Code plugin (T3
    marketplace listing per docs/DEPENDENCIES.md §Marketplace Status).
    T0 (install companion) is unavailable for per-skill reference files.
    T1 (require dependency) is reserved pending plugin-spec `requires`
    field support. T2 (vendor) is the only feasible tier today.
-->

# Requirements Capture Template (clarify mode)

This reference is loaded by `skills/discuss/SKILL.md` §"Step 3-clarify-
finalization" when the leader writes the per-session requirements.md
after clarify dialog completes.

## Output path

Write to: `.athanor/sessions/{session-id}/requirements.md`

(Distinct from synthesis mode's `.athanor/sessions/{session-id}/discuss.md`.
Both files can coexist in the same session when clarify chains into
synthesis via the Phase 4 menu option [2].)

## When a document is warranted

- **Always for clarify mode finalization.** Even compact clarify dialogues
  produce a requirements.md so `/athanor:plan` can read it downstream
  (the plan integration is the primary value proposition).
- Skip document creation only when the user explicitly says "I just wanted
  to think out loud, don't write a doc" — and even then, log a one-line
  ATHANOR_RESULT summary so the session has a trace.

## Section matrix

| Section | Required when... |
|---|---|
| Summary | Always (1-3 line forward-looking prose) |
| Problem Frame | Always (situational, backward-looking) |
| Actors | Triggered when multiple humans / agents / systems involved |
| Key Flows | Triggered when multi-step interaction or coordination across flows |
| Requirements | Always (with R-IDs) |
| Acceptance Examples | Required for behavioral-conditional requirements ("When X, Y" / "If X, Y") |
| Success Criteria | Always |
| Scope Boundaries | Always (single list — athanor v0.9.0 supports Standard tier only) |
| Key Decisions | Include when material |
| Dependencies / Assumptions | Include when material |
| Outstanding Questions | Include when material |

## Summary vs Problem Frame discipline

Both describe the work, but from different angles:

| Section | Question it answers | Time direction | Length |
|---|---|---|---|
| `## Summary` | What is this doc proposing? | Forward-looking | 1-3 lines |
| `## Problem Frame` | Why does this proposal exist? | Backward-looking | Paragraphs |

- **Summary** doesn't need problem context. A reader scanning Summary gets
  the proposal at a glance.
- **Problem Frame** doesn't restate the proposal. It establishes the
  situation, the pain, and the cost — then stops.

## ID conventions

Every requirements doc uses these stable ID prefixes:

- `R1`, `R2`, ... — Requirements (always assigned)
- `A1`, `A2`, ... — Actors (when Actors section present)
- `F1`, `F2`, ... — Key Flows (when Key Flows section present)
- `AE1`, `AE2`, ... — Acceptance Examples (when present)

**No other ID namespaces.** The IDs survive doc edits — never renumber on
reorder or insertion; gaps from deletion are fine.

**ID format:** `R1.`, `A1.`, `F1.`, `AE1.` as plain prefix at bullet start.
Do not bold the ID prefix.

## Template

```markdown
---
date: YYYY-MM-DD
topic: <kebab-case-topic>
---

# <Topic Title>

## Summary

[1-3 line prose — what this doc proposes, in plain language, forward-looking]

---

## Problem Frame

[Who is affected, what is changing, and why it matters. Backward-looking.
Establishes the pain that motivates the work — does NOT restate the proposal
(that lives in Summary).]

---

## Actors

[Include when multiple actors meaningfully involved. Each gets an A-ID.]

- A1. [Name or role]: [What they do in this context]
- A2. [Name or role]: [What they do in this context]

---

## Key Flows

[Include when multi-step interaction. Each flow gets trigger / actors / steps
/ outcome / Covered-by back-reference.]

- F1. [Flow name]
  - **Trigger:** [What initiates the flow]
  - **Actors:** A1, A2
  - **Steps:** [3-7 steps]
  - **Outcome:** [What is true after the flow completes]
  - **Covered by:** R1, R2, R5

---

## Requirements

[Group under bold inline headers when requirements span distinct concerns.
R-IDs are sequential across groups — numbering does NOT restart per group.]

**[Group header, e.g., "Authentication"]**
- R1. [Concrete requirement]
- R2. [Concrete requirement]

**[Group header, e.g., "Audit logging"]**
- R3. [Concrete requirement]

---

## Acceptance Examples

[Required for any behavioral-conditional requirement ("When X, Y" / "If X, Y").
The list is not exhaustive; each example disambiguates one or more R-IDs.]

- AE1. **Covers R1, R2.** Given [state], when [action], [outcome].
- AE2. **Covers R4.** Given [state], when [action], [outcome].

---

## Success Criteria

- [How we will know this solved the right problem — human outcome.]
- [How a downstream agent or implementer can tell the handoff was clean.]

---

## Scope Boundaries

[Single bulleted list of explicit non-goals. v0.9.0 supports Standard tier
only — Deep-product split (Deferred for later / Outside this product's
identity) is v0.9.1+.]

- [Deliberate non-goal or exclusion]

### Deferred to Follow-Up Work

- [Work that will be done separately]: [Where or when]

---

## Key Decisions

- [Decision]: [Rationale]

---

## Dependencies / Assumptions

- [Material dependency or assumption]

---

## Outstanding Questions

### Resolve Before Planning

- [Affects R1][User decision] [Question that must be answered before planning]

### Deferred to Planning

- [Affects R2][Technical] [Question answered during planning or codebase exploration]
- [Affects R2][Needs research] [Question likely requiring research during planning]
```

## Layout rules

- **Horizontal rules (`---`)** between top-level sections.
- **Bold leader labels** inside Flows and Acceptance Examples (`**Trigger:**`,
  `**Covers R4, R8.**`).
- **Tables** only for genuinely comparative info; bullets are cheaper.
- **Grouping within Requirements** under bold inline headers (not H3s) when
  multiple distinct concerns exist.

## Size heuristics

- If a capability-named group has only one requirement, ungroup it.
- If total requirements exceed ~15-20, stop and ask whether this is one
  brainstorm or several.
- For very small clarify dialogues with only 1-3 simple requirements, plain
  bullets without R-IDs are acceptable (skipping ID assignment).

## Finalization checklist (before saving)

- What would `/athanor:plan` still have to invent if this doc shipped as-is?
- Does every Requirement have either an observable behavior or a stated
  reason it is structural?
- Do Success Criteria cover both human outcome and downstream-agent handoff?
- If Actors are named, is each actor mentioned in at least one requirement,
  flow, or scope boundary?
- If Key Flows are present, does each flow identify actor / trigger /
  outcome and a failure/escape path when relevant?
- Do any requirements depend on something claimed to be out of scope?
- Are any unresolved items actually product decisions rather than planning
  questions?
- Did implementation details leak in when they shouldn't have?
- Do any requirements claim infrastructure is absent without verification?
  If so, verify now or label as an unverified assumption.

If `/athanor:plan` would need to invent product behavior, scope boundaries,
or success criteria, the clarify dialog is not complete yet — return to
Step 2-clarify and probe further before finalizing.

## Attribution

Concept adopted from compound-engineering@3.8.3 ce-brainstorm (MIT, Kieran Klaassen / Every Inc).
See NOTICE.md §"Concepts adopted from upstream" and concepts/requirements-capture.md
(Subtask 11) for the LIFT inventory.
Source: https://github.com/EveryInc/compound-engineering-plugin

