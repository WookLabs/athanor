# Task Splitter Reference

Detailed reference for `/athanor:work` Step 0.5 (Task Splitter dispatch).
Cross-linked from `skills/work/SKILL.md` Step 0.5.

## Pre-flight State Detection

Leader는 다음을 확인한다 (파일 존재 확인만 수행 — Thin Leader 예외):
- `plan.md`에 `## Subtasks` 헤더가 존재하는가? → `has_subtasks`
- `.athanor/sessions/{id}/work-log.md`가 존재하는가? → `work_in_progress`
- `## Subtasks` 섹션 직전 또는 직후에 `<!-- athanor:subtasks:manual -->` 마커가 있는가? → `manual_marker`

## Dispatch Decision Matrix

| has_subtasks | work_in_progress | 동작 |
|---|---|---|
| No | - | [신규] Splitter 무조건 디스패치 |
| Yes | Yes | [Resume] 사용자 확인: R(기본)/S/A |
| Yes | No | [Manual Edit 가능성] manual_marker 있으면 자동 Keep; 없으면 사용자 확인: K/R(기본)/A |

**Resume 프롬프트** (has_subtasks AND work_in_progress):
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ 진행 중인 작업이 감지되었습니다.
  work-log.md가 이미 존재합니다.

  [R] Resume  - 기존 subtasks 유지 (기본값)
  [S] Re-split - subtask 재생성 (진행 상태 초기화)
  [A] Abort
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Manual Edit 프롬프트** (has_subtasks AND NOT work_in_progress AND NOT manual_marker):
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ 기존 Subtasks 섹션이 감지되었습니다.
  (수동 편집되었을 수 있습니다)

  [K] Keep as-is - 기존 Subtasks 유지
  [R] Regenerate - plan.md로부터 재생성 (기본값)
  [A] Abort
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
(구 세션에서는 R 선택이 기존 /athanor:plan Task Splitter와 동일한 결과를 줍니다.)

## Snapshot & Restore

Splitter를 디스패치하기로 결정한 경우, 직전에 `plan.md`를 `plan.md.bak`으로 복사한다
(leader의 기존 session-creation 예외와 같은 infra 수준의 파일 조작).
Splitter 완료 후 post-split 검증에 실패하면 `plan.md.bak`을 `plan.md`로 복원하고 abort한다.

## Splitter Worker Dispatch

Note: outer fence uses ~~~ to avoid clashing with inner ``` blocks.

~~~
Agent({
  description: "Athanor task splitter",
  model: "sonnet",
  prompt: "You are the Athanor Task Splitter.

## Task
Split this confirmed plan into granular, executable subtasks.
Read the confirmed plan from: .athanor/sessions/{session-id}/plan.md

## Idempotency (strip-then-append)
plan.md MAY already contain a `## Subtasks` section from a previous run.
If it does, remove that entire section (from the `## Subtasks` header through
the next `## ` header or EOF, whichever comes first) before appending the new one.
Do NOT touch any content under other `## ` headers that come after Subtasks.
This keeps re-runs clean without eating unrelated sections.

## Atomic Write Rule
Prepare the complete new plan.md content in memory first. Only when the full
new content (original body + fresh Subtasks block) is ready, write it to plan.md
in a single write. Do not perform incremental writes.

## Rules (per subtask)
- ONE atomic unit of work, 5-30 minutes
- Include verification strategy (type: command|check|review|none)
- Respect dependency ordering
- Be specific: files, functions, expected changes
- IDs must be stable, unique, sequential (Subtask 1, 2, ...)
- depends_on references must all point to existing subtask IDs
- **v0.8.0**: Assign `execution_note` per subtask using these classification heuristics:
  - **source code modification** (.py/.js/.ts/.rb/.go/etc.) introducing new
    behavior or contract → `execution_note: spec-then-tdd`
  - **source code modification** preserving existing behavior (refactor,
    narrow bug fix without contract change) → `execution_note: test-aware`
  - **prose-only modification** (.md / `_doc` strings in config / CHANGELOG /
    README / doc-only edits) → `execution_note: direct`
  - **security-adjacent configuration changes** (hooks/hooks.json,
    .claude-plugin/plugin.json `hooks` field, schemas/*.json behavior
    constraints, anything under hooks/ or scripts/hooks/, athanor.json
    `hooks` block that the Stop hook reads at runtime) — these are JSON
    files, not source code, so the "source code" rules above do not apply.
    Default classification: **`test-aware`** (require regression test
    accompanying the config edit). If the JSON change introduces a new
    runtime contract (new hook event, new field consumed by code paths,
    materially different schema constraint) → **`spec-then-tdd`**. NEVER
    classify these files as `direct` even when the edit looks small —
    silent reclassification of security-adjacent files defeats the purpose
    of the discipline.
- **v0.8.0**: For `execution_note: spec-then-tdd` subtasks, copy the parent
  phase's `Verify:` MUST/SHOULD bullets into the subtask's
  `acceptance_criteria` field. If the parent phase has free-form prose Verify
  (no MUST/SHOULD bullets), reclassify the subtask to `test-aware` and note
  the reclassification reason in the subtask's task description. The
  `acceptance_criteria` field is **only** populated for spec-then-tdd subtasks
  (test-aware and direct subtasks must NOT have an `acceptance_criteria` line).
- **v0.10.1**: Every subtask MUST carry a `classification_reason: <one-line>`
  field directly below `execution_note`. The reason is a single descriptive
  sentence explaining which heuristic rule above fired ("source-code mod
  introducing new behavior" / "tests/** only, doc-shape change" /
  "security-adjacent JSON edit, no new runtime contract" / etc.). The
  reason is descriptive not prescriptive — the heuristic itself is
  unchanged; v0.10.1 only adds the audit field so misclassifications are
  diagnosable from the work log. Splitter MUST emit the field for every
  subtask regardless of classification value (spec-then-tdd / test-aware
  / direct all require a reason). Length contract: one line, ≤ 200 chars,
  no embedded newlines. Free-form English or Korean prose.

## Output Format
Append this section to plan.md (after stripping any old Subtasks block):

---

## Subtasks

- [ ] **Subtask 1: {title}**
  - task: {what to do}
  - files: [{file paths}]
  - verify: {type: command|check|review|none, value: ...}
  - depends_on: []
  - execution_note: {spec-then-tdd|test-aware|direct}  # v0.8.0 — required
  - classification_reason: {one-line descriptive reason}  # v0.10.1 — required for every subtask
  - acceptance_criteria:                                # v0.8.0 — ONLY when execution_note == spec-then-tdd
    - MUST <observable assertion copied from parent phase Verify>
    - MUST <observable assertion>
    - SHOULD <quality assertion>

- [ ] **Subtask 2: {title}**
  - task: {what to do}
  - files: [...]
  - verify: {...}
  - depends_on: [1]
  - execution_note: {spec-then-tdd|test-aware|direct}
  - classification_reason: {one-line descriptive reason}

...

<!-- athanor:subtasks:generated -->

Also create .athanor/sessions/{session-id}/decisions.md (OVERWRITE if exists):

# Decision Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
{list all key decisions from the plan}

Save to: .athanor/sessions/{session-id}/plan.md
Save to: .athanor/sessions/{session-id}/decisions.md

Return:
ATHANOR_RESULT
status: success
summary: {subtask count and structure, 1-2 sentences}
END_RESULT"
})
~~~

## Post-split Validation

Splitter 복귀 후 leader는 plan.md를 재로드하고 다음을 검증:
1. `## Subtasks` 헤더가 존재하는가?
2. 최소 1개 이상의 `- [ ] **Subtask N:**` 항목이 있는가?
3. 각 subtask에 task/files/verify/depends_on 필드가 모두 있는가?
4. 모든 depends_on 참조가 실제 존재하는 subtask 번호인가?
5. decisions.md가 생성/갱신되었는가?
6. Subtasks 섹션 끝에 `<!-- athanor:subtasks:generated -->` 마커가 존재하는가?
7. **v0.8.0**: 각 subtask에 `execution_note` 필드가 존재하는가? 값은
   `spec-then-tdd | test-aware | direct` 셋 중 하나여야 한다.
8. **v0.8.0**: `execution_note: spec-then-tdd` 인 subtask는 `acceptance_criteria`
   필드를 가지며 최소 1개 MUST bullet이 있어야 한다.
9. **v0.10.1**: 각 subtask에 `classification_reason` 필드가 존재하며 비어 있지
   않은가? (분류값과 무관하게 모든 subtask가 가져야 한다 — Splitter audit trail
   요건). 200 chars 초과 또는 newline 포함 시 검증 실패.

하나라도 실패하면:
- `plan.md.bak` → `plan.md`로 복원
- `decisions.md`는 복원 대상 제외 (다음 성공 run에서 overwrite됨)
- Leader 메시지:
  `⚠ Task Splitter 검증 실패 — plan.md를 원복했습니다.
  /athanor:plan으로 돌아가 플랜을 검토하거나 plan.md를 직접 수정 후
  /athanor:work를 재실행해주세요.`
- Abort.

검증 성공 시 `plan.md.bak` 삭제 후 Step 1로 진행.

## Fast Paths

- **Resume(R) 선택**: Splitter 디스패치 스킵. 기존 `## Subtasks`와 기존 `decisions.md`를 그대로 사용.
  Subtask ID와 진행 상태가 안전하게 유지된다.
- **Keep as-is(K) 선택**: 수동 편집된 Subtasks를 그대로 사용.
  `decisions.md`가 없으면 경고만 띄우고 진행한다.
