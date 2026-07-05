# LFG Loop Scope Change Critic

Use this when a cycle discovers work outside the locked objective.

The critic reads `loop.md`, current receipts, latest diff summary, and the
proposed scope change. It returns one of:

- `accept`: the change is required to satisfy the objective;
- `reject`: the change is unrelated and should be deferred;
- `escalate`: user decision required.

High-impact, destructive, or product-direction changes always escalate. Accepted
changes are appended to `loop.md` under `Scope Changes`; rejected changes become
residuals or follow-up items.
