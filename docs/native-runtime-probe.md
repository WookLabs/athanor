# Native Runtime Probe

P19 adds a read-only gate for Claude-native execution surfaces. It closes the
gap between P12 backend recommendations and the actual local readiness of
native surfaces such as `/goal`, `/loop`, worktrees, dynamic workflows, and
agent teams.

## Run

Fixture gate:

```text
python scripts/gates/native_runtime_probe.py --fixture-root tests/fixtures/native_runtime_probe --json
```

Local conservative probe:

```text
python scripts/gates/native_runtime_probe.py --json
```

Profile probe:

```text
python scripts/gates/native_runtime_probe.py --profile path/to/profile.json --json
```

## Surface Statuses

- `available`: local evidence says the surface exists.
- `documented`: current docs or CLI evidence say the surface exists, but this
  gate did not launch it.
- `manual`: a manual operator path exists, such as `git worktree`.
- `unavailable`: evidence says the surface is missing.
- `unknown`: no local evidence was found.

## Safety Contract

The probe does not:

- start `/goal`;
- start `/loop`;
- create worktrees;
- launch dynamic workflows;
- launch agent teams;
- mutate settings;
- export telemetry.

Every native launch plan is emitted as `mode: dry-run-only` with
`auto_launch_allowed: false`. Dynamic workflow, agent-team, and worktree plans
require explicit operator approval and carry cleanup requirements where relevant.

Profiles that set `auto_launch_allowed: true` fail with
`auto_launch_not_allowed`.

