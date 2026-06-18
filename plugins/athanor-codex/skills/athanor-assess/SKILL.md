---
name: athanor-assess
description: Run a goal-aligned, multi-lens assessment of a codebase, plugin, workflow, plan, or team structure with weighted dimensions, a 100-point score, confidence, overbuilt/underbuilt findings, and a priority plan.
---

# Athanor Assess

Use this when the user asks to evaluate, score, audit maturity, judge team
composition, compare a system against a goal, or identify overbuilt and
underbuilt parts before planning implementation.

## Protocol

1. Restate the target, the user goal, and the decision the assessment should
   support. If the goal is inferred, label it as inferred.
2. Build a 100-point weighted rubric. Start from these dimensions and adjust
   weights only when the goal requires it:
   - Goal Fit
   - Structure and Responsibility Boundaries
   - Workflow Efficiency
   - Team / Role Composition
   - Evidence, Tests, and Gates
   - Safety and Permission Boundaries
   - Maintainability
   - Operator / User Experience
   - Learning and Feedback Loops
   - Simplicity and Cost Discipline
3. Inspect current evidence with `rg`, file reads, manifests, docs, tests, CI,
   gate scripts, schemas, ledgers, receipts, and command output when useful.
4. Score each dimension from 0 to 100. Keep `score` separate from
   `confidence`; confidence is low, medium, or high depending on evidence
   strength.
5. Identify:
   - Overbuilt
   - Underbuilt
   - Add
   - Remove / Simplify
   - Weak Evidence
6. Produce a numbered Priority Plan. The plan should be actionable but not
   executed unless the user explicitly asks for implementation.

## Output

Use this shape:

```markdown
# Assessment Report: <target>

## Goal Interpretation

## Score Summary

Final Score: <score> / 100
Confidence: <low|medium|high>

## Scoring Table

| Dimension | Weight | Score | Confidence | Evidence | Gap |
|---|---:|---:|---|---|---|

## Overbuilt

## Underbuilt

## Add

## Remove / Simplify

## Team / Role Assessment

## Weak Evidence

## Priority Plan

1. ...
```

## Codex Constraints

- Do not modify files during assessment.
- Do not fabricate parallel worker output. If sub-agents are unavailable or not
  explicitly requested, perform the lenses locally and label them as local
  lenses.
- Do not treat a high score as proof. Cite evidence and confidence.
- Do not start implementation after assessment unless the user explicitly asks.
