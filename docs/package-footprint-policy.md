# Package Footprint Policy

P21 adds a read-only package footprint policy gate. It separates Athanor's
repo-local development history from the default ship profile so a valid plugin
package does not silently become a large archive of plans, tests, and CI
history.

The current reduction decision is tracked in
`docs/package-footprint-reduction.md`.

## Run

```text
python scripts/gates/package_footprint_policy.py --json
```

Strict mode treats warnings as failures:

```text
python scripts/gates/package_footprint_policy.py --strict --json
```

## What It Checks

- package file count budget;
- package total byte budget;
- per-file large-file budget;
- dev-only candidates for ship profile review;
- zero irreversible actions.

The gate uses the same broad package scan as distribution smoke, excluding
local runtime/cache directories such as `.athanor/`, `.git/`,
`.pytest_cache/`, `.venv/`, `__pycache__/`, and `ref/`.

## Ship Profile Buckets

The report classifies files into buckets such as:

- `runtime`;
- `runtime_support`;
- `distribution_metadata`;
- `schemas`;
- `docs`;
- `development_history`;
- `development_metadata`;
- `development_ci`;
- `tests`;
- `evals`;
- `maintenance`;
- `other`.

The default dev-only candidates are:

- `tests/**`;
- `.venv/**`;
- `docs/plans/**`;
- `docs/archive/**`;
- `docs/goals-completed/**`;
- `docs/architecture/**`;
- `.github/**`;
- `.python-version`;
- `pyproject.toml`;
- `uv.lock`.

Each candidate is reported with `recommended_action:
exclude-from-ship-profile`. This is a recommendation for a future packaging
profile, not a deletion instruction.

The report also emits `ship_profile` and `ship_profile_decisions`. Budget
checks apply to the default ship profile after explicit exclusions, while the
full repo-local scan remains visible for audit and cleanup planning.

## Read-Only Policy

The gate never deletes, moves, or rewrites files. It emits
`irreversible_actions: 0`, has `mutates_files_by_default: false`, and does not
use external telemetry.

Keep development records repo-local until an explicit packaging profile exists.
The distinction is:

- repo-local: useful for engineering memory, review, and audits;
- ship profile: the minimum runtime and operator surface users need by default.

## CI Posture

CI runs the gate without `--strict` first. That means budget failures fail CI,
while dev-only candidates produce a warning status and an exit code of `0`.
The maintenance profile can include this warning while remaining safe for
operator review.
