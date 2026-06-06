"""Regression tests for v0.18.0 Subtask 2.3 — `scripts/hooks/freeze_guard.py`.

Phase 3 of the v0.18.0 Plan-Scoped Freeze Manifest series. The Freeze
guard is the **inner** PreToolUse evaluator that the dispatcher invokes
after the kernel guard returns 0 and config consultation determines
freeze is enabled (`hooks.freeze.mode in {"warn", "session"}`).

Contract (per plan.md §Phase 3 + Subtask 2.3 acceptance criteria):

  `evaluate_payload(payload, config, mode="session") -> (exit_code, stderr)`

Behavior invariants under test:
  1. Edit / Write / MultiEdit gated on `file_path` against the loaded
     session allowlist.
  2. Bash conservative patterns (`> FILE`, `>> FILE`, `tee FILE`,
     `sed -i FILE`, `mv X Y`, `cp X Y`) extract destination paths and
     gate them against the allowlist.
  3. Subprocess writes (`python -c "open('foo','w')..."`, `make build`,
     `codex exec`, etc.) are explicitly NOT gated — D2 honesty residual,
     documented in the module docstring.
  4. `mode="warn"` logs the violation to
     `.athanor/sessions/<id>/freeze-violations.jsonl` but allows
     (returns `(0, "")`).
  5. `mode="session"` logs the violation AND blocks
     (returns `(2, "BLOCKED: ...")`).
  6. Missing allowlist → fail-open ``(0, "")`` (the dispatcher already
     gates this case; freeze guard mirrors the contract for direct
     callers).
  7. Allowlist matching supports exact path, fnmatch glob, and the
     default-included `.athanor/sessions/<id>/**` shape.
  8. User-extension paths from `config.hooks.freeze.extraAllowedPaths`
     are merged into the matching set.
  9. Violation log appended atomically (JSONL — one JSON object per line;
     subsequent appends preserve prior lines).
 10. Non-gated tools (e.g., `Read`, `Grep`, unknown) pass through
     unconditionally with `(0, "")`.

Tests use `tmp_path` for isolation and synthesize allowlist dicts
directly (no dependency on the builder script — pure unit coverage of
the evaluator surface).
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_HOOKS = REPO_ROOT / "scripts" / "hooks"

if str(SCRIPTS_HOOKS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_HOOKS))


@pytest.fixture()
def freeze_guard():
    """Import freeze_guard fresh per test (no shared state)."""
    if "freeze_guard" in sys.modules:
        del sys.modules["freeze_guard"]
    return importlib.import_module("freeze_guard")


# ---------------------------------------------------------------------------
# Payload + allowlist helpers
# ---------------------------------------------------------------------------


def _edit(path: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


def _write(path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path}}


def _multiedit(path: str) -> dict:
    return {"tool_name": "MultiEdit", "tool_input": {"file_path": path}}


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _read(path: str) -> dict:
    return {"tool_name": "Read", "tool_input": {"file_path": path}}


def _allowlist(
    paths: list[str],
    session_id: str = "2026-05-29-001",
    session_dir: Path | None = None,
) -> dict:
    """Build a minimal allowlist dict matching the builder's output shape."""
    default_session = f".athanor/sessions/{session_id}/**"
    al = {
        "session_id": session_id,
        "allowed_paths": [default_session, ".athanor/lessons/**"] + list(paths),
        "default_paths": [default_session, ".athanor/lessons/**"],
        "subtask_paths": list(paths),
        "extras": [],
        "built_from": "plan.md",
    }
    if session_dir is not None:
        al["_session_dir"] = str(session_dir)
    return al


# ---------------------------------------------------------------------------
# Module surface + symbols
# ---------------------------------------------------------------------------


def test_module_importable(freeze_guard):
    """The module must import cleanly."""
    assert freeze_guard is not None


def test_evaluate_payload_exists(freeze_guard):
    """`evaluate_payload` is the public entry point."""
    assert hasattr(freeze_guard, "evaluate_payload")
    assert callable(freeze_guard.evaluate_payload)


def test_path_traversal_escapes_allowlist(freeze_guard):
    """F1 (v0.18.6) — a `..` path-traversal candidate must NOT match a session
    allowlist glob.

    `_normalize_path` collapsed quotes/`./`/backslash but NOT `..`, and fnmatch
    `*` crosses `/`, so `.athanor/sessions/<id>/../../../scripts/x.py` matched
    the session glob and an out-of-scope edit slipped the freeze (bug hunt F1).
    """
    escaped = (
        ".athanor/sessions/2026-06-06-001/../../../scripts/hooks/freeze_guard.py"
    )
    allowed = [".athanor/sessions/2026-06-06-001/**"]
    assert freeze_guard._path_in_allowlist(escaped, allowed) is False, (
        "a path escaping the session dir via `..` must not match the session "
        "allowlist glob (path-traversal, F1)."
    )


def test_clean_session_path_still_in_allowlist(freeze_guard):
    """F1 guard — a clean in-session path still matches after the `..` collapse
    (the fix must not over-reject legitimate edits)."""
    inside = ".athanor/sessions/2026-06-06-001/work-log.md"
    allowed = [".athanor/sessions/2026-06-06-001/**"]
    assert freeze_guard._path_in_allowlist(inside, allowed) is True
    # A harmless `./` + intra-path `a/b/../c` still resolves inside.
    tidy = ".athanor/sessions/2026-06-06-001/sub/../work-log.md"
    assert freeze_guard._path_in_allowlist(tidy, allowed) is True


def test_evaluate_payload_returns_tuple(freeze_guard, tmp_path):
    """Return contract: (exit_code: int, stderr_message: str)."""
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    result = freeze_guard.evaluate_payload(_edit("src/foo.py"), al, mode="session")
    assert isinstance(result, tuple)
    assert len(result) == 2
    exit_code, stderr_message = result
    assert isinstance(exit_code, int)
    assert isinstance(stderr_message, str)


def test_module_docstring_documents_d2_honesty(freeze_guard):
    """D2 honesty: module docstring must label freeze as Claude-tool-only,
    NOT a comprehensive editing envelope."""
    doc = freeze_guard.__doc__ or ""
    lower = doc.lower()
    assert "subprocess" in lower, (
        "freeze_guard.py docstring must mention subprocess writes (D2)."
    )
    assert "not" in lower and "gated" in lower, (
        "freeze_guard.py docstring must state subprocess writes are NOT gated."
    )
    assert "claude" in lower and "file" in lower, (
        "freeze_guard.py docstring must describe freeze as a Claude file-tool "
        "allowlist (not a comprehensive editing envelope)."
    )


# ---------------------------------------------------------------------------
# Edit / Write / MultiEdit gating
# ---------------------------------------------------------------------------


def test_edit_path_in_allowlist_allowed(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(_edit("src/foo.py"), al, mode="session")
    assert exit_code == 0


def test_edit_path_outside_allowlist_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, stderr = freeze_guard.evaluate_payload(
        _edit("src/secret.py"), al, mode="session"
    )
    assert exit_code == 2
    assert "BLOCKED" in stderr
    assert "src/secret.py" in stderr


def test_write_path_outside_allowlist_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _write("src/secret.py"), al, mode="session"
    )
    assert exit_code == 2


def test_multiedit_path_outside_allowlist_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _multiedit("src/secret.py"), al, mode="session"
    )
    assert exit_code == 2


def test_write_into_session_dir_allowed_via_default(freeze_guard, tmp_path):
    """`.athanor/sessions/<id>/**` is a default-included glob."""
    al = _allowlist([], session_id="2026-05-29-001", session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _write(".athanor/sessions/2026-05-29-001/work-log.md"),
        al, mode="session"
    )
    assert exit_code == 0


def test_write_into_lessons_allowed_via_default(freeze_guard, tmp_path):
    al = _allowlist([], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _write(".athanor/lessons/2026-05-29-foo.md"), al, mode="session"
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Glob pattern matching
# ---------------------------------------------------------------------------


def test_glob_pattern_matches_descendants(freeze_guard, tmp_path):
    al = _allowlist(["src/**/*.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _edit("src/sub/dir/file.py"), al, mode="session"
    )
    assert exit_code == 0


def test_glob_pattern_does_not_match_other_extension(freeze_guard, tmp_path):
    al = _allowlist(["src/**/*.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _edit("src/sub/dir/file.md"), al, mode="session"
    )
    assert exit_code == 2


def test_simple_glob_matches_immediate_children(freeze_guard, tmp_path):
    al = _allowlist(["tests/test_*.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _edit("tests/test_foo.py"), al, mode="session"
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Bash conservative pattern gating
# ---------------------------------------------------------------------------


def test_bash_redirect_overwrite_outside_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, stderr = freeze_guard.evaluate_payload(
        _bash("echo 'data' > src/secret.py"), al, mode="session"
    )
    assert exit_code == 2
    assert "BLOCKED" in stderr


def test_bash_redirect_overwrite_inside_allowed(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("echo 'data' > src/foo.py"), al, mode="session"
    )
    assert exit_code == 0


def test_bash_redirect_append_outside_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("echo 'data' >> src/secret.py"), al, mode="session"
    )
    assert exit_code == 2


def test_bash_tee_target_outside_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("echo 'data' | tee src/secret.py"), al, mode="session"
    )
    assert exit_code == 2


def test_bash_sed_i_target_outside_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("sed -i 's/x/y/g' src/secret.py"), al, mode="session"
    )
    assert exit_code == 2


def test_bash_mv_dest_outside_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("mv src/foo.py src/secret.py"), al, mode="session"
    )
    assert exit_code == 2


def test_bash_cp_dest_outside_blocked(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("cp src/foo.py src/secret.py"), al, mode="session"
    )
    assert exit_code == 2


def test_bash_no_write_passes_through(freeze_guard, tmp_path):
    """Bash commands that don't match a write pattern pass through."""
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("ls -la src/"), al, mode="session"
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# D2 honesty residual: subprocess writes NOT gated
# ---------------------------------------------------------------------------


def test_python_c_subprocess_write_not_detected(freeze_guard, tmp_path):
    """Subprocess writes via `python -c` are NOT detected (D2 residual)."""
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("python -c \"open('src/secret.py','w').write('x')\""),
        al, mode="session"
    )
    # Pass-through — D2 documented in module docstring.
    assert exit_code == 0


def test_make_build_subprocess_not_detected(freeze_guard, tmp_path):
    """`make build` writes to `build/` not gated (D2 residual)."""
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("make build"), al, mode="session"
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# mode = warn vs session
# ---------------------------------------------------------------------------


def test_mode_warn_logs_but_allows(freeze_guard, tmp_path, monkeypatch):
    session_id = "2026-05-29-001"
    session_dir = tmp_path / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    al = _allowlist(["src/foo.py"], session_id=session_id, session_dir=session_dir)
    exit_code, stderr = freeze_guard.evaluate_payload(
        _edit("src/secret.py"), al, mode="warn"
    )
    assert exit_code == 0
    assert stderr == ""

    log_path = session_dir / "freeze-violations.jsonl"
    assert log_path.is_file(), "warn mode must append a violation log line"
    line = log_path.read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["tool"] == "Edit"
    assert record["target"] == "src/secret.py"
    assert record["mode"] == "warn"


def test_mode_session_blocks(freeze_guard, tmp_path, monkeypatch):
    session_id = "2026-05-29-001"
    session_dir = tmp_path / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    al = _allowlist(["src/foo.py"], session_id=session_id, session_dir=session_dir)
    exit_code, stderr = freeze_guard.evaluate_payload(
        _edit("src/secret.py"), al, mode="session"
    )
    assert exit_code == 2
    assert "BLOCKED" in stderr


def test_mode_session_also_logs(freeze_guard, tmp_path, monkeypatch):
    """session-mode blocks AND logs the violation."""
    session_id = "2026-05-29-001"
    session_dir = tmp_path / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    al = _allowlist(["src/foo.py"], session_id=session_id, session_dir=session_dir)
    freeze_guard.evaluate_payload(_edit("src/secret.py"), al, mode="session")

    log_path = session_dir / "freeze-violations.jsonl"
    assert log_path.is_file()
    line = log_path.read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["mode"] == "session"


# ---------------------------------------------------------------------------
# Missing allowlist → fail-open
# ---------------------------------------------------------------------------


def test_missing_allowlist_failopen(freeze_guard):
    """allowlist=None → fail-open."""
    exit_code, stderr = freeze_guard.evaluate_payload(
        _edit("src/secret.py"), None, mode="session"
    )
    assert exit_code == 0
    assert stderr == ""


def test_empty_allowlist_dict_failopen(freeze_guard):
    """allowlist={} (missing keys) → fail-open (cannot enforce)."""
    exit_code, _ = freeze_guard.evaluate_payload(
        _edit("src/secret.py"), {}, mode="session"
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Non-gated tools pass through
# ---------------------------------------------------------------------------


def test_read_passes_through(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _read("src/secret.py"), al, mode="session"
    )
    assert exit_code == 0


def test_unknown_tool_passes_through(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        {"tool_name": "SomeOtherTool", "tool_input": {"x": "y"}},
        al, mode="session"
    )
    assert exit_code == 0


def test_malformed_payload_failopen(freeze_guard, tmp_path):
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        "not a dict", al, mode="session"  # type: ignore[arg-type]
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Violation log atomicity
# ---------------------------------------------------------------------------


def test_violation_log_appends_jsonl(freeze_guard, tmp_path, monkeypatch):
    """Multiple violations append; each line is independently parseable."""
    session_id = "2026-05-29-001"
    session_dir = tmp_path / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    al = _allowlist(["src/foo.py"], session_id=session_id, session_dir=session_dir)
    freeze_guard.evaluate_payload(_edit("src/a.py"), al, mode="warn")
    freeze_guard.evaluate_payload(_edit("src/b.py"), al, mode="warn")

    log_path = session_dir / "freeze-violations.jsonl"
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    records = [json.loads(ln) for ln in lines]
    targets = [r["target"] for r in records]
    assert "src/a.py" in targets
    assert "src/b.py" in targets


def test_violation_log_record_has_timestamp(freeze_guard, tmp_path, monkeypatch):
    session_id = "2026-05-29-001"
    session_dir = tmp_path / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    al = _allowlist(["src/foo.py"], session_id=session_id, session_dir=session_dir)
    freeze_guard.evaluate_payload(_edit("src/a.py"), al, mode="session")

    log_path = session_dir / "freeze-violations.jsonl"
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert "timestamp" in record
    # ISO-8601 UTC ends with Z
    assert record["timestamp"].endswith("Z") or "T" in record["timestamp"]


# ---------------------------------------------------------------------------
# User-extension paths (extraAllowedPaths) via config
# ---------------------------------------------------------------------------


def test_config_extra_allowed_paths_merged(freeze_guard, tmp_path):
    """`config.hooks.freeze.extraAllowedPaths` extends the allowlist."""
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    config = {
        "hooks": {
            "freeze": {
                "mode": "session",
                "extraAllowedPaths": ["CHANGELOG.md"],
            }
        }
    }
    # The function signature accepts a config kwarg for these extras.
    exit_code, _ = freeze_guard.evaluate_payload(
        _edit("CHANGELOG.md"), al, mode="session", config=config
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Bash destination path glob match (session dir)
# ---------------------------------------------------------------------------


def test_bash_redirect_into_session_dir_allowed(freeze_guard, tmp_path):
    """`echo > .athanor/sessions/<id>/foo` matches the default-included glob."""
    al = _allowlist([], session_id="2026-05-29-001", session_dir=tmp_path)
    exit_code, _ = freeze_guard.evaluate_payload(
        _bash("echo 'foo' > .athanor/sessions/2026-05-29-001/note.md"),
        al, mode="session"
    )
    assert exit_code == 0


def test_default_mode_is_session(freeze_guard, tmp_path):
    """The function default for `mode` is `session` (per signature in plan)."""
    al = _allowlist(["src/foo.py"], session_dir=tmp_path)
    # No mode argument — should default to session behavior (block on miss).
    exit_code, _ = freeze_guard.evaluate_payload(
        _edit("src/secret.py"), al
    )
    assert exit_code == 2
