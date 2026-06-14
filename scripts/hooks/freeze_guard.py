#!/usr/bin/env python3
"""
Athanor v0.18.0 PreToolUse Freeze guard.

**This is a Claude file-tool allowlist, not a comprehensive editing
envelope.** Read the D2 honesty residual section below before relying
on freeze as a security boundary.

The Freeze guard is Phase 3 of the v0.18.0 Plan-Scoped Freeze Manifest.
It is the **inner** PreToolUse evaluator that the PreToolUse dispatcher
calls after the kernel guard returns 0 and config consultation determines
freeze is enabled (`hooks.freeze.mode in {"warn", "session"}`).

For each PreToolUse event, the guard reads the per-session allowlist
(`.athanor/sessions/<id>/freeze-allowlist.json` — built by
`scripts/work/build_freeze_allowlist.py`) and decides whether the
proposed Claude tool invocation may proceed.

What is gated
=============

1. **Claude file-tool writes** — `Edit`, `Write`, `MultiEdit`,
   `NotebookEdit`. The destination is resolved via `extract_target_path`:
   `tool_input.file_path` for Edit/Write/MultiEdit, and
   `tool_input.notebook_path` for NotebookEdit. If the resolved path does
   not match any entry in the loaded allowlist, the guard logs and
   (depending on `mode`) blocks.
2. **Bash conservative write patterns** — the guard scans the
   `tool_input.command` string for these shapes:
     - ``> FILE``     redirect overwrite
     - ``>> FILE``    redirect append
     - ``tee FILE``   tee write target
     - ``sed -i FILE`` in-place sed
     - ``mv X Y``     destination ``Y`` gated
     - ``cp X Y``     destination ``Y`` gated
   For each extracted target path, the same allowlist check runs.

Modes
=====

- ``off`` — the dispatcher must not call this evaluator; the freeze
  layer is silent. (We accept ``mode="off"`` defensively as fail-open
  for direct callers.)
- ``warn`` — every violation is appended to
  ``.athanor/sessions/<id>/freeze-violations.jsonl``; the call is
  ALLOWED (``exit 0``). Useful for staging plans before flipping to
  ``session``.
- ``session`` — every violation is logged AND blocked (``exit 2``).
  The stderr message names the offending path and points the user at
  the legitimate-edit workflow.

Allowlist matching
==================

- **Exact match** on the project-relative POSIX path.
- **Glob match** via :func:`fnmatch.fnmatch`. Globs in the allowlist
  (e.g., ``src/**/*.py``, ``.athanor/sessions/<id>/**``) match
  descendants per shell-glob semantics. ``**`` is expanded to match
  any number of path segments (the builder never expands globs; the
  guard matches at evaluation time).
- **Path normalization** strips quotes and ``./`` prefix on both
  sides so ``./src/foo.py`` and ``src/foo.py`` are equivalent.

The allowlist is the dict produced by the builder; the guard reads
the ``allowed_paths`` key. User-extension paths from
``config.hooks.freeze.allowedPaths`` are unioned at evaluation
time so a user can extend the allowlist without re-running the builder.

D2 honesty residual — subprocess writes NOT gated
=================================================

The freeze guard inspects Claude's tool-input arguments only. **It does
NOT see writes that happen inside subprocesses launched via Bash.**

Examples that bypass the freeze envelope:

- ``python -c "open('out.txt', 'w').write('x')"`` — write target is
  inside the Python program, not the Bash command string.
- ``make build`` — Makefile-driven writes; destinations are determined
  inside ``make``.
- ``codex exec ...`` — Codex CLI dispatches that produce files.
- ``git apply patch`` — git-mediated file writes.
- ``npm run ...``, ``cargo build``, etc. — toolchain-driven writes.

These bypass freeze because the destination path is not syntactically
visible in the Bash command string. The v0.18.0 CHANGELOG labels this
surface as "Claude file-tool allowlist" — NOT "editing envelope" — to
set honest expectations. v0.19.0 adds PostToolUse evidence streams for
pytest results and observed file-change candidates, but Freeze enforcement
remains PreToolUse-only. Observed D2 file changes are surfaced as concerns
rather than new blocks.

Architectural note: failure-open contract
=========================================

The freeze guard is invoked by a dispatcher that has already loaded
config and decided freeze is enabled. Direct callers passing
``allowlist=None`` or ``allowlist={}`` get a fail-open ``(0, "")``
return — the guard cannot enforce against a missing allowlist, and
the dispatcher is expected to gate this case upstream by exiting 0
silently (see Phase 2 dispatcher contract).

Stdlib-only — same constraint as the rest of ``scripts/hooks/*.py``.
"""
from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _athanor_hook_runtime as _runtime  # noqa: E402

__all__ = [
    "classify_paths_against_allowlist",
    "evaluate_payload",
    "extract_bash_write_targets",
]


# ---------------------------------------------------------------------------
# Bash write-pattern extractors (conservative)
# ---------------------------------------------------------------------------
# Each pattern captures the destination path in group 1. Conservative on
# purpose — quoted/multi-piped commands may slip through (documented
# residual). The v0.18.0 freeze surface explicitly accepts this trade-off
# in exchange for low false-positive rates.

# `> file` — redirect overwrite. Avoid matching `>=`, `>>`, `>&`.
_BASH_REDIRECT_OVERWRITE = re.compile(r"(?<![>&])>(?![>&=])\s*([^\s|;&<>()]+)")
# `>> file` — redirect append.
_BASH_REDIRECT_APPEND = re.compile(r">>\s*([^\s|;&<>()]+)")
# `tee file` — first non-flag positional arg.
_BASH_TEE = re.compile(r"\btee\b(?:\s+-[a-zA-Z]+)*\s+([^\s|;&<>()]+)")
# `sed -i FILE` — in-place sed. The substitution expression may appear
# between -i and FILE; capture the LAST positional argument heuristically.
_BASH_SED_I = re.compile(r"\bsed\b\s+(?:-[a-zA-Z]+\s+)*-i(?:\s+[^\s]+)?\s+(?:'[^']*'|\"[^\"]*\"|[^\s]+)\s+([^\s|;&<>()]+)")
# `mv X Y` and `cp X Y` — destination is the LAST positional argument.
# Conservative: match exactly two positional arguments (X and Y), no flags
# in between. Real-world `mv -f X Y` and `cp -r X Y` are covered by the
# flag-skip prefix.
_BASH_MV = re.compile(r"\bmv\b(?:\s+-[a-zA-Z]+)*\s+([^\s|;&<>()]+)\s+([^\s|;&<>()]+)")
_BASH_CP = re.compile(r"\bcp\b(?:\s+-[a-zA-Z]+)*\s+([^\s|;&<>()]+)\s+([^\s|;&<>()]+)")


# ---------------------------------------------------------------------------
# Path normalization (mirrors build_freeze_allowlist._normalize_path)
# ---------------------------------------------------------------------------


def _normalize_path(raw: str) -> str:
    """Strip quotes and `./` prefix; convert to POSIX. Glob chars preserved."""
    if not raw:
        return ""
    s = raw.strip().rstrip(",").strip()
    # Strip surrounding single/double quotes.
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        s = s[1:-1].strip()
    while s.startswith("./"):
        s = s[2:]
    return s.replace("\\", "/")


# ---------------------------------------------------------------------------
# Allowlist matching
# ---------------------------------------------------------------------------


def _expand_globstar(pattern: str) -> list[str]:
    """Expand `**` to give multiple fnmatch-compatible patterns.

    fnmatch.fnmatch does not natively handle `**` as a path-segment
    wildcard. Convert `dir/**/file` into multiple patterns:
      - `dir/file`        (zero segments)
      - `dir/*/file`      (one segment)
      - `dir/*/*/file`    (two segments)
      - ... up to a reasonable depth (8 — same bound as
        `_athanor_hook_runtime._WALK_UP_DEPTH`).

    `**` at end (e.g., `dir/**`) expands to `dir/*`, `dir/*/*`, etc.
    """
    if "**" not in pattern:
        return [pattern]
    # Split on `**`, then expand each gap with 0..MAX_DEPTH segments.
    parts = pattern.split("**")
    if len(parts) == 1:
        return [pattern]
    max_depth = 8
    results = [""]
    for i, part in enumerate(parts):
        if i == 0:
            results = [part]
            continue
        new_results: list[str] = []
        for r in results:
            # `**` between two non-empty parts: insert 0..N intermediate `*` segments.
            # `**` at the very end (part == "" or starts with "/"): expand to
            # match any descendant.
            base = r.rstrip("/")
            tail = part.lstrip("/")
            for depth in range(max_depth + 1):
                if depth == 0:
                    if base and tail:
                        new_results.append(f"{base}/{tail}")
                    elif base:
                        new_results.append(base)
                    elif tail:
                        new_results.append(tail)
                    else:
                        new_results.append("")
                else:
                    middle = "/".join(["*"] * depth)
                    if base and tail:
                        new_results.append(f"{base}/{middle}/{tail}")
                    elif base:
                        new_results.append(f"{base}/{middle}")
                    elif tail:
                        new_results.append(f"{middle}/{tail}")
                    else:
                        new_results.append(middle)
        results = new_results
    # Dedupe while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for r in results:
        if r and r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _path_matches_pattern(path: str, pattern: str) -> bool:
    """Match `path` against `pattern` using globstar-expanded fnmatch."""
    if not pattern:
        return False
    if path == pattern:
        return True
    for expanded in _expand_globstar(pattern):
        if fnmatch.fnmatchcase(path, expanded):
            return True
    return False


def _path_in_allowlist(path: str, allowed_paths: list[str]) -> bool:
    """Return True if `path` matches any entry in `allowed_paths`."""
    normalized = _normalize_path(path)
    if not normalized:
        return False
    # v0.18.6 (bug hunt F1): collapse `.`/`..` segments before matching. Without
    # this, a path-traversal candidate (`.athanor/sessions/<id>/../../../x.py`)
    # keeps its `..` and matches a session glob because fnmatch `*` crosses `/`
    # — letting an out-of-scope edit slip the freeze. normpath canonicalizes so
    # an escaping path resolves to its real (out-of-allowlist) location, and a
    # candidate that escapes above the tree keeps a leading `..` that matches no
    # normal allowlist prefix (fail-closed).
    normalized = posixpath.normpath(normalized)
    for entry in allowed_paths:
        if not isinstance(entry, str):
            continue
        norm_entry = _normalize_path(entry)
        if _path_matches_pattern(normalized, norm_entry):
            return True
    return False


def classify_paths_against_allowlist(
    paths: list[str],
    allowlist: Optional[dict],
    config: Optional[dict] = None,
) -> list[dict]:
    """Classify observed file-change paths against the effective allowlist.

    This is evidence-only support for PostToolUse D2 follow-up work. Missing
    or empty allowlists return ``unknown_allowlist`` rather than pretending a
    path was allowed or denied.
    """
    if not isinstance(allowlist, dict):
        allowed_paths: list[str] = []
    else:
        allowed_paths = _merged_allowed_paths(allowlist, config)

    classified: list[dict] = []
    seen: set[str] = set()
    for raw in paths:
        if not isinstance(raw, str):
            continue
        normalized = _normalize_path(raw)
        if not normalized:
            continue
        normalized = posixpath.normpath(normalized)
        if normalized in seen:
            continue
        seen.add(normalized)

        if not allowed_paths:
            status = "unknown_allowlist"
        elif _path_in_allowlist(normalized, allowed_paths):
            status = "in_allowlist"
        else:
            status = "out_of_allowlist"
        classified.append({"path": normalized, "allowlist_status": status})
    return classified


# ---------------------------------------------------------------------------
# Bash destination extraction
# ---------------------------------------------------------------------------


def _extract_bash_write_targets(command: str) -> list[str]:
    """Return all gated destination paths found in `command`.

    Conservative — only the documented Bash patterns are inspected.
    Subprocess writes (Python -c, make, codex exec, etc.) are NOT in
    scope; see module docstring D2 residual section.
    """
    if not command:
        return []
    targets: list[str] = []

    # Order matters slightly: append before overwrite (the `>>` token
    # would also match `>` if we scanned overwrite first). Append regex
    # is `>>\s*PATH`; overwrite regex uses a negative lookahead so they
    # don't double-fire on the same `>>`.
    for m in _BASH_REDIRECT_APPEND.finditer(command):
        targets.append(m.group(1))
    for m in _BASH_REDIRECT_OVERWRITE.finditer(command):
        targets.append(m.group(1))
    for m in _BASH_TEE.finditer(command):
        targets.append(m.group(1))
    for m in _BASH_SED_I.finditer(command):
        targets.append(m.group(1))
    for m in _BASH_MV.finditer(command):
        # Destination is group 2.
        targets.append(m.group(2))
    for m in _BASH_CP.finditer(command):
        targets.append(m.group(2))

    # Dedupe while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for t in targets:
        norm = _normalize_path(t)
        if norm and norm not in seen:
            seen.add(norm)
            deduped.append(norm)
    return deduped


def extract_bash_write_targets(command: str) -> list[str]:
    """Public wrapper for conservative Bash write-target extraction."""
    return _extract_bash_write_targets(command)


# ---------------------------------------------------------------------------
# Violation logging
# ---------------------------------------------------------------------------


def _session_dir_for_log(allowlist: dict) -> Optional[Path]:
    """Resolve where to write the violation log.

    Priority:
      1. `_session_dir` key on the allowlist (test convenience / explicit).
      2. `.athanor/sessions/<session_id>/` resolved from cwd.

    Returns None if the directory cannot be resolved (callers skip
    logging in that case).
    """
    explicit = allowlist.get("_session_dir") if isinstance(allowlist, dict) else None
    if explicit:
        try:
            return Path(explicit)
        except (TypeError, ValueError):
            return None
    sid = allowlist.get("session_id") if isinstance(allowlist, dict) else None
    if not isinstance(sid, str) or not sid:
        return None
    try:
        return (Path.cwd() / ".athanor" / "sessions" / sid).resolve()
    except (OSError, ValueError):
        return None


def _log_violation(
    allowlist: dict,
    tool: str,
    target: str,
    mode: str,
    matched_pattern: Optional[str] = None,
) -> None:
    """Append a JSONL line to `freeze-violations.jsonl` in the session dir.

    Failures (missing session dir, write error) are swallowed — the
    freeze guard must not crash on logging.
    """
    session_dir = _session_dir_for_log(allowlist)
    if session_dir is None:
        return
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    log_path = session_dir / "freeze-violations.jsonl"
    record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": tool,
        "target": target,
        "mode": mode,
    }
    if matched_pattern is not None:
        record["matched_pattern"] = matched_pattern

    line = json.dumps(record, sort_keys=False, ensure_ascii=False) + "\n"
    # Atomic-append: open with O_APPEND so concurrent writers don't
    # interleave partial lines (POSIX guarantees atomicity of single
    # write() calls smaller than PIPE_BUF; JSONL records here are well
    # under that threshold).
    try:
        with open(log_path, "a", encoding="utf-8") as fp:
            fp.write(line)
    except OSError:
        return


# ---------------------------------------------------------------------------
# Allowlist construction (with config extras union)
# ---------------------------------------------------------------------------


def _merged_allowed_paths(
    allowlist: dict,
    config: Optional[dict],
) -> list[str]:
    """Return the effective allowlist as a list of patterns.

    Union of:
      1. `allowlist["allowed_paths"]` (already includes builder-side
         defaults + subtask paths + builder-side extras).
      2. `config["hooks"]["freeze"]["allowedPaths"]` if config is
         provided — runtime extension so users can add paths without
         re-running the builder.
    """
    paths: list[str] = []
    if isinstance(allowlist, dict):
        raw = allowlist.get("allowed_paths", [])
        if isinstance(raw, list):
            for p in raw:
                if isinstance(p, str):
                    paths.append(p)
    if isinstance(config, dict):
        hooks = config.get("hooks", {})
        if isinstance(hooks, dict):
            freeze = hooks.get("freeze", {})
            if isinstance(freeze, dict):
                extras = freeze.get("allowedPaths", [])
                if isinstance(extras, list):
                    for p in extras:
                        if isinstance(p, str):
                            paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# Absolute-path relativization
# ---------------------------------------------------------------------------


def _relativize_target(target: str, root: Optional[Path]) -> str:
    """Convert an ABSOLUTE `target` to its project-relative POSIX form.

    The allowlist stores project-relative paths, but real Claude Code
    payloads send absolute ``file_path`` values. When ``target`` is
    absolute and lies under ``root``, return the ``root``-relative POSIX
    path so the allowlist match can succeed.

    Fail-closed boundary (plan §3.2 / rubric D): if ``target`` is NOT
    absolute, ``root`` is ``None``, or ``target`` lies OUTSIDE ``root``,
    return it UNCHANGED. The caller then runs it through ``normpath``,
    which keeps a leading ``..`` for an escaping absolute path so it
    matches no allowlist prefix — BLOCKED, never silently allowed. We
    never auto-allow an out-of-root path here.
    """
    if not target or not os.path.isabs(target):
        return target
    if root is None:
        return target
    try:
        rel = Path(target).relative_to(root)
    except ValueError:
        # Outside root — leave absolute so normpath keeps it out of the
        # allowlist (fail-closed). Do NOT silently allow.
        return target
    return rel.as_posix()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_payload(
    payload: dict,
    allowlist: Optional[dict],
    mode: str = "session",
    config: Optional[dict] = None,
    *,
    project_root: Optional[Path] = None,
) -> tuple[int, str]:
    """Evaluate a PreToolUse payload against the freeze allowlist.

    Parameters
    ----------
    payload : dict
        Parsed PreToolUse event JSON. Must include ``tool_name`` and
        ``tool_input``; malformed shapes fail-open ``(0, "")``.
    allowlist : Optional[dict]
        The dict produced by ``scripts/work/build_freeze_allowlist.py``.
        ``None`` or ``{}`` (missing ``allowed_paths``) fails-open — the
        guard cannot enforce against a missing allowlist. The dispatcher
        is expected to gate this case upstream by exiting 0 silently.
    mode : str
        One of ``"off"`` (fail-open), ``"warn"`` (log + allow), or
        ``"session"`` (log + block). Default is ``"session"``.
    config : Optional[dict]
        Parsed ``athanor.json``. Used to union
        ``hooks.freeze.allowedPaths`` into the matching set.
    project_root : Optional[Path], keyword-only
        Project root used to relativize ABSOLUTE tool-target paths before
        the allowlist match. Real Claude Code payloads send absolute
        ``file_path`` values while the allowlist stores project-relative
        POSIX paths — without this the guard would block every real edit.
        Keyword-only so the existing positional
        ``evaluate_payload(payload, allowlist, mode=...)`` call sites stay
        unbroken. When ``None``, resolves via
        ``_athanor_hook_runtime.resolve_project_root()`` (today's
        cwd-coupled behavior); the dispatcher passes its already-resolved
        root to avoid ambient-cwd dependence. Mirrors the sibling
        ``pretool_kernel_guard.evaluate_payload(payload, project_root=...)``
        signature. An absolute path OUTSIDE the resolved root fails the
        relativization and falls through to ``normpath`` (keeping a leading
        ``..``) so it matches no allowlist prefix — fail-closed, never
        silently allowed.

    Returns
    -------
    (exit_code, stderr_message) : tuple[int, str]
        ``exit_code`` is 0 (allow) or 2 (block). ``stderr_message`` is
        empty on allow; on block, a single-line BLOCKED: message naming
        the offending path.
    """
    # Defensive: unknown mode → fail-open. The dispatcher only calls us
    # for "warn" / "session"; treat "off" and anything else as no-op.
    if mode not in ("warn", "session"):
        return (0, "")

    # Fail-open contract on missing allowlist.
    if not isinstance(allowlist, dict):
        return (0, "")
    allowed_paths = _merged_allowed_paths(allowlist, config)
    if not allowed_paths:
        return (0, "")

    if not isinstance(payload, dict):
        return (0, "")
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return (0, "")

    # Resolve the project root used to relativize ABSOLUTE target paths.
    # `None` → today's cwd-coupled behavior via the shared runtime helper;
    # the dispatcher passes its already-resolved root explicitly.
    root = project_root if project_root is not None else _runtime.resolve_project_root()

    # ---- File-write tools (Edit / Write / MultiEdit / NotebookEdit) ----
    # Sourced from the shared WRITE_TOOLS tuple so NotebookEdit is gated like
    # the rest. `extract_target_path` resolves the destination — `notebook_path`
    # for NotebookEdit, `file_path` for the others. Freeze gates writes only;
    # reads are never freeze-gated (handled by the pass-through tail below).
    if tool_name in _runtime.WRITE_TOOLS:
        target = _runtime.extract_target_path(tool_name, tool_input)
        if not isinstance(target, str) or not target:
            return (0, "")
        # Real payloads send absolute paths; relativize against root before the
        # allowlist match. Out-of-root absolute paths stay absolute and fail
        # the match below (fail-closed).
        match_target = _relativize_target(target, root)
        if _path_in_allowlist(match_target, allowed_paths):
            return (0, "")
        # Violation
        _log_violation(allowlist, tool_name, _normalize_path(target), mode)
        if mode == "warn":
            return (0, "")
        return (
            2,
            f"BLOCKED: freeze: {target} not in session allowlist. "
            f"Edit plan.md + re-run Splitter, edit freeze-allowlist.json, "
            f"or flip hooks.freeze.mode to 'off'.",
        )

    # ---- Bash (conservative pattern gating) ----
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not isinstance(command, str) or not command:
            return (0, "")
        targets = _extract_bash_write_targets(command)
        for t in targets:
            # Same absolute→relative relativization as the file-tool branch so
            # Bash redirects to absolute in-allowlist paths are allowed and
            # out-of-root absolute paths fail-closed.
            match_t = _relativize_target(t, root)
            if _path_in_allowlist(match_t, allowed_paths):
                continue
            # Violation
            _log_violation(allowlist, "Bash", t, mode)
            if mode == "warn":
                # Keep scanning — log every violation, then allow.
                continue
            return (
                2,
                f"BLOCKED: freeze: Bash write to {t} not in session allowlist. "
                f"Edit plan.md + re-run Splitter, edit freeze-allowlist.json, "
                f"or flip hooks.freeze.mode to 'off'.",
            )
        return (0, "")

    # Other tools (Read, Grep, etc.) pass through unconditionally —
    # freeze does not gate reads.
    return (0, "")


# ---------------------------------------------------------------------------
# CLI entry point (subprocess-invoked by the dispatcher in the future)
# ---------------------------------------------------------------------------

def _read_stdin_payload() -> Optional[dict]:
    """Read PreToolUse event JSON from stdin. Returns None on any error."""
    try:
        if sys.stdin.isatty():
            return None
    except (OSError, ValueError):
        pass
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return None
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def main() -> int:
    """CLI entry: read stdin payload, look up allowlist, evaluate.

    The dispatcher is expected to invoke ``evaluate_payload`` in-process;
    this CLI entry exists for standalone testing and parity with
    ``pretool_kernel_guard.py``.
    """
    payload = _read_stdin_payload()
    if payload is None:
        return 0
    # CLI path can't know the session without walking up; this is a
    # placeholder for direct invocation. Returns 0 (allow) unconditionally
    # when invoked without a wired-up dispatcher.
    return 0


if __name__ == "__main__":
    sys.exit(main())
