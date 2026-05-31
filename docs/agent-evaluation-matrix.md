# Agent Evaluation Matrix (Goal 36470e54, Cycle C001 / G1)

평가일: 2026-05-31
방법: 3개 병렬 평가 에이전트 (ECC / CE+autoresearch / athanor 자체 감사)

## 1. ref 에이전트 채택 평가

### ECC (259 files → 68 unique, i18n/중복 제외)

| 카테고리 | 예시 | athanor 커버 | 판정 |
|---------|------|-------------|------|
| Per-language reviewers (~13 langs) | python/rust/react-reviewer | reviewer 6-lens (language-agnostic) | SKIP |
| Per-language build resolvers | build-error-resolver | executor + ci-watcher | SKIP |
| Planner/architect | planner, architect | /athanor:plan cross-model (더 강함) | SKIP |
| TDD enforcement | tdd-guide | Spec-then-TDD (더 강함) | SKIP |
| Lessons/learning | observer, continuous-learning-v2 | learner + lessons | SKIP |
| Business/comms | chief-of-staff, marketing-agent | 범위 밖 | SKIP |
| 기타 49 카테고리 | — | — | SKIP |

**ECC 결과: 0 ADOPT / 68 SKIP.** 개념 흡수 후보 1건: `silent-failure-hunter` (swallowed error / empty catch 휴리스틱) → reviewer quality lens prose 추가 옵션.

### CE (43 production agents) + autoresearch (1)

| 클러스터 | 에이전트 수 | athanor 커버 | 판정 |
|---------|-----------|-------------|------|
| Reviewer personas | ~20 (correctness/security/perf/testing/maintainability/architecture) | reviewer 6-lens (이미 CE confidence-anchoring rubric 흡수함) | SKIP |
| Document review | 8 (coherence/feasibility/product-lens/scope-guardian 등) | Critic + discuss dual-mode + scope-drift | SKIP |
| Researcher/knowledge | 6 (best-practices/framework-docs/web/learnings/session-historian) | researcher + learner + claude-mem/context7 MCP | SKIP |
| Domain/language/UI 특화 | ~9 (swift-ios/julik-frontend/figma/data-integrity 등) | 범위 밖 (general-purpose 위반) | SKIP |
| autoresearch docs-manager | 1 | work direct-mode + executor | SKIP |

**CE+autoresearch 결과: 0 ADOPT / 44 SKIP.** 개념 흡수 후보 1건: `project-standards-reviewer` (repo 자체 CLAUDE.md 표준 감사) → reviewer quality lens prose 옵션. (athanor는 이미 Stop hook + scope-drift로 표준 강제.)

### gstack / superpowers
agent 0개 (skill-based). athanor 11-agent + concept-absorption 철학과 정렬.

## 2. ref 채택 종합 결정

**ADOPT: 0개.** 전수 평가 결과 ref 6개 플러그인의 어떤 에이전트도 athanor의 minimal 11-agent 모델에 wholesale 채택할 가치 없음. 모든 후보가 (a) reviewer 6-lens / critic / researcher / learner가 이미 subsume, (b) 범위 밖(business/UI/language-specific), 또는 (c) Thin Leader 위반.

이는 v0.12.0 "concept absorption ≠ wholesale vendoring" (97% 제거) 정책 + v0.15.x에서 마지막 2개 vendored agent(ce-git-history-analyzer, ce-repo-research-analyst) 제거한 이력과 일관됨.

**선택적 개념 흡수 (새 에이전트 아님, prose만):** silent-failure-hunter + project-standards-reviewer 휴리스틱을 reviewer quality lens에 1-2 bullet 추가 — G2/G3에서 결정.

## 3. athanor 11 에이전트 자체 감사 (G3 준비)

### 핵심 구조 발견
모든 11개 `agents/*.md`가 `name: athanor-*` frontmatter 보유 → Claude Code가 **registered agent type**으로 등록 (@-mention 가능). 그러나 skill들은 role을 **INLINE `Agent({prompt})`** 로 dispatch하고 registered agent를 쓰지 않음. planner/critic은 심지어 registered agent 사용이 **COLLISION GUARD로 금지**됨 (`planner-dispatch.md:145`, `critic-variants.md:30`).

| 분류 | 에이전트 | dispatch 경로 | .md load-bearing? |
|------|---------|--------------|------------------|
| Pipeline (8) | analyst, planner, critic, executor, learner, researcher, reviewer, cleaner | INLINE prompt (planner/critic은 registered 금지) | **No** — @-mention 편의 + 문서뿐 |
| v0.14.0 (3) | releaser, codex-dispatcher, ci-watcher | advisory pointer ("MAY use") | **Partial** — test-locked (`test_regression_v014_agent_definitions.py`) |

### 핵심 약점 (정리 대상)
- **dead agent 0개** (전부 ≥1 참조) — 단순 삭제 대상 없음
- 진짜 문제: `name: athanor-*` frontmatter (live 등록) vs CLAUDE.md "reference documents, not implementations" 서술 **불일치**. 이 불일치가 planner/critic COLLISION GUARD의 원인.
- 8개 pipeline agent .md는 skill dispatch에 load-bearing 아님 (role은 100% inline)

### G3 정리 옵션 (사용자 결정 필요)
- **옵션 A**: 8개 pipeline agent .md의 `name:`/`tools:` frontmatter 제거 → 순수 문서화 (registered collision 해소, @-mention surface 상실)
- **옵션 B**: 8개 pipeline agent .md 삭제 (inline dispatch만 유지, @-mention 상실)
- **옵션 C**: 현행 유지 + COLLISION GUARD 문서화 강화
- 3개 v0.14.0 agents: **KEEP** (test-locked, advisory pointer 역할)

## 4. G1 결론

✅ ref 6개 플러그인 에이전트 전수 평가 완료. ADOPT 0개 (개념 흡수 2건 옵션). athanor 11개 감사 완료 — dead 0개, 구조적 불일치(frontmatter vs 문서) 1건 식별. G3 정리는 frontmatter 일관성 + 선택적 개념 흡수로 수렴.
