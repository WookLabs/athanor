---
name: athanor-analyze
description: Analyze a codebase, subsystem, or change surface before planning or implementation using Athanor's Codex-native fast analysis workflow.
---

# Athanor Analyze

Use this to understand where work should happen before planning, debugging, or
implementation. The output should be fast, grounded, and scoped.

## Protocol

1. Restate the analysis question and split it into concrete focus areas:
   repo structure, relevant modules, tests, dependencies, recent changes, and
   risks.
2. Inspect local truth first with `rg`, file reads, manifests, tests, and git
   history when useful. Prefer targeted reads over broad file dumps.
3. Check `.athanor/sessions/` and `.athanor/lessons/` when present. Summarize
   useful prior context under `Historical Context`; say when none applies.
4. For each focus area, report findings with evidence: paths, symbols,
   commands, or config entries.
5. End with recommended next actions: plan, debug, scope-drift check, review,
   or implementation.

## Output

Use this shape:

```text
Question:
Focus areas:
Historical Context:
Findings:
Risks / Unknowns:
Next actions:
```

## Codex Constraints

- Do not edit files during analysis.
- Use sub-agents only when the user explicitly requested parallel agent work.
- Do not invent architecture beyond evidence in the repo.
