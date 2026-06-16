# Athanor Ref Deep Research

Date: 2026-06-16
Branch: `feat/hook-payload-replay`
Purpose: compare Athanor against current Claude Code hook/plugin references and
turn the findings into an adoption plan for a higher-performance, higher-trust
plugin.

## Executive Verdict

Athanor is ahead on evidence depth and replay discipline, but behind on hook
productization breadth. The current branch has strong live-redacted payload
fixtures, replay gates, health diagnostics, and provenance-aware PostToolUse
evidence. The strongest references are wider in hook lifecycle coverage,
installer/catalog UX, and cross-runtime hook generation.

The next optimization layer should not add many default runtime hooks. The
better direction is a cataloged, opt-in hook platform with measured overhead,
evidence-backed promotion rules, and a small safety-rule corpus that shares
the current replay/provenance standards.

## Reference Set

All refs are cloned under ignored `ref/` directories in this worktree.

| Ref | HEAD | Role | Files | Hook files | Test-like files | Packaging |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `alexei-led/cc-thingz` | `2e590b6` | Closest architecture competitor: generated hooks across Claude, Codex, Gemini, and Pi | 986 | 162 | 168 | npm, pyproject, Makefile |
| `anthropics/claude-code` | `64ceb97` | Official plugin examples and hook patterns | 203 | 56 | 0 | examples only |
| `disler/claude-code-hooks-mastery` | `052ad1c` | Hook lifecycle teaching/reference corpus | 130 | 33 | 0 | docs/settings |
| `ElliotJLT/hooksmith` | `836fb7d` | Hook registry and installer UX reference | 35 | 25 | 0 | npm |
| `fricklers/claude-code-config` | `c86b358` | Practical personal hook safety/config reference | 48 | 8 | 0 | settings/scripts |
| `karanb192/claude-code-hooks` | `ebcc2a2` | Safety hook corpus with JS tests | 16 | 9 | 4 | npm |
| `obra/superpowers` | `8cf3900` | SessionStart skill discipline reference | 147 | 5 | 52 | npm |
| `shakacode/claude-code-commands-skills-agents` | `2c375be` | Command/skill/agent packaging reference | 37 | 1 | 0 | docs/scripts |
| `sjnims/plugin-dev` | `7b2a821` | Plugin authoring/onboarding reference | 148 | 13 | 0 | docs/scripts |

Upstream URLs:

- https://github.com/alexei-led/cc-thingz
- https://github.com/anthropics/claude-code
- https://github.com/disler/claude-code-hooks-mastery
- https://github.com/ElliotJLT/hooksmith
- https://github.com/fricklers/claude-code-config
- https://github.com/karanb192/claude-code-hooks
- https://github.com/obra/superpowers
- https://github.com/shakacode/claude-code-commands-skills-agents
- https://github.com/sjnims/plugin-dev

## Scorecard

Scores are relative to the observed reference set, not absolute product
quality.

| Dimension | Athanor | Ref leader | Leader score | Read |
| --- | ---: | --- | ---: | --- |
| Evidence/replay rigor | 9.7 | Athanor | 9.7 | Live-redacted fixtures plus replay gates are the strongest observed proof layer. |
| Hook lifecycle breadth | 6.5 | `cc-thingz`, official examples, Disler | 8.5 | Athanor registers Stop, PreToolUse, PostToolUse; refs cover SessionStart, UserPromptSubmit, Notification, PreCompact, and failure events. |
| Hook catalog/installer UX | 5.5 | `hooksmith` | 9.0 | Athanor lacks a discoverable optional hook registry and install/remove flow. |
| Safety rule corpus | 7.5 | `karanb192`, `fricklers`, `cc-thingz` | 8.5 | Athanor has kernel/freeze defenses; refs have broader dangerous-command and secret-protection taxonomies. |
| Cross-runtime portability | 7.0 | `cc-thingz` | 9.2 | Athanor has Codex companion docs and hook awareness; refs generate manifests for multiple runtimes. |
| Plugin-dev onboarding | 7.0 | official examples, `sjnims/plugin-dev` | 9.0 | Athanor docs are strong internally, weaker as an external authoring guide. |
| Performance posture | 8.6 | Athanor, `cc-thingz` | 8.8 | Athanor keeps default hook count low; `cc-thingz` is broader but includes focused runners and skip paths. |
| Adoption risk control | 9.3 | Athanor | 9.3 | Athanor's strict deferral and evidence gates reduce false confidence better than refs. |

## Hook Event Coverage

| Project | Registered or documented events | Athanor read |
| --- | --- | --- |
| Athanor | Stop, PreToolUse, PostToolUse | Strong core enforcement plus evidence. Missing opt-in breadth. |
| `cc-thingz` Claude dev-flow | SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Notification, Stop | Best multi-event packaged workflow. Good source for opt-in catalog shape. |
| `cc-thingz` Codex dev-flow | PreToolUse, PostToolUse, Stop, SessionStart | Best cross-runtime manifest reference. |
| official `hookify` | PreToolUse, PostToolUse, Stop, UserPromptSubmit | Good official plugin example; not a full safety platform. |
| official `security-guidance` | SessionStart, UserPromptSubmit, PostToolUse, Stop | Good guidance pattern for contextual safety prompts. |
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
| No optional hook catalog | `hooksmith` exposes named hooks and install UX; Athanor exposes only registered hooks and docs. | Users cannot discover or enable advanced hooks safely. | Add a static catalog first; defer settings mutation. |
| Limited event breadth | Athanor registers 3 events; refs exercise or document 8-12 events. | Athanor misses early prompt/context and compaction surfaces. | Add capture-first entries for SessionStart, UserPromptSubmit, PreCompact, and failure events. |
| Safety corpus lacks shared taxonomy | `karanb192` and `fricklers` have broader dangerous-command/secret patterns. | Current guardrails are strong but less reusable across hook features. | Add pattern IDs, severity, mode, and tests before new blocking behavior. |
| Cross-runtime hook generation is manual | `cc-thingz` tests generated manifests for multiple targets. | Codex companion drift remains possible over time. | Add a manifest matrix doc and only then consider generator code. |
| External plugin-dev onboarding is thin | Official and plugin-dev refs show authoring workflow examples. | Contributors need to infer boundaries from internal docs. | Add authoring docs once catalog schema exists. |
| Performance budgets are implicit | Athanor is narrow by design, but no measured hook SLA is documented. | Future opt-in hooks could accumulate latency. | Define per-hook budget fields and benchmark command in catalog schema. |

## Adoption Plan

### P0: Catalog The Current Hook Surface

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

Add capture-only catalog entries for SessionStart, UserPromptSubmit,
PreCompact, PermissionRequest, PostToolUseFailure, and SubagentStop. Promotion
requires live-redacted payload fixtures and replayable handlers. UserPromptSubmit
already has spike evidence, so it is the first candidate for a formal catalog
entry, not immediate default enforcement.

### P3: Cross-Runtime Manifest Matrix

Create a generator only after the catalog has stabilized. The first step should
be a manifest matrix test that asserts the intended Claude/Codex support table.
Use `cc-thingz` as the reference, but do not copy its broad default hook bundle.

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

The next implementation unit should be P0: a tracked hook catalog plus tests
that prove every currently registered hook appears in the catalog and every
catalog event is either registered, disabled, or capture-only by policy. This
turns the ref research into a stable architecture boundary before adding new
runtime behavior.

Expected files:

- `schemas/hook-catalog.schema.json`
- `hooks/catalog.json`
- `tests/test_regression_hook_catalog.py`
- `docs/hook-catalog.md`
- update `README.md` only with a short pointer after the catalog doc exists

Completion evidence:

- catalog validates against schema
- all registered hooks in `hooks/hooks.json` have catalog entries
- no enabled catalog entry points at an unregistered hook
- capture-only and disabled entries are explicitly non-runtime
- release-ready checks still pass
