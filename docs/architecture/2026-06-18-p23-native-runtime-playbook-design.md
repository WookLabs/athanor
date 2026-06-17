# P23 Native Runtime Playbook Design

Date: 2026-06-18
Branch: `feat/p23-native-runtime-playbook`

## Context

P19 made native Claude Code runtime readiness visible without launching
anything. That was the correct safety posture, but it leaves a practical gap:
operators can see that worktree, dynamic workflow, or agent-team backends are
possible, yet they do not have a checked, repeatable lifecycle recipe for
starting, collecting evidence, and cleaning up those surfaces.

The current harness-engineering pattern from OpenAI, Anthropic, LangChain,
Harbor, and Terminal-Bench is not "launch more agents by default". It is
environment legibility, explicit constraints, rerunnable evidence, and
operator control where mutation is possible.

## Design

`scripts/gates/native_runtime_playbook.py` will reuse the P19 probe as its
source of truth. The playbook builder consumes either:

- a raw native runtime profile through `--profile`; or
- the existing P19 fixture root through `--fixture-root`.

For each passing probe launch plan, it emits a structured recipe with:

- preflight commands to inspect the environment;
- an exact approval prompt;
- manual command templates;
- evidence required before claiming success;
- cleanup commands;
- safety metadata proving the report itself is read-only.

If the underlying probe fails, the playbook report fails and does not present
the native runtime surface as executable.

## Safety Properties

- no commands are executed by the playbook builder;
- `auto_execute` is always `false`;
- `mutates_files_by_default` is always `false`;
- `external_telemetry` is always `false`;
- native recipes require operator approval;
- cleanup is explicit for worktree, dynamic workflow, and agent-team recipes;
- auto-launch attempts still fail through `auto_launch_not_allowed`.

## Score Impact

P23 is expected to move native execution escalation from 9.35 to 9.6. It does
not solve pushed event/channel compatibility; that remains P24.

## Verification

```text
python -m pytest tests/test_regression_native_runtime_playbook.py tests/test_regression_native_runtime_probe.py tests/test_regression_v019_release_story.py -q
python scripts/gates/native_runtime_playbook.py --fixture-root tests/fixtures/native_runtime_probe --json
python scripts/gates/native_runtime_probe.py --fixture-root tests/fixtures/native_runtime_probe --json
python scripts/gates/harness_decision_ledger.py --json
```

## Follow-Up

Only after real operator-approved playbook runs produce useful evidence should
Athanor consider a separate apply-mode launcher. That launcher must require an
explicit flag and should remain outside the default CI path.
