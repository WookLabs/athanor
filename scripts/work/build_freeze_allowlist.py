#!/usr/bin/env python3
"""v0.18.0 Phase 1 plan-scoped freeze allowlist builder.

Reads `.athanor/sessions/<id>/plan.md`, extracts every Subtask's `files:`
declaration, writes `freeze-allowlist.json` for `freeze_guard.py` (PreToolUse
inner guard) to consume.

Public API (per plan.md §Phase 1 + Subtask 1.2 acceptance criteria):
  parse_subtask_files(plan_md_path) -> list[{subtask_id, files}]
  build_allowlist(parsed, session_id, extras) -> dict
  write_allowlist(allowlist, output_path) -> None  (atomic, tempfile+os.replace)

Two Splitter output shapes supported:
  Shape A (plan.md narrative):    `#### Subtask N — title` + `**files**:`
  Shape B (canonical splitter):   `- [ ] **Subtask N: title**` + `  - files:`

Contract locked by `tests/test_regression_v018_splitter_files_contract.py`.
Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_LESSONS_GLOB = ".athanor/lessons/**"

# Shape A: plan.md narrative form.
_HDR_A = re.compile(r"^#{3,5}[ \t]+Subtask[ \t]+([\d.]+)[ \t]*[—\-]?", re.MULTILINE)
_FILES_A = re.compile(r"^[ \t]*\*\*files\*\*[ \t]*:[ \t]*(.*)$", re.MULTILINE)
# Shape B: canonical splitter checkbox bullet form.
_HDR_B = re.compile(
    r"^[ \t]*-[ \t]*\[\s*[ xX]?\s*\][ \t]+\*\*Subtask[ \t]+([\w\.\-]+)[ \t]*:.*?\*\*[ \t]*$"
)
_FILES_B = re.compile(r"^[ \t]{2,4}-[ \t]+files[ \t]*:[ \t]*(.*?)[ \t]*$")


# ---------------------------------------------------------------------------
# Path normalization
# ---------------------------------------------------------------------------


def _normalize_path(raw: str) -> str:
    """Strip backticks/quotes/`./`; convert to POSIX. Glob chars preserved."""
    if not raw:
        return ""
    s = raw.strip().rstrip(",").strip()
    # Backtick code-span — extract first quoted token (handles trailing prose).
    if s.startswith("`"):
        end = s.find("`", 1)
        if end > 0:
            s = s[1:end].strip()
    # Strip surrounding single/double quotes.
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        s = s[1:-1].strip()
    while s.startswith("./"):
        s = s[2:]
    return s.replace("\\", "/")


# ---------------------------------------------------------------------------
# parse_subtask_files
# ---------------------------------------------------------------------------


def parse_subtask_files(plan_md_path: str) -> list[dict]:
    """Parse `plan.md`; extract `files:` declarations per Subtask block.

    Returns list of `{"subtask_id": str, "files": list[str]}`.

    Behavior:
      - Missing/unreadable plan.md → [] + stderr warning.
      - No `## Subtasks` section → [].
      - Shape B preferred (canonical); falls back to Shape A.
      - Shape B subtasks without `files:` line → entry with `files: []`.
      - Shape A subtasks without `**files**:` marker → skipped (narrative).
      - Globs preserved; paths POSIX-normalized.
    """
    path = Path(plan_md_path)
    if not path.is_file():
        sys.stderr.write(
            f"[build_freeze_allowlist] WARN: plan.md not found at {plan_md_path}; "
            "emitting defaults only.\n"
        )
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"[build_freeze_allowlist] WARN: read failed: {exc}\n")
        return []

    anchor = re.search(r"^##[ \t]+Subtasks\b", text, re.MULTILINE)
    if not anchor:
        return []
    body = text[anchor.end():]
    entries_b = _parse_shape_b(body)
    return entries_b if entries_b else _parse_shape_a(body)


def _parse_shape_a(body: str) -> list[dict]:
    """Shape A: `#### Subtask N — title` + `**files**:` block."""
    headers = list(_HDR_A.finditer(body))
    entries: list[dict] = []
    for idx, m in enumerate(headers):
        sid = m.group(1).strip()
        start = m.end()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(body)
        files = _extract_files_a(body[start:end])
        if files is not None:
            entries.append({"subtask_id": sid, "files": files})
    return entries


def _extract_files_a(block: str) -> list[str] | None:
    """Return None if no marker, [] if empty, else list of normalized paths."""
    m = _FILES_A.search(block)
    if not m:
        return None
    inline = m.group(1).strip()
    if inline:
        bracket = re.match(r"^\[(.*)\]\s*$", inline)
        if bracket:
            inner = bracket.group(1).strip()
            if not inner:
                return []
            raw = [p.strip() for p in inner.split(",")]
        else:
            raw = [inline]
        return [n for n in (_normalize_path(p) for p in raw) if n]
    # Bullet form: walk lines until boundary.
    bullets: list[str] = []
    for line in block[m.end():].splitlines():
        s = line.strip()
        if not s:
            continue
        # Boundary: next field marker, heading, or separator.
        if (s.startswith("**") and s.endswith(":")) or re.match(r"^#{1,5}\s", s) \
                or s == "---" or re.match(r"^\*\*\w+\*\*\s*:", s):
            break
        if s.startswith(("- ", "* ")):
            norm = _normalize_path(s[2:])
            if norm:
                bullets.append(norm)
            continue
        break
    return bullets


def _parse_shape_b(body: str) -> list[dict]:
    """Shape B: `- [ ] **Subtask N: title**` + `  - files: [...]` bullet."""
    records: list[dict] = []
    cur_id: str | None = None
    cur_files: list[str] = []

    def _flush():
        nonlocal cur_id, cur_files
        if cur_id is not None:
            records.append({"subtask_id": cur_id, "files": cur_files})
        cur_id = None
        cur_files = []

    for line in body.splitlines():
        m_hdr = _HDR_B.match(line)
        if m_hdr:
            _flush()
            cur_id = m_hdr.group(1)
            cur_files = []
            continue
        if cur_id is None:
            continue
        m_f = _FILES_B.match(line)
        if m_f:
            cur_files = _parse_files_value_b(m_f.group(1))
    _flush()
    return records


def _parse_files_value_b(value: str) -> list[str]:
    """Parse RHS of a Shape B `files:` field. `[a,b]` | `[]` | bare | empty."""
    v = value.strip()
    if not v:
        return []
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        parts = [p for p in (x.strip() for x in inner.split(",")) if p]
        return [n for n in (_normalize_path(p) for p in parts) if n]
    norm = _normalize_path(v)
    return [norm] if norm else []


# ---------------------------------------------------------------------------
# build_allowlist
# ---------------------------------------------------------------------------


def build_allowlist(
    parsed: list[dict],
    session_id: str,
    extras: list[str] | None = None,
) -> dict:
    """Compose allowlist: defaults + deduped subtask paths + deduped extras.

    Extras EXTEND (never replace) the dynamic allowlist (Subtask 1.2 contract).
    """
    extras = list(extras or [])
    defaults = [f".athanor/sessions/{session_id}/**", _LESSONS_GLOB]

    seen: set[str] = set(defaults)
    subtask_paths: list[str] = []
    for entry in parsed:
        for p in entry.get("files", []) or []:
            n = _normalize_path(p)
            if n and n not in seen:
                seen.add(n)
                subtask_paths.append(n)

    normed_extras: list[str] = []
    for e in extras:
        n = _normalize_path(e)
        if n and n not in seen:
            seen.add(n)
            normed_extras.append(n)

    return {
        "session_id": session_id,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowed_paths": list(defaults) + subtask_paths + normed_extras,
        "default_paths": list(defaults),
        "subtask_paths": list(subtask_paths),
        "extras": list(normed_extras),
        "built_from": "plan.md",
    }


# ---------------------------------------------------------------------------
# write_allowlist (atomic; tempfile + os.replace, v0.14.2 lesson)
# ---------------------------------------------------------------------------


def write_allowlist(allowlist: dict, output_path: str) -> None:
    """Atomic write via tempfile in same dir + os.replace."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(allowlist, indent=2, sort_keys=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=out.name + ".", suffix=".tmp", dir=str(out.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            fp.write(payload)
        os.replace(tmp, out)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _read_extras_from_athanor_json(project_root: Path) -> list[str]:
    cfg = project_root / "athanor.json"
    if not cfg.is_file():
        return []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    extras = data.get("hooks", {}).get("freeze", {}).get("extraAllowedPaths", [])
    if not isinstance(extras, list):
        return []
    return [str(p) for p in extras if isinstance(p, str)]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build per-session freeze allowlist from plan.md Subtasks."
    )
    p.add_argument("--session-id", required=True)
    p.add_argument("--project-root", default=None)
    p.add_argument("--output", default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    root = Path(args.project_root).resolve() if args.project_root else Path.cwd().resolve()
    sid = args.session_id
    plan_md = root / ".athanor" / "sessions" / sid / "plan.md"
    parsed = parse_subtask_files(str(plan_md))
    extras = _read_extras_from_athanor_json(root)
    allowlist = build_allowlist(parsed, session_id=sid, extras=extras)
    out_path = Path(args.output) if args.output else (
        root / ".athanor" / "sessions" / sid / "freeze-allowlist.json"
    )
    write_allowlist(allowlist, str(out_path))
    sys.stderr.write(
        f"[build_freeze_allowlist] wrote {out_path} "
        f"({len(allowlist['allowed_paths'])} entries; "
        f"{len(allowlist['subtask_paths'])} from plan, "
        f"{len(allowlist['default_paths'])} defaults, "
        f"{len(allowlist['extras'])} extras)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
