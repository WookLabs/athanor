# Residual Review Findings — chore/fable5-audit-r3

Source: `/athanor:review` 6-lens report on a5b1038..b623c59 (session 2026-06-12-001,
consolidated report in the session tree, gitignored — headline 0 critical / 1 high /
13 medium / 11 low post-dedup, avg lens score 8.2/10). The High plus 6 high-confidence
accuracy/test-gap findings were fixed in commit b623c59 (`fix(review): apply review
feedback`); this file records what remains, per the LFG Step 5 durable-residual
contract.

Lineage note: this branch itself resolved all 8 round-2 residual Mediums recorded in
`chore-fable5-audit.md` (walk-up dedup/constant/$HOME-stop → P1; double-resolve,
opt-in re-walk, double-tokenize → P2; pointer-presence assertion → P3 M4; companion
pin directionality → P4 M5).

## Residual Review Findings

### Medium

1. **M2 `$HOME` stop is env-influenceable — `$HOME` manipulation can suppress state-dir creation** — security, confidence 55 — `scripts/hooks/hook_state.py:117-139`. Documented fail-open disposition, no weaker than the existing `hooks.profile:"off"` opt-out; net tightening. Recommendation: optionally note in `hook_state.py` that `$HOME` participates in the opt-in ceiling.
2. **Dispatcher traceback-to-stderr can surface file paths into CI logs on the fail-open path** — security, confidence 50 — `scripts/hooks/pretool_dispatcher.py:215-217`. `format_exc()` dumps no frame locals; paths already appear in existing BLOCKED messages. Recommendation: acceptable per the P12 fail-loud rationale; cap to `type(exc).__name__` + `repr(exc)` only if log hygiene becomes a requirement.
3. **P1 memoization and P2 root-threading partially redundant mechanisms for the same goal** — architecture, confidence 70 — `pretool_dispatcher.py:181` + `_athanor_hook_runtime.py:171`. Threading is the actual consistency guarantee; the memo's in-process value is test-side. Recommendation: one comment at `main()` naming the load-bearing mechanism, or fold the memo (see item 5) — a design decision, not a defect.
4. **Module-level `lru_cache` test isolation rests on manual `cache_clear()` discipline** — architecture + performance, confidence 72 — `tests/conftest.py` (absence); 5 manual call sites in `tests/test_regression_v0188_walkup_unification.py`. Recommendation: autouse fixture calling `resolve_project_root.cache_clear()` around each test.
5. **`lru_cache` on `resolve_project_root` is dead on the production hot path (zero hits)** — performance, confidence 80 — `_athanor_hook_runtime.py:171-218`. Hooks are one-shot processes; the dispatcher resolves once and threads; the Stop path never calls it. The misleading docstring was already corrected in b623c59. Recommendation: either delete the memo (P2 threading is the real win) or route the Stop path through it so it earns hits.
6. **Cache key (`os.environ["HOME"]`) and walk ceiling (`Path.home()`) derive home independently** — architecture + performance, confidence 70 — `_athanor_hook_runtime.py:213` vs `:148`. Key under-identifies the walk when `$HOME` is unset; plus one redundant `Path.home()` syscall per miss. Recommendation: key on `str(Path.home())` or pass the known home into `_walk_up`.
7. **`resolve_project_root.cache_clear` is a monkey-patched function attribute** — architecture, confidence 55 — `_athanor_hook_runtime.py:218` (`# type: ignore[attr-defined]`). Recommendation: named `reset_project_root_cache()` helper or decorate the public function so `cache_clear` is native.

### Low

1. **Symlink freeze-escape xfail is non-strict** — security, confidence 40 — `tests/test_regression_v018_freeze_guard.py:860-863`. Consider `strict=True` so closing the escape trips loudly (the lexical-only companion guard already covers the transition).
2. **`WalkResult.stopped_at_home` has zero consumers** — architecture, confidence 65 — `_athanor_hook_runtime.py:108-110`. Keep for contract symmetry; add a one-line "no caller branches on this yet" note.
3. **`del project_root  # reserved for future use` in `evaluate_payload`** — architecture (+ security/documentation cross-lens), confidence 50 — `pretool_kernel_guard.py:528`. Wire it or drop it; a reserved-but-deleted param is a promise with no enforcement.
4. **`_walk_up(marker_check=None)` `TypeError` branch untested (`# pragma: no cover`)** — testing, confidence 80 — `_athanor_hook_runtime.py:147-148`. Optional one-line `pytest.raises(TypeError)` lock.
5. **M8 parity tests assert passthrough-contract only; mis-wiring is caught by the subprocess suite** — testing, confidence 70 — `tests/test_regression_v016_pretool_kernel_guard.py:623-665`. Recorded decision; no change required.
6. **`marker_check` required-but-typed-optional** — quality, confidence 70 — `_athanor_hook_runtime.py:114-115,139-140`. Deliberate trade; nit.
7. **P12 decision comment mildly editorializing** — quality, confidence 45 — `pretool_dispatcher.py:194-202`. Keep; optionally shorten the "§Core Principle" sentence.
8. **`segments is None` self-compute seam repeated across 3 checkers** — quality, confidence 60 — `pretool_kernel_guard.py:117-118,384-385,412-414`. Justified back-compat duplication, parity-pinned; leave as-is.
9. **CHANGELOG "+14 verdict-parity tests" doesn't name the two-file split** — documentation, confidence 40 — count verified correct (8 dispatcher + 6 kernel-guard); optional parenthetical.

### Positive notes (no action)

- freeze.md `NotebookEdit` listing and the archive relocation track the code exactly (architecture, confidence 80).
- Walkup test file carries exactly the claimed 13 invariant tests; lesson `2026-06-11-008` ↔ CHANGELOG net-zero-budget framing coherent.
