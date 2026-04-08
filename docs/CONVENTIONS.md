# Athanor — Conventions

> 모든 스킬과 에이전트가 따르는 표준 규약

---

## 1. Dispatch Pattern

### Leader → Worker Dispatch

모든 `/athanor:*` 스킬은 **Thin Leader** 패턴을 따른다:

```
Leader (SKILL.md)                 Worker (Agent tool)
┌──────────────────┐             ┌──────────────────────┐
│ 1. 사용자 입력 파싱│  dispatch   │ dispatch packet 수신  │
│ 2. dispatch packet│ ────────→  │ 작업 수행              │
│    구성           │             │ result brief 작성      │
│ 3. Agent tool 호출│ ←────────  │ brief 반환             │
│ 4. brief 파싱     │   result   │                        │
│ 5. 사용자에게 표시 │             └──────────────────────┘
└──────────────────┘
```

### Agent Tool 호출 표준

```
Agent({
  description: "간결한 작업 설명 (3-5 단어)",
  prompt: "{dispatch packet — 아래 포맷 참조}",
  subagent_type: "general-purpose",
  model: "{athanor.json models 설정에 따라}"
})
```

- **병렬 dispatch**: 독립적인 worker는 하나의 메시지에 여러 Agent 호출로 병렬 실행
- **순차 dispatch**: 의존성 있으면 이전 worker 결과 수신 후 다음 dispatch
- **model 선택**: athanor.json의 `models` 설정 참조. 미지정 시 기본 모델 사용

### 에러 핸들링

| 상황 | Leader 동작 |
|------|------------|
| Worker timeout | "Worker가 응답하지 않습니다. 재시도할까요?" |
| Worker crash | 에러 메시지 표시 + 재dispatch 제안 |
| Worker 부분 결과 | 받은 결과만 표시 + 실패 부분 안내 |
| MCP 미접근 | .md fallback 안내 |

---

## 2. Dispatch Packet Format

Worker에게 보내는 프롬프트는 다음 구조를 따른다:

### 분석/리서치 작업 (discuss, analyze)

```markdown
You are an Athanor {role} worker.

## Task
{구체적 작업 설명}

## Context
- Session: .athanor/sessions/{session-id}/
- Previous: {이전 단계 파일 경로, 있으면}
- Decisions: {확정된 결정 사항, 있으면}

## Constraints
- {지켜야 할 규칙들}

## Output
Save your results to: .athanor/sessions/{session-id}/{output-file}

Return a brief summary (under 300 words) of your findings.
Format: ATHANOR_RESULT ... END_RESULT
```

### 실행 작업 (work — executor)

```markdown
You are an Athanor executor worker.

## Subtask
{task description}

## Context
- Files: {관련 파일 경로 + 라인 범위}
- Decisions: {따라야 할 결정 사항}
- Constraints: {규칙/제한}
- Previous discoveries: {이전 wave 발견, team 모드만}

## Verify
- type: {command | check | review | none}
- value: {검증 커맨드 또는 조건}

## Ralph-Loop
Attempt the task → run verification → if fail, analyze and retry.
Max retries: {maxRetries from config}

## Output
Tag discoveries with importance:
<!-- importance: permanent --> for lasting lessons
<!-- importance: working --> for task-specific details

Return result brief:
ATHANOR_RESULT
status: {success|failure}
changed: {files changed}
decisions: {decisions made}
discoveries: {tagged discoveries}
END_RESULT
```

---

## 3. Result Brief Format

Worker가 반환하는 표준 포맷:

```
ATHANOR_RESULT
status: {success|failure|partial}
summary: {1-2문장 요약}
details:
  - {핵심 발견/결과 1}
  - {핵심 발견/결과 2}
files_changed:
  - {파일 경로}: {변경 설명}
discoveries:
  - {importance: permanent|working}: {내용}
END_RESULT
```

**규칙:**
- brief는 **300 단어 이내**
- Leader 컨텍스트 오염을 최소화하기 위해 간결하게
- 상세 내용은 .md 파일에 저장, brief에는 요약만

---

## 4. Session File I/O 규약

### 디렉토리 구조

```
.athanor/
  sessions/
    {YYYY-MM-DD-NNN}/          ← 세션 디렉토리
      discuss.md               ← /athanor:discuss 결과
      analyze.md               ← /athanor:analyze 결과
      plan.md                  ← /athanor:plan 확정 플랜 + subtask list
      plan-claude.md           ← Claude planner 원본 (plan 중간 산출물)
      plan-codex.md            ← Codex planner 원본 (plan 중간 산출물)
      review-of-claude.md      ← Codex의 Claude plan 리뷰
      review-of-codex.md       ← Claude의 Codex plan 리뷰
      decisions.md             ← 확정 결정 로그
      work-log.md              ← /athanor:work 진행 기록
      discoveries/             ← worker discovery briefs
        worker-{agent-id}.md   ← 개별 worker 발견
  athanor.json                 ← 프로젝트 루트에 위치 (sessions 안이 아님)
```

### 파일 쓰기 규칙

| 누가 쓰나 | 파일 | 시점 |
|-----------|------|------|
| discuss worker | `discuss.md` | /athanor:discuss 완료 시 |
| analyze workers | `analyze.md` | /athanor:analyze 완료 시 (Leader가 merge) |
| planner workers | `plan-claude.md`, `plan-codex.md` | /athanor:plan Step 2 |
| review workers | `review-of-claude.md`, `review-of-codex.md` | /athanor:plan Step 3 |
| critic worker | `plan.md` | /athanor:plan Step 4 (최종 통합) |
| Leader | `decisions.md` | /athanor:plan 확정 시 |
| executor workers | `work-log.md`, `discoveries/worker-*.md` | /athanor:work 각 subtask 완료 시 |

### 파일 읽기 규칙

| 누가 읽나 | 파일 | 목적 |
|-----------|------|------|
| planner | `discuss.md`, `analyze.md` | 이전 단계 컨텍스트 |
| critic | `plan-claude.md`, `plan-codex.md`, `review-of-*.md` | 통합 입력 |
| executor | `plan.md`, `decisions.md` | 작업 지시 + 재논의 방지 |
| executor (team) | `discoveries/worker-*.md` | 이전 wave 발견 |

### 세션 ID 생성 규칙

```
YYYY-MM-DD-NNN

예: 2026-04-08-001, 2026-04-08-002
```

- Leader가 `/athanor:discuss`, `/athanor:plan`, `/athanor:work` 시작 시 새 세션 생성
- 같은 세션 ID로 discuss → analyze → plan → work 일관 사용
- `.athanor/sessions/` 내 기존 디렉토리 스캔 → 오늘 날짜 최대 NNN + 1

### 파일 잠금

- **없음** — solo 모드는 순차 실행이라 충돌 불가
- team 모드에서도 각 worker는 자기 discovery 파일만 씀 (충돌 없음)
- `plan.md`, `work-log.md`는 Leader만 쓰거나 append-only

---

## 5. Discovery File Convention

### Naming

```
discoveries/worker-{agent-description-slug}-{timestamp}.md
```

예: `discoveries/worker-executor-otp-reset-20260408-143022.md`

### Content Format

```markdown
# Discovery: {worker description}

## What was done
- {작업 내용}

## Decisions made
- {작업 중 내린 결정}

## Discoveries

<!-- importance: permanent -->
{영구 보존할 발견}

<!-- importance: working -->
{임시 발견 — 시간 지나면 삭제}

## Files changed
- {file}: {description}

## Verification
- Command: {what was run}
- Result: {pass/fail}
```
