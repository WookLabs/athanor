# Concept: Review Personas

**Source:** ce-code-review@3.8.3 (https://github.com/EveryInc/compound-engineering-plugin)
**Target:** skills/review/SKILL.md §"Personas"
**License:** MIT
**Author:** Kieran Klaassen / Every Inc
**Commit SHA:** TBD — filled after v0.12.0 ship merge

## Why this concept survives v0.12.0

The multi-lens review approach — running parallel reviewer personas that each examine the diff through one orthogonal concern — is the most durable structural insight from `ce-code-review`. It pre-dates any specific stack and survives independent of the 18-persona file zoo that upstream ships. athanor-native review converges on a compact 6-lens set (correctness / security / performance / testing / maintainability / adversarial) that maps onto our existing review-of-a.md / review-of-b.md outputs without requiring per-language sub-agent files.

The concept survives because it composes cleanly with the Thin Leader contract: each persona is one clean-context worker dispatch, results merge in the leader, and no shared state is needed between personas. Compression from 18 to 6 is intentional — the upstream stack-specific personas are out of scope for a general-purpose orchestrator.

## What was lifted

- The 6-persona lens vocabulary (correctness, security, performance, testing, maintainability, adversarial)
- The "parallel personas examine same diff through orthogonal lenses" structural pattern
- The "merge persona findings into a single review document" output shape
- The "adversarial reviewer challenges the other personas' conclusions" idea

## What was NOT lifted

- CE's 18-persona-file structure (separate `.md` per persona at depth 2)
- Stack-specific personas: `dhh-rails`, `kieran-rails`, `kieran-python`, `kieran-typescript`, `julik-frontend-races`, `swift-ios`
- Conditional-routing heuristics from CE's `persona-catalog.md` that pick personas based on detected stack
- Per-persona system-prompt boilerplate (CE templates persona voice; athanor uses a unified bilingual voice)

## Verification

`tests/test_regression_v012_review_personas_array.py` locks the 6-persona array in `skills/review/SKILL.md` and asserts no stack-specific personas leak into the athanor-native review skill body.
