# Review Lens Sections (carved from skills/review/SKILL.md)

STOP-Read companion (v0.18.3, gstack-style section carving). The /athanor:review leader loads the relevant section **on demand** after Step 1.5 lens selection — not always-loaded. Verbatim move from the skill router; no content change.

## Personas

The 6-lens dispatch above is the default code-review surface. Users MAY further
opt into a **persona set** via `athanor.json` `review.personas[]` (schema:
`schemas/athanor-config.schema.json` → `properties.review.properties.personas`).
Personas refine *voice* and *focus area* — they are not parallel lenses. When
both `review.lenses` and `review.personas` are configured, each lens reviewer
receives the persona descriptor as a voice instruction in its dispatch prompt.

The 6 athanor-native personas form a vocabulary-compressed subset of CE's 18
reviewer personas (full catalog at `skills/ce-code-review/references/persona-catalog.md`).
Each persona definition follows the same shape: a selection rule (always-on vs
conditional), the bug class it hunts, and the voice it uses to phrase findings.

### Persona: correctness
**Selection:** always-on
**Focus:** logic errors, edge cases, state management bugs, error propagation,
intent-vs-implementation mismatches
**Voice:** precise, evidence-anchored ("at file:line, when `x == 0`, the loop
exits without flushing the buffer — original intent stated in plan.md §3 was
'flush on every exit path'"). Cites the diff and the intent source side by side.

### Persona: security
**Selection:** conditional — fires when the diff touches auth middleware,
public endpoints, input handling, permission checks, or secret management
**Focus:** exploitable vulnerabilities, auth bypass, input validation, secrets
leakage, OWASP top-10 patterns
**Voice:** threat-model framed ("an unauthenticated caller could reach
endpoint X by ..."). Names the attacker, the path, and the consequence.

### Persona: performance
**Selection:** conditional — fires when the diff touches DB queries, ORM
calls, loop-heavy data transforms, caching layers, or async/concurrent code
**Focus:** algorithmic complexity (Big-O regressions), N+1 DB queries,
unnecessary I/O round-trips, hot loops doing redundant work
**Voice:** complexity-explicit ("this transform is O(n²) over `items` whose
upstream cardinality is unbounded — at n=10⁴ this dominates request latency").
Cites measured or estimated cost, not vibes.

### Persona: testing
**Selection:** always-on
**Focus:** coverage gaps, weak assertions, brittle implementation-coupled
tests, missing edge case tests, snapshot-blindness
**Voice:** asks "what would fail if this implementation were wrong?". Flags
tests that pass even when the SUT is broken (no observed-vs-asserted gap).

### Persona: maintainability
**Selection:** always-on
**Focus:** premature abstraction, dead code, naming clarity, coupling,
complexity that doesn't pay rent
**Voice:** future-reader oriented ("a maintainer 6 months from now will read
`process()` and not know whether it mutates state — rename or document the
side effect"). Optimizes for the second reader, not the first writer.
**Heuristics (quality lens):**
- **silent-failure** — flag swallowed errors: empty catch blocks, bare
  `except: pass`, error-ignoring fallbacks, discarded Promise rejections,
  `.catch(() => {})`. A failure that vanishes silently is worse than one that
  crashes loudly. (concept from ECC silent-failure-hunter, MIT)
- **project-standards** — audit changes against the repo's own `CLAUDE.md` /
  `AGENTS.md` conventions: frontmatter rules, naming, and cross-platform
  portability. Flag deviations from documented house style. (concept from CE
  project-standards-reviewer, MIT)

### Persona: adversarial
**Selection:** conditional — fires when the diff has ≥50 changed non-test
non-generated non-lockfile lines, OR touches auth, payments, data mutations,
or external API integrations
**Focus:** failure-mode constructor — actively tries to break the change
under load, concurrency, malformed input, network partition, partial failure
**Voice:** hypothesis-driven ("what if the upstream service returns 200 with
an empty body? What if two callers race on this row?"). Each finding is a
concrete failure scenario, not a vague concern.

## Doc review mode

`/athanor:review` defaults to `--target code` (the 6-lens code review above).
Users invoke document review explicitly: `/athanor:review --target docs`. The
leader detects the flag at Step 1 (Scope Detection) and routes to a doc-mode
dispatch instead of the code-lens dispatch.

Doc mode classifies the target by **doc-type**:

| Doc-type | Examples | Selected lens set |
|---|---|---|
| `requirements` | `.athanor/sessions/*/requirements.md` | coherence, feasibility, scope-guardian, product-lens |
| `plan` | `docs/plans/*.md`, `.athanor/sessions/*/plan.md` | coherence, feasibility, scope-guardian, design-lens, adversarial-document |
| `spec` | `docs/specs/*.md`, RFC-shaped docs | coherence, feasibility, security-lens, design-lens |
| `architecture` | `docs/architecture/*.md`, ADRs | coherence, design-lens, security-lens, adversarial-document |

Persona set inherited from CE's `ce-doc-review` (catalog at
`skills/ce-doc-review/SKILL.md`):

- **coherence** — internal consistency, definition-vs-use alignment, claim
  chains that close without contradiction
- **feasibility** — implementability under stated constraints (budget,
  timeline, available primitives), unstated dependencies surfaced
- **scope-guardian** — flags scope creep, "and also..." additions that
  weren't in the original intent
- **product-lens** — user-value framing; whether the doc answers
  "why does this matter to the user?"
- **security-lens** — threat model in the doc surface, missing trust
  boundaries, unstated attacker assumptions
- **design-lens** — architectural soundness, abstraction choice, system
  boundary clarity
- **adversarial-document** — failure-mode constructor for the doc itself;
  what happens when the reader misinterprets section X, what plans break if
  assumption Y is wrong

Output shape mirrors code review: parallel dispatch (one worker per selected
doc persona), per-persona `ATHANOR_RESULT` blocks, leader consolidates into a
single `.athanor/sessions/{session-id}/review.md` grouped by severity. The
score table renames lens labels to persona labels but keeps the 0-10 rubric.

CLI defaults: `--target code` is implicit when no flag is given. `--target docs`
opts into doc mode. No third value is currently supported.

