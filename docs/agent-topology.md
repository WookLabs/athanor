# Agent Topology

Last reviewed: 2026-06-19.

This document is the current operating map for Athanor skills, reference roles,
and registered agents. The executable contract is
[`agent-topology-contract.json`](agent-topology-contract.json), checked by
`scripts/gates/agent_topology.py`.

## Decision

No new registered agent is added for the expanded skill set. The registered
surface stays intentionally small:

- `ci-watcher` for CI watch and autofix loops.
- `codex-dispatcher` for safe Codex CLI invocation.
- `learner` for lessons extraction.
- `releaser` for release ceremony automation.

The seven pipeline roles in `docs/agent-roles/` stay reference-only. They have
no `name:` frontmatter because skills dispatch them inline with session paths
and task-specific packets. Registering them would add surface area without a
usable standalone invocation path.

`prompt-gen` is an output-only intake-framing skill, not a new agent. It treats
the raw request as prompt material, emits `prompt-gen.md`, and recommends the
next skill. It should not execute, plan the solution, run downstream commands,
or silently invoke the recommended skill.

`deep-plan` and `lite-plan` are planning-wrapper skills, not new agents. They
bind the requested planning tier, then delegate to the canonical `plan`
protocol and normal `plan.md` artifact path.

## Scorecard

| Area | Current | Target | Notes |
|---|---:|---:|---|
| Registered-agent minimalism | 92/100 | 94/100 | Four registered agents are enough for reusable standalone work. |
| Reference role documentation | 82/100 | 92/100 | Roles are useful, but need a current topology contract. |
| Skill-to-role routing clarity | 68/100 | 94/100 | The largest gap; every skill now needs an explicit route. |
| `prompt-gen` intake ownership | 72/100 | 90/100 | Keep it as a leader skill with handoffs, not an agent. |
| Claude/Codex runtime parity | 85/100 | 92/100 | Skills are mirrored; topology now documents the runtime boundary. |
| Test and gate enforcement | 74/100 | 93/100 | Add a read-only topology gate to prevent drift. |
| Operational simplicity | 91/100 | 93/100 | Preserve low agent count and low dispatch ambiguity. |
| Organization efficiency model | 78/100 | 91/100 | Add a clear org chart, owner roles, and handoff map. |

Overall current score: 80/100. Target after this topology pass: 92/100.

## Topology Rules

- New skills default to a `skill_routes` entry in the contract, not a new
  registered agent.
- A new registered agent requires standalone invocation need, a prompt that does
  not depend on session-specific paths, reuse across two or more skills, and a
  topology contract update.
- A reference role requires at least one owner skill, no `name:` frontmatter, and
  a route reference from the contract.
- `prompt-gen` must keep `leader_kind: intake-framing`, no registered agents,
  and handoffs to at least `discuss`, `plan`, and `work`.

## Gate

Run:

```text
python scripts/gates/agent_topology.py --json
```

The gate is read-only. It checks registered agent files, reference-role files,
skill route coverage, route references, `prompt-gen` intake status, and entry
point links from `CLAUDE.md`, `README.md`, and `docs/package-knowledge-index.md`.
