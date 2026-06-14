#!/usr/bin/env python3
"""
Athanor v0.17.0 (S08) hook capability probe.

Passive probe — does NOT trigger Claude Code hook events itself. Inspects
the artifacts that already exist in this repo (or the installed plugin
tree) and emits a structured report at `.athanor/hook-capability.json`
documenting what athanor KNOWS about each Claude Code hook event class.

Purpose: de-risk v0.18.0 / v0.19.0 hook design by capturing, in one
machine-readable place, the empirical + documentary evidence we already
have for the four event types athanor cares about next:

  - SessionStart      (system-reminder-channel skill auto-load; not a hook
                       registration target athanor currently uses)
  - UserPromptSubmit  (forward-compat — additionalContext via stdout JSON)
  - PostToolUse       (evidence-only — v0.19.0 pytest exit-code sniffer)
  - PreCompact        (forward-compat — context-compaction inspection)

Inspection inputs:

  1. hooks/hooks.json                  — which events athanor currently registers
  2. CLAUDE.md                         — prose references to event semantics
  3. docs/STATE.md (Stop hook spike)   — empirical evidence from 2026-05-18
  4. skills/work/references/spec-then-tdd-handler.md
                                       — v0.19.0 evidence-bound anchor for
                                         PostToolUse pytest sniffer

Output:
  `.athanor/hook-capability.json`  (project-root relative; created if needed)

Usage:
  python3 scripts/hooks/capability_probe.py [--output PATH]

Run via /athanor:setup or standalone. Stdlib-only.

Exit codes:
  0  report written successfully
  0  report skipped because project root not resolvable (best-effort, never
     fails the caller — this is a probe, not a gate)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import _athanor_hook_runtime as _runtime  # noqa: F401
    _HAS_RUNTIME = True
except ImportError:
    _HAS_RUNTIME = False


# ---------------------------------------------------------------------------
# Helpers — repo discovery + safe text reads
# ---------------------------------------------------------------------------


def _resolve_project_root(explicit: Path | None = None) -> Path | None:
    """Locate the project root.

    Preference order:
      1. Explicit override (`--output` parent or CLI-passed dir).
      2. `_athanor_hook_runtime.resolve_project_root()` when importable.
      3. Walk up from this script's location for `.git/` or `athanor.json`.
      4. Walk up from `Path.cwd()` for `.git/` or `athanor.json`.

    Returns ``None`` if nothing matches — caller treats this as "skip".
    """
    if explicit is not None:
        return explicit
    if _HAS_RUNTIME:
        try:
            root = _runtime.resolve_project_root()
            if root is not None:
                return root
        except (OSError, FileNotFoundError):
            # Expected filesystem errors → degrade to the walk-up below.
            # Narrowed from a catch-all `except Exception` (fail-loud): an
            # UNEXPECTED error (e.g. an AttributeError from a future runtime
            # refactor) must propagate, not be masked by the walk-up — matches
            # the narrow-except discipline used elsewhere in this module.
            pass
    for start in (SCRIPTS_DIR, Path.cwd()):
        try:
            cur = start.resolve()
        except (OSError, FileNotFoundError):
            continue
        for _ in range(8):
            if (cur / ".git").is_dir() or (cur / "athanor.json").is_file():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
    return None


def _safe_read(path: Path) -> str:
    """Read a text file, returning '' on any error. Probe must never raise."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _detect_claude_code_version() -> str | None:
    """Best-effort: look for a Claude Code version string in the environment.

    We avoid spawning `claude --version` because (a) we may not be inside a
    CC-spawned process, (b) it adds a subprocess dep, and (c) probes must
    stay passive. Currently returns the `CLAUDE_CODE_VERSION` env var if
    set; otherwise None.
    """
    return os.environ.get("CLAUDE_CODE_VERSION") or None


# ---------------------------------------------------------------------------
# Per-event capability inspection
# ---------------------------------------------------------------------------


def _registered_events(hooks_json_text: str) -> set[str]:
    """Extract the set of event keys currently registered in hooks/hooks.json.

    Tolerates malformed JSON (returns empty set) — this is a documentation
    probe, not a validator.
    """
    if not hooks_json_text.strip():
        return set()
    try:
        data = json.loads(hooks_json_text)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict):
        return set()
    hooks_section = data.get("hooks")
    if not isinstance(hooks_section, dict):
        return set()
    return set(hooks_section.keys())


def _inspect_session_start(
    claude_md: str,
    state_md: str,
    registered: set[str],
) -> dict:
    """SessionStart capability.

    Known facts (per CLAUDE.md §using-superpowers boundary and STATE.md):
      - Claude Code's SessionStart system reminder channel auto-loads skills
        described as "ABSOLUTELY MUST invoke before response" — this is a
        PLATFORM behavior, NOT a hook event athanor registers.
      - Athanor's hooks.json registers Stop + PreToolUse only as of v0.17.0.
      - The platform passes the skill body via an additionalContext-style
        system reminder. Payload-shape introspection from athanor's side is
        not currently available because we don't register the event.
    """
    supported = False  # athanor does not register; nothing to assert
    notes_parts = []
    if "SessionStart" not in registered:
        notes_parts.append(
            "athanor does not register SessionStart in hooks/hooks.json — "
            "system-reminder skill loading is a Claude Code platform "
            "mechanism, not a hook event athanor consumes."
        )
    # Confirm CLAUDE.md still references the SessionStart-as-platform mechanism.
    if "SessionStart" in claude_md and "platform" in claude_md.lower():
        notes_parts.append(
            "CLAUDE.md documents SessionStart as a Claude Code platform "
            "mechanism (system reminder channel), not athanor hook surface."
        )
    if "SessionStart fiction" in state_md:
        notes_parts.append(
            "STATE.md §U3 records the v0.10.x 'SessionStart fiction' "
            "honesty correction — athanor never wired SessionStart and now "
            "documents that explicitly."
        )
    return {
        "supported": supported,
        "registered_in_hooks_json": "SessionStart" in registered,
        "payload_keys": [],
        "notes": " ".join(notes_parts) or "no notes",
    }


def _inspect_user_prompt_submit(registered: set[str]) -> dict:
    """UserPromptSubmit capability.

    No empirical evidence in this repo (athanor does not currently
    register UserPromptSubmit). v0.18.0 forward-compat: Claude Code's
    documented contract is to accept JSON on stdout with an
    `additionalContext` field which is then injected into the model's
    next-turn context. We mark this as `unprobed` so v0.18.0 design
    teams know to validate empirically before relying on it.
    """
    return {
        "supported": False,
        "registered_in_hooks_json": "UserPromptSubmit" in registered,
        "payload_keys": [],
        "stdout_additional_context_accepted": None,
        "notes": (
            "athanor does not register UserPromptSubmit as of v0.17.0; "
            "documented Claude Code contract is stdout JSON with "
            "`additionalContext` field. v0.18.0 design must spike-verify "
            "(analogous to the 2026-05-18 Stop spike) before relying on it."
        ),
    }


def _inspect_post_tool_use(
    registered: set[str],
    handler_md: str,
) -> dict:
    """PostToolUse capability.

    v0.19.0 registers an evidence-only sniffer. It records pytest Bash
    command results to session JSONL and never blocks. The registration is
    real, but this passive capability probe still does not manufacture a
    live Claude Code PostToolUse event; payload-shape certainty remains
    nullable until a live run stamps evidence.

    Key empirical question: is `tool_response` (or equivalent) present in
    the installed Claude Code version's PostToolUse payload, and does it
    carry exit code + stdout/stderr? The tolerant sniffer supports several
    likely field names; this report keeps `tool_response_available` as
    None until live evidence proves the exact runtime shape.
    """
    anchor_present = bool(
        re.search(r"PostToolUse[^\n]*test[- ]evidence sniffer", handler_md, re.IGNORECASE)
    )
    registered_posttool = "PostToolUse" in registered
    return {
        "supported": registered_posttool,
        "support_level": "evidence-only" if registered_posttool else "forward-compat",
        "registered_in_hooks_json": registered_posttool,
        "payload_keys": (
            ["hook_event_name", "tool_name", "tool_input", "tool_response"]
            if registered_posttool
            else []
        ),
        "tool_response_available": None,
        "forward_compat_anchor_present": anchor_present,
        "notes": (
            "athanor registers PostToolUse as an evidence-only pytest "
            "sniffer when hooks.json contains the event. The sniffer is "
            "tolerant of likely payload field names and always fails open; "
            "`tool_response_available` remains null until a live Claude Code "
            "run confirms the exact response fields."
        ),
    }


def _inspect_pre_compact(registered: set[str]) -> dict:
    """PreCompact capability.

    No athanor surface uses PreCompact. Recorded here for forward
    visibility — v0.18.0/v0.19.0 may want to snapshot session state or
    discoveries before compaction.
    """
    return {
        "supported": False,
        "registered_in_hooks_json": "PreCompact" in registered,
        "payload_keys": [],
        "notes": (
            "athanor does not register PreCompact as of v0.17.0. Forward "
            "candidate: snapshot .athanor/sessions/<latest>/discoveries/ "
            "before compaction discards them. Requires spike-verify of "
            "payload shape + timing before relying on it."
        ),
    }


# ---------------------------------------------------------------------------
# Main probe assembly
# ---------------------------------------------------------------------------


def build_capability_report(project_root: Path) -> dict:
    """Inspect repo artifacts and assemble the capability report dict.

    Pure function over filesystem reads; safe to call from tests.
    """
    hooks_json = _safe_read(project_root / "hooks" / "hooks.json")
    claude_md = _safe_read(project_root / "CLAUDE.md")
    state_md = _safe_read(project_root / "docs" / "STATE.md")
    handler_md = _safe_read(
        project_root / "skills" / "work" / "references" / "spec-then-tdd-handler.md"
    )

    registered = _registered_events(hooks_json)
    cc_version = _detect_claude_code_version()

    report = {
        "schema_version": 1,
        "probed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "probe_mode": "passive",
        "claude_code_version": cc_version,
        "athanor_registered_events": sorted(registered),
        "events": {
            "SessionStart": _inspect_session_start(claude_md, state_md, registered),
            "UserPromptSubmit": _inspect_user_prompt_submit(registered),
            "PostToolUse": _inspect_post_tool_use(registered, handler_md),
            "PreCompact": _inspect_pre_compact(registered),
        },
        "recommendations_for_v018_v019": [
            "v0.18.0: spike-verify UserPromptSubmit stdout-additionalContext "
            "contract before designing any context-injection feature on top "
            "of it (mirror the 2026-05-18 Stop hook spike methodology — "
            "log-only probe registered in ~/.claude/settings.json).",
            "v0.19.0: use the evidence-only PostToolUse sniffer to collect "
            "pytest exit code + output tail in session JSONL. Promote Phase "
            "3 from advisory to enforced only after live evidence confirms "
            "the installed Claude Code payload shape.",
            "v0.18.0+: do NOT register SessionStart in hooks/hooks.json — "
            "skill loading is a Claude Code platform mechanism handled "
            "outside athanor's hook surface. Re-affirming this avoids the "
            "v0.10.x SessionStart fiction documented in STATE.md §U3.",
            "Cross-platform: any new hook command MUST use "
            "`python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/hooks/...\"` per the "
            "v0.11.4 plugin-root deployment lesson. Bare relative paths "
            "silently fail-open outside athanor's source repo.",
            "Honesty label: every new event the probe marks `supported: "
            "false` MUST stay false until a spike with empirical evidence "
            "lands in docs/STATE.md (same bar as the 2026-05-18 Stop spike).",
        ],
    }
    return report


def write_capability_report(report: dict, project_root: Path) -> Path:
    """Atomically write the probe report to .athanor/hook-capability.json.

    Uses write-temp-then-rename to avoid partial-write corruption if the
    process is interrupted. Mirrors the atomic-write lesson from v0.14.2.
    """
    out_dir = project_root / ".athanor"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "hook-capability.json"
    tmp_path = out_dir / "hook-capability.json.tmp"
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, out_path)
    return out_path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Passive probe — emits .athanor/hook-capability.json "
                    "documenting Claude Code hook event coverage."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output path (defaults to <project>/.athanor/hook-capability.json).",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Override project root (defaults to walk-up from cwd / script dir).",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Echo the JSON report to stdout (in addition to writing it).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    project_root = _resolve_project_root(args.project_root)
    if project_root is None:
        # Best-effort: probe is informational, never fails the caller.
        sys.stderr.write(
            "capability_probe: could not resolve project root; skipping.\n"
        )
        return 0
    report = build_capability_report(project_root)
    if args.output is not None:
        out_dir = args.output.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
        args.output.write_text(payload, encoding="utf-8")
        out_path = args.output
    else:
        out_path = write_capability_report(report, project_root)
    if args.print:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    sys.stderr.write(f"capability_probe: wrote {out_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
