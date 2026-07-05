# /athanor:lfg vs /athanor:lfg-loop

`/athanor:lfg` is one delivery cycle: plan, work, review, fix, residual handoff,
browser test when relevant, PR/CI handling, and result packet.

`/athanor:lfg-loop` is the macro harness around one or more delivery cycles. It
adds objective intake, deep research/discovery, architecture/design gates,
durable loop state, per-cycle receipts, assessment/review evaluators, controller
decisions, human escalation, terminal persistence, and next-loop selection.

`/athanor:lfg-loop` invokes `/athanor:lfg`; it does not reimplement or bypass it.
