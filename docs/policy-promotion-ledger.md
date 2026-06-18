# Policy Promotion Ledger

Policy promotion is the learning-governance path from an observed issue to an
enforced operating rule. It keeps lessons from becoming unbounded prose.

Committed policy promotion records live under:

```text
docs/policy-promotions/*.json
```

The read-only gate is:

```text
python scripts/gates/policy_promotion_ledger.py --json
```

## Lifecycle

```text
incident -> lesson -> candidate_policy -> policy -> gate_candidate -> gate -> retired
```

Each promotion record must have:

- owner office `learning-governance` and owner role `policy-steward`;
- source refs and evidence refs that resolve in the repository;
- acceptance criteria;
- rollback plan once the item reaches `policy` or later;
- ordered, gap-free `state_history[]`;
- one current state matching `current_state`;
- safety metadata proving read-only default behavior.

`gate_candidate` and `gate` states must include:

- `gate_refs[]`;
- `test_refs[]`;
- `schema_refs[]`.

`retired` states must include:

- `retired_reason`;
- `replacement_refs[]`.

This ledger deliberately does not rewrite lesson files, install hooks, launch
runtimes, or execute promoted gates. It only proves that learning governance
can promote or retire policy with evidence.
