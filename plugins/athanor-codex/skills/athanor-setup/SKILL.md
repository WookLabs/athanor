---
name: athanor-setup
description: Check Athanor Codex companion installation, marketplace visibility, config files, session directories, and unsupported Claude-only runtime features.
---

# Athanor Setup

Run a Codex-focused health check for the Athanor companion.

## Protocol

1. Check plugin packaging:
   - `plugins/athanor-codex/.codex-plugin/plugin.json`
   - `.agents/plugins/marketplace.json`
   - `codex plugin list`
2. Validate the Codex plugin with the local plugin validator when available:
   `python3 /home/wook/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/athanor-codex`
3. Check project state:
   - `athanor.json` exists or can be created by the Claude Athanor setup flow.
   - `.athanor/` session and lesson directories are present when used.
   - existing Claude `.claude-plugin/plugin.json` and `hooks/hooks.json` still
     exist.
4. Report unsupported Codex companion features honestly:
   - Claude `Stop` hook runtime gate;
   - Claude `PreToolUse` Kernel Guard and Freeze;
   - Claude `Task`-based worker dispatch.
5. End with concrete next steps: install marketplace, install plugin, run a
   smoke prompt, or fix the specific missing file.

## Output

Use a compact table with `PASS`, `WARN`, or `FAIL`, followed by exact commands
for any remediation.
