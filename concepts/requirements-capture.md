# Concept: Requirements Capture (R-ID / A-ID / F-ID / AE-ID)

**Source:** ce-brainstorm@3.8.3 (https://github.com/EveryInc/compound-engineering-plugin)
**Target:** skills/discuss/references/requirements-capture.md
**License:** MIT
**Author:** Kieran Klaassen / Every Inc
**Commit SHA:** TBD — filled after v0.12.0 ship merge

## Why this concept survives v0.12.0

The id-scheme contract (R-ID for requirements, A-ID for assumptions, F-ID for findings, AE-ID for acceptance examples) is the most durable artifact from `ce-brainstorm`. It gives the leader and worker a shared vocabulary for tracking the dialogue across the discuss → plan → work pipeline without depending on the upstream dialogue script. The scheme was already partially formalized in v0.9.0 absorption, and Subtask 10 added the Attribution prefix so that captured requirements carry their source persona inline. The result is a small, stable contract that survives any future rewrite of the discuss skill body.

The id-scheme also composes with athanor's session-directory convention: requirements written into `.athanor/sessions/{id}/requirements.md` carry their R-IDs through to `plan.md` subtasks, then through to `work-log.md` traces. This cross-session traceability is the practical reason to lift the concept and freeze it under `skills/discuss/references/`.

## What was lifted

- R-ID (requirement) / A-ID (assumption) / F-ID (finding) / AE-ID (acceptance example) id-scheme contract
- The "every dialogue artifact gets a stable id" rule
- Attribution prefix on captured requirements (added Subtask 10 — formalizes which persona / clarification round produced the R)
- The "requirements.md is the dialogue artifact, not the conversation transcript" output-shape rule
- v0.9.0 absorption groundwork (formalized the id scheme into athanor-native discuss vocabulary)

## What was NOT lifted

- ce-brainstorm's full dialogue flow (the upstream skill body's step-by-step user-prompting script)
- Gap-probe template variations (CE ships multiple gap-probe templates tuned to different problem domains; athanor uses a single clarify-mode template)
- The upstream "decision tree" routing between brainstorm phases
- CE's per-domain example libraries that demonstrate the id-scheme in product / infra / docs contexts

## Verification

The id-scheme appears in `skills/discuss/references/requirements-capture.md` and is referenced from `skills/discuss/SKILL.md`. v0.9.0 regression tests under `tests/test_regression_v0_9_0_*` lock the four id-schemes; v0.12.0 adds attribution-prefix coverage via Subtask 10's verification line.
