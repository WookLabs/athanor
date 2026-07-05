# LFG Loop Enforcement Scope

LFG Loop quality is explicit and artifact-based:

- durable loop ledger;
- per-cycle receipts;
- assessment/review artifacts;
- controller exit codes;
- run-log and decision log;
- human escalation.

These gates are stronger than prose checks because they inspect command-shaped
evidence. They are still leader-orchestrated, so the honesty label is
`advisory (leader-bound artifacts and exit codes)`, not a global runtime gate.

There is no active Stop completion-claim hook in this architecture. Do not claim
hidden end-of-turn claim verification. Claims must cite fresh evidence and the
loop terminal artifact.
