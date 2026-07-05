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

  skill_line_number_ref_check(skills_dir)
    Detects rotting deep-prose `line NNN` references in skills/**/*.md.
    Pure-relocation safety brake: when prose moves, line-number anchors
    rot silently; this guard surfaces the rot at lint time.

  skill_size_cap_check(skills_dir)
    Advisory size ratchet — prevents regrowth beyond the measured baseline
    + 5% headroom per skill. Does NOT enforce shrink (the diet itself is
    delivered by relocation + verified by char-count ACs). To lower a cap
    a future release must relocate the load-bearing prose AND retarget the
    cap constant in the same change.

CLI:
  python -m scripts.gates.lint_checks marketplace-sync <plugin> <marketplace>
  python -m scripts.gates.lint_checks agent-descriptions <agents_dir>
  python -m scripts.gates.lint_checks hook-events <hooks_json>
  python -m scripts.gates.lint_checks hook-items <hooks_json>
  python -m scripts.gates.lint_checks skill-provenance <skill_md>
  python -m scripts.gates.lint_checks skill-line-refs <skills_dir>
  python -m scripts.gates.lint_checks skill-size-cap <skills_dir>

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
# Guard 6: skill line-number reference rot (D3 — session 2026-07-03-004)
# ---------------------------------------------------------------------------
# Regex (match = violation), corrected from both planners per §D3:
# Bare "line NNN" / "~line NNN" / "(line NNN)" / "/ line NNN" in prose —
# the 4 known rots include a slash-form ("/ line 559:") that the
# parenthetical-only regex both planners proposed WOULD NOT catch.
# Discriminate legit single-digit refs ("line 1 of file", "sentinel on
# line 1") from rotting deep-prose refs by REQUIRING 2+ digits. The
# `\d{2,5}` threshold is the clean discriminator: deep-prose refs use 3
# digits; response-line refs use 1.
_LINE_REF_RE = re.compile(
    r'(?<!\w)(?:[/(]\s*|/~\s*|\s)~?\s*lines?\s+\d{2,5}\b',
    re.IGNORECASE,
)

# Fenced code block markers — content between them is an allowlist zone
# (code comments legitimately cite source lines).
_FENCE_RE = re.compile(r'^[ \t]*```', re.MULTILINE)


def _skill_line_refs_in_text(body: str) -> list[str]:
    """Return one violation string per `line NNN`-style ref OUTSIDE fenced blocks.

    Splits the body on ``` fence markers; odd-indexed chunks are inside code
    blocks (allowed), even-indexed chunks are prose (linted). Within each
    prose chunk, every `_LINE_REF_RE` match becomes a violation entry
    carrying the matched text so the operator can locate the rot.
    """
    # Split on fence lines, preserving which halves are "outside" (prose).
    parts = _FENCE_RE.split(body)
    violations: list[str] = []
    for i, chunk in enumerate(parts):
        if i % 2 == 1:
            continue  # inside a fenced code block — allowlist zone
        for m in _LINE_REF_RE.finditer(chunk):
            violations.append(
                f"skill-line-number-ref violation: rotting deep-prose reference "
                f"{m.group(0)!r} -- rewrite as `(Section <heading-name>)` "
                f"(line numbers rot when prose relocates)"
            )
    return violations


def skill_line_number_ref_check(skills_dir: Path) -> tuple[bool, list[str]]:
    """Detect rotting `line NNN` references in `skills_dir/**/SKILL.md` prose.

    Scope: every `*.md` file under `skills_dir` (covers `SKILL.md` plus
    `references/*.md`). NOT `docs/`, NOT `agents/`, NOT `tests/`.

    Allowlist (per §D3):
      * Inside fenced code blocks (between ``` markers) — code comments
        legitimately cite source lines.
      * `path/to/file.py:123` file:line citations — no `line` keyword, not
        matched by the regex.
      * Single-digit `line 1` / `line 2` references (response/file) —
        filtered by the 2+ digit threshold.

    Returns (ok, violations). Pure function — does not raise.
    """
    if not skills_dir.is_dir():
        return False, [f"skill-line-number-ref violation: {skills_dir} not a directory"]

    violations: list[str] = []
    for md in sorted(skills_dir.rglob("*.md")):
        if not md.is_file():
            continue
        text, err = _read_text(md)
        if err is not None or text is None:
            violations.append(
                f"skill-line-number-ref violation: {err or f'{md} read returned no text'}"
            )
            continue
        violations.extend(_skill_line_refs_in_text(text))
    return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Guard 7: skill size cap (D2 — session 2026-07-03-004 regrowth brake)
# ---------------------------------------------------------------------------
# Caps are measured as `round(current * 1.05)` against the post-Phase-2/3
# baseline (the orchestrator's "measure AFTER relocations" rule from session
# 2026-07-03-004). The cap is a regrowth brake — to lower a cap a future
# release must relocate load-bearing prose AND retarget the cap constant in
# the same change (see §D2 honest label).
SKILL_SIZE_CAPS: dict[str, int] = {
    # Measured POST-Phase-2/3 relocation (session 2026-07-03-004 diet) as
    # `round(current * 1.05)`. The orchestrator's "measure AFTER relocations"
    # rule locks the ratchet to the post-diet baseline so regrowth trips
    # fail-loud at +5% above the slimmed size. See work-log.md for raw len().
    "lfg-loop": 47754,   # post-diet 45480 * 1.05
    "lfg": 41463,        # post-diet 39489 * 1.05
    "setup": 27734,      # current 26413 * 1.05
    "discuss": 26176,    # current 24930 * 1.05
    "debug": 18295,      # current 17424 * 1.05
    "review": 14820,     # current 14114 * 1.05
    "plan": 14602,       # current 13907 * 1.05
    "work": 12536,       # current 11939 * 1.05
}


def skill_size_cap_check(skills_dir: Path) -> tuple[bool, list[str]]:
    """Advisory size ratchet — fail-loud when a SKILL.md regrows past its cap.

    Measures `len(skill_md.read_text(encoding='utf-8'))` (the same number
    Python's `len()` reports and that the char-count ACs in
    session 2026-07-03-004 use) against `SKILL_SIZE_CAPS[skill_name]`.
    Skills not in the dict are skipped (no aspirational target yet).

    Honest scope (§D2 docstring): this is a *regrowth brake*, NOT a shrink
    enforcer. The diet itself is delivered by Phase-2 relocation and
    verified by char-count acceptance criteria. The cap is `current + 5%`
    so a future shrink-then-regrow still trips the brake at +5% above the
    measured baseline. To lower a cap, a future release must do the
    relocation + retarget the lint constant in the same change.

    Returns (ok, violations). Pure function — does not raise.
    """
    if not skills_dir.is_dir():
        return False, [f"skill-size-cap violation: {skills_dir} not a directory"]

    violations: list[str] = []
    for skill_name, cap in SKILL_SIZE_CAPS.items():
        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.is_file():
            # Not all caps need a present file (e.g. mid-rename); skip silently.
            continue
        text, err = _read_text(skill_md)
        if err is not None or text is None:
            violations.append(
                f"skill-size-cap violation: {err or f'{skill_md} read returned no text'}"
            )
            continue
        size = len(text)
        if size > cap:
            violations.append(
                f"skill-size-cap violation: {skill_md} is {size} bytes, "
                f"cap={cap} (baseline*1.05); either relocate load-bearing prose "
                f"into references/*.md or raise the cap with a documented "
                f"justification in the same change"
            )
    return (len(violations) == 0, violations)


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


def _cmd_skill_line_refs(args: argparse.Namespace) -> int:
    ok, violations = skill_line_number_ref_check(Path(args.skills_dir))
    if ok:
        print(f"skill-line-refs ok ({len(list(Path(args.skills_dir).rglob('*.md')))} files)")
        return 0
    for line in violations:
        print(line)
    return 1


def _cmd_skill_size_cap(args: argparse.Namespace) -> int:
    ok, violations = skill_size_cap_check(Path(args.skills_dir))
    if ok:
        print(f"skill-size-cap ok ({len(SKILL_SIZE_CAPS)} capped skills)")
        return 0
    for line in violations:
        print(line)
    return 1


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

    p = sub.add_parser(
        "skill-line-refs",
        help="detect rotting `line NNN` deep-prose references in skills/**/*.md",
    )
    p.add_argument("skills_dir")
    p.set_defaults(func=_cmd_skill_line_refs)

    p = sub.add_parser(
        "skill-size-cap",
        help="regrowth-brake size cap per skill (D2 regrowth brake)",
    )
    p.add_argument("skills_dir")
    p.set_defaults(func=_cmd_skill_size_cap)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
