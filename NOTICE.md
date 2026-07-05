# NOTICE

Athanor incorporates code from third-party open-source projects. Their
copyrights and license notices are reproduced below.

---

## compound-engineering

- **Source**: https://github.com/EveryInc/compound-engineering-plugin (v3.8.3)
- **Copyright**: (c) 2025 Kieran Klaassen / Every Inc
- **License**: MIT
- **Vendored at**: athanor v0.10.0 (2026-05-19)

### Retained vendored skill directories (post-v0.12.0)

Originally vendored verbatim at v0.10.0 with a T2 provenance block. After
the v0.12.0 atomic cut (D8) only 1 ce-* skill directory is retained:

- `skills/ce-test-browser/` — user opt-in UI browser automation; non-identity
  but real utility per D8.

The other 32 vendored ce-* skill directories from the v0.10.0 absorption
were removed at v0.12.0; full enumeration in §"Removed in v0.12.0" below.
A separate v0.11.2 hygiene cut earlier removed 4 lifecycle skills
(`ce-update`, `ce-report-bug`, `ce-release-notes`, `ce-setup`) from the
original CE 3.8.3 inventory; that subset is documented in
`docs/plans/2026-05-20-002-feat-v0.11.2-hygiene-plan.md`.

### Retained vendored sub-agents (historical)

Originally 49 sub-agents vendored at v0.10.0 into `agents/vendored/ce/`.
After the v0.12.0 atomic cut (D12) 2 sub-agents were retained as generic
discovery dispatch targets; both were removed in v0.15.x after confirming
zero live dispatch references:

- `agents/vendored/ce/ce-git-history-analyzer.agent.md` (removed v0.15.x)
- `agents/vendored/ce/ce-repo-research-analyst.agent.md` (removed v0.15.x)

All 49 sub-agents are now removed; `agents/vendored/` no longer exists.
The other 47 sub-agents were removed at v0.12.0; full enumeration in
§"Removed in v0.12.0" below.

### License text

```
MIT License

Copyright (c) 2025 Kieran Klaassen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## superpowers

- **Source**: https://github.com/obra/superpowers (v5.1.0)
- **Copyright**: (c) 2025 Jesse Vincent
- **License**: MIT
- **Originally vendored at**: athanor v0.7.8 (`skills/verification-before-completion/`, v5.0.7)
- **Expanded at**: athanor v0.10.0 (full skill-set, v5.1.0)

### Retained vendored skill directories (post-v0.12.0)

Originally 13 sp-* skills + `verification-before-completion` vendored at
v0.10.0 (the latter actually first vendored at v0.7.8). After the v0.12.0
atomic cut all 13 sp-* directories were removed; the surviving retained
superpowers-origin file is:

- `skills/verification-before-completion/` (vendored earlier at athanor
  v0.7.8; see that skill's provenance block for source-commit pinning) —
  kept under the unprefixed slot per its v0.7.8 vendoring path; Stop hook
  pairs with this skill at the runtime gate.

The 13 sp-* directories removed at v0.12.0 are enumerated under §"Removed
in v0.12.0" below; 2 of them (`sp-systematic-debugging`, `sp-using-superpowers`)
have their concepts absorbed into athanor-native skills as prose subsections —
see §"Concepts adopted from upstream" further below.

### License text

```
MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## claude-octopus

- **Source**: https://github.com/nyldn/claude-octopus (SHA `3c260845f136cc6e3398a1d87ca5fb053a52b1d0`)
- **Copyright**: (c) 2026 nyldn
- **License**: MIT

### Vendored files

- `skills/scope-drift/SKILL.md`

### License text

```
MIT License

Copyright (c) 2026 nyldn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Removed in v0.12.0

v0.12.0 atomic cut removed 45 vendored skill directories (5 LIFT-source +
40 DROP; `ce-test-browser` carved out per D8) and 47 vendored sub-agents
(2 carved out per D12, subsequently removed in v0.15.x). The originally
absorbed upstreams retain their MIT attribution above; this section
enumerates which paths were removed so the audit trail records what
concepts went where.

### Removed compound-engineering skill directories (32 of 33 ce-*)

**3 LIFT-source — concept absorbed into athanor-native skill prose** (full
attribution in §"Concepts adopted from upstream" below):

- `skills/ce-code-review/` — concept absorbed into `skills/review/SKILL.md`
  §"Personas" (6-persona vocabulary).
- `skills/ce-doc-review/` — concept absorbed into `skills/review/SKILL.md`
  §"Doc review mode" (7-lens doc persona array + `--target docs` CLI flag).
- `skills/ce-brainstorm/` — concept absorbed into
  `skills/discuss/references/requirements-capture.md` (R-ID / A-ID / F-ID /
  AE-ID template).

**29 DROP — not covered by athanor identity surface** (users wanting these
flows install the upstream compound-engineering plugin):

- `skills/ce-agent-native-architecture/`
- `skills/ce-agent-native-audit/`
- `skills/ce-clean-gone-branches/`
- `skills/ce-commit/`
- `skills/ce-commit-push-pr/`
- `skills/ce-compound/`
- `skills/ce-compound-refresh/`
- `skills/ce-debug/`
- `skills/ce-demo-reel/`
- `skills/ce-dhh-rails-style/`
- `skills/ce-frontend-design/`
- `skills/ce-gemini-imagegen/`
- `skills/ce-ideate/`
- `skills/ce-lfg/` (D9 full DROP — athanor-native `/athanor:lfg` replaces)
- `skills/ce-optimize/`
- `skills/ce-plan/` (D9 full DROP — athanor-native `/athanor:plan` replaces)
- `skills/ce-polish-beta/`
- `skills/ce-product-pulse/`
- `skills/ce-proof/`
- `skills/ce-resolve-pr-feedback/`
- `skills/ce-riffrec-feedback-analysis/`
- `skills/ce-sessions/`
- `skills/ce-simplify-code/`
- `skills/ce-slack-research/`
- `skills/ce-strategy/`
- `skills/ce-test-xcode/`
- `skills/ce-work/` (D9 full DROP — athanor-native `/athanor:work` replaces)
- `skills/ce-work-beta/`
- `skills/ce-worktree/`

### Removed superpowers skill directories (13 of 13 sp-*)

**2 LIFT-source — concept absorbed into athanor-native skill prose** (full
attribution in §"Concepts adopted from upstream" below):

- `skills/sp-systematic-debugging/` — concept absorbed into
  `skills/debug/SKILL.md` §"Systematic Debugging Discipline" (Iron Law +
  Four Phases).
- `skills/sp-using-superpowers/` — concept formalized in CLAUDE.md
  §"using-superpowers boundary (v0.11.1)" (skill-discovery preamble pattern).

**11 DROP — not covered by athanor identity surface** (users wanting these
flows install the upstream superpowers plugin):

- `skills/sp-brainstorming/`
- `skills/sp-dispatching-parallel-agents/`
- `skills/sp-executing-plans/`
- `skills/sp-finishing-a-development-branch/`
- `skills/sp-receiving-code-review/`
- `skills/sp-requesting-code-review/`
- `skills/sp-subagent-driven-development/`
- `skills/sp-test-driven-development/`
- `skills/sp-using-git-worktrees/`
- `skills/sp-writing-plans/`
- `skills/sp-writing-skills/`

### Removed compound-engineering sub-agents (49 of 49)

Removed under `agents/vendored/ce/` — all 49 dropped (47 at v0.12.0; the
remaining 2 D12-retained generics at v0.15.x after confirming zero live
dispatch references). No athanor-native dispatch target relies on them.
`agents/vendored/` no longer exists on disk. v0.12.0 full path list (47):

- `agents/vendored/ce/ce-acceptance-criteria-generator.agent.md`
- `agents/vendored/ce/ce-agent-architecture-designer.agent.md`
- `agents/vendored/ce/ce-agent-instruction-writer.agent.md`
- `agents/vendored/ce/ce-architecture-analyzer.agent.md`
- `agents/vendored/ce/ce-brainstorm-facilitator.agent.md`
- `agents/vendored/ce/ce-changelog-writer.agent.md`
- `agents/vendored/ce/ce-code-reviewer.agent.md`
- `agents/vendored/ce/ce-codebase-analyst.agent.md`
- `agents/vendored/ce/ce-commit-message-writer.agent.md`
- `agents/vendored/ce/ce-debug-investigator.agent.md`
- `agents/vendored/ce/ce-debug-root-cause-analyst.agent.md`
- `agents/vendored/ce/ce-debugger.agent.md`
- `agents/vendored/ce/ce-demo-narrator.agent.md`
- `agents/vendored/ce/ce-design-critic.agent.md`
- `agents/vendored/ce/ce-design-implementer.agent.md`
- `agents/vendored/ce/ce-dhh-rails-reviewer.agent.md`
- `agents/vendored/ce/ce-doc-reviewer.agent.md`
- `agents/vendored/ce/ce-frontend-architect.agent.md`
- `agents/vendored/ce/ce-gemini-image-generator.agent.md`
- `agents/vendored/ce/ce-idea-evaluator.agent.md`
- `agents/vendored/ce/ce-idea-generator.agent.md`
- `agents/vendored/ce/ce-implementation-planner.agent.md`
- `agents/vendored/ce/ce-merge-conflict-resolver.agent.md`
- `agents/vendored/ce/ce-optimizer.agent.md`
- `agents/vendored/ce/ce-pr-feedback-analyst.agent.md`
- `agents/vendored/ce/ce-plan-critic.agent.md`
- `agents/vendored/ce/ce-plan-writer.agent.md`
- `agents/vendored/ce/ce-polish-finisher.agent.md`
- `agents/vendored/ce/ce-product-pulse-reporter.agent.md`
- `agents/vendored/ce/ce-proof-checker.agent.md`
- `agents/vendored/ce/ce-release-notes-writer.agent.md`
- `agents/vendored/ce/ce-riffrec-analyst.agent.md`
- `agents/vendored/ce/ce-session-summarizer.agent.md`
- `agents/vendored/ce/ce-simplifier.agent.md`
- `agents/vendored/ce/ce-slack-researcher.agent.md`
- `agents/vendored/ce/ce-strategist.agent.md`
- `agents/vendored/ce/ce-task-decomposer.agent.md`
- `agents/vendored/ce/ce-task-executor.agent.md`
- `agents/vendored/ce/ce-test-author.agent.md`
- `agents/vendored/ce/ce-test-runner-browser.agent.md`
- `agents/vendored/ce/ce-test-runner-xcode.agent.md`
- `agents/vendored/ce/ce-tester.agent.md`
- `agents/vendored/ce/ce-verifier.agent.md`
- `agents/vendored/ce/ce-work-executor.agent.md`
- `agents/vendored/ce/ce-worktree-manager.agent.md`
- `agents/vendored/ce/ce-writing-coach.agent.md`
- `agents/vendored/ce/ce-yaml-engineer.agent.md`

Exact filenames may differ minimally from the original 49 set; the
canonical removal record is the cutover commit history. The bulk
removal reason is uniform: post-cutover athanor dispatches do not target
these agents.

---

## Concepts adopted from upstream (post-v0.12.0)

The following concepts have been lifted from upstream plugins and integrated
into athanor-native skills as prose subsections (NOT as vendored skill
directories). Original copyright + MIT license preserved. Source URLs:
compound-engineering — https://github.com/EveryInc/compound-engineering-plugin;
superpowers — https://github.com/obra/superpowers.

### 1. Reviewer-persona vocabulary
From `ce-code-review@3.8.3` (MIT, (c) 2025 Kieran Klaassen / Every Inc) → `skills/review/SKILL.md` §"Personas" (6-persona vocabulary). Inventory: `concepts/review-personas.md`.

### 2. Iron Law + Four Phases (debugging discipline)
From `sp-systematic-debugging@5.1.0` (MIT, (c) 2025 Jesse Vincent) → `skills/debug/SKILL.md` §"Systematic Debugging Discipline". Inventory: `concepts/systematic-debugging.md`.

### 3. Requirements capture (R-ID / A-ID / F-ID / AE-ID)
From `ce-brainstorm@3.8.3` (MIT, (c) 2025 Kieran Klaassen / Every Inc) → `skills/discuss/references/requirements-capture.md` (v0.9.0 absorption; v0.12.0 attribution formalized). Inventory: `concepts/requirements-capture.md`.

### 4. Skill-discovery preamble
From `sp-using-superpowers@5.1.0` (MIT, (c) 2025 Jesse Vincent) → `CLAUDE.md` §"using-superpowers boundary (v0.11.1)" (formalized v0.11.1, attribution v0.12.0). Inventory: `concepts/skill-discovery-preamble.md`.

### 5. Doc-review persona mode
From `ce-doc-review@3.8.3` (MIT, (c) 2025 Kieran Klaassen / Every Inc) → `skills/review/SKILL.md` §"Doc review mode" (7-lens doc persona array + `--target docs` CLI flag). Inventory: `concepts/doc-review-mode.md`.

### 6. Silent-failure heuristic (reviewer quality lens)
From `silent-failure-hunter` (ECC, MIT) → `skills/review/SKILL.md` §"Persona: maintainability" + `agents/reviewer.md` quality lens. Flags swallowed errors (empty catch blocks, bare `except: pass`, error-ignoring fallbacks, discarded Promise rejections). Absorbed as prose heuristic; no agent vendored (Goal 36470e54 C002, "no ref agent adoption justified" decision).

### 7. Project-standards heuristic (reviewer quality lens)
From `project-standards-reviewer` (CE, MIT) → `skills/review/SKILL.md` §"Persona: maintainability" + `agents/reviewer.md` quality lens. Audits changes against the repo's own `CLAUDE.md` / `AGENTS.md` conventions (frontmatter rules, naming, cross-platform portability). Absorbed as prose heuristic; no agent vendored (Goal 36470e54 C002).

---

## Native syntheses (not lifted)

Athanor-native skills synthesized internally from existing athanor patterns
(NOT lifted from any upstream plugin). No upstream attribution applies; the
entry below records the synthesis lineage for audit completeness.

- `/athanor:lfg-loop` (v0.13.0) — Macro Ralph loop combining user goal + Ralph loop pattern + /athanor:lfg cycle. Orchestration layer over existing 4 identity invariants; no upstream attribution (synthesis of internal patterns).
