# Athanor Codex

Codex-native companion skills for Athanor. This plugin carries the practical
workflow parts of Athanor into Codex while keeping Claude Code runtime features
separate.

## Install

From this repository:

```bash
codex plugin marketplace add <path-to-athanor>/.agents/plugins/marketplace.json
codex plugin add athanor-codex@athanor
```

The selector is `athanor-codex@athanor`.

## Update During Local Development

After changing plugin files, refresh the Codex cache version and reinstall:

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py <path-to-athanor>/plugins/athanor-codex
codex plugin add athanor-codex@athanor
```

Start a new Codex thread after reinstalling so the updated skill list and
skill bodies are loaded.

## Skills

- `athanor-analyze` — analyze codebase surface before planning.
- `athanor-assess` — score a target against a goal with weighted dimensions.
- `athanor-prompt-gen` — refine vague requests into prompts and recommend the next skill.
- `athanor-discuss` — clarify intent or synthesize a decision.
- `athanor-plan` — produce a decision-complete implementation plan.
- `athanor-deep-plan` — thin wrapper for `athanor-plan --depth=deep`.
- `athanor-lite-plan` — thin wrapper for `athanor-plan --depth=lite`.
- `athanor-work` — execute an accepted plan with verification discipline.
- `athanor-lfg` — run the end-to-end plan/work/review/PR/CI pipeline.
- `athanor-lfg-loop` — iterate LFG cycles against a durable goal ledger.
- `athanor-release` — run release ceremony steps and release-ready checks.
- `athanor-ci-watch` — monitor GitHub Actions, fix concrete failures, and retry.
- `athanor-review` — review changes across practical quality lenses.
- `athanor-debug` — diagnose failures before fixing.
- `athanor-scope-drift` — compare diff against stated plan or intent.
- `athanor-verify` — verify material completion claims before final response.
- `athanor-setup` — check install, marketplace, config, and runtime boundaries.

## Runtime Boundaries

This is not a Claude runtime port. Codex does not receive Athanor's
hidden hook enforcement, Claude PreToolUse Kernel Guard, Freeze enforcement, or
Claude Task worker dispatch from this companion. Skills should state those
limits instead of claiming hook-backed enforcement.

The manual mirror source of truth is
`docs/codex-mirror-source-map.md`. After changing a Claude skill, Codex skill,
or registered agent mirror, run:

```bash
python scripts/gates/codex_mirror_parity.py --json
```
