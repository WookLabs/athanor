# Residual Review Findings — feat/output-language-ko

Source: 5-lens review (security, architecture, testing, quality, documentation;
performance skipped — no runtime source) of 3bfbfcc..HEAD, session
2026-06-12-002. Totals: Critical 0 / High 2 / Medium 12 / Low 6. The 2 High
and 9 polish Mediums were fixed in review-fix round 1
(`fix(review): apply review feedback`). The findings below were deliberately
deferred — they remain open and unblocking.

## Residual Review Findings

1. **[Medium · architecture, quality · confidence 60] Directive wording drift
   across the 9 native skills — no shared canonical directive sentence.**
   - Where: the 9 `output.language` directive inserts (e.g.
     `skills/analyze/SKILL.md` "follows the **resolved** output.language" vs
     `skills/review/SKILL.md` "follows the **interpreted** output.language" vs
     Korean-led phrasing in `skills/work|lfg|lfg-goal|setup/SKILL.md`).
   - Why deferred: rewording all 9 inserts is broad surface churn (line caps,
     tone-smoke corpus, pinned counts) for a consistency gain; the regression
     lock was instead strengthened to pin the canonical-pointer substring in
     all 8 non-setup skills, which guards the load-bearing part.
   - Recommendation: if revisited, hoist a one-line canonical directive
     sentence into `skills/setup/SKILL.md` §"output.language 해석 (canonical)"
     and have the 9 skills cite it — mirroring the jq-snippet pointer
     discipline. Normalize the 3 citation styles in the same pass.

2. **[Low · security · confidence 60] Setup jq snippet lacks the
   `command -v jq` guard its sibling snippets carry.**
   - Where: `skills/setup/SKILL.md` §"output.language 해석 (canonical)"
     (`OUTPUT_LANG=$(jq -r ... 2>/dev/null)`).
   - Why deferred: behavior is already fail-closed — with jq absent the
     command substitution yields an empty string and the `case` allowlist
     collapses it to `en`. The guard would be parity polish, not a defect fix
     (explicitly judged "resilient, not a vuln" by the security lens).
   - Recommendation: mirror the `command -v jq` guard used by
     `skills/plan/references/codex-availability.md` if the snippet is touched
     again.

3. **[Low · testing · confidence 60] Schema enum negative control asserts on
   jsonschema error-message substrings.**
   - Where: `tests/test_regression_schema_validates_config.py` (the
     reject-`"both"` test's `"both" in msg or "enum" in msg or "language" in
     msg`).
   - Why deferred: the three-way OR already hedges against message rewording,
     and the adjacent unknown-key test correctly asserts only the exception
     type; risk is low.
   - Recommendation: switch the assertion to
     `excinfo.value.validator == "enum"` for version-stable intent if the
     test is next edited.
