# P21 Package Footprint Policy Design

Date: 2026-06-18

## Context

The latest workflow/loop/harness comparison identifies package footprint
policy as the clearest sub-9.5 gap. Athanor already has distribution smoke, but
that gate proves the package is loadable rather than lean.

## Design

Add `scripts/gates/package_footprint_policy.py` as a read-only classifier and
budget gate. It reuses the distribution smoke package scan so excluded local
runtime/cache directories remain consistent. It then performs a full file
classification pass and emits:

- package summary;
- largest files;
- bucket totals;
- dev-only candidates;
- recommendations;
- pass/warn/fail checks;
- read-only profile metadata.

## Status Semantics

- `fail`: hard package budgets fail.
- `warn`: hard budgets pass, but dev-only candidates exist.
- `pass`: no failures and no warnings.

The default CLI exits `0` for `pass` and `warn`. `--strict` exits `1` for
`warn`.

## Candidate Policy

The first candidate set is intentionally conservative:

- `tests/**`;
- `docs/plans/**`;
- `docs/archive/**`;
- `docs/loops-completed/**`;
- `docs/architecture/**`;
- `.github/**`.

These paths remain repo-local. The gate only recommends
`exclude-from-ship-profile`; it does not remove files.

## Integration

The gate is wired into CI and the P20 maintenance profile. A warn-only report
does not break CI, but it makes ship-profile debt visible in the same recurring
operator report as entropy cleanup, distribution smoke, observability, native
runtime readiness, and decision-ledger status.

## Architecture Review

The design keeps the current safety posture:

- no mutation by default;
- no hidden packaging rewrite;
- no external telemetry;
- no dependency on Claude CLI;
- no strict failure until budgets or the operator choose it.

This moves package-footprint policy from an informal research finding into a
repeatable harness signal.
