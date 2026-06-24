# Worker Context Packets

A worker context packet is the prompt-level convention for handing a
clean-context worker enough bounded context to act well — without turning the
leader into an implementer. It is a dispatch-quality convention, **not**
runtime-enforced and **not** proof of completion: it never replaces receipts,
tests, work logs, review findings, or user ratification.

## Thin Leader framing

The principle is Thin Leader. The leader assembles source references,
constraints, a write policy, and an output contract, then dispatches a clean
worker. The worker reads the cited artifacts and does the work. The packet is
how that handoff is made explicit so it does not silently degrade into a thin,
intent-free prompt.

Rich context is allowed, but it must be **bounded, summarized, and sourced**:

- `source_refs` distinguish the source of truth (paths the worker reads) from
  injected summaries, so provenance stays auditable.
- `memory_refs` carry only `safe_to_inject` summaries drawn from
  [`docs/memory-index.md`](memory-index.md) — never raw lesson bodies or
  transcripts.
- Handoff-derived context follows [`docs/handoff-artifact.md`](handoff-artifact.md)
  and stays reference-first.

## Source of truth lives elsewhere — reference, don't re-encode

This doc deliberately does **not** restate the field-level shapes. The real,
singly-sourced contracts are:

- **Executor dispatch packet shape** —
  [`skills/work/references/splitter.md`](../skills/work/references/splitter.md).
  How `/athanor:work` builds the per-subtask dispatch (`subtask_id`,
  `files_in_scope`, `verify`, `execution_note`, …) is owned there.
- **Result schema (`ATHANOR_RESULT` … `END_RESULT`)** —
  [`skills/work/references/spec-then-tdd-handler.md`](../skills/work/references/spec-then-tdd-handler.md).
  The result envelope a worker emits is owned there; do not duplicate the field
  list into this convention.
- **Actually-enforced runtime write-scope** —
  [`skills/work/references/freeze.md`](../skills/work/references/freeze.md).
  Write-policy enforcement is a real PreToolUse gate. This packet convention
  only *declares* a write policy; `freeze.md` is what the runtime blocks on.

When those three contracts change, they change in one place. This doc points at
them so dispatch guidance stays discoverable without a second mirror to keep in
sync.

## Non-goals / honesty

This layer is convention-only. State plainly: it is **not runtime-enforced**.

- No packet broker, queue, or runtime packet engine, and no packet-builder
  agent — assembly is leader prose.
- No machine-enforced packet parsing. Worker fitness is proven by the real
  runtime gates (freeze write-scope, the Phase 3 spec-then-tdd gate, the Stop
  completion-claim hook) and by receipts/tests — not by this convention.
- No retroactive conversion of historical `.athanor/sessions/` artifacts, and
  no raw transcript injection (use `source_refs` plus bounded summaries).
- Runtime blocking can be added later only when there is code-backed evidence
  for the specific dispatch path being described.
