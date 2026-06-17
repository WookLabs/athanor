# P19 Native Runtime Probe Design

Date: 2026-06-17
Status: planned

## Context

The post-P16 deep research report scored runtime backend recommendation,
worktree isolation, and dynamic workflow / agent-team readiness below the 9.5
target because P12 can recommend native Claude Code surfaces but cannot yet
prove what is locally available or safe to launch.

P19 closes that gap without expanding the runtime blast radius. The probe is a
read-only harness gate that records availability and dry-run launch plans for:

- `/goal`
- `/loop`
- manual worktree isolation
- dynamic workflows
- agent teams

It does not start Claude sessions, create worktrees, schedule loops, mutate
settings, or export telemetry.

## Approach

Add `scripts/gates/native_runtime_probe.py` as a deterministic gate with two
modes:

1. Fixture mode for CI:
   `python scripts/gates/native_runtime_probe.py --fixture-root tests/fixtures/native_runtime_probe --json`
2. Local profile mode for ad hoc checks:
   `python scripts/gates/native_runtime_probe.py --profile path/to/profile.json --json`

The gate reads a capability profile, normalizes the known native surfaces, and
emits:

- surface status: `available`, `documented`, `manual`, `unavailable`, or
  `unknown`;
- evidence refs for each status;
- dry-run launch plans for requested backends;
- policy violations when a profile attempts to mark native surfaces as
  auto-launchable by default.

## Architecture

`native_runtime_probe.py`

- validates profile JSON;
- normalizes missing surfaces to `unknown`;
- maps P12 backends to native surfaces;
- creates launch plans with `mode: dry-run-only`;
- fails profiles that set `auto_launch_allowed: true`;
- evaluates fixture expectations.

`schemas/native-runtime-probe-report.schema.json`

- validates the fixture-mode report shape.

`tests/test_regression_native_runtime_probe.py`

- locks schema-valid fixture output;
- locks dry-run-only launch plans;
- locks fail-loud invalid profile handling;
- locks policy failure for auto-launch attempts.

CI integration adds a named `Native runtime probe gate` before the broad pytest
suite.

## Safety Rules

1. Native surfaces are probeable, not automatically launchable.
2. Dynamic workflow, agent-team, `/goal`, and `/loop` plans require explicit
   operator approval.
3. Worktree plans must state cleanup requirements and stay dry-run by default.
4. Unknown capabilities are warnings, not hard failures, unless a profile tries
   to use them as executable defaults.
5. The gate must remain dependency-free beyond Python stdlib.

## Score Movement

Expected score movement after P19:

- Runtime backend recommendation: 9.2 -> 9.55
- Worktree isolation: 8.8 -> 9.5
- Dynamic workflow / agent-team readiness: 8.9 -> 9.5

The score movement is bounded: P19 proves safe readiness and dry-run planning,
not full native orchestration.

