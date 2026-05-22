# Concept: Systematic Debugging Discipline

**Source:** sp-systematic-debugging@5.1.0 (https://github.com/obra/superpowers)
**Target:** skills/debug/SKILL.md §"Systematic Debugging Discipline"
**License:** MIT
**Author:** Jesse Vincent
**Commit SHA:** TBD — filled after v0.12.0 ship merge

## Why this concept survives v0.12.0

The systematic-debugging discipline encodes three durable principles that survive independent of `sp-systematic-debugging`'s procedural body: (1) the Iron Law — never propose a fix without first reproducing the failure deterministically; (2) the Four Phases — reproduce → isolate → understand → fix, in order, with no phase skipped; (3) the "3+ fixes for the same class of failure means you're solving the wrong problem — escalate to an architectural question" rule. These principles are not language-specific or stack-specific; they apply equally to Python pytest failures, JavaScript runtime errors, or shell-script regressions.

Subtask 9 lifted these three principles into `skills/debug/SKILL.md` as a named "Systematic Debugging Discipline" section. They compose with athanor's parallel-dispatch debug pattern (error trace + git history + code-trace workers run in parallel) by giving each worker a shared discipline contract — every worker is expected to confirm reproduction before proposing a fix, and the leader gates synthesis on convergent reproduction reports.

## What was lifted

- The Iron Law (no fix without reproduction)
- The Four Phases (reproduce → isolate → understand → fix)
- The "3+ fixes for one class = architectural problem" escalation rule
- The vocabulary: "deterministic reproduction", "isolation step", "root-cause hypothesis", "fix-then-verify"

## What was NOT lifted

- Language-specific debugging steps from `sp-systematic-debugging`'s body (pytest -x walkthroughs, JavaScript stack-trace patterns, etc.)
- The skill body's full procedural walkthrough (athanor compresses to principles; the worker fills in language-specific moves)
- Per-language reproduction-script templates
- The upstream "debugging session log" output shape (athanor uses `.athanor/sessions/{id}/debug.md` instead)

## Verification

`tests/test_regression_v012_lift_concept_present.py::test_debug_skill_has_systematic_debugging_discipline_lift` locks the presence of the three principles and the section name in `skills/debug/SKILL.md`.
