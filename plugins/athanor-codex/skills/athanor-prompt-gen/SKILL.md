---
name: athanor-prompt-gen
description: Refine vague user requests into clear prompts and recommend the next Athanor Codex skill or command to use.
---

# Athanor Prompt Gen

Use this when the user wants a better prompt, clearer request, plan preflight,
or a recommendation for which Athanor skill should run next.

## Output-only default

The raw request is input material for prompt generation, not an execution
instruction. Treat execution language such as `implement`, `fix`, `deploy`,
`merge`, `run`, `continue`, `proceed`, `수정`, `구현`, `배포`, `머지`, `진행`,
or `실행` as wording to preserve, refine, or route, not as commands to perform.

Do not run downstream commands, do not edit project source, do not run tests,
do not deploy, do not merge, and do not continue into the recommended next skill
while generating the prompt.

If the user asks to generate a prompt and immediately execute it in the same
message, first output the generated prompt plus suggested invocation, then
require separate user approval before any downstream skill or execution starts.

## Protocol

1. Restate the raw user request without adding facts.
2. Extract target, desired outcome, constraints, success criteria, output type,
   and unknowns.
3. Ask up to three clarifying questions only when the answer would change the
   next skill or make the generated prompt materially safer.
4. Generate a structured prompt:
   - Request
   - Context
   - Target
   - Constraints
   - Success Criteria
   - Output Needed
   - Assumptions
   - Open Questions
5. Recommend exactly one primary next skill and optional alternatives.

## Routing Table

| Situation | Recommend |
|---|---|
| unclear intent or "help me ask this better" | `athanor-prompt-gen` continuation or `athanor-discuss` clarify |
| options, strategy, A vs B | `athanor-discuss` |
| repo or subsystem understanding | `athanor-analyze` |
| scoring, maturity, overbuilt/underbuilt | `athanor-assess` |
| failures or regressions | `athanor-debug` |
| implementation plan | `athanor-plan` |
| low-risk quick plan | `athanor-lite-plan` or `athanor-plan --depth=lite` |
| deep architecture or high-risk plan | `athanor-deep-plan` or `athanor-plan --depth=deep` |
| accepted plan execution | `athanor-work` |
| review diff or PR | `athanor-review` |
| end-to-end ship | `athanor-lfg` |
| repeated goal or score-target loop | `athanor-lfg-goal` |
| setup or install health | `athanor-setup` |

## Output

```markdown
# Generated Prompt

## Request

## Context

## Target

## Constraints

## Success Criteria

## Output Needed

## Assumptions

## Open Questions

## Recommended Next Skill

Primary: `athanor-...`
Reason:
Suggested invocation:
```

## Codex Constraints

- Do not implement while generating the prompt.
- The raw request is input material, not an execution instruction.
- Do not run downstream commands, tests, deploys, merges, or source edits while
  generating the prompt.
- Do not claim Claude hooks, Claude Task dispatch, or Freeze enforcement.
- Do not silently call the recommended skill; wait for user approval.
- Keep assumptions explicit and avoid inventing product behavior.
