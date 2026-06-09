# Athanor Codex Companion

This plugin is a Codex-native companion for Athanor. It does not emulate the
Claude Code runtime.

## Boundaries

- Use `athanor-*` skill names only. Do not expose generic `plan`, `work`,
  `debug`, or `review` names from this plugin.
- Do not add Codex hooks, MCP servers, apps, or Claude `Task` assumptions in
  this companion unless a later migration explicitly designs them.
- Treat Claude Code hooks (`Stop`, `PreToolUse`, Freeze, Kernel Guard) as
  unsupported in Codex. Mention this honestly in setup diagnostics.
- Preserve the existing Claude Athanor plugin surface in the repo root.

## Codex Behavior

- Prefer local file inspection, `rg`, and existing repo conventions before
  proposing changes.
- Use sub-agents only when the user explicitly requests delegation or parallel
  agent work in the current Codex environment.
- Keep outputs concise and implementation-oriented. Athanor Codex skills should
  move a task toward a decision, fix, review finding, or verified state.
- Use `.athanor/sessions/` artifacts when they help continuity, but do not
  pretend Codex has Claude's hook-enforced Thin Leader runtime.
