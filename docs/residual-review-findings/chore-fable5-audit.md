# Residual Review Findings — chore/fable5-audit

Source: `/athanor:review` 6-lens report on 043244c..b35965c (session 2026-06-11-001,
consolidated report in the session tree, gitignored — headline 0 critical / 4 high /
15 medium / 11 low, avg lens score 7.7/10). All 4 High findings plus 6 adjacent items
were fixed in commit 2f815de (`fix(review): apply review feedback`); this file records
what remains, per the LFG Step 5 durable-residual contract.

## Residual Review Findings

### Medium

1. **Walk-up depth `range(8)` duplicated as a magic literal** — architecture + quality, confidence 85 — `scripts/hooks/hook_state.py:118` (`_athanor_opt_in`), `:77` (`_project_dir`) vs `_WALK_UP_DEPTH = 8` at `scripts/hooks/_athanor_hook_runtime.py:36`. Recommendation: define/import one named constant; a future depth tune currently diverges the walkers silently.
2. **`_athanor_opt_in` omits the `$HOME` stop-bound its claimed mirror enforces** — architecture, confidence 70 — `scripts/hooks/hook_state.py:115-127` vs `_athanor_hook_runtime.py:189`. Recommendation: add the `$HOME` stop or enumerate the intentional differences in the docstring.
3. **Walk-up logic triplicated with subtly different stop conditions** — quality (cross-lens → architecture), confidence 80 — `_athanor_opt_in` / `_find_athanor_config_path` / `_project_dir`. Recommendation: architecture decision to extract one parametrized walk-up helper; the hijack-guard invariant is currently maintained in triplicate. Subsumes items 1–2 if taken.
4. **Canonical stop-phrase pattern lacks a pointer-presence assertion** — architecture, confidence 65 — `tests/test_regression_stop_phrase_canonical.py:13-16` locks non-re-embedding only; a skill could drop its pointer line and stay green. Recommendation: positive assert that each pointer-bearing skill contains `stop-phrase-whitelist`.
5. **Companion parity is mostly one-way token-pins** — architecture, confidence 60 — `tests/test_regression_codex_companion.py:69-80`; only the UNDETERMINED test re-derives from the parent. Recommendation: adopt the derivation-guard shape where a companion clause mirrors a parent clause; otherwise document the one-way pins.
6. **`resolve_project_root()` walked twice per PreToolUse when freeze active** — performance, confidence 90 — `scripts/hooks/pretool_dispatcher.py:86` and `:183`. Recommendation: resolve once in `main()`, thread down.
7. **`_athanor_opt_in` walk re-run ~4× per Stop event** — performance, confidence 85 — `hook_state.py:161` via `stop_verify_claims.py:863,1045,1125,1139`. Recommendation: memoize on the resolved root; pin call-count behavior when fixing (performance cross-lens → testing).
8. **`_command_segments` tokenizes the same command twice per Bash call** — performance, confidence 90 — `pretool_kernel_guard.py:106` and `:327`. Recommendation: compute segments once in the Bash branch, pass the list.
9. **`{"Read"} | set(_runtime.WRITE_TOOLS)` rebuilt per file-tool call** — performance, confidence 80 — `pretool_kernel_guard.py:495`. Recommendation: hoist `_CRED_GATE_TOOLS = frozenset(...)`.
10. **`_relativize_target` lacks absolute-`..` / symlink escape tests** — testing, confidence 55 — `scripts/hooks/freeze_guard.py:428-453` (lexical `relative_to`, no `resolve()`). Recommendation: add `{root}/sub/../../etc/x` → BLOCKED case; optionally a symlink-escape case.

### Low

1. **freeze.md still says 3 gated tools (now 4 with NotebookEdit)** — security, confidence 40 — `skills/work/references/freeze.md` L24-25; pre-existing recorded residual, not worse this round.
2. **`from tests._version import …` with no `tests/__init__.py`** — architecture, confidence 55 — import-mode fragile (works via conftest sys.path injection only).
3. **DESIGN.md verification one-liner reads as the gate** — architecture, confidence 50 — label the `python -c` snippet "(illustrative; the binding check is `tests/test_regression_agent_effort_level.py`)".
4. **One companion parity token is a long verbatim prose span** — testing, confidence 60 — `test_regression_codex_companion.py:312-339`; brittle though non-vacuous.
5. **Several companion doc-pin tokens anchor on prose** — testing, confidence 50 — `test_regression_codex_companion.py:118-127`; command-shape tokens carry the contract.
6. **`_athanor_opt_in` predicate naming (no `is_`/`has_` prefix)** — quality, confidence 60 — `hook_state.py:99`.
7. *(informational, no action)* `tests/test_regression_v011_8_deprecation_preamble.py`'s surviving 45-count asserts are the only copies — load-bearing, no redundancy (testing, confidence 70).
8. *(informational, no action)* `_relativize_target` per-target `Path` ops and `tests/_version.py` import-time read are bounded/test-only — acceptable at current scale (performance, confidence 70/60).

## Related work-session strategic residuals (out of review scope)

Recorded in the session work-log; deliberately deferred from the 41-subtask round-2 plan:

- **P22** CLAUDE.md diet below the 178-line cap (file sits exactly at the cap; every addition now requires a compensating trim).
- **P21/P26-class** retirement decision for the 7 reference-only agent docs (inline dispatch is canonical; docs remain as reference).
- **P12-class** `pretool_dispatcher` broad `except Exception` fail-open hardening (narrow the catch or add a stderr breadcrumb).
- **P1/P3/P4** strategic items from the 54-agent audit (lfg Workflow port, real-payload fixture corpus, kernel-guard parser upgrade) — see `analyze.md` in the session tree.
