# Runtime Execution Adapter

P12 adds a read-only runtime backend recommendation layer for Athanor.

Run the fixture gate:

```bash
python scripts/gates/runtime_execution_adapter.py --fixture-root tests/fixtures/runtime_execution --json
```

Run one direct recommendation:

```bash
python scripts/gates/runtime_execution_adapter.py \
  --task "Review three independent modules" \
  --risk medium \
  --estimated-files 6 \
  --parallel-workers 3 \
  --same-file-risk low \
  --json
```

Backends:

- `solo`: one focused session in the current checkout.
- `subagent-wave`: bounded parallel workers reporting to one lead.
- `dynamic-workflow`: large or rerunnable fanout when the capability is available.
- `agent-team`: peer-coordinated Claude Code sessions when explicitly available.
- `manual-worktree`: isolated manual workspace path for high conflict or required isolation.

The adapter does not launch dynamic workflows, spawn agent teams, create
worktrees, mutate settings, or export telemetry. It emits a decision contract
that future live command flows can consume.
