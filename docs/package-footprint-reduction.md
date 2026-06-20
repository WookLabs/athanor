# Package Footprint Reduction

This document records the current ship-profile reduction decision for
development-only and reference-radar assets. It does not authorize deletion.
The goal is to keep useful engineering evidence repo-local while keeping the
default shipped plugin focused on runtime and operator-facing surfaces.

## Verification Commands

```text
python scripts/gates/package_footprint_policy.py --json
python scripts/gates/catalog_admission.py --json
```

Use `package_footprint_policy.py` as the package-size and ship-profile evidence
gate. Use `catalog_admission.py` as the reference radar evidence gate for
`ref/` inventory and adoption decisions.

## Ship-Profile Decisions

| Path prefix | Ship-profile action | Repo-local action | Deletion policy | Reason |
|---|---|---|---|---|
| `docs/plans/` | exclude from default ship profile | keep repo-local | do not delete | Implementation plans are execution history and review evidence. |
| `docs/archive/` | exclude from default ship profile | keep repo-local | do not delete | Archived docs are historical audit material, not runtime surface. |
| `tests/` | exclude from default ship profile | keep repo-local | do not delete | Tests run in CI and local verification, but users do not need them in the runtime package. |
| `docs/architecture/` | exclude from default ship profile | keep repo-local | do not delete | Deep architecture analysis informs maintainers and should not inflate default context. |
| `ref/` | exclude from default ship profile | keep repo-local | do not delete | External clones are reference radar inputs and must never be treated as shipped plugin content. |

## Policy

- Keep repo-local evidence available for audits, ref analysis, and future
  comparison.
- Exclude the listed prefixes from the default ship profile where packaging
  supports explicit profiles.
- Do not delete historical files as part of footprint reduction unless a
  separate cleanup decision names the artifact, owner, replacement evidence,
  and rollback path.
- Keep `ref/` governed by catalog admission rather than package footprint
  alone.
- Keep package warnings bounded: dev-only candidates may warn, but file and
  byte budgets should be evaluated against the default ship profile.

## Current Gate Contract

`scripts/gates/package_footprint_policy.py --json` emits:

- full repo-local package scan;
- default `ship_profile` summary after exclusions;
- explicit `ship_profile_decisions`;
- dev-only candidate examples;
- `irreversible_actions: 0`.

The gate is read-only. It does not delete, move, or rewrite files.
