# Maintenance Profile

P20 adds a read-only maintenance profile for recurring Athanor care. It is a
single command that an operator, CI job, or Claude `/loop` prompt can run
without deleting files, updating refs, launching agents, or exporting telemetry.

## Run

CI-safe profile:

```text
python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json
```

Local profile with Claude CLI checks:

```text
python scripts/gates/maintenance_profile.py --samples 1 --json
```

## Included Steps

- entropy cleanup, including stale plan/ref checks;
- distribution smoke;
- observability snapshot;
- native runtime probe;
- harness decision ledger.

## Suggested `/loop` Prompt

```text
/loop weekly: Run `python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json` from the repository root, review the JSON summary, and take no irreversible actions without explicit user approval.
```

## Non-Goals

The profile does not:

- register scheduled tasks;
- append trend history by default;
- update ref repositories;
- delete stale files;
- create worktrees;
- launch native Claude dynamic workflows or agent teams;
- export telemetry.

The report always includes `irreversible_actions: 0`.

