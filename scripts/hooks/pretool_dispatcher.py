#!/usr/bin/env python3
"""
Athanor v0.18.0 PreToolUse single-outer-entry dispatcher.

Sole PreToolUse handler (``hooks/hooks.json``). Runs inner guards in
fixed priority order:

  1. **Kernel guard FIRST** — catastrophic worker hazards (destructive
     shell, force-push to protected branches, sensitive cred file access).
     Runs UNCONDITIONALLY. Preserves v0.16.0 fail-CLOSED behavior on
     missing athanor.json (``rm -rf /`` still blocks with no config).
  2. **Freeze guard SECOND** — plan-scoped allowlist (v0.18.0 opt-in).
     Consulted ONLY when ``hooks.freeze.mode != "off"``. Default is
     ``"off"`` so the surface is bit-for-bit v0.16.0 for non-opt-in users.

C10 single-outer-entry: ``scripts/gates/manifest_checks.py::
hook_uniqueness_check`` enforces one outer entry per event. The
dispatcher pattern keeps that invariant while running multiple inner
guards in priority order.

Codex-review-of-Plan-A invariant lock: ``rm -rf /`` must block even when
athanor.json is missing AND freeze is off. Locked by
``test_regression_v018_pretool_dispatcher.py::test_missing_athanor_json_still_blocks_rm_rf_root``.

Fail-open contract:
  - empty / malformed / non-object stdin → exit 0 (mirrors v0.16.0).
  - opt-in freeze: missing ``freeze-allowlist.json`` causes no enforcement.

Stdlib-only. Invoked via ``sh "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/run_hook.sh"
"${CLAUDE_PLUGIN_ROOT}/scripts/hooks/pretool_dispatcher.py"`` (portable
interpreter launcher; v0.11.4 plugin-root expansion lesson).

Subtask 2.2 ships this script BEFORE ``freeze_guard.py`` (Subtask 2.3).
The freeze import is deferred to the freeze branch and guarded with
``try/except ImportError`` so dispatcher is fully usable against the
default ``mode="off"`` before 2.3 lands.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _athanor_hook_runtime as _runtime  # noqa: E402
from pretool_kernel_guard import evaluate_payload as kernel_evaluate  # noqa: E402
from safety_patterns import classify_pretool_payload  # noqa: E402

# Session ID pattern per CLAUDE.md §Session Lookup Convention.
_SESSION_ID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{3}$")


def _stderr(msg: str) -> None:
    """Emit one prefixed stderr line (surfaced to model on exit 2)."""
    print(f"athanor (pretool guard): {msg}", file=sys.stderr)


def _freeze_mode(config) -> str:
    """Return configured freeze mode (``off`` | ``session`` | ``warn``).
    Defensive on shape — anything off-contract collapses to ``"off"``."""
    if not isinstance(config, dict):
        return "off"
    hooks_section = config.get("hooks")
    if not isinstance(hooks_section, dict):
        return "off"
    freeze_section = hooks_section.get("freeze")
    if not isinstance(freeze_section, dict):
        return "off"
    mode = freeze_section.get("mode", "off")
    if not isinstance(mode, str) or mode not in {"off", "session", "warn"}:
        return "off"
    return mode


def _safety_corpus_mode(config) -> str:
    """Return opt-in safety corpus mode (``off`` | ``observe`` | ``warn``)."""
    if not isinstance(config, dict):
        return "off"
    hooks_section = config.get("hooks")
    if not isinstance(hooks_section, dict):
        return "off"
    corpus = hooks_section.get("safetyCorpus")
    if not isinstance(corpus, dict):
        return "off"
    mode = corpus.get("mode", "off")
    if not isinstance(mode, str) or mode not in {"off", "observe", "warn"}:
        return "off"
    return mode


def _current_git_branch(project_root: Path | None) -> str | None:
    if project_root is None:
        return None
    try:
        proc = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(project_root),
            text=True,
            capture_output=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    branch = proc.stdout.strip()
    return branch or None


def _write_safety_findings(project_root: Path, records: list[dict[str, str]]) -> None:
    out_dir = project_root / ".athanor"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "hook-safety.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _observe_safety_corpus(payload: dict, config: dict, project_root: Path | None) -> str:
    """Run the opt-in safety corpus and return a warn-mode summary string."""
    mode = _safety_corpus_mode(config)
    if mode == "off" or project_root is None:
        return ""
    branch = _current_git_branch(project_root)
    findings = classify_pretool_payload(payload, branch=branch)
    if not findings:
        return ""
    now = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, str]] = []
    for finding in findings:
        record = finding.to_record()
        record["hook_event_name"] = "PreToolUse"
        record["timestamp"] = now
        records.append(record)
    try:
        _write_safety_findings(project_root, records)
    except OSError:
        return ""
    if mode == "warn":
        return ", ".join(record["pattern_id"] for record in records)
    return ""


def _latest_session_dir() -> Optional[Path]:
    """Resolve the latest session directory per CLAUDE.md Session Lookup
    Convention: lexicographic-sort matching `<YYYY-MM-DD>-<NNN>` names.

    Walks up from cwd (matching ``_athanor_hook_runtime`` semantics) to
    find a `.athanor/sessions/` parent. Returns the latest dir Path, or
    None if no matching dir exists.
    """
    root = _runtime.resolve_project_root()
    if root is None:
        return None
    sessions_dir = root / ".athanor" / "sessions"
    if not sessions_dir.is_dir():
        return None
    candidates: list[str] = []
    try:
        for child in sessions_dir.iterdir():
            if child.is_dir() and _SESSION_ID_PATTERN.match(child.name):
                candidates.append(child.name)
    except OSError:
        return None
    if not candidates:
        return None
    candidates.sort()
    return sessions_dir / candidates[-1]


def _read_freeze_allowlist() -> Optional[dict]:
    """Read `.athanor/sessions/<latest>/freeze-allowlist.json` and return
    the parsed dict. None on any failure (missing dir, missing file,
    unreadable, malformed) — the dispatcher will fail-open in that case
    (the contract Subtask 2.3 freeze_guard mirrors).

    Augments the loaded dict with `_session_dir` so freeze_guard's
    violation logger writes to the correct path even when cwd is set
    elsewhere.
    """
    session_dir = _latest_session_dir()
    if session_dir is None:
        return None
    allowlist_path = session_dir / "freeze-allowlist.json"
    if not allowlist_path.is_file():
        return None
    try:
        data = json.loads(allowlist_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    # Pin the session dir so violations.jsonl lands next to the allowlist
    # the dispatcher actually loaded — defensive against cwd drift.
    data["_session_dir"] = str(session_dir)
    return data


def main() -> int:
    """Entry: read stdin, run kernel FIRST, then freeze if opted in."""
    payload = _runtime.read_stdin_payload()
    if payload is None:
        # fail-open on missing/unparseable stdin — but fail-LOUD: a guard that
        # silently no-ops hides the failure (§Core Principle: fail-loud over
        # silent fallback). Other hooks emit the same breadcrumb here.
        _stderr("stdin missing or unparseable; passing (fail-open)")
        return 0

    # Step 1: kernel guard FIRST. Reads its own profile internally
    # (fail-CLOSED "standard" default on missing config), so catastrophic
    # blocks hold even with no athanor.json.
    kernel_exit, kernel_msg = kernel_evaluate(payload)
    if kernel_exit != 0:
        if kernel_msg:
            _stderr(kernel_msg)
        return kernel_exit

    # Step 2: only after kernel passed, consult config for freeze.
    config = _runtime.read_athanor_config()
    if _runtime.is_hook_profile_off(config):
        return 0  # global opt-out (same as Stop hook)

    root = _runtime.resolve_project_root()
    warning = _observe_safety_corpus(payload, config, root)
    if warning:
        _stderr(f"safety corpus observation: {warning}")

    mode = _freeze_mode(config)
    if mode == "off":
        return 0  # default — freeze layer skipped entirely

    # Step 3: lazy-import freeze_guard (Subtask 2.3). Missing module is
    # opt-in fail-open with a stderr breadcrumb.
    try:
        from freeze_guard import evaluate_payload as freeze_evaluate  # type: ignore
    except ImportError:
        _stderr(
            "freeze_guard module not available; passing (fail-open). "
            "Install athanor v0.18.0 Phase 2 (Subtask 2.3) to enable."
        )
        return 0

    # Step 4: load per-session allowlist. Missing allowlist → fail-open
    # (the freeze_guard signature mirrors this; we short-circuit early
    # to avoid the lazy-load + import cost on every PreToolUse event).
    allowlist = _read_freeze_allowlist()
    if allowlist is None:
        return 0

    # Resolve the project root so freeze_guard can relativize ABSOLUTE
    # tool-target paths (real Claude Code payloads send absolute file_path
    # values; the allowlist stores project-relative POSIX paths). None is
    # tolerated — freeze_guard falls back to its own cwd-coupled resolver.
    # root already resolved for safety corpus observation above.

    try:
        freeze_exit, freeze_msg = freeze_evaluate(
            payload, allowlist, mode=mode, config=config, project_root=root
        )
    except Exception as exc:  # noqa: BLE001 — defensive: never brick PreToolUse
        _stderr(f"freeze_guard raised {type(exc).__name__}; passing (fail-open)")
        return 0

    if freeze_exit != 0:
        if freeze_msg:
            _stderr(freeze_msg)
        return freeze_exit
    return 0


if __name__ == "__main__":
    sys.exit(main())
