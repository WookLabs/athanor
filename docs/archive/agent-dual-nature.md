# Native Agent Dual Nature + COLLISION GUARD

Companion doc for `CLAUDE.md` §"Native Agent Inventory". Detailed rationale for
why all 11 `agents/*.md` files and their `name: athanor-*` frontmatter are
retained, and why skills must dispatch pipeline roles via inline `Agent()`
prompts rather than the registered agent types.

Decided in Goal 36470e54 Cycle C002 (G3). See
`.athanor/goals/36470e54/decisions.md` D-C002-3.

## The two natures

Each file in `agents/` serves two distinct purposes:

1. **Reference document for the inline-dispatched pipeline role.** Athanor
   skills (`/athanor:plan`, `/athanor:work`, `/athanor:review`, etc.) run a
   clean-context worker pipeline. When a skill dispatches a role (analyst,
   critic, executor, learner, planner, researcher, reviewer, plus executor
   variants), it does so via an **inline `Agent()` prompt** assembled at
   dispatch time. The `agents/<role>.md` file is the *reference contract* for
   that prompt — it documents the role's purpose, allowed tools, output shape,
   and rules. It is NOT the full implementation; the canonical dispatch text
   lives in the respective skill's `SKILL.md`. The agent `.md` and the skill's
   inline prompt are kept in sync by hand (each agent file carries a sync note).

2. **Live registered agent type for standalone `@-mention` use.** Because each
   file carries `name: athanor-*` frontmatter, Claude Code registers it as an
   addressable agent type. A user can invoke e.g. `@athanor-reviewer` directly,
   outside any skill pipeline, for ad-hoc standalone use.

## COLLISION GUARD

**Skills never dispatch the 8 pipeline roles via `subagent_type` referencing
the registered `athanor-*` agent.** They always use an inline `Agent()` prompt.

For **planner** and **critic** this is not merely a style preference — it is
explicitly WRONG to dispatch via the registered agent. The inline dispatch
prompt carries **session-specific file paths** — e.g.
`.athanor/sessions/{id}/plan-a.md`, `.athanor/sessions/{id}/plan-b.md`,
`.athanor/sessions/{id}/review-of-a.md` — that the registered standalone agent
definition does not contain. A `subagent_type` dispatch would launch the agent
with only its static frontmatter/body context and silently drop the
session-specific paths, producing a worker that reads/writes the wrong (or no)
files. The registered agent types therefore exist for standalone @-mention
convenience only, never as the pipeline's dispatch mechanism.

## KEEP rationale (why nothing is removed)

- Removing the `name: athanor-*` frontmatter would break standalone
  `@-mention` invocation (nature 2).
- Removing the `.md` files would drop the inline-dispatch reference contract
  (nature 1) that keeps skill prompts auditable and in sync.
- Cycle C001 (`docs/agent-evaluation-matrix.md`) concluded **0 ref-agent
  adoptions** — and the 11 native agents are themselves not dead: each is an
  active inline-dispatch reference and/or a registered standalone type.

This is consistent with athanor's broader trajectory: v0.12.0 concept
absorption (vendor *concepts* as prose, not agent directories) and v0.15.x
removal of the last 2 vendored generic agents. The 11 native agents are the
stable, non-vendored core — retained in full.

## The 11 agents

`analyst`, `cleaner`, `critic`, `executor`, `learner`, `planner`,
`researcher`, `reviewer` (v0.7.x), `releaser`, `codex-dispatcher`,
`ci-watcher` (v0.14.0). The 8 pipeline roles subject to the COLLISION GUARD are
the dispatch-bearing roles (analyst, critic, executor, learner, planner,
researcher, reviewer, plus executor variants); `cleaner`, `releaser`,
`codex-dispatcher`, and `ci-watcher` are lifecycle/automation helpers.
