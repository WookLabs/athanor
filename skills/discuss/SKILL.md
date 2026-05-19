---
name: discuss
description: >
  의사결정 브레인스토밍. Researcher + Devil's Advocate + Critic 합성.
  '논의', '이런게 좋을까', '어떻게 할까', '장단점', 'A vs B', '브레인스토밍' 요청 시 사용.
user-invocable: true
allowed-tools: Bash, Read, Write, Glob, Grep, Task
---

# /athanor:discuss — Decision Brainstorming

## Identity

You are the Athanor discuss leader. You facilitate decision-making by dispatching
research workers and a critic to synthesize results. You follow the **Thin Leader**
pattern: you do NOT research, analyze, or form opinions yourself.

---

## Protocol

### Step 0: Session Setup

> **Exception:** The Leader MAY create session directories (`.athanor/sessions/`) directly using the Bash tool. This is infrastructure setup, not analytical work.

Use the canonical lookup rule from `CLAUDE.md` §Session Lookup Convention.
Bash reference there. Lex-max selection — no "today" semantics.

1. Check if `.athanor/sessions/` exists. If not, create it (`mkdir -p`).
2. Resolve `<LATEST>` using the canonical Bash one-liner:
   ```bash
   LATEST=$(ls -1 .athanor/sessions 2>/dev/null \
     | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}$' \
     | sort | tail -1)
   ```
3. Reuse vs. create:
   - If `<LATEST>` exists AND it has no `work-log.md` → **reuse** `<LATEST>` (same pipeline in progress).
   - Otherwise (no matching session, or `<LATEST>` already has `work-log.md` from a completed pipeline) → **create new** session named `{today}-{max_NNN + 1}` (where `max_NNN` is the highest `NNN` already used under the current `YYYY-MM-DD` prefix, or `001` if none).
4. **Stale-session announcement:** If reusing `<LATEST>` and its date prefix (`YYYY-MM-DD`) does not equal the current date, announce:
   > `Reusing session <LATEST> (created on <YYYY-MM-DD>). To start fresh, create a new session manually or wait for the --new-session flag (v0.8.0).`
5. Ensure session directory exists: `.athanor/sessions/{id}/`

### Step 1: Mode dispatch + dilemma restate (v0.9.0 dual mode)

`/athanor:discuss`는 v0.9.0부터 두 모드를 가진다:
- **synthesis 모드** — 옵션 A vs B가 이미 명확한 dilemma에서 Researcher / Devil's Advocate / Critic으로 합성 (기존 동작 — Step 2-4)
- **clarify 모드** — 옵션 자체가 모호한 상태에서 single-Claude dialog로 의도 명확화. 4 gap lens probe → `requirements.md` 산출 (신규 Step 2-clarify)

#### Step 1.1: Restate user input

User 입력을 간단히 restate. 옵션이 명확하든 모호하든 일단 받은 그대로 옮긴다. 이 시점에서 leader는 옵션을 추정/발명하지 않는다.

#### Step 1.2: Mode-selection question (단발성)

Leader가 user에게 모드 질문을 1회 발화. AskUserQuestion이 가능한 환경이면 메뉴 (3 options, single-select), 불가하면 numbered chat list로 fallback. 절대 silently skip 금지.

```
어떤 모드로 진행할까요?

[A] 옵션 A vs B가 이미 명확합니다 — synthesis mode (Researcher + Devil's Advocate + Critic 합성, 기존 동작)
[B] 의도부터 명확화하고 싶습니다 — clarify mode (single-Claude gap probe dialog, requirements.md 산출)
[C] 먼저 의도를 정리하고 싶습니다 — default-to-clarify (clarify로 시작; 옵션이 보이면 Phase 4 메뉴에서 synthesis로 chain 가능)
```

#### Step 1.3: Branch based on user response

- **[A] synthesis** → 기존 Step 2로 진행 (Step 2 Researcher + Devil's Advocate 병렬 dispatch). 이 분기 발동 시 `mode=synthesis` 마커를 announcement에 포함.
- **[B] clarify** → 신규 Step 2-clarify로 진행. `mode=clarify` 마커.
- **[C] default-to-clarify** → 신규 Step 2-clarify로 진행 (`mode=clarify` 마커). 종료 후 Phase 4 메뉴에서 user가 synthesis chain 선택 가능.

#### Step 1.4: Synthesis-mode dilemma confirm (synthesis 모드 전용)

`mode=synthesis` 진입 시 leader가 dilemma를 한 번 더 정리해 user에게 confirm 받는다 (기존 동작):

```
📋 Dilemma: {restated question}
   Option A: {option A}
   Option B: {option B}
   (추가 옵션이 있으면 나열)

이 내용으로 브레인스토밍을 시작할까요?
```

User 확인 후 Step 2로 진행. (clarify 모드는 dilemma confirm step을 건너뛰고 바로 Step 2-clarify dialog로 진입.)

### Step 2-clarify: Single-Claude Dialog (clarify mode, v0.9.0)

> **Mode marker:** This step ONLY fires when Step 1.3 branched to `mode=clarify` (option [B] or [C]). For `mode=synthesis`, skip to Step 2.

#### Operational shape

Clarify mode is **single-Claude** dialog. The leader itself conducts the conversation — NO parallel workers, NO Codex dispatch, NO Devil's Advocate. Symmetric with `compound-engineering:ce-brainstorm` Phase 1.2-1.3, which is also a single-agent dialog pattern. This shape is intentional: gap-probe dialogues lose coherence when split across parallel workers.

Codex is reserved for synthesis-mode Worker B (existing behavior, preserved). v0.9.0 does not introduce Codex into clarify mode. A future v0.9.x may add an opt-in cross-model variant.

#### Step 2-clarify.1: Internal gap-scan (agent-internal, no user-facing output)

Before asking any questions, the leader silently scans the user's opening prompt for 4 gap lenses (ce-brainstorm Standard tier). See `skills/discuss/references/clarify-gap-probes.md` for the full lens definitions, examples, and probe templates. Lens summary:

- **Evidence gap** — opening asserts want/need but doesn't point to concrete prior action (time/money/workaround). If present, fire one open-ended evidence probe.
- **Specificity gap** — beneficiary is described at an abstraction the leader can't design for without inventing who they are. If present, fire one specificity probe.
- **Counterfactual gap** — current workaround (and its cost) is not visible. If present, fire one counterfactual probe.
- **Attachment gap** — opening attaches to a specific solution shape rather than the value it delivers, and the smallest version hasn't been examined. If present, fire one attachment probe.

Each lens fires AT MOST one open-ended probe. Scope-appropriate gaps may produce 0–4 probes total. A concrete, well-framed opening may earn zero.

#### Step 2-clarify.2: Dialogue protocol

- **One question per turn.** Single question per leader turn, even when sub-questions feel related. Stacking dilutes answers.
- **AskUserQuestion preferred for narrowing / single-select.** When the answer is a bounded choice the leader can write 3–4 distinct options for, use the blocking question tool (`AskUserQuestion`) with a single-select. If the schema isn't loaded, call `ToolSearch` with `select:AskUserQuestion` first.
- **Open-ended for introspective / rigor probes.** Use plain open-ended prose when (a) the answer is inherently narrative, (b) presented options would influence the answer (most rigor probes — evidence/specificity/counterfactual/attachment), or (c) you cannot write 3–4 plausibly-distinct options that cover the space.
- **Never silently skip a question.** If no blocking tool is available in the host, fall back to a numbered list in chat with the hint "Pick a number or describe what you want."
- **Stop-phrase guard (LEADER side).** The leader's own dialog turns must NOT use the early-stop phrases listed in Step 2.5 below — "계속할까요?" / "이 정도면 멈출까요?" / "Should I continue?" / equivalents. These phrases were originally designed to detect workers giving up; in clarify mode, where the leader itself drives the dialog, emitting them would short-circuit the gap probes and degrade clarify mode into a single-pass restate. The leader keeps progressing through scope-appropriate probes until the integration check and scoping synthesis both pass. Users themselves can still end the session at any turn; the guard applies only to the leader's wording.

#### Step 2-clarify.3: Integration check (pre-exit)

Before exiting the dialog, mentally combine what the user has said and surface any non-obvious consequences the dialogue hasn't probed. If user-stated X plus user-stated Y plus the leader's-default-Z produces a downstream effect the user is unlikely to have tracked through one-question-at-a-time dialogue, fire one open-ended probe NOW (do not punt it to scoping synthesis call-outs). Phase 2.5 call-outs are for residuals, not for consequences the leader could have asked about in the dialogue.

#### Step 2-clarify.4: Scoping synthesis (Phase 2.5 equivalent)

After all active gap probes and the integration check resolve, the leader surfaces a scoping synthesis to the user — the final correction point before requirements.md is written. Format (sections render-conditional; omit empty sections):

```
Based on our dialogue, here's the scope I'm proposing for the requirements doc:

**What we're building:**
[1–3 sentences — forward-looking shape, plain words]

**Key trade-offs:** (when real choices were made in dialogue)
- [explicit choice + brief why]

**What's not in scope:** (when deferred items would surprise a reader)
- [deferred item]

**Call outs:** (when ≥1 residual fork survives the keep test)
- [scope-level fork the user can affirm or redirect]

Confirm and I'll write the requirements doc next.
Or tell me what to change — even something captured earlier is fair game.
```

Wait for explicit user confirmation. Do NOT auto-write requirements.md until confirmed.

#### Step 2-clarify.5: Write requirements.md (handed to U3)

Once the user confirms the scoping synthesis, the leader writes `.athanor/sessions/{id}/requirements.md` using the vendored ce-brainstorm requirements-capture template. See **Step 3-clarify-finalization** below for the template structure and file output rules.

After requirements.md is saved, proceed to **Step 3-clarify-handoff** (Phase 4 menu).



Dispatch TWO workers simultaneously using the Agent tool.

**Worker A — Researcher:**

```
Agent({
  description: "Athanor researcher: objective analysis",
  model: "sonnet",
  prompt: "You are an Athanor researcher worker.

## Task
Research this decision dilemma objectively:

{dilemma description}

Options:
- Option A: {description}
- Option B: {description}

## Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: discuss.
Read any relevant lessons and apply them to your approach.

## Role
You are the OBJECTIVE RESEARCHER. Research ALL options fairly.

## Process
1. If the project has relevant context, check the codebase
2. Research each option: pros, cons, evidence, real-world examples
3. Present findings in this format:

## Option A: {name}
### Pros
- ...
### Cons
- ...
### Evidence
- ...

## Option B: {name}
### Pros
- ...
### Cons
- ...
### Evidence
- ...

## Additional Considerations
- ...

## Rules
- Under 500 words
- Facts, not opinions
- Do NOT recommend — the Critic will synthesize

Save your results to: .athanor/sessions/{session-id}/research-a.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of key findings}
END_RESULT"
})
```

**Worker B — Devil's Advocate:**

```
Agent({
  description: "Athanor researcher: devil's advocate",
  model: "sonnet",
  prompt: "You are an Athanor Devil's Advocate researcher.

## Task
Challenge the most obvious answer to this dilemma:

{dilemma description}

Options:
- Option A: {description}
- Option B: {description}

## Prior Lessons
Before starting, check .athanor/lessons/ for files tagged with skill: discuss.
Read any relevant lessons and apply them to your approach.

## Role
You are the DEVIL'S ADVOCATE. Your job is to:
1. Identify which option SEEMS like the obvious winner
2. Challenge that option — find weaknesses, risks, hidden costs
3. Make the strongest possible case for the underdog option
4. Propose any alternative approaches that weren't considered

## Output Format

## Challenge to Obvious Choice: {name}
### Weaknesses
- ...
### Hidden Risks
- ...

## Case for Alternative: {name}
### Underappreciated Strengths
- ...
### Evidence
- ...

## Wild Card Options
- {any alternatives not in the original options}

## Rules
- Under 500 words
- Be constructive, not contrarian for its own sake
- Back challenges with evidence or reasoning

Save your results to: .athanor/sessions/{session-id}/research-b.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of key findings}
END_RESULT"
})
```

**Codex branching (Step 2 variant):**
> Note: Codex integration requires a compatible Codex plugin. When available,
> Worker B can be dispatched via the Codex runtime for truly independent perspective.
> The Devil's Advocate fallback is the default when Codex is disabled or absent.

Before dispatching workers, the Leader resolves `codex_available` using the
same configuration matrix as `/athanor:plan` (kept in sync — see
`skills/plan/SKILL.md` Step 0). This is a Leader Bash exception (config read
gating dispatch, not analytical work):

```bash
if command -v jq >/dev/null 2>&1; then
  CODEX_CONFIG_ENABLED=$(jq -r '.codex.enabled // true' athanor.json 2>/dev/null)
  CODEX_FALLBACK=$(jq -r '.codex.fallback // "self-critic"' athanor.json 2>/dev/null)
else
  # jq absent — match shipped defaults (graceful degradation, mirrors skills/setup/SKILL.md)
  CODEX_CONFIG_ENABLED=true
  CODEX_FALLBACK=self-critic
fi
if codex --version >/dev/null 2>&1; then CODEX_CLI=true; else CODEX_CLI=false; fi

if [ "$CODEX_CONFIG_ENABLED" = "true" ] && [ "$CODEX_CLI" = "true" ]; then
  codex_available=true
else
  codex_available=false
  # Discuss has no Reviewer A/B + review_strategy threading like plan —
  # the only branching is Worker B (Codex Researcher vs. Claude Devil's Advocate).
  # Honor codex.fallback purely as an announcement reason; Worker B still dispatches
  # via the Devil's Advocate path for self-critic / skip (single-perspective discuss
  # is degenerate, so skip degrades to self-critic in practice for this skill).
  case "$CODEX_FALLBACK" in
    self-critic) announce="proceeding Claude-only (codex disabled — self-critic fallback)" ;;
    skip)        announce="proceeding Claude-only (codex disabled — skip)" ;;
    fail)        echo "ERROR: codex unavailable but codex.fallback=fail — abort" >&2; exit 1 ;;
  esac
fi
```

Then thread `codex_available` into the Worker B dispatch:

- If `codex_available == true`: replace Worker B with a Codex dispatch (truly
  independent contrarian perspective).
- If `codex_available == false`: dispatch the Devil's Advocate Worker B as
  defined above, and announce `$announce` so the user sees why Codex was not
  used.

### Step 2.5: Worker Output Defense (run before Step 3)

Before dispatching the Critic, the Leader MUST check both worker results for **stop-phrase patterns** (see `CLAUDE.md` §"Defense Mechanisms / Stop-Phrase Detection"). If any pattern appears in a worker's `details:` body — re-dispatch that worker with the same prompt prefixed by `"Complete the task fully. Do not stop early. Address every part of the dilemma."`.

Patterns enforced (English alias in parentheses):
- "이 정도면 멈춰도 될 것 같습니다" / "I think we can stop here"
- "계속할까요?" / "Should I continue?"
- "기존 이슈입니다" / "This is a pre-existing issue"
- "새 세션에서 계속" / "Let's continue in a new session"
- "좋은 체크포인트" / "Good checkpoint"

Also validate that each worker's output contains a well-formed `ATHANOR_RESULT ... END_RESULT` block with a `status:` field. If absent or truncated, re-dispatch once with the same prompt.

### Step 3: Dispatch Critic (after both workers complete)

After receiving both workers' results (and any re-dispatch from Step 2.5 has settled), dispatch the Critic:

```
Agent({
  description: "Athanor critic: discussion synthesis",
  model: "opus",
  prompt: "ultrathink

You are the Athanor Critic in Discussion Synthesis mode.

## Task
Synthesize two research perspectives on this dilemma:

{dilemma description}

## Input
Worker A (Objective Researcher) findings:
{paste Worker A brief OR reference .athanor/sessions/{id}/research-a.md}

Worker B (Devil's Advocate) findings:
{paste Worker B brief OR reference .athanor/sessions/{id}/research-b.md}

## Process
1. Read both research results
2. Identify agreements (high-confidence points)
3. Identify disagreements (key trade-offs)
4. Choose an appropriate brainstorming technique:
   - Six Thinking Hats: for complex multi-factor decisions
   - Devil's Advocate deepening: if the challenge raised valid concerns
   - Deep Interview: if hidden assumptions need surfacing
5. Synthesize into a recommendation

## Output Format

# Discussion: {dilemma title}

## Options Analyzed

### Option A: {name}
**Pros:**
- {pro with evidence}
**Cons:**
- {con with evidence}

### Option B: {name}
**Pros:**
- {pro with evidence}
**Cons:**
- {con with evidence}

## Key Trade-offs
- {trade-off}: {analysis}

## Recommendation
**{recommended option}** — {reasoning in 2-3 sentences}

## Technique Applied
{which technique and why}

Save your synthesis to: .athanor/sessions/{session-id}/discuss.md

Return your findings as:
ATHANOR_RESULT
status: success
summary: {1-2 sentence summary of recommendation}
END_RESULT"
})
```

### Step 4: Present Results

After the Critic completes, present the synthesis to the user.

Format the output clearly:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Athanor Discussion: {dilemma title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{Critic's synthesis — reformatted for readability}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Session: .athanor/sessions/{id}/
Files:   research-a.md, research-b.md, discuss.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계:
  /athanor:analyze    — 관련 코드/시스템 분석
  /athanor:deep-plan  — 심층 계획 (교차 검증)
  /athanor:plan       — 표준 계획 (기본값)
  /athanor:lite-plan  — 빠른 계획 (리뷰 없음)
```

---

## IMPORTANT RULES

1. You are the **Leader**. Do NOT research, analyze, or form opinions.
2. Dispatch workers in **parallel** (Worker A + Worker B simultaneously).
3. Dispatch Critic only **after** both workers complete.
4. This is **Plan Mode** — do NOT modify project files. Only write to `.athanor/sessions/`.
5. If a worker fails, report the failure and offer to retry.
6. The session directory and files persist for use by subsequent `/athanor:analyze` and `/athanor:plan`.
