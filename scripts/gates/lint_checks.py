#!/usr/bin/env python3
"""
scripts/gates/lint_checks.py — frontmatter & manifest lint for Athanor.

Five guard functions extracted from v0.7.2 audit findings (2026-05). Each
guard is a (path -> (ok, violations|str)) primitive, designed to be wrapped
by pytest regression tests in `tests/test_regression_lint_checks.py` and
optionally by `/athanor:setup` checks.

Functions:
  marketplace_version_sync_check(plugin_json, marketplace_json)
    plugin.json.version == marketplace.json.plugins[0].version

  agent_descriptions_unique_check(agents_dir, prefix_len=60)
    All agent .md files under agents_dir must have frontmatter `description:`
    whose first `prefix_len` chars are unique across the directory. Closes
    the v0.6.2 Codex dispatch collision class.

  hook_events_known_check(hooks_json)
    Every top-level event key under "hooks" must be in the Claude Code
    whitelist. Catches typos like `Stoped`, `PreCommit`, etc.

  hook_items_well_formed_check(hooks_json)
    Each hook item's required field by `type`:
      command -> "command"
      prompt  -> "prompt"
      http    -> "url"
      mcp_tool -> "tool"
      agent   -> "agent" or "subagent"
    Missing required field per type is a violation.

  vendored_skill_provenance_check(skill_md)
    Vendored skills (those carrying upstream license) must include a
    `<!-- Provenance:` HTML comment within the first 60 lines of body.

CLI:
  python -m scripts.gates.lint_checks marketplace-sync <plugin> <marketplace>
  python -m scripts.gates.lint_checks agent-descriptions <agents_dir>
  python -m scripts.gates.lint_checks hook-events <hooks_json>
  python -m scripts.gates.lint_checks hook-items <hooks_json>
  python -m scripts.gates.lint_checks skill-provenance <skill_md>

Stdlib only. UTF-8 everywhere. Resilient to malformed inputs (returns
(False, [...]) — never raises).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Claude Code hook event whitelist (2026-05 spec).
KNOWN_HOOK_EVENTS = frozenset({
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "UserPromptExpansion",
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "PostToolUseFailure",
    "PreCompact",
    "Stop",
    "SubagentStop",
    "SubagentStart",
    "Notification",
    "PermissionRequest",
    "TeammateIdle",
    "TaskCreated",
    "TaskCompleted",
    "WorktreeCreate",
    "WorktreeRemove",
    "ConfigChange",
    "Elicitation",
    "ElicitationResult",
    "FileChanged",
    "InstructionsLoaded",
})

# Required field per hook item type.
HOOK_ITEM_REQUIRED_FIELD = {
    "command": "command",
    "prompt": "prompt",
    "http": "url",
    "mcp_tool": "tool",
    "agent": "agent",
}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_DESCRIPTION_RE = re.compile(r"^description:\s*(.+?)$", re.MULTILINE)


def _read_text(path: Path) -> tuple[str | None, str | None]:
    """Return (text, error). Either text is set or error is set."""
    if not path.is_file():
        return None, f"{path} not found"
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, f"{path} read error: {exc}"


def _read_json(path: Path) -> tuple[dict | list | None, str | None]:
    """Return (data, error). Either data is set or error is set."""
    text, err = _read_text(path)
    if err is not None or text is None:
        return None, err or f"{path} read returned no text"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"{path} is not valid JSON: {exc}"


def _extract_description(md_text: str) -> str | None:
    """Pull `description:` line from frontmatter. Strips YAML block scalar `>`."""
    fm_match = _FRONTMATTER_RE.match(md_text)
    if not fm_match:
        return None
    fm = fm_match.group(1)
    desc_match = _DESCRIPTION_RE.search(fm)
    if not desc_match:
        return None
    desc = desc_match.group(1).strip()
    if desc == ">":
        # Block scalar — concatenate following indented lines until next key.
        lines = fm.splitlines()
        try:
            i = next(idx for idx, ln in enumerate(lines) if ln.startswith("description:"))
        except StopIteration:
            return None
        body: list[str] = []
        for ln in lines[i + 1:]:
            if not ln.startswith((" ", "\t")):
                break
            body.append(ln.strip())
        desc = " ".join(body)
    return desc


# ---------------------------------------------------------------------------
# Guard 1: marketplace.json plugins[0].version sync
# ---------------------------------------------------------------------------
def marketplace_version_sync_check(
    plugin_json_path: Path, marketplace_json_path: Path
) -> tuple[bool, str]:
    """plugin.json.version must equal marketplace.json.plugins[0].version."""
    plugin, err = _read_json(plugin_json_path)
    if err:
        return False, f"marketplace-version-sync violation: {err}"
    marketplace, err = _read_json(marketplace_json_path)
    if err:
        return False, f"marketplace-version-sync violation: {err}"

    if not isinstance(plugin, dict):
        return False, f"marketplace-version-sync violation: {plugin_json_path} is not a JSON object"
    if not isinstance(marketplace, dict):
        return False, f"marketplace-version-sync violation: {marketplace_json_path} is not a JSON object"

    plugin_version = plugin.get("version")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        return False, "marketplace-version-sync violation: marketplace.json missing plugins[]"
    market_version = plugins[0].get("version") if isinstance(plugins[0], dict) else None

    if plugin_version != market_version:
        return False, (
            "marketplace-version-sync violation: "
            f"plugin.json.version={plugin_version!r} != "
            f"marketplace.json.plugins[0].version={market_version!r}"
        )
    return True, f"marketplace-version-sync ok: {plugin_version}"


# ---------------------------------------------------------------------------
# Guard 2: agent description unique prefix
# ---------------------------------------------------------------------------
def agent_descriptions_unique_check(
    agents_dir: Path, prefix_len: int = 60
) -> tuple[bool, list[str]]:
    """All agent .md files must have unique description[:prefix_len]."""
    if not agents_dir.is_dir():
        return False, [f"agent-descriptions violation: {agents_dir} not a directory"]

    seen: dict[str, str] = {}  # prefix -> first agent file path
    violations: list[str] = []
    files = sorted(p for p in agents_dir.glob("*.md") if p.is_file())
    for f in files:
        text, err = _read_text(f)
        if err is not None or text is None:
            violations.append(f"agent-descriptions violation: {err or f'{f} read returned no text'}")
            continue
        desc = _extract_description(text)
        if desc is None:
            violations.append(
                f"agent-descriptions violation: {f.name} missing description in frontmatter"
            )
            continue
        prefix = desc[:prefix_len].strip().lower()
        if prefix in seen:
            violations.append(
                f"agent-descriptions violation: {f.name} description prefix collides with "
                f"{seen[prefix]} (first {prefix_len} chars: {desc[:prefix_len]!r})"
            )
        else:
            seen[prefix] = f.name
    return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Guard 3: hook event keys are known
# ---------------------------------------------------------------------------
def hook_events_known_check(hooks_json_path: Path) -> tuple[bool, list[str]]:
    """Every top-level event key under `hooks` must be in KNOWN_HOOK_EVENTS."""
    data, err = _read_json(hooks_json_path)
    if err:
        return False, [f"hook-events-known violation: {err}"]
    if not isinstance(data, dict):
        return False, [f"hook-events-known violation: {hooks_json_path} root is not an object"]

    hooks_raw = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks_raw, dict):
        return True, []  # no hooks block — out of scope here
    hooks: dict = hooks_raw

    violations: list[str] = []
    for event in hooks:
        if not isinstance(event, str) or event not in KNOWN_HOOK_EVENTS:
            violations.append(
                f"hook-events-known violation: {hooks_json_path} registers "
                f"unknown event {event!r} (not in Claude Code whitelist)"
            )
    return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Guard 4: hook items have required fields per type
# ---------------------------------------------------------------------------
def hook_items_well_formed_check(hooks_json_path: Path) -> tuple[bool, list[str]]:
    """Each hookItem must carry the required field for its `type`."""
    data, err = _read_json(hooks_json_path)
    if err:
        return False, [f"hook-items-well-formed violation: {err}"]
    if not isinstance(data, dict):
        return False, [
            f"hook-items-well-formed violation: {hooks_json_path} root is not an object"
        ]

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return True, []

    violations: list[str] = []
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            continue
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            inner = entry.get("hooks", [])
            if not isinstance(inner, list):
                continue
            for j, item in enumerate(inner):
                if not isinstance(item, dict):
                    continue
                t = item.get("type")
                if not isinstance(t, str):
                    violations.append(
                        f"hook-items-well-formed violation: {hooks_json_path} "
                        f"event={event!r} entry={i} item={j} type field missing or non-string"
                    )
                    continue
                req = HOOK_ITEM_REQUIRED_FIELD.get(t)
                if req is None:
                    violations.append(
                        f"hook-items-well-formed violation: {hooks_json_path} "
                        f"event={event!r} entry={i} item={j} unknown type={t!r}"
                    )
                    continue
                if req not in item or not item[req]:
                    violations.append(
                        f"hook-items-well-formed violation: {hooks_json_path} "
                        f"event={event!r} entry={i} item={j} type={t!r} missing required field {req!r}"
                    )
    return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Guard 5: vendored skill carries Provenance comment
# ---------------------------------------------------------------------------
def vendored_skill_provenance_check(skill_md_path: Path) -> tuple[bool, str]:
    """Vendored skill body must include `<!-- Provenance:` within first 60 lines after frontmatter."""
    text, err = _read_text(skill_md_path)
    if err is not None or text is None:
        return False, f"vendored-skill-provenance violation: {err or f'{skill_md_path} read returned no text'}"
    assert text is not None  # narrow for type checker after the guard above

    fm_match = _FRONTMATTER_RE.match(text)
    body_start = fm_match.end() if fm_match else 0
    body = text[body_start:]
    head = "\n".join(body.splitlines()[:60])
    if "<!-- Provenance:" not in head:
        return False, (
            f"vendored-skill-provenance violation: {skill_md_path} missing "
            "`<!-- Provenance:` block in first 60 lines of body"
        )
    return True, f"vendored-skill-provenance ok: {skill_md_path.name}"


# ---------------------------------------------------------------------------
# CLI dispatcher
# ---------------------------------------------------------------------------
def _cmd_marketplace_sync(args: argparse.Namespace) -> int:
    ok, msg = marketplace_version_sync_check(Path(args.plugin), Path(args.marketplace))
    print(msg)
    return 0 if ok else 1


def _cmd_agent_descriptions(args: argparse.Namespace) -> int:
    ok, violations = agent_descriptions_unique_check(Path(args.agents_dir))
    if ok:
        print(f"agent-descriptions ok ({len(list(Path(args.agents_dir).glob('*.md')))} files)")
        return 0
    for line in violations:
        print(line)
    return 1


def _cmd_hook_events(args: argparse.Namespace) -> int:
    ok, violations = hook_events_known_check(Path(args.hooks_json))
    if ok:
        print("hook-events-known ok")
        return 0
    for line in violations:
        print(line)
    return 1


def _cmd_hook_items(args: argparse.Namespace) -> int:
    ok, violations = hook_items_well_formed_check(Path(args.hooks_json))
    if ok:
        print("hook-items-well-formed ok")
        return 0
    for line in violations:
        print(line)
    return 1


def _cmd_skill_provenance(args: argparse.Namespace) -> int:
    ok, msg = vendored_skill_provenance_check(Path(args.skill_md))
    print(msg)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.gates.lint_checks",
        description="Athanor frontmatter & manifest lint guards",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("marketplace-sync", help="plugin.json/marketplace.json version sync")
    p.add_argument("plugin")
    p.add_argument("marketplace")
    p.set_defaults(func=_cmd_marketplace_sync)

    p = sub.add_parser("agent-descriptions", help="agents/*.md description prefix uniqueness")
    p.add_argument("agents_dir")
    p.set_defaults(func=_cmd_agent_descriptions)

    p = sub.add_parser("hook-events", help="hooks.json event keys against whitelist")
    p.add_argument("hooks_json")
    p.set_defaults(func=_cmd_hook_events)

    p = sub.add_parser("hook-items", help="hooks.json item type/field consistency")
    p.add_argument("hooks_json")
    p.set_defaults(func=_cmd_hook_items)

    p = sub.add_parser("skill-provenance", help="vendored SKILL.md Provenance presence")
    p.add_argument("skill_md")
    p.set_defaults(func=_cmd_skill_provenance)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
