# Goal 36470e54 [COMPLETE]

<!-- status: complete; ratified 2026-05-31 -->: ref 에이전트 마이그레이션 + 평가 + athanor 에이전트 정리

## Goal statement
ref/ 의 쓸만한 에이전트를 athanor 플러그인으로 마이그레이션하고, 평가한 뒤,
athanor 플러그인을 정리한다. 쓸모없는 에이전트는 제거한다.

## G-markers (locked at bootstrap)

- [x] G1 — ref 6개 플러그인 에이전트 전수 평가 매트릭스 산출
  - acceptance_criterion: MUST 모든 ref 에이전트군(ECC 259 / CE 46 / autoresearch 1 / gstack·superpowers 0 skill-based)을 athanor 채택 관점에서 평가한 매트릭스가 `docs/` 또는 session에 존재. 각 후보에 ADOPT/ADAPT/SKIP 판정 + 근거(athanor 고유 가치 충족? Thin Leader 호환? 11-agent 모델 적합? 기존 reviewer 6-lens와 중복?).
  - closed_by: C001
  - evidence_refs:

- [x] G2 — ADOPT 판정 에이전트 마이그레이션 (0개일 수 있음 — 명시적 결정)
  - acceptance_criterion: MUST G1에서 ADOPT된 각 에이전트가 `agents/`에 존재 + 최소 1개 skill dispatch 참조 + 회귀 테스트 green. ADOPT 0개로 결론나면 "no adoption justified" 결정을 decisions.md에 기록(이것도 유효한 완료).
  - closed_by: C002
  - evidence_refs:

- [x] G3 — athanor 11개 에이전트 dead/약참조 감사 + 정리
  - acceptance_criterion: MUST 모든 잔존 에이전트가 ≥1개 실제 dispatch 참조 보유(grep 검증). 제거 대상은 dispatch 참조 0(inventory-only 언급은 dispatch 아님) 확인 후 제거. CLAUDE.md Native Agent Inventory가 실제 agents/ 디렉토리와 정확히 일치.
  - closed_by: C002
  - evidence_refs:

- [x] G4 — 문서 정합 + release
  - acceptance_criterion: MUST CLAUDE.md 에이전트 인벤토리 + NOTICE.md 정합, 5-manifest 버전 bump, 전체 테스트 suite green.
  - closed_by: C003
  - evidence_refs:

## Cycle queue

| cycle | targets | status |
|---|---|---|
| C001 | G1 (평가 only, no ship) | pending |
| C002 | G2, G3 (마이그레이션 + 정리) | pending |
| C003 | G4 (문서 + release) | pending |

## Verify command
python3 -c "import pathlib,re,sys; agents={p.stem for p in pathlib.Path('agents').glob('*.md')}; claude=pathlib.Path('CLAUDE.md').read_text(); missing=[a for a in agents if a not in claude]; sys.exit(1 if missing else 0)"

## Test-count command
python3 -m pytest --collect-only -q tests/ 2>/dev/null | tail -1

## Stop conditions
- complete: G1-G4 전부 [x] + 각 closed_by:CNNN + validator-passed receipt
- invalid_cycle: receipt aggregate=invalid_steps_present 2 cycle 연속
- blocked: Tier 3 user abort
- max_iterations: cycle counter == 5

## Scope changes (append-only)

| id | proposed_by | timestamp | summary | status | decision |
|---|---|---|---|---|---|
