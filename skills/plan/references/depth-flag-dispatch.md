# Depth Flag Dispatch (v0.17.0 — active handler)

This file documents the **active** `--depth=<value>` + `--no-review`
flag-dispatch contract used by `skills/plan/SKILL.md` Step 1 §"Tier
Classification". S07 (Wave 2 of the v0.17.x refactor) collapsed the
former `/athanor:deep-plan` and `/athanor:lite-plan` skill slots into a
single `/athanor:plan` invocation. The current surface restores
`skills/deep-plan/SKILL.md` and `skills/lite-plan/SKILL.md` as thin wrapper
entrypoints that force the matching tier but still delegate here.

Provenance note: this file shipped as a `forward-compat stub` between S02
(Wave 1) and S07 (Wave 2). S07 promotes the stub to the live handler —
the contract below is no longer aspirational.

## Surface

`/athanor:plan` supports the following flags. Each binds at Step 1
before tier-keyword classification runs:

- `--depth=standard` (default if no flag and no trigger keyword match) —
  Standard tier: Claude plan + Codex review + Refinement Critic. Two to
  three dispatches total.
- `--depth=deep` — canonical flag form also used by the
  `/athanor:deep-plan` thin wrapper.
  Deep tier: Planner A (Claude) + Planner B (Codex) cross-planning +
  Reviewer A reviews B + Reviewer B reviews A + 4-input Synthesis
  Critic. Five dispatches total.
- `--depth=lite` — canonical flag form also used by the
  `/athanor:lite-plan` thin wrapper.
  Lite tier: Planner A (Claude) only; Steps 3 and 4 skipped; plan-a.md
  copied to plan.md. One dispatch.
- `--no-review` — orthogonal to `--depth`. Binds `review_strategy=none`
  so Step 3 is skipped and the Critic falls through to its
  review-skipped variant (deep tier 2-input synthesis, or standard tier
  pass-through with `<!-- athanor:review-skipped -->` prefix). Useful
  when the user wants the planner cross-model adversarial structure
  but does not want the Codex/Claude review round.

## Tier classification ordering

The Step 1 handler in `skills/plan/SKILL.md`:

1. **First** parses `--depth` from the invocation arguments. If present
   and the value is one of `standard | deep | lite`, the Leader binds
   `tier` directly and announces:

   ```
   Tier: <value> (--depth flag)
   ```

2. **Otherwise** falls back to the v0.16.x trigger-keyword heuristic:

   - Deep-tier muscle memory: "딥 플랜", "deep plan", "심층",
     "교차 모델 계획", "풀 플랜".
   - Lite-tier muscle memory: "라이트 플랜", "lite plan",
     "간단한 계획", "빠른", "quick plan".
   - Default when nothing matches: standard tier.

3. **Independently** parses `--no-review`. If present, binds
   `review_strategy=none` overriding the Codex availability matrix
   result from Step 0. The Step 3 / Step 4 dispatch table treats the
   tier × review_strategy=none combination as documented in
   `skills/plan/SKILL.md` §"Tier Dispatch Table".

Invalid values (`--depth=full`, `--depth=quick`, etc.) fall through to
the trigger-keyword heuristic — the Leader announces the fallback path
rather than erroring out, to preserve forward compatibility if new
synonyms accumulate.

## Backwards compatibility

- `/athanor:deep-plan` and `/athanor:lite-plan` are live thin wrappers again.
  They do not own separate protocols or artifacts; they bind `tier=deep` or
  `tier=lite` and then follow `skills/plan/SKILL.md`.
- Contradictory wrapper invocations fail loud: `/athanor:deep-plan
  --depth=lite` and `/athanor:lite-plan --depth=deep` stop before worker
  dispatch and tell the user to remove the flag or invoke `/athanor:plan
  --depth=<value>` directly.
- The canonical flag forms remain `/athanor:plan --depth=deep` and
  `/athanor:plan --depth=lite` (see `docs/v0.17.0-migration.md` for the
  historical flag-mapping table).
- Pre-S07 invocations without any `--depth=` argument continue to
  behave identically to v0.16.x: the trigger-keyword heuristic runs
  unchanged and the muscle-memory shorthand keeps working.
- The `description:` frontmatter in `skills/plan/SKILL.md` carries the
  deep-tier and lite-tier shorthand strings so Claude Code skill
  auto-discovery still surfaces `/athanor:plan` for "딥 플랜",
  "라이트 플랜", etc.

## Implementation anchor

- Step 1 handler: `skills/plan/SKILL.md` §"Tier Classification".
- Thin wrappers: `skills/deep-plan/SKILL.md`,
  `skills/lite-plan/SKILL.md`.
- Regression locks: `tests/test_regression_s07_depth_flag_collapse.py`
  (acceptance criteria), `tests/test_regression_s02_plan_skill_split.py`
  (forward-compat anchor — passes both before and after S07 because the
  three `--depth=*` substrings remain present here).
- Migration guide: `docs/v0.17.0-migration.md`.
