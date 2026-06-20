# Full Ref Optimization Analysis

Date: 2026-06-20

Purpose: evaluate every repository currently cloned under `ref/` against
Athanor v0.19.2, then identify what to add, avoid, remove, or defer.

This is the refreshed pass after expanding `ref/` from 29 repositories to 64
repositories, then to **190**, and then to **346** local reference repositories
after the latest web/GitHub search and clone pass. The score measures value and
fit for Athanor, not absolute project quality.

## Baseline

Athanor v0.19.2 currently has:

- 11 user-facing native commands:
  `setup`, `prompt-gen`, `discuss`, `analyze`, `assess`, `debug`, `plan`,
  `work`, `review`, `lfg`, and `lfg-goal`.
- 4 registered agents: `learner`, `releaser`, `ci-watcher`,
  `codex-dispatcher`.
- 7 reference-only roles: `analyst`, `cleaner`, `critic`, `executor`,
  `planner`, `researcher`, `reviewer`.
- Thin Leader discipline, cross-model planning, Spec-then-TDD execution,
  Stop/PreToolUse/PostToolUse hook enforcement, package knowledge index,
  organization gates, workflow traces, and local score-target goal loops.
- A new local memory-index gate is in progress in this branch:
  `docs/memory-index.md`, `scripts/gates/memory_index.py`, and
  `schemas/memory-index-report.schema.json`.

Current local evidence:

- `python scripts/gates/agent_topology.py --json`: pass, 4 registered agents.
- `python scripts/gates/package_knowledge_index.py --json`: pass.
- `python scripts/gates/memory_index.py --json`: pass, read-only/no telemetry.

## Method

Six read-only analysis batches inspected independent ref groups during the
64-ref pass:

1. official/runtime/standard contracts;
2. catalogs, marketplaces, and admission policies;
3. loop and harness engineering;
4. memory, trace, eval, and observability;
5. agent runtime/control-plane structures;
6. hooks, workflow plugins, and direct remaining refs.

The resulting recommendations were reconciled against Athanor's topology,
package-facing docs, and active optimization plan.

The 190-ref expansion added a second evidence pass:

- local inventory: 190 git refs, 93 plugin manifests, 143 `SKILL.md` refs,
  23 refs with agent files, and 106 refs with hook hints;
- parallel bucket analysis for plugin/skill, loop/harness, memory/eval,
  hook/safety, and runtime/catalog groups;
- new read-only gate:
  `python scripts/gates/catalog_admission.py --json`;
- current catalog-admission output: `warn`, 190 entries, 0 failures,
  111 runtime-surface-capped refs, 34 unknown-license refs, and
  `irreversible_actions: 0`.

The 346-ref refresh added a third evidence pass:

- 156 additional GitHub/web-discovered refs were cloned into `ref/`;
- `catalog_admission` now covers 346 entries with 0 failures;
- current catalog-admission output: `warn`, 346 entries,
  185 runtime-surface-capped refs, 88 unknown-license refs, and
  `irreversible_actions: 0`.

## Athanor Scorecard

| Dimension | Current | Target | Read |
|---|---:|---:|---|
| Thin Leader topology | 96 | 96 | Strong. Do not add registered agents. |
| Command surface discipline | 93 | 94 | Strong. New work should be modes/gates, not commands. |
| Memory retrieval | 86 | 92 | Local index, learner handoff, and retrieval eval exist; more real-query coverage remains. |
| Loop operations | 84 | 94 | Needs readiness, run-log, budget, VCR, lock, kill criteria. |
| Eval and trace replay | 88 | 93 | Scorer/reducer metadata and trace query CLI exist; broader captured trace coverage remains. |
| Hook safety and UX | 88 | 94 | Good default narrowness; needs observe-first corpus and list/info UX. |
| Runtime contract validation | 85 | 93 | Runtime surface and Codex mirror parity are gated; skill/hook contract tightening remains. |
| Skill/catalog admission | 82 | 91 | Read-only fail-cap gate now covers 346 refs; still needs plugin/skill/hook contract tightening. |
| Work-item/stage control | 86 | 90 | File-local transition audit and approval/intervention gate exist; real-run adoption remains. |
| Package/ref governance | 90 | 92 | Reference radar and explicit ship-profile exclusions are executable; release packaging still needs composite verification. |

Overall ref-fit maturity: **89/100 now**, target **93-95/100** without growing
the visible command or registered-agent surface.

## Curated Repository Scores

The table below is the curated seed set from the 64-ref pass. The 346-ref pass
is now covered mechanically by `scripts/gates/catalog_admission.py`; it should
be treated as the authoritative full-inventory view because manually listing
346 refs in this document would become stale immediately.

| Ref | Category | Score | Athanor Read |
|---|---|---:|---|
| `boshu2-12-factor-agentops` | agentops principles | 94 | Strongest operating-discipline reference: least privilege, external validation, ratchet progress, learning promotion. |
| `jpicklyk-task-orchestrator` | work graph | 92 | Best file-local work-item/stage-transition candidate if shrunk from MCP server to gate. |
| `anthropics-claude-plugins-official` | official plugin | 91 | Best manifest, marketplace, and skill-eval contract reference. |
| `cobusgreyling-loop-engineering` | loop operations | 90 | Best loop readiness, L1/L2/L3 rollout, cost, run-log, and anti-pattern reference. |
| `alexei-led-cc-thingz` | multi-runtime plugins | 88 | Strong source-to-runtime compiler pattern for Claude/Codex drift. |
| `anthropics-claude-code` | official runtime | 88 | Strong official hook/plugin examples; absorb contracts only. |
| `obra-superpowers` | process skills | 88 | Strong behavior tests and evidence discipline; avoid ceremony creep. |
| `openai-codex` | runtime contracts | 88 | Strong strict schemas, goal/hook notifications, token/context budgets. |
| `rajudandigam-agent-inspect` | trace debugging | 88 | Best local trace search/timeline/stats/diff pattern. |
| `Th0rgal-open-ralph-wiggum` | loop controller | 88 | Strong resume/task ledger/status ergonomics; avoid promise-only completion. |
| `walkinglabs-learn-harness-engineering` | harness course | 88 | VCR/pass-state/clean-state ideas fit Athanor gates. |
| `breim-loop-harness` | loop readiness | 86 | Strong NO-GO loop qualification and verifier-first discipline. |
| `gsd-build-get-shit-done` | workflow OS | 86 | Strong routing/state ideas; too broad as a model. |
| `humanlayer-12-factor-agents` | agent principles | 86 | Useful execution-state and HITL vocabulary; principle docs only. |
| `netresearch-claude-code-marketplace` | marketplace governance | 86 | Best source-reference marketplace separation and no-orphan checks. |
| `anthropics-skills` | official skills | 84 | Good progressive disclosure and script/reference split. |
| `shakacode-claude-code-commands-skills-agents` | PR workflow | 84 | Best PR review comment triage and checkpoint pattern. |
| `wquguru-harness-books` | harness books | 83 | Useful compact/recovery/tool-result ledger invariants. |
| `iamarvindh-claude-loop-engineering` | loop skill | 82 | Strong loop-intake schema; absorb into `lfg-goal` rather than new command. |
| `fricklers-claude-code-config` | config/hooks | 82 | Good minimal hook/config hygiene. |
| `tjdrhs90-rn-launch-harness` | domain harness | 82 | Strong generator/evaluator, file handoff, status/resume, retro trend. Domain surface is out of scope. |
| `UKGovernmentBEIS-inspect_ai` | eval framework | 82 | Strong scorer/reducer/log discipline; avoid framework dependency. |
| `openai-openai-agents-python` | agent SDK | 80 | Useful guardrail/handoff/trace vocabulary; do not import SDK architecture. |
| `agent-team-foundation-first-tree` | context tree | 78 | Useful team context/ownership and session event schema; hosted workspace is out. |
| `jeremylongshore-claude-code-plugins-plus-skills` | catalog/eval | 78 | Useful rubrics and generated catalogs; huge catalog is anti-pattern. |
| `rohitg00-agentmemory` | memory platform | 70 | Retrieval eval and retention ideas are useful; 53-tool MCP/server surface is too much. |
| `alchaincyf-loop-engineering-orange-book` | loop guide | 70 | Good loop language and anti-pattern framing; documentation-only. |
| `darkrishabh-agent-skills-eval` | skill eval | 69 | Useful with-skill vs without-skill baseline and deterministic assertions. |
| `rohitg00-pro-workflow` | workflow/memory | 66 | Useful handoff/compact and learning replay; too many skills/hooks/agents. |
| `strands-agents-harness-sdk` | harness SDK | 64 | Intervention vocabulary is useful; SDK/control framework is too broad. |
| `hesreallyhim-awesome-claude-code` | catalog | 63 | CSV fields are useful for freshness/license/stale decisions. |
| `AgentsKit-io-agentskit` | agent toolkit | 62 | Durable step JSONL and egress gate ideas; package surface is broad. |
| `disler-claude-code-hooks-mastery` | hook demos | 62 | Useful lifecycle examples and command-local validators; too many default events. |
| `hamelsmu-evals-skills` | eval skills | 62 | Good eval-audit thinking; mostly procedural docs. |
| `nexu-io-harness-engineering-guide` | harness guide | 62 | Useful permission/eval taxonomy; managed-agent runtime is out. |
| `Picrew-awesome-agent-harness` | catalog/radar | 62 | Useful YAML radar and verification reports; stars/categories are weak signals. |
| `snarktank-ralph` | Ralph loop | 61 | Simple story ledger; verification and safety are weak. |
| `alirezarezvani-claude-skills` | large skill pack | 58 | Skill tester/rubric useful; 300+ skills and 90+ agents are anti-pattern. |
| `Agent-Field-agentfield` | control plane | 58 | Lifecycle log vocabulary useful; server/API/DID product surface is out. |
| `launchdarkly-labs-claude-code-session-start-hook` | remote policy hook | 58 | Local targeting idea only; remote prompt injection is wrong for core. |
| `RUCAIBox-awesome-agent-harness` | academic catalog | 58 | Governance taxonomy only; huge reading list is not runtime input. |
| `thedotmack-claude-mem` | memory product | 62 | Progressive search pattern useful; daemon/vector/viewer/telemetry are wrong for core. |
| `yucai0302-memory-loop` | minimal memory | 58 | Memory write protocol/size warning useful; full injection lacks evidence. |
| `xiaolai-claude-plugin-marketplace` | bridge marketplace | 57 | Port-status/human-review idea useful; auto conversion must not imply approval. |
| `latitude-dev-eval-skills` | eval workflow | 57 | Golden dataset process useful; product/platform coupling is out. |
| `ai-boost-awesome-harness-engineering` | harness catalog | 55 | Removal criteria useful; executable evidence weak. |
| `ElliotJLT-hooksmith` | hook registry UX | 54 | Good list/info/install UX; installer safety is below Athanor bar. |
| `JanSzewczyk-claude-plugins` | stack plugins | 52 | Routing table useful; stack-specific agents are out of scope. |
| `VoltAgent-awesome-agent-skills` | skill catalog | 47 | Security warning/maturity criteria useful; unstructured link dump is weak. |
| `RoggeOhta-awesome-codex-cli` | Codex catalog | 40 | Official-resource ordering useful; README-only and stale-risk. |
| `harnessclaw-harnessclaw` | desktop harness UI | 35 | SQLite audit table idea only; desktop product surface is out. |
| `rohitg00-awesome-claude-code-toolkit` | toolkit catalog | 35 | Hook ideas only; install bundle is surface sprawl. |
| `AgentOps-AI-agentops` | cloud observability | 34 | Local semantic attribute map only; SDK/exporter/dashboard are out. |
| `CloudAI-X-claude-workflow-v2` | workflow plugin | 62 | Verification fanout ideas; command/agent surface too broad. |
| `dashed-claude-marketplace` | local marketplace | 72 | Schema validation and Codex sync check useful; symlink/install flow is not core. |
| `HKUDS-OpenHarness` | open harness app | 76 | Non-overridable deny and blockable hooks useful; `full_auto`/autopilot are wrong defaults. |
| `humanlayer-humanlayer` | HITL platform | 72 | Approval event vocabulary useful; daemon/UI product is out. |
| `luzhenqian-claude-harness` | runtime explainer | 76 | Compact/recovery/cost-state ideas; runtime reimplementation is out. |
| `openai-evals` | eval framework | 74 | Metrics and JSONL sample discipline useful; external stores/model-graded gates are optional only. |
| `revfactory-harness` | team factory | 74 | Team architecture patterns useful as admission rubric; auto agent generation is too risky for core. |
| `shareAI-lab-learn-claude-code` | Claude Code course | 78 | Worktree binding and compaction recovery ideas; educational surface is broad. |
| `sjnims-plugin-dev` | plugin authoring | 75 | Changed-file validation and schema references useful; no runtime-user surface. |

## 346-Ref Expansion Findings

The newer refs reinforced the original architecture and changed the execution
order.

Strongest added or reweighted refs:

| Ref | Bucket | Admission Read |
|---|---|---|
| `compound-engineering-plugin` | plugin/process | Valuable no-external-service and knowledge-compounding patterns; broad skill/agent surface is capped below direct adoption. |
| `claude-octopus` | review/diversity | Useful blind-spot review pattern; not a core runtime surface. |
| `Citadel` | control plane | Useful cost/session/hook concepts; too broad as a default control plane. |
| `sd0xdev-sd0x-dev-flow` | harness/plugin | Strong dual-review/state-machine ideas; 96 skills and 15 agents are a surface-sprawl warning. |
| `gmickel-flow-next` | spec/Ralph | Good cross-runtime spec/Ralph structure; mirror parity ideas fit Task 6. |
| `OthmanAdi-planning-with-files` | planning files | Strong persistent file planning and cross-runtime hook shape. |
| `agentic-in-inferoa` | loop/evidence | Strong evidence/session report and loop policy ideas. |
| `anshulixyz-multi-agent-loop-kit` | loop/memory | Useful journal, radar, and approval gate vocabulary. |
| `zilliztech-memsearch` | memory | Rebuildable derived index and recall eval are useful; service/vector shape stays out. |
| `NevaMind-AI-memU` | memory | Memory hierarchy and source trace ideas fit a local gate. |
| `nidhinjs-prompt-master` | prompt generation | Prompt lint/scope/stop-condition ideas fit `prompt-gen`; model/version claims stay out. |
| `maxritter-pilot-shell` | manifest/review gates | Manifest drift and enforced review gates fit local CI. |
| `keli-wen-agentic-harness-patterns-skill` | harness skill | Permission gate and lazy skill-runtime concepts fit admission policy. |
| `muratcankoylan-Agent-Skills-for-Context-Engineering` | context engineering | Tool-design and deterministic eval gates fit internal references. |
| `daymade-claude-code-skills` | skills marketplace | Large polished skill marketplace; useful admission-rubric evidence, not a direct import. |
| `thClaws-thClaws` | harness runtime | Strong Rust harness/control-plane reference; too broad for Athanor core. |
| `trailofbits-skills-curated` | curated marketplace | Strong curation/security signal; absorb review criteria, not marketplace scope. |
| `LerianStudio-ring` | plugin/process | Strong TDD/debug/review practice pack; large agent/skill surface remains capped. |
| `OpenTracy-OpenTracy` | loop/eval | Useful propose/eval/approve/ship loop framing; MCP/BYOK app surface stays out. |
| `cybernetix-lab-moss-harness` | harness template | Useful observability/recovery vocabulary; template product surface is out. |
| `kawaz-claude-plugin-reference` | plugin reference | Useful live plugin/skill/hook verification reference. |
| `protectskills-MaliciousAgentSkillsBench` | skill security eval | Useful adversarial skill benchmark reference for admission/security checks. |

New or strengthened conclusions:

- `catalog_admission` must run before absorbing future refs.
- Work-item/stage transition and trace replay/retrieval eval are now more
  important than adding more skills.
- Codex mirror parity remains important because many refs ship multi-runtime
  layouts.
- Large skill/agent catalogs are useful radar and strong anti-pattern evidence.
- No new registered agent is justified by the 346-ref pass.

## Cross-Cutting Verdict

The expanded pass reinforces Athanor's existing direction:

- **Do not add registered agents.** The 4-agent topology remains correct.
- **Do not add a new command family.** New power should appear as gates,
  schemas, optional modes, and reference docs.
- **Do add stronger contracts.** The strongest refs are strict about schema,
  status, budget, stage transition, and evidence.
- **Do add admission control.** Large catalogs prove why Athanor needs a
  source-reference ledger and fail-cap rubric before absorbing anything.
- **Do add local replay/search/eval tools.** Use file-local scripts, not
  daemons, viewers, broad MCP tools, or cloud telemetry.

## Add Candidates

### P1 - Memory Index Integration And Retrieval Eval

Task 1 has created the minimal memory index. The next step is to connect it to
Learner and handoff artifacts, then add retrieval quality evaluation.

Recommended shape:

- Learner emits memory-indexable records with stable ids, source path,
  evidence refs, confidence, stale-after hint, and safe-to-inject summary.
- `plan`, `work`, `review`, and `lfg-goal` cite memory ids and content hashes,
  not raw history.
- Add a fixture-backed retrieval eval with query/gold ids, P@K, R@K, hit rate,
  latency, and context budget metrics.
- Keep no daemon, no vector DB, no web viewer, no default transcript ingestion.

Reference support:

- `rohitg00-agentmemory`: retrieval eval and retention/access signals.
- `rajudandigam-agent-inspect`: local trace search/timeline/stats/diff.
- `thedotmack-claude-mem`: progressive search/context/detail pattern.
- `yucai0302-memory-loop`: compact write protocol and size warnings.

### P1 - `lfg-goal` Loop Readiness, Run Log, Budget, And VCR

Strengthen goal loops before and during execution:

- pre-loop NO-GO/readiness gate;
- objective verifier and hard stop criteria;
- scope denylist and blast-radius limit;
- append-only loop-run-log JSONL;
- `acting_on` lock and multi-loop collision detection;
- budget fields for cycles, wall time, and token estimate;
- VCR-style verified/activated/pass-state evidence;
- task min-attempts and kill criteria.

Reference support:

- `cobusgreyling-loop-engineering`: readiness, L1/L2/L3, budget, run-log.
- `breim-loop-harness`: verifier-first NO-GO gate.
- `iamarvindh-claude-loop-engineering`: loop-intake schema.
- `walkinglabs-learn-harness-engineering`: VCR/pass-state/clean-state.
- `Th0rgal-open-ralph-wiggum`: task min-iterations and status/resume.

### P1 - Contract And Admission Gates

Add gates that prevent surface sprawl and drift:

- plugin manifest contract gate;
- skill admission gate with frontmatter, trigger examples, line/token budget,
  required references, and eval evidence;
- hook contract gate with event/matcher/timeout/source/status checks;
- source-reference ledger for external refs and adoption decisions;
- fail-cap rubric: the weakest dimension caps the candidate decision.

Current implementation status:

- `docs/catalog-admission-policy.md` defines the fail-cap policy.
- `schemas/catalog-entry.schema.json` validates per-ref admission entries.
- `scripts/gates/catalog_admission.py` emits 346 local ref entries with
  `adopt`, `adapt`, `observe`, `reject`, or `sunset` recommendations.
- `tests/test_regression_catalog_admission.py` locks full-ref coverage,
  no-telemetry/read-only behavior, and runtime-surface cap behavior.

Reference support:

- `anthropics-claude-plugins-official`: manifest and skill eval standards.
- `netresearch-claude-code-marketplace`: source refs, no-orphan checks.
- `jeremylongshore-claude-code-plugins-plus-skills`: rubric and generated
  catalog separation.
- `dashed-claude-marketplace`: JSON schemas and Codex sync check.
- `sjnims-plugin-dev`: changed-file validation and distribution references.

### P1 - Work-Item And Stage Transition Gate

Add a file-local work-item/stage model without running an MCP server:

- work item id, owner, stage, dependency blockers, actor, decision, evidence;
- allowed transitions such as `queued -> work -> review -> done/blocked`;
- required note/evidence gates for state changes;
- structured approval/intervention states;
- append-only transition audit JSONL.

Reference support:

- `jpicklyk-task-orchestrator`: role transitions and required notes.
- `boshu2-12-factor-agentops`: least privilege, ratchet progress, external
  validation, learning promotion.
- `humanlayer-humanlayer`: approval event vocabulary.
- `strands-agents-harness-sdk`: Proceed/Deny/Guide/Interrupt/Transform
  intervention vocabulary.

Current implementation status:

- `docs/work-item-stage-transitions.md` documents the file-local stage
  transition contract.
- `scripts/gates/work_item_stage.py` validates work-item dependencies,
  required evidence, allowed transitions, approval/intervention states, and
  append-only-shaped JSONL audit sequences.
- `schemas/work-item-stage-report.schema.json` validates the report shape.
- `tests/test_regression_work_item_stage.py` locks valid and invalid
  transition fixtures.

### P2 - Trace Replay/Search/Stats/Diff

Extend workflow trace tooling:

- `timeline`, `stats`, `search`, and `diff` read-only commands;
- local redaction profiles: local, share, strict;
- trace item schema with confidence/source fields;
- reconcile the documented `workflow_trace_eval.py` name with the actual
  runner or add a thin wrapper;
- keep export optional and local-first.

Reference support:

- `rajudandigam-agent-inspect`: local trace CLI and redaction profiles.
- `openai-evals`: metrics and JSONL samples.
- `UKGovernmentBEIS-inspect_ai`: sample ids, logs, offline rescore.

### P2 - Hook Rule Pack And Hook UX

Keep default enabled hooks narrow, but improve discovery and safe expansion:

- `hooks list/info/installed/preview`;
- observe-first dangerous-command and secret-path corpus expansion;
- stage ladder: `disabled -> observe -> warn -> block`;
- command-local opt-in validators;
- timeout/performance budgets and no default auto-format/test/stage.

Reference support:

- `karanb192-claude-code-hooks`: safety corpus and tests.
- `ElliotJLT-hooksmith`: browsing UX only.
- `disler-claude-code-hooks-mastery`: lifecycle examples and command-local
  validators.
- `anthropics-claude-code`: Hookify/security guidance.

### P2 - Runtime Boundary And Codex Mirror Parity

Make Claude/Codex differences explicit and verifiable:

- source map for Claude skill -> Codex mirror skill;
- unsupported Claude-only hooks documented as advisory in Codex;
- port status and human-review gate;
- no automatic conversion as approval.

Reference support:

- `alexei-led-cc-thingz`: source-to-runtime generation.
- `xiaolai-claude-plugin-marketplace`: Claude/Codex dual manifest and manual
  review.
- `openai-codex`: plugin read/status contracts.

Current implementation status:

- `docs/codex-mirror-source-map.md` maps every Claude skill, the Claude-only
  browser test skill, and the Codex `release`/`ci-watch` agent mirrors.
- `scripts/gates/codex_mirror_parity.py --json` verifies missing mirror rows,
  stale version references, description anchors, and unsupported Claude-only
  runtime surfaces.
- `plugins/athanor-codex/README.md` points maintainers to the map and gate.

### P2 - Reference Radar And Ship-Profile Governance

Track external refs in a small source file instead of package-facing link
dumps:

- id, category, URL, local ref, why included, last reviewed, license,
  adoption status, sunset condition, evidence paths;
- verify freshness and local path existence;
- keep `ref/`, `docs/plans`, `docs/archive`, `tests`, and deep architecture
  history outside default shipped context where packaging supports it.

Reference support:

- `Picrew-awesome-agent-harness`: YAML source and verification reports.
- `hesreallyhim-awesome-claude-code`: freshness/license/stale columns.
- `ai-boost-awesome-harness-engineering`: component removal criteria.

Current implementation status:

- `docs/package-footprint-reduction.md` records explicit actions for
  `docs/plans/`, `docs/archive/`, `tests/`, `docs/architecture/`, and `ref/`.
- `scripts/gates/package_footprint_policy.py --json` now emits a full
  repo-local footprint, a default `ship_profile` summary, and explicit
  `ship_profile_decisions`.
- Package size budgets are evaluated against the default ship profile after
  exclusions, while repo-local evidence remains visible and retained.
- `docs/package-knowledge-index.md` links the reduction doc without linking
  development-history paths directly.

## Add Agents?

No new registered agent is recommended.

Rejected registered-agent candidates:

- `memory-indexer`: use `learner` plus scripts/gates.
- `trace-auditor`: use read-only scripts and optional review lens.
- `catalog-admission-auditor`: use gate plus `assess` rubric.
- `stage-auditor`: use file-local stage transition gate first.
- `security-auditor`: use reviewer/security lens plus hook rule packs.
- `plugin-validator`: use release/setup gates.
- `architect`/`engineer`/`advisor`: keep as reference roles or inline packets.
- `workflow-router`: keep routing inside `prompt-gen` and route contract.

Potential reference-only roles if later needed:

- `stage-steward`;
- `permission-auditor`;
- `policy-promoter`;
- `receipt-verifier`;
- `human-approval-clerk`;
- `dependency-resolver`.

Do not register these until an explicit topology gate proves standalone
invocation, reuse across at least two skills, and no simpler gate/script route.

## Add Skills?

Recommended additions are mostly internal or mode-level, not new broad
commands.

Potential internal skills or skill surfaces:

- `memory-replay`: optional helper for search/context/detail usage.
- `catalog-admission`: likely a gate and `assess` mode, not a native command.
- `loop-readiness`: should be folded into `lfg-goal` preflight first.
- `stage-receipt` or `work-item`: likely schema/gate surfaces first.
- `intervention-review`: likely a review lens or approval artifact first.
- `pr-comment-triage`: optional `review`/`lfg` mode.

Do not add output-style, language-pack, SaaS-pack, stack-specific, mobile-app,
or business-domain skills to Athanor core.

## Remove Or Reduce Candidates

### R1 - Package Footprint

The package footprint gate already warns on development-only surfaces. This
remains a concrete reduction target.

Recommendation:

- keep development history in repo;
- exclude docs/plans, docs/archive, docs/architecture, tests, and ref clones
  from default ship profile where packaging supports it;
- keep package-facing index short.

### R2 - Manual Codex Mirror Drift

Manual duplicated Codex companion text should be reduced by a parity source map
and read-only mirror gate before adding a generator. The current branch now has
that gate; a generator remains unnecessary until the map shows repeated,
mechanical drift.

### R3 - Hook Candidate Entropy

Do not enable more default hooks. Require each candidate to declare:

- stage;
- promotion evidence;
- timeout budget;
- data retention policy;
- source ref;
- sunset condition.

### R4 - Skill Body Bloat

Official skill refs reinforce thin `SKILL.md` files. Long skill bodies such as
`lfg-goal` and `plan` should gradually move durable details into references and
schemas.

### R5 - Catalog Creep

Large catalogs are useful radar, not runtime surface. Avoid:

- imported link dumps;
- generated skill floods;
- star/badge-based adoption;
- public marketplace ambitions;
- automatic skill/agent generation as trusted output.

### R6 - Control Plane Creep

Avoid moving Athanor into:

- daemon/server control plane;
- desktop app shell;
- cloud telemetry dashboard;
- DID/VC/auth product surface;
- broad MCP server with many tools;
- default dynamic agent teams;
- default full-auto/autopilot.

## Optimized Target State

After the next optimization pass:

- 11 native commands remain enough.
- 4 registered agents remain enough.
- Capability increases through local gates, schemas, artifacts, optional modes,
  and reference docs.
- `lfg-goal` becomes auditable through readiness, run logs, budgets, locks,
  VCR/pass-state, and evaluator separation.
- Memory becomes searchable and measurable without daemon/vector/web/MCP sprawl.
- Hook expansion becomes safer through observe-first rule packs and catalog UX.
- External ideas pass through an admission ledger before entering runtime.
- Work-item/stage transitions become auditable without introducing a server.

## Updated Priority Order

Completed in this branch so far:

1. Memory index contract.
2. Learner memory-index export and compact handoff artifact.
3. `lfg-goal` run log, budget, and lock helper.
4. Scorer/reducer eval profile.
5. Hook rule-pack UX and observe-first safety corpus expansion.
6. Catalog admission fail-cap gate for all 346 refs.
7. Codex mirror source map and runtime-boundary gate.
8. Trace replay/search/stats/diff CLI and memory retrieval-quality eval.
9. Latest web/GitHub candidate expansion cloned all 156 new refs into `ref/`,
   raising the local reference set to 346.
10. File-local work-item/stage transition and structured
    approval/intervention gate.
11. Package/reference radar and ship-profile reduction decisions.
12. Release story and composite verification coverage for the stable local
    gates.

Remaining priority order:

No remaining implementation task from this optimization plan is open. Further
score gains should come from real-run adoption, broader captured trace
coverage, and future ref refreshes rather than adding more default surface.

## Decision

The expanded 346-ref pass supports Athanor's current architecture but raises
the bar for evidence. The next improvements should make Athanor more auditable
and selective, not bigger: absorb concepts, gate behavior, keep the live
surface small, and make long-running work measurable.
