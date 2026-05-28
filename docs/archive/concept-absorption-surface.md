<!-- Relocated from CLAUDE.md at v0.16.0.
     Canonical runtime reference remains in CLAUDE.md (1-paragraph summary).
     This file contains historical detail (D8/D9/D10/D11/D12 decisions, vendor manifest, removed items inventory) moved here to reduce per-session token load. -->

# Concept Absorption Surface (Historical Detail)

## Concept Absorption Surface (post-v0.12.0)

This section was previously titled §"Vendored Surface — Identity Guard
Layer" through v0.10.0 → v0.11.8. v0.12.0 renames it to reflect the
post-cutover reality: the wholesale vendored surface is gone; what
remains is a 5-concept absorption inventory + 1 KEEP skill + 2 KEEP
sub-agents.

athanor v0.10.0 originally absorbed **compound-engineering v3.8.3**
(33 skills + 49 sub-agents) and **superpowers v5.1.0** (13 skills) under
the `/athanor:ce-*` and `/athanor:sp-*` namespaces. **v0.10.0
plan-of-record misread the user's concept-absorption intent as wholesale
plugin vendoring.** v0.12.0 atomic cut closes the scope correction —
surface reduced from 95 items down to 3 (97%): 1 KEEP skill +
2 KEEP sub-agents, plus 5 concepts absorbed as prose subsections in
athanor-native skills. See
`docs/archive/v010-v011-vendoring-scope-correction.md` for the full
retrospective and `docs/v0.12.0-migration.md` for the user-facing
migration guide.

### Retained vendored items

**1 retained skill** (D8):

- `/athanor:ce-test-browser` — user opt-in UI browser automation
  (compound-engineering v3.8.3). Non-identity but real utility; T2
  provenance block preserved.

**2 retained sub-agents** (D12) under `agents/vendored/ce/`:

- `ce-git-history-analyzer.agent.md` — generic git-history discovery
  dispatch target.
- `ce-repo-research-analyst.agent.md` — generic repo-research discovery
  dispatch target.

### 5 concepts absorbed as native prose (NOT vendored directories)

The following upstream concepts have been lifted into athanor-native
skills with full MIT attribution preserved. Each entry cross-links to
NOTICE.md §"Concepts adopted from upstream" for the canonical attribution
ledger.

1. **Reviewer-persona vocabulary** — from `ce-code-review@3.8.3` (MIT,
   Kieran Klaassen / Every Inc) into `skills/review/SKILL.md` §"Personas".
   See NOTICE.md §"Concepts adopted from upstream" entry #1.
2. **Iron Law + Four Phases (debugging discipline)** — from
   `sp-systematic-debugging@5.1.0` (MIT, Jesse Vincent) into
   `skills/debug/SKILL.md` §"Systematic Debugging Discipline". See NOTICE.md
   §"Concepts adopted from upstream" entry #2.
3. **Requirements capture (R-ID / A-ID / F-ID / AE-ID)** — from
   `ce-brainstorm@3.8.3` (MIT, Kieran Klaassen / Every Inc) into
   `skills/discuss/references/requirements-capture.md` (v0.9.0
   absorption; v0.12.0 attribution formalized). See NOTICE.md §"Concepts
   adopted from upstream" entry #3.
4. **Skill-discovery preamble** — from `sp-using-superpowers@5.1.0` (MIT,
   Jesse Vincent) into CLAUDE.md §"using-superpowers boundary (v0.11.1)".
   See NOTICE.md §"Concepts adopted from upstream" entry #4.
5. **Doc-review persona mode** — from `ce-doc-review@3.8.3` (MIT, Kieran
   Klaassen / Every Inc) into `skills/review/SKILL.md` §"Doc review mode".
   See NOTICE.md §"Concepts adopted from upstream" entry #5.

### Removed in v0.12.0

The atomic cut removed **45 skill directories** + **47 sub-agents** under
the vendored namespaces. Full enumeration lives in NOTICE.md §"Removed in
v0.12.0" + `docs/v0.12.0-migration.md` (user-facing migration table).
Summary grouped by source plugin:

**compound-engineering v3.8.3 — originally 33 ce-* skill directories, 32 removed at v0.12.0** (3
LIFT-source + 29 DROP; `ce-test-browser` carved out per D8):

- LIFT-source (concept absorbed into native skills): `ce-code-review`,
  `ce-doc-review`, `ce-brainstorm`.
- DROP (no athanor-native migration target — install upstream
  compound-engineering if needed): `ce-agent-native-architecture`,
  `ce-agent-native-audit`, `ce-clean-gone-branches`, `ce-commit`,
  `ce-commit-push-pr`, `ce-compound`, `ce-compound-refresh`, `ce-debug`,
  `ce-demo-reel`, `ce-dhh-rails-style`, `ce-frontend-design`,
  `ce-gemini-imagegen`, `ce-ideate`, `ce-lfg` (D9 full DROP),
  `ce-optimize`, `ce-plan` (D9 full DROP), `ce-polish-beta`,
  `ce-product-pulse`, `ce-proof`, `ce-resolve-pr-feedback`,
  `ce-riffrec-feedback-analysis`, `ce-sessions`, `ce-simplify-code`,
  `ce-slack-research`, `ce-strategy`, `ce-test-xcode`, `ce-work` (D9
  full DROP), `ce-work-beta`, `ce-worktree`.

**superpowers v5.1.0 — originally 13 sp-* skill directories, all removed at v0.12.0** (2
LIFT-source + 11 DROP):

- LIFT-source (concept absorbed into native skills): `sp-systematic-debugging`,
  `sp-using-superpowers`.
- DROP (install upstream superpowers if needed):
  `sp-brainstorming`, `sp-dispatching-parallel-agents`,
  `sp-executing-plans`, `sp-finishing-a-development-branch`,
  `sp-receiving-code-review`, `sp-requesting-code-review`,
  `sp-subagent-driven-development`, `sp-test-driven-development`,
  `sp-using-git-worktrees`, `sp-writing-plans`, `sp-writing-skills`.

**compound-engineering sub-agents — originally 49, with 47 removed at v0.12.0** under
`agents/vendored/ce/`. 2 retained per D12 above (`ce-git-history-analyzer`,
`ce-repo-research-analyst`); the remaining 47 `*.agent.md` files removed
together (no athanor-native dispatch target relies on them post-cutover).

### Identity guard layer (what survives the cutover)

The four athanor identity commitments survive the v0.12.0 cutover intact.
Post-cutover the surface is much smaller (1 KEEP skill + 2 KEEP sub-agents
+ 5 absorbed concept prose subsections); the identity commitments are
upheld by *native skill prose + regression locks* — namespace defense is
no longer needed because the inflated vendored namespace was removed:

1. **Thin Leader contract.** The athanor leader (main session) NEVER does
   implementation work directly. It dispatches clean-context workers and
   presents results. The post-v0.12.0 surface is athanor-native + 1 KEEP
   skill + 2 KEEP sub-agents — the wholesale vendored namespace that
   previously required guard prose against agent-direct voice is gone.
2. **Cross-model adversarial planning stays athanor-native.** `/athanor:plan`
   dispatches Planner A (Claude) + Planner B (Codex) + Critic per
   v0.7.x~v0.9.0. CE's single-agent planning skill (`ce-plan`) was DROPped
   per D9; users wanting CE's flow install the upstream compound-engineering
   plugin.
3. **Spec-then-TDD discipline stays athanor-native.** `/athanor:work`
   applies Splitter `execution_note` classification + conjunction-of-three
   Phase 3 gate. CE's execution skill (`ce-work`) and superpowers'
   test-driven-development skill (`sp-test-driven-development`) were
   DROPped at v0.12.0 (D9 + DROP-class respectively); users wanting those
   flows install the upstream plugins directly.
4. **Stop hook runtime gate scope.** The Stop hook
   (`scripts/hooks/stop_verify_claims.py`) triggers on every `Stop` event
   regardless of which skill produced the turn output. Per D11 the
   v0.10.2 vendor-aware whitelist extension (18 idioms + paraphrase regex
   layer + Cyrillic / Greek / Armenian homoglyph fold) is preserved with
   rationale re-framed to **general defensive coverage**: those idioms +
   normalizations apply broadly to English / Korean material-claim
   phrasing and are not vendored-prose-specific. The companion-fix arc
   5 layers (v0.11.3 input parser → v0.11.4 plugin-root path → v0.11.5
   doc drift → v0.11.6 sentinel body hash → v0.11.7 scanner extension +
   B1 minimal) survive the cutover intact (D10). Honesty residuals
   (v0.11.8+): LLM-class semantic similarity, conditional / speculative
   tense without prefix marker, multi-paragraph quote spans,
   Cherokee / full-width-Latin homoglyphs.

### Vendor manifest (post-v0.12.0)

- Source plugins (origin attribution preserved):
  `compound-engineering@3.8.3`
  (https://github.com/EveryInc/compound-engineering-plugin),
  `superpowers@5.1.0` (https://github.com/obra/superpowers).
- Vendor pattern: T2 (per `docs/DEPENDENCIES.md` §Tier ordering).
- Layout (post-v0.12.0): `skills/ce-test-browser/` (1 KEEP) at depth 1
  under `skills/`; 2 sub-agents at `agents/vendored/ce/*.agent.md`.
  No `skills/ce-*` or `skills/sp-*` directories beyond `ce-test-browser`
  exist.
- Concept-absorption inventory (5 LIFT entries): NOTICE.md §"Concepts
  adopted from upstream"; per-concept inventory under `concepts/*.md`.
- Drift check process: `scripts/check_vendor_drift.py` (since v0.10.1)
  walks the present skill tree, so it naturally iterates the post-cutover
  surface.

### What the post-v0.12.0 surface does NOT do

- Does NOT carry a wholesale vendored namespace. Users who need
  upstream CE or superpowers skills install those plugins directly
  (`docs/v0.12.0-migration.md` documents the path).
- Does NOT re-license athanor (athanor stays MIT; CE and superpowers
  stay MIT under their copyright holders).
- Does NOT deprecate any athanor-native skill in favour of a vendored
  variant.
- Does NOT auto-install upstream plugins as dependencies. athanor
  stands alone.
