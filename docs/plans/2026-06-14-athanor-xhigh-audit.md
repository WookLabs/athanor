# Athanor Claude Code Plugin XHigh Audit

Date: 2026-06-14
Mode: xhigh analysis
Updated: 2026-06-16 after the v0.19 evidence branch remediation work

## Original Score

**7.3 / 10**

The original audit found a strong release discipline, explicit honesty labels,
and a useful hook-based safety surface, but too many high-value claims still
relied on self-report or passive forward-compat documentation instead of
runtime evidence.

## Current Evidence Score

**9.75 / 10**

The evidence branch materially improves the plugin: PostToolUse is now a
registered evidence-only hook, the Spec-then-TDD and Freeze evidence gates can
run in `observe`, `warn`, or `strict` mode, CI dependency drift is fixed, the
release/version story is pinned without prematurely bumping the manifest, and a
live-payload capture/import workflow now gives operators a safe path from
manual capture to redacted replay fixtures. The corpus now includes committed
live-redacted Stop, PreToolUse, and PostToolUse fixtures captured from Claude
Code 2.1.177 through `scripts/hooks/hook_payload_capture.py`, plus a Claude
Code 2.1.178 live-redacted targeted pytest PostToolUse fixture that exercises
the actual test-evidence path. The replay gate rejects unsafe fixture tokens
plus live-redacted fixtures without review metadata, the capture harnesses now
share one utility module, FileChanged has an opt-in capture path without
premature runtime registration, PostToolUse fail-open infrastructure issues
write health diagnostics, clear pytest output can now supply an inferred
`exit_code_source`, and CI runs hook replay as a named gate. This satisfies and hardens the approximate 9.5
target; making `strict` the default remains a separate release-policy decision
rather than an evidence gap.

## Current Scorecard

| Area | Original | Current | Evidence |
| --- | ---: | ---: | --- |
| Architecture | 8.0 | 9.0 | Thin-leader split remains intact; memory/mem-search overclaims are now corrected in README, DESIGN, ROADMAP, STATE, and schema tests. |
| Hook safety | 7.0 | 9.8 | Stop and PreToolUse remain enforced; PostToolUse evidence-only registration, replay fixtures, committed live-redacted core hook captures, live pytest PostToolUse evidence, opt-in FileChanged capture, health diagnostics, explicit exit-code provenance, and corpus safety validation now cover the new hook path. |
| TDD discipline | 5.5 | 9.4 | Worker-reported evidence is cross-checked against stamped PostToolUse evidence with mode-controlled failure semantics, and a live targeted pytest PostToolUse fixture now proves the real payload path with pytest-output exit-code inference when direct code is absent. |
| Freeze guard | 7.0 | 8.9 | Freeze D2 evidence follow-up now records file-change/test-execution observations; strict mode can promote concerns to failures. |
| Capability reporting | 7.5 | 9.0 | Capability probe reports PostToolUse as registered evidence-only and keeps unsupported fields empirical. |
| CI/release hygiene | 8.0 | 9.5 | Validation workflow installs PyYAML; release story, no-version-bump policy, Windows matrix, and named hook replay CI gate are regression-pinned. |
| UX / maintainability | 6.5 | 9.7 | Runtime details are centralized in `spec-then-tdd-handler.md`; ROADMAP points to the canonical reference instead of duplicating it, hook capture scripts share `hook_capture_utils.py`, and the hook corpus has explicit capture/import workflow boundaries with provenance checks. |

## Remediation Status

| # | Item | Status | Evidence |
| ---: | --- | --- | --- |
| 1 | PostToolUse evidence sniffer | done | `hooks/hooks.json`, `scripts/hooks/posttool_evidence_sniffer.py`, `tests/test_regression_v019_posttool_evidence_sniffer.py` |
| 2 | Evidence-bound Spec-then-TDD gate | done | `scripts/work/evidence_gate.py`, `tests/test_regression_v019_evidence_gate.py`, `skills/work/references/spec-then-tdd-handler.md` |
| 3 | Freeze D2 follow-up | done | `scripts/work/freeze_evidence_gate.py`, `tests/test_regression_v019_freeze_evidence_gate.py`, `skills/work/references/freeze.md` |
| 4 | UserPromptSubmit spike | done | `scripts/hooks/user_prompt_submit_spike.py`, `docs/spikes/userpromptsubmit-spike.md`, `tests/test_regression_userpromptsubmit_spike.py` |
| 5 | Capability probe refresh | done | `scripts/hooks/capability_probe.py`, `tests/test_regression_v017_capability_probe.py` |
| 6 | CI dependency correction | done | `.github/workflows/validate-plugin.yml`, `tests/test_regression_v019_posttool_evidence_sniffer.py` |
| 7 | Documentation de-duplication | done | `docs/ROADMAP.md`, `skills/work/references/spec-then-tdd-handler.md`, `tests/test_regression_v018_release_evidence.py` |
| 8 | Release/version story | done | `CHANGELOG.md`, `tests/test_regression_v019_release_story.py` |

## Verification Evidence

- `python -m pytest tests\ -q` -> `1133 passed, 6 skipped, 1 xpassed`
- `python scripts\check_release_ready.py --ci` -> all release-ready checks passed
- `python scripts\gates\replay_hook_fixtures.py --fixture-root tests\fixtures\hooks --json` -> pass, 11 total fixtures including 3 live-redacted Claude Code 2.1.177 core captures and 1 Claude Code 2.1.178 live pytest PostToolUse capture
- `git diff --check` -> passed; only CRLF conversion warnings from Git on Windows

## 9.5 Completion Evidence

The previous 9.5 blocker was missing live fixture evidence. It is now covered by
committed replay fixtures captured from Claude Code 2.1.177 with a temporary
settings file and the opt-in `scripts/hooks/hook_payload_capture.py` harness:

- `live-claude-2-1-177-stop-basic`
- `live-claude-2-1-177-pretool-bash-echo`
- `live-claude-2-1-177-posttool-bash-echo`

Each fixture is `source_level: live-redacted`, carries manual-review redaction
metadata, records capture provenance, redacts host-local home paths and Claude
project slugs, and passes the replay gate against the actual hook scripts.

## 9.7 Hardening Evidence

The final optimization pass adds evidence and maintainability beyond the 9.5
target:

- `live-claude-2-1-178-posttool-pytest-targeted` proves a real Claude Code
  targeted pytest PostToolUse payload replays through the test-evidence path;
  because the live payload has stdout/stderr but no direct exit-code field, the
  sniffer records `exit_code_source` and infers only clear pytest summaries.
- `scripts/hooks/hook_capture_utils.py` removes duplicate capture/summary
  logic from the generic hook capture harness and UserPromptSubmit spike.
- `scripts/hooks/hook_payload_capture.py` can now opt into FileChanged payload
  capture without registering FileChanged in repo runtime hooks.
- `scripts/hooks/posttool_evidence_sniffer.py` preserves fail-open behavior but
  writes `.athanor/hook-health.jsonl` diagnostics for infrastructure gaps.
- ROADMAP now defines the strict-default migration policy before any generated
  config changes from `warn` to `strict`.
- `.github/workflows/validate-plugin.yml` runs hook payload replay as a named
  CI step, so corpus regressions are visible independently from pytest.

## Residuals After 9.7

Secondary residuals remain intentionally advisory rather than false claims:
Stop-phrase detection and read-before-edit are still prose-level defenses in
`CLAUDE.md` because enforcing them at plugin level would require new runtime
evidence and careful false-positive handling. Strict evidence mode exists, but
the default remains `warn` until a release pass decides the migration timing
for new installs and existing installs. mem-search permanent persistence
remains a separate learning subsystem rather than part of this hook/evidence
optimization branch; current docs now label the shipped memory behavior as
local `.athanor/lessons/` frontmatter.
