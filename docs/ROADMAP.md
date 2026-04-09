# Athanor — Implementation Roadmap

> 각 Phase는 이전 Phase 완료 후 진행. 각 항목은 독립 커밋 단위.

---

## Phase 0: Skeleton ✅ DONE
- [x] plugin.json 작성
- [x] 디렉토리 구조 생성 (skills/, agents/, hooks/, docs/)
- [x] CLAUDE.md 작성
- [x] athanor.json.template 생성
- [x] .gitignore 정리
- [x] DESIGN.md 작성
- [x] 초기 커밋 + push

---

## Phase 1: Foundation — /athanor:setup + 인프라
> 목표: 플러그인이 로딩되고, 환경 점검이 동작하는 상태

### 1.1 플러그인 로딩 검증
- [x] Claude Code에서 `--plugin-dir` 로 로딩 테스트
- [x] 5개 스킬이 `/athanor:` prefix로 표시되는지 확인
- [x] plugin.json 필드 누락/오류 수정

### 1.2 Session 디렉토리 관리
- [x] `.athanor/sessions/` 디렉토리 자동 생성 로직
- [x] 세션 ID 생성 규칙 정의 (날짜 기반: `2026-04-08-001`)
- [x] 세션 디렉토리 구조 템플릿 (discuss.md, analyze.md, plan.md, decisions.md, work-log.md, discoveries/)

### 1.3 Config 관리
- [x] athanor.json 로딩 로직 (setup SKILL.md에 기술)
- [x] athanor.json.template → 프로젝트 루트에 복사
- [x] 기본값 fallback (config 없어도 동작)

### 1.4 /athanor:setup 구현
- [x] Health check worker agent 작성
- [x] LSP(Serena) 연결 확인 방법
- [x] mem-search 동작 확인 방법
- [x] Codex 연결 확인 방법
- [x] Agent Teams 활성화 확인
- [x] 상태 테이블 출력 포맷
- [x] 트리거 언어 설정 (ko/en/both)

### 1.5 테스트
- [x] `/athanor:setup` 실행 → 상태 테이블 출력 확인
- [x] athanor.json 자동 생성 확인

---

## Phase 2: Dispatch Pattern — 핵심 인프라
> 목표: "Leader dispatch → Worker 실행 → Brief 반환" 패턴 검증

### 2.1 Dispatch Helper
- [x] Agent tool 호출 표준 패턴 정의 (SKILL.md 내 가이드라인)
- [x] dispatch packet 포맷 확정
- [x] result brief 포맷 확정
- [x] 에러 핸들링 (worker timeout, crash)

### 2.2 .md 파일 I/O 규약
- [x] 세션 파일 읽기/쓰기 규약 (어디에 뭘 저장)
- [x] 파일 잠금 없음 확인 (solo에서는 순차라 불필요)
- [x] discovery 파일 naming 규약 (`worker-{subtask-id}.md`)

### 2.3 Smoke Test
- [x] 단순 agent dispatch → 파일 하나 읽기 → brief 반환
- [x] worker가 mem-search 접근 가능한지 실증 테스트
- [x] worker가 LSP(Serena) 접근 가능한지 실증 테스트

---

## Phase 3: /athanor:discuss — 첫 번째 워크플로우
> 목표: A vs B 의사결정 → 구조화된 분석 결과

### 3.1 Researcher Agent
- [x] researcher.md 보강 (mem-search recall 지시 추가)
- [x] 출력 포맷 확정 (Option A pros/cons, Option B pros/cons)

### 3.2 Critic Agent
- [x] critic.md를 discuss용으로 분리 or 범용화
- [x] 합성 로직: 두 researcher 결과 → 통합 추천
- [x] brainstorming 기법 선택 로직 (Six Hats, Deep Interview 등)

### 3.3 Codex Integration (Optional)
- [x] Codex dispatch 방법 확정 (codex:rescue? 직접 호출?)
- [x] Codex 없을 때 fallback: Devil's Advocate 모드 Claude agent
- [x] athanor.json의 codex.enabled 반영

### 3.4 discuss SKILL.md 보강
- [x] Leader 동작 상세화 (parse → dispatch → collect → present → save)
- [x] discuss.md 출력 포맷 확정

### 3.5 테스트
- [x] `/athanor:discuss "TypeScript vs Python for this project?"` 실행
- [x] discuss.md 생성 및 내용 확인
- [x] Codex fallback 동작 확인

---

## Phase 4: /athanor:analyze — 병렬 분석
> 목표: 병렬 agent N개로 빠른 코드베이스 분석

### 4.1 Analyst Agent 보강
- [x] LSP 도구 사용 지시 강화 (get_symbols_overview, find_symbol 등)
- [x] "파일 통째로 읽지 마라" 규칙 강화
- [x] 출력 brevity 가이드라인

### 4.2 병렬 Dispatch
- [x] 분석 대상을 N개 focus area로 분할하는 로직
- [x] N개 analyst agent 동시 dispatch
- [x] 결과 merge 로직 (Leader가 수행? 별도 merge agent?)

### 4.3 mem-search Recall Worker
- [x] 분석 대상 관련 과거 lesson/memory 검색
- [x] 결과를 analyze.md에 "Historical Context" 섹션으로 포함

### 4.4 analyze SKILL.md 보강
- [x] 병렬 dispatch 패턴 상세화
- [x] analyze.md 출력 포맷 확정

### 4.5 테스트
- [x] `/athanor:analyze "이 프로젝트의 모듈 구조 분석"` 실행
- [x] 병렬 agent 3개 동시 실행 확인
- [x] analyze.md 생성 및 LSP 활용 확인

---

## Phase 5: /athanor:plan — Cross-Model Adversarial Planning
> 목표: 두 모델이 독립 플랜 → 교차 리뷰 → Critic 통합

### 5.1 Planner Agent (Claude용)
- [x] planner.md 보강 — 이전 discuss.md, analyze.md 읽기 지시
- [x] Plan 출력 포맷 확정 (Goal, Approach, Phases, Risks)
- [x] plan-claude.md 저장

### 5.2 Planner Agent (Codex/Contrarian용)
- [x] Codex dispatch 패턴 확정
- [x] Codex 없을 때: "You are a contrarian planner" 프롬프트
- [x] plan-codex.md 저장

### 5.3 Cross-Review
- [x] Step 2 완료 후 Step 3 시작 (순차 의존)
- [x] Claude reviews plan-codex.md → review-of-codex.md
- [x] Codex reviews plan-claude.md → review-of-claude.md
- [x] 두 리뷰 병렬 실행

### 5.4 Critic Synthesis
- [x] critic.md 보강 — 4개 문서 읽기 지시
- [x] Merged plan 출력
- [x] UNRESOLVED 충돌 → 사용자 선택지 형식
- [x] 충돌 없으면 바로 확정 제안

### 5.5 Task Splitter
- [x] 확정된 플랜 → granular subtask 분할
- [x] subtask 포맷: id, task, files, decisions, constraints, verify, depends_on
- [x] 검증 전략 분류 (command/check/review/none)
- [x] plan.md 최종 섹션에 subtask list 추가

### 5.6 Decision Log
- [x] decisions.md 자동 생성
- [x] /plan 확정 시 결정사항 자동 기록
- [x] 충돌 해결 시 선택 이유 기록

### 5.7 테스트
- [x] `/athanor:plan "OTP 모듈에 타이머 리셋 기능 추가"` 실행
- [x] plan-claude.md, plan-codex.md 생성 확인
- [x] review 파일 생성 확인
- [x] critic 통합 결과 확인
- [x] subtask list 생성 확인
- [x] decisions.md 생성 확인

---

## Phase 6: /athanor:work --solo — 순차 실행
> 목표: plan.md의 subtask를 순차 dispatch + ralph-loop으로 전부 완료

### 6.1 Executor Agent 보강
- [x] dispatch packet 파싱 로직
- [x] ralph-loop 구현 (attempt → verify → retry/pass)
- [x] 검증 전략별 동작 (command: Bash, check: file exists, review: self-check, none: 1회)
- [x] result brief 포맷 (변경사항, 결정, discoveries)
- [x] discovery importance 태깅

### 6.2 Solo Mode Leader Flow
- [x] plan.md에서 subtask list 파싱
- [x] depends_on 순서 정렬
- [x] dispatch packet 빌드
- [x] 순차 dispatch → result 수집
- [x] TodoList 연동 (TaskCreate → TaskUpdate)

### 6.3 실패 처리
- [x] ralph-loop maxRetries 초과 → failure brief 반환
- [x] Leader가 실패 받으면 사용자에게 선택지: retry / skip / abort
- [x] Circuit Breaker: N개 연속 실패 → 전체 중단 + 에스컬레이션

### 6.4 중간 취소
- [x] 취소 시 현재까지 진행 상황 보존
- [x] TodoList 현재 상태 반영
- [x] 재개 시 미완료 subtask부터 시작

### 6.5 work-log.md
- [x] 각 subtask 완료/실패 시 work-log.md에 기록
- [x] 타임스탬프, 상태, brief 요약

### 6.6 테스트
- [x] 3-subtask 플랜으로 solo 실행
- [x] ralph-loop 재시도 동작 확인
- [x] 실패 → 사용자 선택지 확인
- [x] TodoList 진행 표시 확인
- [x] work-log.md 기록 확인

---

## Phase 7: /athanor:work --team — 병렬 실행
> 목표: wave 기반 병렬 dispatch + discovery relay

### 7.1 Wave Grouping
- [x] subtask의 depends_on 분석 → wave 분배
- [x] wave 내 subtask는 동시 실행 가능
- [x] waveSize (athanor.json) 적용

### 7.2 Parallel Dispatch
- [x] wave 내 subtask 동시 Agent dispatch
- [x] worktree 격리 (가능하면)
- [x] 모든 worker 완료 대기

### 7.3 Discovery Relay
- [x] wave 완료 후 각 worker의 discovery brief 수집
- [x] `.athanor/sessions/{id}/discoveries/` 에 저장
- [x] 다음 wave worker에 이전 discoveries 주입

### 7.4 테스트
- [x] 2-worker wave로 병렬 실행 확인
- [x] discovery relay: wave 1 결과가 wave 2에 전달 확인
- [x] 충돌 없이 병합 확인

---

## Phase 8: Learning & Memory — 성장 메커니즘
> 목표: 사용할수록 똑똑해지는 Athanor

### 8.1 Learner Agent
- [x] learner.md 에이전트 정의 작성
- [x] 세션 결과 분석 로직 (성공/실패/패턴)
- [x] structured lesson 추출
- [x] 기존 lesson과 중복 체크
- [x] mem-search에 lesson 저장

### 8.2 Memory Decay + Access Count
- [x] working memory에 access_count 메타데이터 추가
- [x] worker가 memory 참조 시 access_count 증가 로직
- [x] decay 규칙 구현:
  - age > 7일 + 참조 0회 → 삭제
  - age > 7일 + 참조 5회+ → permanent 승격
  - age > 30일 + 참조 0회 → 삭제

### 8.3 Working Cleaner 보강
- [x] access_count 기반 smart promotion
- [x] 단순 age 삭제 → decay model 적용
- [x] Cleaner Report 출력

### 8.4 /work 완료 시 자동 트리거
- [x] /work 완료 → Learner dispatch → Cleaner dispatch (순차)
- [x] 전체 completion summary (subtasks + lessons + cleaned)

### 8.5 테스트
- [x] /work 완료 후 lesson 생성 확인
- [x] 다음 세션에서 lesson이 worker에 주입되는지 확인
- [x] access_count 증가 + 자동 승격 확인
- [x] 30일+ 미참조 memory 삭제 확인

---

## Phase 9: Polish & Defense
> 목표: 안정성, 방어, 문서화

### 9.1 Model Configuration
- [x] agent frontmatter에 model 필드 추가
- [x] athanor.json의 models 설정 → agent dispatch 시 적용
- [x] 테스트: analyst가 sonnet으로 실행되는지 확인

### 9.2 Defense Mechanisms
- [x] stop-phrase 감지 (조기 중단 패턴)
- [x] Read:Edit 비율 모니터링 (worker 품질 체크)
- [x] effort=max 강제 (중요 worker에만)

### 9.3 Error Handling
- [x] 모든 agent dispatch에 timeout 설정
- [x] Codex 연결 실패 → graceful fallback
- [x] 세션 파일 손상 → 복구 or 재생성

### 9.4 Documentation
- [x] README.md 작성 (설치, 사용법, 예제)
- [x] CONTRIBUTING.md
- [x] DESIGN.md 최종 정리

### 9.5 Release
- [x] 전체 기능 통합 테스트
- [x] v0.1.0 태그 + push
- [x] GitHub Release 생성

---

## Post-Release: 구조 개선

### 3-Tier Plan 재구조화 + Real Codex Integration
- [x] `/athanor:plan` → 3-tier 분리: `deep-plan`, `plan` (standard), `lite-plan`
- [x] 파일명 중립화: `plan-claude/codex` → `plan-a/b`, `review-of-claude/codex` → `review-of-a/b`
- [x] Codex CLI 직접 호출 패턴: `codex exec --full-auto --ephemeral`
- [x] CONVENTIONS.md, ROADMAP.md 문서 반영

---

## Dependency Graph

```
Phase 0 (✅)
  ↓
Phase 1 (setup + 인프라)
  ↓
Phase 2 (dispatch 패턴 검증)
  ↓
Phase 3 (discuss)  ←──── Phase 4 (analyze)
  │                       │
  └──────┬────────────────┘
         ↓
Phase 5 (plan) ← discuss + analyze 결과 활용
         ↓
Phase 6 (work --solo)
         ↓
Phase 7 (work --team)
         ↓
Phase 8 (learning & memory)
         ↓
Phase 9 (polish & release)
```

Phase 3과 4는 **병렬 개발 가능** (서로 독립).
Phase 5는 3+4 완료 후.
Phase 7은 6 완료 후.

---

## Estimated Scope

| Phase | 파일 수 | 핵심 난이도 |
|-------|---------|------------|
| 1 | ~3 | Low — 설정/점검 |
| 2 | ~2 | Medium — 패턴 검증 |
| 3 | ~3 | Medium — 첫 워크플로우 |
| 4 | ~3 | Medium — 병렬 패턴 |
| 5 | ~6 | **High** — 교차 플래닝 |
| 6 | ~5 | **High** — ralph-loop |
| 7 | ~3 | Medium — wave 병렬 |
| 8 | ~4 | Medium — 학습 메커니즘 |
| 9 | ~5 | Low — 정리/문서 |
