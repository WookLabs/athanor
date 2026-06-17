# Native Runtime Playbook

`scripts/gates/native_runtime_playbook.py` turns the read-only native runtime
probe into operator-approved lifecycle recipes for Claude Code native
surfaces.

Run the fixture gate:

```text
python scripts/gates/native_runtime_playbook.py --fixture-root tests/fixtures/native_runtime_probe --json
```

Run a local profile:

```text
python scripts/gates/native_runtime_playbook.py --json
```

## Safety Contract

The playbook builder is a report generator. It does not run commands, create
worktrees, start dynamic workflows, start agent teams, modify Claude settings,
write runtime state, or export telemetry.

Every native recipe keeps:

- `auto_execute: false`
- `operator_approval_required: true`
- `mutates_files_by_default: false`
- `external_telemetry: false`
- `irreversible_actions: 0`

If a profile tries to set a native surface to auto-launch, the underlying
native runtime probe fails with `auto_launch_not_allowed` and the playbook
does not emit recipes for that profile.

## Recipe Types

`manual-worktree` includes git status and worktree preflight checks, a manual
`git worktree add` template, evidence requirements, and cleanup commands for
`git worktree remove` and `git worktree prune`.

`dynamic-workflow` includes Claude/version and repo preflight checks, a manual
Claude prompt template, worker evidence requirements, and cleanup steps for
closing spawned workflow sessions.

`agent-team` includes Claude/version and repo preflight checks, a manual team
lifecycle prompt template, role/evidence requirements, and cleanup steps for
closing each team session and reconciling handoff notes.

## Operator Rule

Do not run a recipe command until the operator has typed the exact approval
phrase shown in `approval_prompt`. After execution, record the required
evidence and run the relevant validation gate before claiming success.
