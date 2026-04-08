# Athanor — Design Document

> General-purpose agentic workflow orchestrator plugin for Claude Code
> Repository: WookLabs/athanor

## Philosophy

**"기능 100개 모음이 아니라, 5개 워크플로우 단계."**

기존 플러그인(ECC, Citadel, superpowers)은 기능을 많이 제공하지만 실제로 쓰는 건 일부.
Athanor은 실제 작업 흐름에 맞춘 5개 커맨드만 제공한다.

## Architecture

### Thin Leader Pattern

Leader(본체)는 **절대 직접 작업하지 않는다.**
입력 파싱 → worker dispatch → 결과 수집 → 사용자에게 표시. 이것만 한다.

```
User
  ↕
Leader (thin router) ── 파일 안 읽음, 분석 안 함, 코드 안 씀
  │
  ├── /athanor:discuss ──→ worker(들) ──→ 결과 brief
  ├── /athanor:analyze ──→ worker(들) ──→ 결과 brief
  ├── /athanor:plan    ──→ worker(들) ──→ 결과 brief
  ├── /athanor:work    ──→ worker(들) ──→ 결과 brief
  └── /athanor:setup   ──→ worker      ──→ 결과 brief
```

**모든 실제 작업은 깨끗한 컨텍스트의 worker가 수행.**
Worker는 mem-search, LSP(Serena), .md 파일을 통해 컨텍스트를 얻는다.

Leader 컨텍스트에는 dispatch 기록 + 결과 brief만 쌓이므로,
세션이 아무리 길어져도 컨텍스트가 터지지 않는다.

### Mode Separation

```
┌─────────── Plan Mode (읽기/생각만) ───────────┐
│                                                │
│  /athanor:discuss → /athanor:analyze → /athanor:plan │
│  → 사용자 확정                                  │
│                                                │
└────────────────────┬───────────────────────────┘
                     ↓
              /athanor:work (Execution Mode)
              실제 코드 수정, 빌드, 테스트
              완료 시 → 메모리 자동 저장
```

Plan Mode에서는 절대 파일을 수정하지 않는다.
Execution Mode 전환은 사용자 확정 후에만 발생한다.

---

## Commands

### /athanor:setup — Infrastructure Health Check

인프라 유틸리티. Athanor이 제대로 동작할 환경을 점검하고 설정한다.

**기능:**
- LSP(Serena) 연결 상태 확인
- mem-search 동작 여부 확인
- Codex 연결 확인 (optional)
- Agent Teams 활성화 확인 및 설정
- athanor.json 생성/업데이트
- 트리거 언어 설정 (한글/영어)

### /athanor:discuss — Decision Brainstorming

의사결정 지원. "A가 좋을까 B가 좋을까?" 같은 고민에 대해
여러 관점에서 브레인스토밍한다.

**흐름:**
```
입력: "A vs B?" (고민)
  ↓
처리: Claude critic + Codex가 각각 독립 리서치/의견
  ↓
출력: 선택지 나열 + 각 장단점 + 추천
  ↓
저장: .athanor/sessions/{id}/discuss.md
```

**기법:** Six Thinking Hats, Deep Interview, Devil's Advocate 등
상황에 맞는 기법을 자동 선택하거나 사용자가 지정.

**특징:**
- 느려도 됨 (깊이가 중요)
- Claude + Codex 핑퐁 방식
- Codex 없으면 Claude self-critic fallback

### /athanor:analyze — Parallel Fast Analysis

현재 상태를 빠르게 파악한다. 여러 에이전트가 병렬로 분석.

**흐름:**
```
입력: 분석 대상/질문
  ↓
처리: 병렬 에이전트 N개 동시 투입
      - LSP(Serena) 심볼 분석
      - mem-search 관련 과거 지식 recall
      - 코드 구조/의존성 파악
  ↓
출력: 구조화된 분석 리포트
  ↓
저장: .athanor/sessions/{id}/analyze.md
```

**특징:**
- 속도가 생명
- LSP 우선 (파일 통째로 읽기 금지)
- 병렬 에이전트 산개

### /athanor:plan — Cross-Model Adversarial Planning

두 모델이 독립적으로 계획을 세우고, 서로 교차 리뷰한다.

**흐름:**
```
         ┌── Claude → Plan A ──→ Codex Review A ──┐
입력 ────┤                                         ├── Critic 통합
         └── Codex  → Plan B ──→ Claude Review B ──┘
                                                      ↓
                                              충돌 없으면 → 사용자에게 제시
                                              충돌 있으면 → 선택지 제시
                                                      ↓
                                              사용자 확정
                                                      ↓
                                              Task Splitter → 세세한 subtask 목록
```

**Codex fallback:**
Codex 없으면 Claude-only에서:
- Claude Plan → Claude Self-Critic Review
- 단일 모델이지만 critic이 plan을 공격적으로 비판

**Task Splitter:**
확정된 플랜을 매우 세세한 subtask로 쪼갠다.
각 subtask에는 검증 전략이 포함된다:

```
- command: "npm test"           # 커맨드 기반 검증
- check: "file_exists(out.md)"  # 파일 기반 검증
- review: true                  # self-review
- none: true                    # 1회 실행 (검증 불필요)
```

**저장:** .athanor/sessions/{id}/plan.md

### /athanor:work — Execution with TodoList Grinding

확정된 플랜의 모든 subtask를 완료할 때까지 실행한다.

**모드:**
```
/athanor:work --solo    순차 실행 (1개씩)
/athanor:work --team    병렬 실행 (Agent Teams, wave 방식)
```

사용자가 모드를 미리 지정한다.

**Solo 모드:**
```
for each subtask in TodoList:
    dispatch to clean-context worker
    worker: ralph-loop (검증 통과까지 반복)
    result brief → Leader
    TodoList에서 완료 체크
```

**Team 모드 (Wave 방식):**
```
Wave 1: Worker A, B, C 병렬 dispatch
        각자 ralph-loop
        결과 → discovery brief 파일로 저장
Wave 2: Worker D, E, F 병렬 dispatch
        이전 wave discovery 읽고 시작
        ...
완료까지 반복
```

**Dispatch Packet:**
Worker에게 넘기는 정보:
```
{
  subtask: "OTP 모듈에 타이머 리셋 로직 추가",
  context: {
    files: ["src/otp.sv:45-80"],
    decisions: ["리셋은 동기식으로"],
    constraints: ["lint 통과 필수"]
  },
  verify: { command: "make lint && make sim" }
}
```

**완료 시:**
1. 자동 메모리 저장 (2-tier)
2. working_cleaner 실행

**중간 취소:**
/btw로 취소 가능. 현재까지 진행 상황 저장.

**Worker 실패 시:**
Worker가 죽으면 Leader가 감지 → 재dispatch.
ralph-loop 무한루프 → /btw로 사용자가 취소.
subtask 반복 실패 → 사용자에게 물어봄.

---

## Session Communication

### .md File Based

모든 단계 간 통신은 .athanor/ 디렉토리의 .md 파일을 통한다.

```
.athanor/
  sessions/
    {session-id}/
      discuss.md       ← /athanor:discuss 결과
      analyze.md       ← /athanor:analyze 결과
      plan.md          ← /athanor:plan 확정안 + subtask 목록
      work-log.md      ← /athanor:work 진행 기록
      discoveries/
        worker-{id}.md ← team 모드 discovery relay
  athanor.json           ← 프로젝트 config
```

### Discovery Relay (Team Mode)

각 worker는:
1. 작업 시작 전 — 이전 wave의 discovery 파일 모두 읽음
2. 작업 완료 후 — 자신의 discovery brief 작성

Discovery brief 내용:
- 무엇을 했는지
- 어떤 결정을 내렸는지
- 무엇을 발견했는지
- 실패한 것은 무엇인지

---

## Memory Model

### 2-Tier Architecture

**영구 메모리 (Permanent)**
- 아키텍처 결정, 프로젝트 목표, 고정 구조/규칙
- 명시적 저장 또는 importance 태그로 승격
- mem-search에 저장

**작업 메모리 (Working/Cache)**
- 작업 내용, 변경 기록, 중간 결과
- 자동 저장 (/athanor:work 완료 시)
- working_cleaner가 자동 관리:
  - 오래된 항목 삭제
  - 쓸모없어진 항목 삭제
  - `important` 태그 → 영구로 승격

### Discovery Importance Tagging

Worker가 작업 중 발견한 것에 중요도 태그:
```
<!-- importance: permanent -->
이 프로젝트에서 async reset은 절대 사용 금지. timing 문제 발생.

<!-- importance: working -->
PR #42에서 lint 경고 3개 수정함.
```

working_cleaner는:
- `permanent` 태그 → mem-search 영구 저장으로 승격
- `working` 태그 → 기간 경과 후 자동 삭제
- 태그 없음 → working으로 간주

---

## Growth / Learning (Adopted from Paperclip + Citadel)

### Learner Agent

/athanor:work 완료 시 Learner가 자동 실행:

```
/athanor:work 완료
  ↓
Learner Agent:
  1. 세션 결과 분석 (성공/실패/패턴)
  2. 교훈 추출 → structured lesson으로 저장
  3. 기존 lesson과 중복 체크 → 병합 or 신규
  ↓
다음 세션 worker들이 자동 참조
```

### Structured Lesson Format

```markdown
---
type: lesson
skill: plan
confidence: high
source: session-042
access_count: 0
created: 2026-04-08
---
async reset은 이 프로젝트에서 timing closure 실패 유발.
/plan critic이 감지 시 경고해야 함.
```

### Memory Decay with Access Count

단순 age-based 삭제 대신 smart decay:

```
age < 7일              → 유지
age > 7일 + 참조 0회   → 삭제
age > 7일 + 참조 5회+  → permanent 자동 승격
age > 30일 + 참조 0회  → 삭제 (working만)
permanent              → 절대 삭제 안 함
```

### Decision Log (from Citadel)

`.athanor/sessions/{id}/decisions.md`에 확정된 결정 기록:

```markdown
| # | 결정 | 이유 | 확정일 |
|---|------|------|--------|
| 1 | 동기식 리셋 사용 | async는 timing 이슈 | 2026-04-08 |
```

Workers가 읽어서 재논의 방지.

### Circuit Breaker at /work Level (from Citadel)

개별 subtask의 ralph-loop과 별도로, /work 전체 레벨에서:

```
N개 subtask 연속 실패 → Circuit Breaker TRIP
→ "접근 방식 자체에 문제가 있을 수 있습니다"
→ 계속 / /plan 복귀 / 사용자 직접 개입 선택지
```

### Model Configuration per Agent (from ECC)

역할별 모델 최적화로 비용/속도 균형:

```json
"models": {
  "analyst": "sonnet",
  "planner": "opus",
  "critic": "opus",
  "executor": "sonnet",
  "cleaner": "haiku",
  "learner": "sonnet"
}
```

---

## Configuration

### athanor.json

```json
{
  "version": "1.0",
  "language": "ko",
  "codex": {
    "enabled": true,
    "fallback": "self-critic"
  },
  "work": {
    "defaultMode": "solo",
    "ralphLoop": {
      "maxRetries": 5
    },
    "circuitBreaker": {
      "consecutiveFailures": 3,
      "action": "ask_user"
    }
  },
  "team": {
    "waveSize": 3,
    "discoveryRelay": true
  },
  "memory": {
    "decayDays": 7,
    "promotionThreshold": 5,
    "maxAgeDays": 30
  },
  "models": {
    "analyst": "sonnet",
    "planner": "opus",
    "critic": "opus",
    "executor": "sonnet",
    "cleaner": "haiku",
    "learner": "sonnet"
  },
  "triggers": {
    "language": "both"
  }
}
```

---

## Differentiators

| | 기존 도구들 | Athanor |
|---|---|---|
| 플래닝 | 단일 모델 플랜 | Cross-model adversarial (Claude×Codex 교차리뷰) |
| 실행 | 한번 시도 | TodoList grinding (전부 완료까지) |
| 리더 | 오케스트레이터가 직접 작업 | Thin leader (dispatch만) |
| 메모리 | 수동 저장 | 자동 2-tier (영구 + 작업캐시 auto-evict) |
| 철학 | 기능 N개 모음 | 5개 워크플로우 단계 |
| 모드 | 항상 같음 | Plan mode → Execution mode 명시적 전환 |
