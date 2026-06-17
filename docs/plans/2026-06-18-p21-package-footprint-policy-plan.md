# P21 Package Footprint Policy Plan

Date: 2026-06-18
Branch: `feat/p21-package-footprint-policy`

## Problem

P20 proved that the maintenance profile can run safely, but the distribution
surface still treats the repository footprint as a single package. The current
scan is valid but broad: tests, historical plans, archives, and architecture
research are visible in the same footprint as runtime skills and metadata.

## Goal

Raise package footprint policy and distribution discipline above 9.5/10 by
adding a read-only gate that classifies files, reports budgets, and identifies
dev-only candidates for future ship-profile exclusion.

## Acceptance Criteria

1. `scripts/gates/package_footprint_policy.py --json` emits a schema-backed
   report.
2. The report includes package bytes, largest files, ship-profile buckets,
   dev-only candidates, recommendations, checks, and zero irreversible actions.
3. Budget failures exit `1`; warn-only dev candidates exit `0` unless
   `--strict` is set.
4. CI runs the gate before broad pytest.
5. Maintenance profile includes the gate as a read-only step.
6. CHANGELOG, operator docs, architecture notes, and harness decision ledger
   explain the policy.

## Verification

```text
python -m pytest tests/test_regression_package_footprint_policy.py tests/test_regression_v019_release_story.py tests/test_regression_maintenance_profile.py -q
python scripts/gates/package_footprint_policy.py --json
python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json
python scripts/gates/harness_decision_ledger.py --json
python -m pytest tests/ -q
git diff --check
```

## Non-Goals

- no file deletion;
- no package exclusion implementation yet;
- no external telemetry;
- no default strict failure on dev-only candidates;
- no marketplace packaging rewrite.
