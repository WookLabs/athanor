---
title: "feat: Athanor Phase 1 — Foundation and /athanor:setup"
type: feat
status: active
date: 2026-04-08
origin: docs/DESIGN.md, docs/ROADMAP.md
---

# feat: Athanor Phase 1 — Foundation and /athanor:setup

## Overview

Athanor 플러그인의 기초 인프라를 구축한다. 세션 디렉토리 관리, config 로딩,
그리고 `/athanor:setup` 스킬이 실제로 worker를 dispatch하고 health check 결과를
사용자에게 보여주는 것까지.

Phase 0(skeleton)에서 파일 구조는 만들었고, 플러그인 로딩도 검증했다.
이제 실제로 **동작하는 첫 번째 스킬**을 만든다.

## Problem Frame

현재 SKILL.md 파일들은 지시문만 있고, 실제 동작 검증이 안 됐다.
특히 핵심 가정인 "worker agent가 MCP 도구(mem-search, LSP)에 접근 가능한가"를
이 Phase에서 실증해야 한다.

## Requirements Trace

- R1. `/athanor:setup` 실행 시 health check 결과를 status table로 출력
- R2. `.athanor/sessions/` 디렉토리가 자동 생성됨
- R3. `athanor.json` 없으면 template에서 자동 생성
- R4. Thin leader 패턴 검증 — setup이 직접 check하지 않고 worker에 dispatch
- R5. Worker agent에서 MCP 도구 접근 가능 여부 실증

## Scope Boundaries

- /athanor:setup만 구현. discuss, analyze, plan, work는 이후 Phase.
- Hook 설치는 하지 않음 (Phase 9)
- 트리거 언어 설정은 config 저장만, 실제 스킬 description 동적 변경은 안 함

## Key Technical Decisions

- **Session ID 형식**: `YYYY-MM-DD-NNN` (날짜 + 3자리 시퀀스). 같은 날 여러 세션 가능. Citadel의 slug 방식보다 간단하고 정렬 가능. (see origin: docs/DESIGN.md)
- **Config 위치**: 프로젝트 루트의 `athanor.json`. `.athanor/` 안이 아닌 루트에 둬서 가시성 확보.
- **Worker dispatch 방식**: Agent tool with `subagent_type: "general-purpose"`. 전용 agent type 정의는 Phase 2에서 검증 후 결정.
- **MCP 접근 검증**: worker 안에서 mem-search write → read 왕복 테스트로 실증. 실패 시 .md fallback 전략 수립.

## Open Questions

### Resolved During Planning

- **Q: setup worker agent 정의를 별도로 만들어야 하나?**
  Resolution: 아니오. SKILL.md가 leader 동작을 정의하고, worker는 general-purpose agent로 dispatch. 별도 agent .md 불필요.

- **Q: athanor.json을 .athanor/ 안에 둘까 프로젝트 루트에 둘까?**
  Resolution: 프로젝트 루트. Citadel은 `.claude/harness.json`을 쓰지만, 우리는 독립 config 파일이므로 루트가 더 가시적.

### Deferred to Implementation

- **Q: LSP(Serena) 연결 확인 구체적 방법** — Serena MCP tool을 호출해보고 응답 여부로 판단. 구체적 tool 이름은 실행 시 확인.
- **Q: Codex CLI 존재 확인 방법** — `which codex` or codex plugin 도구 호출 시도. 실행 시 확인.

## Implementation Units

- [x] **Unit 1: Session 디렉토리 관리 로직 추가**

  **Goal:** setup SKILL.md에 세션 디렉토리 생성 및 관리 지시를 구체화

  **Requirements:** R2

  **Dependencies:** None

  **Files:**
  - Modify: `skills/setup/SKILL.md`

  **Approach:**
  - Worker에게 `.athanor/sessions/` 디렉토리 존재 확인 → 없으면 생성 지시
  - 세션 ID 규칙 (`YYYY-MM-DD-NNN`) 명시
  - 세션 디렉토리 구조 템플릿 정의 (discuss.md, analyze.md, plan.md, decisions.md, work-log.md, discoveries/)

  **Patterns to follow:**
  - Citadel `init-project.js`의 `.planning/` 스캐폴딩 패턴 (see origin: ref/Citadel/hooks_src/init-project.js)

  **Test scenarios:**
  - Happy path: `.athanor/` 없는 프로젝트에서 setup 실행 → 디렉토리 생성 확인
  - Edge case: `.athanor/sessions/` 이미 존재할 때 → 덮어쓰지 않음

  **Verification:** `.athanor/sessions/` 디렉토리가 올바른 구조로 존재

---

- [x] **Unit 2: Config 관리 로직**

  **Goal:** athanor.json 로딩/생성/기본값 fallback 로직 구체화

  **Requirements:** R3

  **Dependencies:** None (Unit 1과 병렬 가능)

  **Files:**
  - Modify: `skills/setup/SKILL.md`
  - Reference: `athanor.json.template`

  **Approach:**
  - Worker가 프로젝트 루트에서 `athanor.json` 확인
  - 없으면 `athanor.json.template` 내용을 기반으로 생성
  - template은 `${CLAUDE_PLUGIN_ROOT}/athanor.json.template` 경로로 참조
  - 있으면 버전 필드 확인 후 누락 필드 보완 여부 판단

  **Patterns to follow:**
  - Citadel `harness.json` 생성 패턴

  **Test scenarios:**
  - Happy path: config 없는 프로젝트 → `athanor.json` 생성 확인
  - Happy path: config 있는 프로젝트 → 기존 config 보존
  - Edge case: config에 일부 필드 누락 → 기본값으로 보완 or 경고

  **Verification:** `athanor.json` 파일이 유효한 JSON으로 존재

---

- [x] **Unit 3: Health Check Worker Dispatch 구현**

  **Goal:** setup SKILL.md를 보강하여 leader가 health check worker를 dispatch하고 결과를 표시

  **Requirements:** R1, R4, R5

  **Dependencies:** Unit 1, Unit 2

  **Files:**
  - Modify: `skills/setup/SKILL.md`

  **Approach:**
  - Leader(SKILL.md)가 단일 worker agent를 dispatch
  - Worker에게 전달할 체크 리스트:
    1. `mem-search` 접근 테스트 (write → read 왕복)
    2. LSP/Serena 도구 호출 시도
    3. Codex 연결 확인 (`codex --version` or plugin 도구)
    4. Agent Teams 환경변수 확인
    5. `athanor.json` 존재/생성 확인
    6. `.athanor/sessions/` 존재/생성 확인
  - Worker가 결과를 JSON 또는 structured text로 반환
  - Leader가 status table로 포맷팅하여 출력
  - 트리거 언어 설정 질문 추가

  **Patterns to follow:**
  - Citadel setup SKILL.md의 step-by-step protocol 패턴
  - Compound-engineering onboarding 스킬의 dispatch 패턴

  **Test scenarios:**
  - Happy path: 모든 도구 사용 가능 → 전부 ✓ 표시
  - Edge case: mem-search 없음 → ✗ 표시 + fallback 안내
  - Edge case: Codex 없음 → ✗ 표시 (optional이므로 경고만)
  - Integration: worker가 실제로 mem-search에 write→read 성공하는지 검증

  **Verification:** `/athanor:setup` 실행 시 status table 출력 + config/session 디렉토리 생성

---

- [x] **Unit 4: MCP 접근성 실증 테스트**

  **Goal:** Worker agent에서 MCP 도구(mem-search) 접근 가능 여부를 실증

  **Requirements:** R5

  **Dependencies:** Unit 3

  **Files:**
  - No new files — setup worker의 mem-search 테스트 결과로 판단

  **Approach:**
  - Unit 3의 health check에서 mem-search write→read 테스트가 핵심
  - 성공: Athanor 전체 아키텍처가 성립. 이후 Phase에서 worker가 mem-search 자유롭게 사용 가능.
  - 실패: `.md` 파일 기반 fallback 전략 수립. DESIGN.md에 fallback 기록.
  - 결과를 STATE.md에 기록

  **Test scenarios:**
  - Happy path: worker agent → mem-search write("athanor-test", "hello") → read → match → 성공
  - Error path: mem-search MCP 미등록 → 에러 catch → 실패 보고 + fallback 안내

  **Verification:** STATE.md에 "MCP 접근: ✓ 실증 완료" 또는 "MCP 접근: ✗ fallback 필요" 기록

## System-Wide Impact

- **Interaction graph:** setup은 다른 스킬에 의존하지 않음. 역으로 다른 스킬들이 setup이 만든 `.athanor/` 디렉토리와 `athanor.json`에 의존.
- **State lifecycle:** `athanor.json`은 프로젝트 수명 동안 유지. `.athanor/sessions/`는 working_cleaner가 관리 (Phase 8).
- **API surface parity:** 없음 — 첫 번째 구현.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| MCP 도구가 sub-agent에서 접근 불가 | .md 파일 기반 fallback 전략 수립 |
| `${CLAUDE_PLUGIN_ROOT}` 변수가 SKILL.md에서 사용 불가 | Citadel ref 참고하여 경로 해결 패턴 확인 |
| Windows 환경에서 `.athanor/` dotfile 디렉토리 문제 | Windows는 dotfile 지원하므로 문제 없을 것으로 예상 |

## Sources & References

- Origin: `docs/DESIGN.md`, `docs/ROADMAP.md`
- Pattern reference: `ref/Citadel/skills/setup/SKILL.md`
- Pattern reference: `ref/Citadel/hooks_src/init-project.js`
- Plugin structure: `ref/compound-engineering-plugin/plugins/compound-engineering/.claude-plugin/plugin.json`
