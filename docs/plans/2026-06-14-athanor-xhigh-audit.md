# Athanor Claude Code Plugin XHigh Audit

Date: 2026-06-14
Mode: xhigh analysis

## Overall Score

**7.3 / 10**

Athanor has a strong release discipline, explicit honesty labels, and a useful
hook-based safety surface. The main weakness is that several high-value claims
still rely on self-report or passive forward-compat documentation instead of
runtime evidence.

## Scorecard

| Area | Score | Finding |
| --- | ---: | --- |
| Architecture | 8.0 | Thin-leader skill split and hook dispatcher shape are coherent. Some historical layers are now heavy. |
| Hook safety | 7.0 | Stop and PreToolUse are well covered. PostToolUse is the missing evidence layer. |
| TDD discipline | 5.5 | Red/green evidence is specified, but authenticity is still self-reported. |
| Freeze guard | 7.0 | Useful opt-in guard. D2 subprocess/file-change residual is honestly documented. |
| Capability reporting | 7.5 | Passive probe is valuable, but unsupported events need to age into live probes. |
| CI/release hygiene | 8.0 | Broad regression suite and release checks exist. Dependency declaration had drift. |
| UX / maintainability | 6.5 | Rich workflow coverage, but several docs/tests still preserve old exact surfaces. |

## Overbuilt Parts

1. The skill/agent surface is broader than the runtime guarantees. Several
   workflows describe strong process discipline while the runtime can only
   enforce part of it.
2. Historical compatibility tests preserve old event inventories too tightly.
   They are useful, but exact-surface locks must be revised when a new hook is
   intentionally added.
3. Roadmap placeholders for v0.18.x and v0.19.0 are clear, but the same future
   intent appears in several places and can drift.

## Underspecified Parts

1. PostToolUse payload shape was only documented as a future spike target.
2. Spec-then-TDD evidence still trusts worker-reported `red_evidence` and
   `full_suite_passed`.
3. CI installs `pytest` and `jsonschema`, while the test suite imports `yaml`.
4. Freeze D2 residual lacks a follow-up evidence stream for subprocess writes
   and test execution results.

## Recommended Work Items

1. **PostToolUse evidence sniffer**
   - Add a PostToolUse command hook.
   - Record pytest-family Bash results to session state as JSONL.
   - Keep v1 evidence-only; do not block sessions until live payload shape is
     proven.
2. **Evidence-bound Spec-then-TDD gate**
   - Cross-check reported `red_evidence` against stamped PostToolUse evidence.
   - Treat mismatch as a work-gate violation after enough live confidence.
3. **Freeze D2 follow-up**
   - Extend PostToolUse evidence to file-change fields if Claude Code exposes
     them.
   - Keep current PreToolUse freeze guard as the first line of defense.
4. **UserPromptSubmit spike**
   - Keep UPS unregistered until a live payload spike exists.
   - Do not convert static dedup to runtime injection yet.
5. **Capability probe refresh**
   - Move PostToolUse from pure forward-compat to registered evidence-only
     status.
   - Keep `tool_response_available` empirical rather than overclaimed.
6. **CI dependency correction**
   - Install `pyyaml` in the validation workflow.
7. **Documentation de-duplication**
   - Make `spec-then-tdd-handler.md` the authoritative runtime behavior doc
     for evidence-bound TDD.
   - Let roadmap entries point to that section instead of restating details.
8. **Release/version story**
   - Defer version bumps to a release-specific pass unless explicitly shipping
     v0.19.0.

## First Item Selected

Item 1, PostToolUse evidence sniffer, is the first implementation target. It
has the best risk/reward ratio because it creates real runtime evidence without
changing user-visible blocking behavior.
