<!-- Provenance:
  upstream: ce@3.8.3 references/compound-engineering-feedback-format.md
  source-commit: vendored at athanor v0.10.0 release time from ce@3.8.3
  upstream-url: https://github.com/EveryInc/compound-engineering-plugin
  license: MIT (Copyright (c) 2025 Kieran Klaassen / Every Inc)
  modifications: none — verbatim copy under T2 vendoring pattern; provenance block inserted after frontmatter only
  t0-t1-disproof:
    Why not T0/T1? ce is shipped as a Claude Code plugin (T3 marketplace
    listing). T0 (install companion) is unavailable for per-skill reference files.
    T1 (require dependency) is reserved pending Claude Code plugin-spec `requires`
    field support. T2 (vendor) is the only feasible tier today.
-->

# Compound Engineering Feedback Format

Use this shape when converting Riffrec evidence into a durable brainstorm or planning input.

## Finding

```markdown
### F1. <Short problem title>

- **Severity:** P0/P1/P2/P3
- **Observed:** <What happened, grounded in transcript/events/screenshots>
- **Expected:** <What the user appeared to expect or what the product should do>
- **Evidence:** <Moment IDs and screenshot links>
- **Confidence:** High/Medium/Low, with reason
- **Requirement candidates:** R1, R2
```

## Requirements Kickoff

```markdown
---
date: YYYY-MM-DD
topic: <topic>
---

# <Topic Title>

## Problem Frame

<Who is affected, what is changing, and why it matters.>

---

## Actors

- A1. User: <Role in the recorded workflow>
- A2. Product surface: <System under test>
- A3. Agent/assistant, if relevant: <Role in the workflow>

---

## Key Flows

- F1. Recorded feedback triage
  - **Trigger:** A Riffrec zip is available for review.
  - **Actors:** A1, A2
  - **Steps:** <3-7 product steps seen in the recording>
  - **Outcome:** <What should be true after the fix>
  - **Covered by:** R1, R2

---

## Requirements

**Observed product behavior**
- R1. <Concrete product behavior requirement>

**Feedback evidence and reviewability**
- R2. <Requirement about making the issue observable or preventing recurrence>

---

## Acceptance Examples

- AE1. **Covers R1.** Given <state>, when <action>, <outcome>.

---

## Success Criteria

- <Human outcome>
- <Downstream agent handoff quality>

---

## Scope Boundaries

- <Deliberate non-goal>

---

## Key Decisions

- <Decision>: <Rationale>

---

## Dependencies / Assumptions

- <Material dependency or assumption>

---

## Outstanding Questions

### Resolve Before Planning

- <Only product questions that block planning>

### Deferred to Planning

- [Technical] <Questions better answered during codebase exploration>

---

## Next Steps

-> /ce-brainstorm to confirm, correct, and regroup the captured requirements before any planning.
```

## Evidence Rules

- Prefer moment IDs and screenshot links over prose-only claims.
- Mark visual interpretation as an inference when the screenshot does not prove intent.
- Requirements should describe product behavior, not implementation details.
- Do not include absolute local paths in CE docs; use repo-relative paths when possible.
