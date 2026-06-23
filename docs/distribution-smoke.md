# Distribution Smoke

Athanor's distribution smoke gate checks what Claude Code actually loads, not
only what the repository intends to expose.

Run it from the repository root:

```bash
python scripts/gates/distribution_smoke.py --json
```

The gate always checks:

- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` parse as
  JSON.
- plugin and marketplace versions match.
- marketplace source remains `./`.
- marketplace description is present.
- plugin-root `agents/` contains only the 4 registered agent files:
  `ci-watcher`, `codex-dispatcher`, `learner`, and `releaser`.
- package footprint excludes local runtime/cache directories such as
  `.athanor/`, `.git/`, `.pytest_cache/`, `.venv/`, and `ref/`.

When `claude` is on `PATH`, the gate also runs:

```bash
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
claude --plugin-dir . plugin details athanor
```

The live loader inventory must report exactly 4 agents. The projected
always-on cost from `claude plugin details` must stay at or below the default
budget of `2200` tokens.

Use `--skip-claude` only for fixture/regression tests or environments that
cannot install Claude Code. CI should run the full gate wherever the CLI is
available.

The 7 inline-only pipeline role documents live under `docs/agent-roles/` so
Claude's plugin loader does not register them as standalone agents. Do not move
those files back under plugin-root `agents/` unless the role is intentionally
becoming a user-invokable registered agent.
