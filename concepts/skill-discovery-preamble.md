# Concept: Skill Discovery Preamble (SessionStart pattern + advisory boundary)

**Source:** sp-using-superpowers@5.1.0 (https://github.com/obra/superpowers)
**Target:** CLAUDE.md §"using-superpowers boundary (v0.11.1)"
**License:** MIT
**Author:** Jesse Vincent
**Commit SHA:** TBD — filled after v0.12.0 ship merge

## Why this concept survives v0.12.0

The `sp-using-superpowers` skill encodes two distinct ideas. The first is the SessionStart system-reminder pattern: Claude Code's platform mechanism auto-loads the skill body into the system-reminder additional-context channel at session start, so the model is aware of available skills before the first user turn. The second is the "1% chance the skill applies → MUST invoke it" pressure that drives skill discovery. The first idea is a useful platform-level pattern worth preserving as documentation; the second is incompatible with athanor's Thin Leader contract because pre-response skill-invocation pressure conflicts with the leader's dispatch-only role.

The v0.11.1 boundary doctrine resolves the tension: athanor preserves the SessionStart pattern as inherited platform behavior (vendored body is T2-locked, edited only by drift script) but explicitly downgrades the "MUST invoke" pressure to advisory in Thin Leader contexts. The boundary is declared inline in each of the 10 athanor-native skills (Identity subsection) and regression-locked. This concept survives because it formalizes the layering — platform mechanism on one side, athanor identity on the other, with a clear advisory boundary between them.

## What was lifted

- The SessionStart system-reminder pattern recognition (skill body auto-loaded into additional-context channel)
- The "athanor `hooks/hooks.json` does NOT register SessionStart — this is a platform mechanism" honesty note
- The Thin-Leader-context advisory boundary (the v0.11.1 doctrine)
- The boundary's inline preamble declaration in each athanor-native skill's Identity subsection
- The regression-lock pattern (`tests/test_regression_v011_1_using_superpowers_boundary.py`)

## What was NOT lifted

- The full `sp-using-superpowers` SKILL.md body verbatim (athanor preserves T2 lock — body is not edited, but the "MUST invoke" pressure is downgraded by the boundary declaration in athanor-native skills, NOT by mutating the vendored body)
- The "1% chance the skill applies → MUST invoke" pressure as a runtime contract in athanor-native skills (it is downgraded to advisory per the v0.11.1 boundary doctrine)
- The upstream pre-response invocation-check enforcement (athanor uses dispatch-time skill selection by the leader, not pre-response self-check by the worker)

## Verification

`tests/test_regression_v011_1_using_superpowers_boundary.py` locks the boundary declaration in each of the 10 athanor-native skills. `CLAUDE.md` §"using-superpowers boundary (v0.11.1)" carries the canonical doctrine prose.
