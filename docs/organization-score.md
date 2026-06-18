# Organization Score Gate

P30 turns the maturity score from a maintained scorecard into a read-only
computed report.

Run:

```text
python scripts/gates/organization_score.py --json
```

The gate reads current evidence from the organization operating model,
work-item registry, stage receipts, policy promotion ledger, harness decision
ledger, package knowledge index, package footprint policy, CI gate coverage,
and composite safety profile.

The target is `9.8`. The report passes only when required inputs do not fail
and the weighted evidence score is at least the target. Bounded warnings, such
as package-footprint dev-only candidates, remain visible as scored residual
gaps instead of being hidden in prose.
