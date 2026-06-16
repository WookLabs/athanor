# Athanor Ref Deep Research

Date: 2026-06-16
Refresh: 2026-06-17
Branch: `feat/hook-payload-replay`
Purpose: compare Athanor against current Claude Code hook/plugin references and
turn the findings into an adoption plan for a higher-performance, higher-trust
plugin.

## Executive Verdict

Athanor is ahead on evidence depth and replay discipline, and the P0-P2 work
has closed much of the original catalog and lifecycle-discovery gap. The
current branch has strong live-redacted payload fixtures, replay gates, health
diagnostics, provenance-aware PostToolUse evidence, an opt-in safety-pattern
corpus, and capture-only lifecycle entries for the next hook surfaces. The
strongest references are still wider in marketplace/product UX, installer
flows, and cross-runtime hook generation.

The next optimization layer should not add many default runtime hooks. The
better direction remains a cataloged, opt-in hook platform with measured
overhead, evidence-backed promotion rules, and cross-runtime manifest tests.
After the 2026-06-17 refresh, the next concrete implementation unit is P3:
Cross-Runtime Manifest Matrix.

## Reference Set

All refs are cloned under ignored `ref/` directories in this worktree.

| Ref | HEAD | Role | Files | Hook files | Test-like files | Packaging |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `alexei-led/cc-thingz` | `2e590b6` | Closest architecture competitor: generated hooks across Claude, Codex, Gemini, and Pi | 946 | 162 | 220 | npm, pyproject, Makefile |
| `anthropics/claude-code` | `64ceb97` | Official plugin examples and hook patterns | 163 | 54 | 2 | examples only |
| `anthropics/claude-plugins-official` | `8e5d93a` | Official marketplace, trust warning, skill-bundle, and plugin structure reference | 318 | 54 | 3 | marketplace/plugin manifests |
| `anthropics/knowledge-work-plugins` | `79e6030` | Official job-function plugin packaging and Cowork plugin-creator reference | 1083 | 19 | 2 | plugin manifests, MCP |
| `disler/claude-code-hooks-mastery` | `052ad1c` | Hook lifecycle teaching/reference corpus | 44 | 7 | 3 | docs/settings |
| `ElliotJLT/hooksmith` | `836fb7d` | Hook registry and installer UX reference | 34 | 25 | 0 | npm |
| `fricklers/claude-code-config` | `c86b358` | Practical personal hook safety/config reference | 43 | 7 | 1 | settings/scripts |
| `jeremylongshore/claude-code-plugins-plus-skills` | `57b5254b` | Large marketplace, plugin validator, analytics, and catalog UX reference | 14572 | 339 | 907 | npm |
| `karanb192/claude-code-hooks` | `ebcc2a2` | Safety hook corpus with JS tests | 15 | 9 | 4 | npm |
| `launchdarkly-labs/claude-code-session-start-hook` | `3bf625e` | Dynamic SessionStart context-injection reference | 9 | 0 | 0 | npm |
| `obra/superpowers` | `8cf3900` | SessionStart skill discipline reference | 132 | 5 | 67 | npm, Claude/Codex plugin manifests |
| `openai/codex` | `40e7dda` | Official Codex hook/trust/managed-hook implementation reference | 4933 | 124 | 604 | npm, Cargo workspace |
| `RoggeOhta/awesome-codex-cli` | `d23a320` | Codex ecosystem discovery reference for skills, plugins, hooks, and bridge tools | 4 | 0 | 0 | index |
| `shakacode/claude-code-commands-skills-agents` | `2c375be` | Command/skill/agent packaging reference | 34 | 1 | 0 | docs/scripts |
| `sjnims/plugin-dev` | `7b2a821` | Plugin authoring/onboarding reference | 105 | 13 | 3 | docs/scripts |

Upstream URLs:

- https://github.com/alexei-led/cc-thingz
- https://github.com/anthropics/claude-code
- https://github.com/anthropics/claude-plugins-official
- https://github.com/anthropics/knowledge-work-plugins
- https://github.com/disler/claude-code-hooks-mastery
- https://github.com/ElliotJLT/hooksmith
- https://github.com/fricklers/claude-code-config
- https://github.com/jeremylongshore/claude-code-plugins-plus-skills
- https://github.com/karanb192/claude-code-hooks
- https://github.com/launchdarkly-labs/claude-code-session-start-hook
- https://github.com/obra/superpowers
- https://github.com/openai/codex
- https://github.com/RoggeOhta/awesome-codex-cli
- https://github.com/shakacode/claude-code-commands-skills-agents
- https://github.com/sjnims/plugin-dev

Web/docs sources reviewed during the refresh:

- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/plugins-reference
- https://developers.openai.com/codex/hooks

## Scorecard

Scores are relative to the observed reference set, not absolute product
quality.

| Dimension | Athanor | Ref leader | Leader score | Read |
| --- | ---: | --- | ---: | --- |
| Evidence/replay rigor | 9.7 | Athanor | 9.7 | Live-redacted fixtures plus replay gates are the strongest observed proof layer. |
| Hook lifecycle breadth | 7.8 | Claude docs, Codex, `cc-thingz`, Disler | 9.0 | Athanor still enables only Stop, PreToolUse, PostToolUse by default, but P2 now catalogs broad lifecycle candidates as capture-only. |
| Hook catalog/installer UX | 7.0 | `hooksmith`, official marketplace, `jeremylongshore` | 9.2 | P0 added a catalog and schema; Athanor still lacks install/remove/dry-run UX. |
| Safety rule corpus | 8.4 | `karanb192`, `fricklers`, `cc-thingz` | 8.7 | P1 added pattern IDs and observe/warn mode; more live false-positive evidence is still needed before stricter behavior. |
| Cross-runtime portability | 7.2 | `cc-thingz`, Codex, `obra/superpowers` | 9.3 | Athanor has Codex awareness and plugin manifests, but no manifest matrix test or generator yet. |
| Plugin-dev onboarding | 7.5 | official examples, `sjnims/plugin-dev`, `knowledge-work-plugins` | 9.1 | Athanor docs are strong internally, but external authoring flow and validation guide remain thin. |
| Performance posture | 8.8 | Athanor, Codex, `cc-thingz` | 9.0 | Athanor keeps default hook count low; next work should make performance budgets executable. |
| Adoption risk control | 9.4 | Athanor, Codex managed-hook trust model | 9.4 | Athanor's strict deferral and evidence gates reduce false confidence; Codex adds a useful managed/trusted hook model. |

## Hook Event Coverage

| Project | Registered or documented events | Athanor read |
| --- | --- | --- |
| Athanor | Enabled: Stop, PreToolUse, PostToolUse. Capture-only/cataloged: FileChanged, SessionStart, UserPromptSubmit, PreCompact, PermissionRequest, PostToolUseFailure, SubagentStop | Strong core enforcement plus evidence. P2 adds opt-in breadth without new default runtime cost. |
| `cc-thingz` Claude dev-flow | SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Notification, Stop | Best multi-event packaged workflow. Good source for opt-in catalog shape. |
| `cc-thingz` Codex dev-flow | PreToolUse, PostToolUse, Stop, SessionStart | Best cross-runtime manifest reference. |
| OpenAI Codex | PreToolUse, PostToolUse, PermissionRequest, SessionStart, Stop, managed/trusted hook state | Best trust/managed-hook model for P3 matrix thinking. |
| Claude Code docs | UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, PostToolBatch, PermissionDenied, Notification, SubagentStart, SubagentStop, Stop, PreCompact, SessionStart, ConfigChange | Canonical event breadth and payload-shape reference; still requires live capture before Athanor enforcement. |
| official `hookify` | PreToolUse, PostToolUse, Stop, UserPromptSubmit | Good official plugin example; not a full safety platform. |
| official `security-guidance` | SessionStart, UserPromptSubmit, PostToolUse, Stop | Good guidance pattern for contextual safety prompts. |
| official marketplace | Plugin directory, skill bundles, marketplace install/discover model | Strong product boundary and trust-warning precedent. |
| `knowledge-work-plugins` | Skills-first plugin scaffolding, connector docs, hook/MCP path portability | Good authoring-flow reference; hooks are rare and should not be over-scaffolded. |
| LaunchDarkly SessionStart hook | SessionStart | Good proof that SessionStart can inject dynamic repo/session context, but it depends on a live remote service and env secret. |
| `obra/superpowers` | SessionStart | Strong single-event discipline pattern. |
| `fricklers` config | PreToolUse, PostToolUse, SessionStart, Stop | Practical personal setup. |
| `hooksmith` catalog | PreToolUse, PostToolUse, SessionStart/End, UserPromptSubmit, PreCompact | Best UX model for optional hooks. |
| `karanb192` docs/logger | SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, SubagentStart, SubagentStop, Stop, PreCompact, Setup, Notification | Broadest lifecycle awareness, but not all implemented as production hooks. |

## Architecture Findings

### Athanor Strengths

- Evidence is replayable instead of anecdotal. `docs/hook-payload-corpus.md`
  defines live-redacted provenance, importer boundaries, redaction rules, and
  replay gates.
- Default runtime surface is narrow. Three registered hooks keep baseline
  overhead and false-positive risk lower than broad hook bundles.
- Policy promotion is explicit. Evidence mode can be observe/warn/strict, but
  strict default migration remains a separate release decision.
- Hook health is observable. PostToolUse fail-open paths now emit diagnostics
  rather than disappearing silently.
- P0-P2 have converted the initial research into code: catalog/schema/tests,
  opt-in safety corpus, and capture-only lifecycle expansion are now present in
  the branch and PR.

### Ref Strengths Worth Absorbing

- `cc-thingz` has a generated hook pipeline. Tests prove hook manifests and
  copied hook assets across Claude, Codex, Gemini, and Pi targets.
- `cc-thingz` has focused test-runner behavior. It maps edited files to pytest,
  Vitest, Jest, Go, Bats, package scripts, and Makefile fallbacks while keeping
  escape hatches like `HOOK_PROJECT_FALLBACK=0`.
- `cc-thingz` file-protector handles patch-based tools, including Codex
  `apply_patch` with multi-file patch extraction.
- `hooksmith` gives hooks product shape: named hook specs, info/install/remove
  commands, and a discoverable catalog.
- `karanb192` has a useful dangerous-command taxonomy with severity levels,
  pattern IDs, structured deny responses, and test coverage.
- `fricklers` keeps practical hooks small: dangerous command block, secret
  protection, commit confirmation, auto-lint, context injection, and todo
  checks.
- Official examples show which hook combinations Anthropic is willing to
  document as plugin patterns.
- Official marketplace refs show trust warnings, install/discover flows,
  skill-bundle registration, and quality/security approval language that
  Athanor should mirror before any installer UX.
- Codex's current hook implementation adds a useful managed/trusted hook model:
  inspect/review/trust/disable at the UI layer, with managed hooks separable
  from user/project/session hooks.
- LaunchDarkly's SessionStart hook validates the value of startup context
  injection, but also shows why remote-service and secret-dependent hooks must
  stay opt-in.
- The Jeremy marketplace ref is useful for validator, analytics, marketplace,
  and plugin-inventory ideas, but its scale and path depth are too high to
  absorb directly into Athanor's performance-sensitive runtime.

### Ref Weaknesses Not To Import Blindly

- Many refs rely on README claims or settings snippets without live payload
  replay evidence.
- Some hook bundles run heavier logic by default. That conflicts with
  Athanor's performance posture unless the behavior is opt-in or bounded.
- Installer mutation of user settings is valuable UX, but unsafe as a first
  step for Athanor unless it preserves existing hooks, shows diffs, and has a
  dry-run path.
- Broad lifecycle support can overfit to documented event names before current
  Claude Code payload shape is captured and replayed.

## Gap Matrix

| Gap | Evidence | Impact | Recommendation |
| --- | --- | --- | --- |
| Installer/dry-run UX still absent | `hooksmith`, official marketplace, and `ccpi` expose install/list/remove/update style flows. | Users can inspect the catalog but cannot safely enable optional hooks through Athanor UX. | Build dry-run first; never clobber existing hooks. |
| Capture-only events still lack live fixtures | P2 catalogs SessionStart, PreCompact, PermissionRequest, PostToolUseFailure, and SubagentStop as capture-only/synthetic. | Promotion remains blocked by payload uncertainty. | Collect live-redacted fixtures and add replayable handlers one event at a time. |
| Safety corpus needs false-positive evidence | P1 has observe/warn taxonomy, but stricter behavior needs local evidence. | Premature blocking would hurt adoption. | Keep default off; collect observe/warn logs before any stricter proposal. |
| Cross-runtime hook generation is manual | `cc-thingz` tests generated manifests for multiple targets. | Codex companion drift remains possible over time. | Add a manifest matrix doc and only then consider generator code. |
| External plugin-dev onboarding is thin | Official and plugin-dev refs show authoring workflow examples. | Contributors need to infer boundaries from internal docs. | Add authoring docs once catalog schema exists. |
| Performance budgets are implicit | Athanor is narrow by design, but no measured hook SLA is documented. | Future opt-in hooks could accumulate latency. | Define per-hook budget fields and benchmark command in catalog schema. |
| Trust review model is implicit | Codex exposes hook inspection/trust/disable behavior and managed hook policy. | Athanor can explain policy but cannot yet model user trust state. | Add trust-state concepts to the matrix before implementing installer mutation. |

## Adoption Plan

### P0: Catalog The Current Hook Surface

Status: done in this branch.

Create a tracked hook catalog that lists current registered hooks and planned
opt-in hooks with these fields:

- `id`
- `event`
- `runtime_default`: `enabled`, `disabled`, or `capture-only`
- `policy_mode`: `observe`, `warn`, `strict`, or `block`
- `evidence_level`: `synthetic`, `live-redacted`, `replay-gated`, or `none`
- `performance_budget_ms`
- `dependencies`
- `risk`
- `source_refs`

This is low risk and immediately improves UX without touching runtime settings.

### P1: Safety Pattern Corpus

Status: done in this branch as default-off observe/warn infrastructure.

Extract a small shared safety-pattern module for dangerous shell operations and
secret-like writes. Start in observe/warn mode, with tests modeled after
`karanb192` and `cc-thingz`:

- destructive filesystem commands
- forced git/history rewrites
- curl/wget pipe-to-shell
- private key and token-shaped write payloads
- protected branch direct commits
- patch-based multi-file edits

Do not widen default blocking until the pattern set has low false-positive
evidence in local replay/capture fixtures.

### P2: Capture-First Lifecycle Expansion

Status: done in this branch as capture-only catalog entries plus generic
capture-snippet coverage. Live fixture collection remains separate follow-up
work.

Add capture-only catalog entries for SessionStart, UserPromptSubmit,
PreCompact, PermissionRequest, PostToolUseFailure, and SubagentStop. Promotion
requires live-redacted payload fixtures and replayable handlers. UserPromptSubmit
already has spike evidence, so it is the first candidate for a formal catalog
entry, not immediate default enforcement.

### P3: Cross-Runtime Manifest Matrix

Next. Create a generator only after the catalog has stabilized. The first step
should be a manifest matrix test that asserts the intended Claude/Codex support
table, including event support, trust/managed policy, plugin-local hook support,
and known unsupported surfaces. Use `cc-thingz`, OpenAI Codex, and
`obra/superpowers` as references, but do not copy a broad default hook bundle.

### P4: Installer/Dry-Run UX

After catalog and manifest matrix are stable, add a dry-run installer that
prints proposed settings changes, detects existing hook entries, and refuses to
clobber user settings. This should follow the `hooksmith` UX idea but keep
Athanor's provenance and dry-run discipline.

## Performance Direction

Keep default hooks narrow:

- Stop: enforce claim verification.
- PreToolUse: enforce kernel/freeze gates.
- PostToolUse: collect evidence and diagnostics.

Everything else starts as disabled or capture-only. Any opt-in hook must declare
expected cost, dependency probes, skip conditions, and fail-open/fail-closed
policy. Heavy commands such as focused test runners belong behind explicit
project opt-in and must support targeted execution plus a no-fallback mode.

## Next Concrete Work

The next implementation unit should be P3: a cross-runtime hook manifest matrix
plus tests. P0-P2 are already implemented in this branch, so the risk now is
drift between Claude Code, Codex, and Athanor's cataloged hook policies.

Expected files:

- `docs/cross-runtime-hook-matrix.md`
- `tests/test_regression_cross_runtime_hook_matrix.py`
- optionally `schemas/cross-runtime-hook-matrix.schema.json`
- update `docs/hook-catalog.md` with a short pointer to the matrix

Completion evidence:

- Claude and Codex supported events are explicit and versioned
- every Athanor catalog event maps to a runtime support status
- plugin-local hook support and trust/managed-hook behavior are explicit
- no generator or installer writes settings yet
- release-ready checks still pass
