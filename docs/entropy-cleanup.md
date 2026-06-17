# Entropy Cleanup Report

P11 adds a read-only cleanup sensor for Athanor harness entropy.

Run:

```bash
python scripts/gates/entropy_cleanup.py --json
```

The gate scans dated implementation plans, capture-only hook candidates, local
`ref/` repositories, and runtime conformance. It does not delete files, update
refs, enable hooks, install hooks, write settings, or contact the network.

Statuses:

- `pass`: no warnings or failures.
- `warn`: cleanup actions exist, but no structural failure was found.
- `fail`: required metadata or runtime conformance is broken.

Warnings exit `0` by default so CI can collect the report without turning
historical cleanup work into a release blocker. Use `--strict` when a scheduled
cleanup run or release pass intentionally wants a zero-warning queue.

Useful options:

```bash
python scripts/gates/entropy_cleanup.py --json --plan-warn-days 14
python scripts/gates/entropy_cleanup.py --json --ref-warn-days 30
python scripts/gates/entropy_cleanup.py --json --strict
```

Report categories:

- `plans`: counts open dated plans and warns when unchecked steps exceed the
  plan warning age.
- `hook_candidates`: checks that capture-only hook candidates carry
  `candidate_since`, `review_after_days`, and source references, then warns
  when review age is exceeded.
- `refs`: reports local `ref/` repositories and warns when the last commit date
  exceeds the freshness threshold.
- `mirrors`: includes the P9 runtime conformance result so Claude/Codex/hook
  drift appears in the same cleanup report.

The output includes stable action ids such as `review-open-plans`,
`review-hook-candidates`, and `refresh-ref-repositories`. Future cleanup loops
can consume these actions without parsing prose.
