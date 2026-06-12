"""Regression tests for v0.18.8 walk-up unification (Phase 1).

Covers the `WalkResult` frozen dataclass + the unified `_walk_up` walker in
`scripts/hooks/_athanor_hook_runtime.py`, plus the four re-expressed call
sites that historically duplicated a `range(8)` walk-up loop with *divergent*
`.git`-hit dispositions:

  - `_find_athanor_config_path` (runtime): .git hit → None
  - `resolve_project_root`      (runtime): .git is itself a *marker* (no stop)
  - `_athanor_opt_in`           (hook_state): .git hit → False (+ NEW HOME stop, M2)
  - `_project_dir`              (hook_state): .git hit → `start.resolve()` fallback

The contract: ONE walker (`_walk_up`) returning a `WalkResult`
(`match` / `stopped_at_git` / `stopped_at_home`) so all four call sites
unify WITHOUT collapsing their distinct dispositions.

Plan reference: v0.18.8 Phase 1 — Walk-up unification (Subtask 1, Steps 1.0–1.6).
Do NOT fold these into tests/test_regression_hook_state_helpers.py — that
file's R2 hijack-guard case must stay green WITHOUT modification.
"""
from __future__ import annotations

import os
import sys
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Optional, get_args, get_origin

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_HOOKS = REPO_ROOT / "scripts" / "hooks"
if str(SCRIPTS_HOOKS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_HOOKS))

import _athanor_hook_runtime as runtime  # noqa: E402
import hook_state  # noqa: E402


# ---------------------------------------------------------------------------
# Step 1.0 — WalkResult contract (MUST go RED before the dataclass lands)
# ---------------------------------------------------------------------------


def test_walkresult_contract():
    """The `WalkResult` frozen dataclass + `_walk_up` signature ARE the
    contract. Before the dataclass lands this raises AttributeError on
    `runtime.WalkResult`; after, the field shape + frozenness + walker
    signature must hold.
    """
    # (1) WalkResult exists and is a dataclass with the three contract fields.
    WalkResult = runtime.WalkResult  # AttributeError pre-implementation
    field_map = {f.name: f for f in fields(WalkResult)}
    assert set(field_map) == {"match", "stopped_at_git", "stopped_at_home"}, (
        f"WalkResult fields drifted: {sorted(field_map)}"
    )

    # (2) `match` is Optional[Path]; the two flags are bool.
    match_type = field_map["match"].type
    # `from __future__ import annotations` may stringify the annotation; accept
    # either the real typing object or its string form.
    if isinstance(match_type, str):
        assert "Path" in match_type and (
            "Optional" in match_type or "None" in match_type
        ), f"match annotation not Optional[Path]: {match_type!r}"
    else:
        assert get_origin(match_type) is not None
        assert Path in get_args(match_type) and type(None) in get_args(match_type)

    # (3) Instances are frozen (immutable contract).
    wr = WalkResult(match=None, stopped_at_git=False, stopped_at_home=False)
    assert wr.match is None
    assert wr.stopped_at_git is False
    assert wr.stopped_at_home is False
    try:
        wr.match = REPO_ROOT  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("WalkResult must be frozen (immutable)")

    # (4) `_walk_up` exists with the contracted signature: explicit `start`
    # positional, `marker_check` positional, keyword-only stop flags + depth.
    import inspect

    sig = inspect.signature(runtime._walk_up)
    params = sig.parameters
    assert "start" in params and "marker_check" in params
    for kw in ("stop_at_git", "stop_at_home", "depth"):
        assert kw in params, f"_walk_up missing keyword param {kw}"
        assert params[kw].kind is inspect.Parameter.KEYWORD_ONLY, (
            f"_walk_up param {kw} must be keyword-only"
        )
    # `start` defaults to cwd (a Path), depth defaults to the named constant.
    assert params["depth"].default == runtime._WALK_UP_DEPTH


# ---------------------------------------------------------------------------
# Invariant (a) — hijack guard: _find_athanor_config_path still stops at .git
# (preservation criterion — EXPECTED never_red; do not contrive breakage)
# ---------------------------------------------------------------------------


def test_find_config_path_stops_at_git_boundary(tmp_path, monkeypatch):
    """`_find_athanor_config_path` must NOT cross a .git boundary upward to
    pick up an ancestor athanor.json (v0.7.9 hijack guard). Re-expressed over
    `_walk_up(stop_at_git=True)` — the .git hit yields match=None → None.
    """
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / "athanor.json").write_text("{}", encoding="utf-8")
    repo = outer / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()  # boundary
    sub = repo / "sub"
    sub.mkdir()
    saved = os.getcwd()
    try:
        os.chdir(sub)
        result = runtime._find_athanor_config_path()
    finally:
        os.chdir(saved)
    assert result is None, (
        f"_find_athanor_config_path crossed .git boundary upward: {result}"
    )


# ---------------------------------------------------------------------------
# Invariant (b) — _project_dir .git-fallback disposition is PRESERVED
# (preservation criterion — EXPECTED never_red)
# ---------------------------------------------------------------------------


def test_project_dir_git_hit_returns_start_resolve(tmp_path):
    """`_project_dir`'s distinctive disposition: when the walk-up hits a .git
    boundary WITHOUT finding `.athanor/`, it returns `start.resolve()` (a
    boundary fallback so state has *somewhere* to live), NOT None. This is the
    case that forbids collapsing all four call sites onto a None-returning
    walker.
    """
    repo = tmp_path / "repo"
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    (repo / ".git").mkdir()  # boundary, but NO .athanor anywhere
    result = hook_state._project_dir(start=sub)
    assert result == sub.resolve(), (
        f"_project_dir .git-fallback must be start.resolve(); got {result}"
    )


def test_project_dir_finds_athanor_dir(tmp_path):
    """Positive control: `.athanor/` present → that directory is returned
    (marker check fires before the .git stop)."""
    repo = tmp_path / "repo"
    sub = repo / "x" / "y"
    sub.mkdir(parents=True)
    (repo / ".athanor").mkdir()
    (repo / ".git").mkdir()
    result = hook_state._project_dir(start=sub)
    assert result == repo.resolve()


# ---------------------------------------------------------------------------
# Invariant (c) — _athanor_opt_in NEW $HOME stop (M2) — RED-capable
# ---------------------------------------------------------------------------


def test_athanor_opt_in_stops_at_home(tmp_path, monkeypatch):
    """M2 NEW behavior: `_athanor_opt_in` now enforces a $HOME stop. An
    athanor.json placed ABOVE $HOME must NOT be found when walking up from a
    start dir at/below $HOME — the walk halts at the HOME boundary.

    Layout:  above/athanor.json   <- ABOVE home, must NOT be honored
             above/home/          <- faked Path.home() (the stop)
             above/home/proj/sub  <- start (no .git, no athanor.json on path)
    """
    above = tmp_path / "above"
    home = above / "home"
    start = home / "proj" / "sub"
    start.mkdir(parents=True)
    (above / "athanor.json").write_text("{}", encoding="utf-8")  # above HOME

    # Fake the home ceiling by patching Path.home on the class — NOT via
    # setenv("HOME"): on Windows, Path.home() reads %USERPROFILE% and IGNORES
    # $HOME (bpo-36264, Python 3.8+), so env-faking is POSIX-only. The SUT
    # calls Path.home().resolve() on this same pathlib.Path class, so the
    # class-attribute patch is deterministic on every platform.
    monkeypatch.setattr(Path, "home", lambda: home)
    result = hook_state._athanor_opt_in(start)
    assert result is False, (
        "opt-in walked past $HOME and honored an athanor.json above it "
        "(M2 HOME-stop not enforced)"
    )


def test_athanor_opt_in_finds_within_home(tmp_path, monkeypatch):
    """Positive control: athanor.json AT/below the start (within HOME bounds)
    is still found — the HOME stop must not break normal opt-in."""
    home = tmp_path / "home"
    proj = home / "proj"
    sub = proj / "sub"
    sub.mkdir(parents=True)
    (proj / "athanor.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    assert hook_state._athanor_opt_in(sub) is True


def test_athanor_opt_in_stops_at_git_boundary(tmp_path, monkeypatch):
    """The pre-existing .git hijack guard survives the re-expression: an
    athanor.json above a .git repo root is NOT honored from inside the repo.
    (Mirrors the untouched helpers-file R2 case; asserted here against the
    re-expressed implementation.)"""
    monkeypatch.setenv("HOME", str(tmp_path))  # HOME far above; .git is the stop
    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / "athanor.json").write_text("{}", encoding="utf-8")
    repo = outer / "repo"
    (repo / ".git").mkdir(parents=True)
    assert hook_state._athanor_opt_in(repo) is False


# ---------------------------------------------------------------------------
# Invariant (d) — env-priority: $CLAUDE_PROJECT_DIR wins for config path
# ---------------------------------------------------------------------------


def test_find_config_path_env_priority(tmp_path, monkeypatch):
    """`$CLAUDE_PROJECT_DIR/athanor.json` (when the file exists) takes priority
    over any walk-up result. The env candidate is returned resolved."""
    env_proj = tmp_path / "envproj"
    env_proj.mkdir()
    (env_proj / "athanor.json").write_text("{}", encoding="utf-8")
    # A different, unrelated cwd with its OWN athanor.json — env must win.
    other = tmp_path / "other"
    other.mkdir()
    (other / "athanor.json").write_text('{"marker":"cwd"}', encoding="utf-8")

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(env_proj))
    saved = os.getcwd()
    try:
        os.chdir(other)
        result = runtime._find_athanor_config_path()
    finally:
        os.chdir(saved)
    assert result == (env_proj / "athanor.json").resolve(), (
        f"env priority not honored; got {result}"
    )


def test_find_config_path_env_missing_file_falls_through(tmp_path, monkeypatch):
    """If $CLAUDE_PROJECT_DIR is set but has NO athanor.json, the helper falls
    through to the cwd walk-up (env is a priority, not an override)."""
    env_proj = tmp_path / "envproj"
    env_proj.mkdir()  # no athanor.json here
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "athanor.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(env_proj))
    saved = os.getcwd()
    try:
        os.chdir(repo)
        result = runtime._find_athanor_config_path()
    finally:
        os.chdir(saved)
    assert result == (repo / "athanor.json"), (
        f"env-missing-file did not fall through to cwd walk-up; got {result}"
    )


# ---------------------------------------------------------------------------
# Invariant (e) — depth-8 bound on the unified walker
# ---------------------------------------------------------------------------


def test_walk_up_depth_8_bound(tmp_path):
    """`_walk_up` visits at most `_WALK_UP_DEPTH` (8) levels: start (level 0)
    through level 7. The far marker sits at EXACTLY level 8 above `start` —
    the FIRST level the depth-8 loop must NOT visit — so an over-walk by even
    one level (`range(depth + 1)` visits levels 0..8) flips this test RED
    (a marker any higher would tolerate one-level over-walks). The level-7
    `near` control below pins the lower edge (an under-walk `range(depth - 1)`
    misses it). `_WALK_UP_DEPTH` stays the SOLE named depth constant (no
    `range(8)` literals survive in hook_state.py — see
    test_hook_state_no_range8_literal).
    """
    assert runtime._WALK_UP_DEPTH == 8
    # Build start = d8 with 9 ancestors inside tmp_path: tmp_path/d0/.../d8.
    deep = tmp_path
    for i in range(9):  # tmp_path/d0/d1/.../d8  → start = d8 (9 dirs deep)
        deep = deep / f"d{i}"
    deep.mkdir(parents=True)
    # Marker at d0 = deep.parents[7] — exactly level 8 above `start`, the
    # boundary level: unreached at depth 8, reached at depth 9.
    marker_dir = deep.parents[7]

    def marker_check(p: Path) -> bool:
        return p == marker_dir.resolve()

    res = runtime._walk_up(
        start=deep, marker_check=marker_check, stop_at_git=False, stop_at_home=False
    )
    assert res.match is None, (
        f"_walk_up exceeded the depth-8 bound and reached the level-8 marker: {res}"
    )

    # Control: a marker exactly 7 levels up (within bound) IS reached.
    near = deep.parents[6]  # 7 levels above `deep`

    def near_check(p: Path) -> bool:
        return p == near.resolve()

    res2 = runtime._walk_up(
        start=deep, marker_check=near_check, stop_at_git=False, stop_at_home=False
    )
    assert res2.match == near.resolve()


def test_hook_state_no_range8_literal():
    """M1: the duplicated `range(8)` literals are gone from hook_state.py —
    the walk-up bound now flows from the single `_WALK_UP_DEPTH` constant via
    the unified `_walk_up`. (Source-pin expression of the
    `grep -c "range(8)" == 0` acceptance criterion.)"""
    src = (REPO_ROOT / "scripts" / "hooks" / "hook_state.py").read_text(
        encoding="utf-8"
    )
    assert "range(8)" not in src, (
        "hook_state.py still contains a literal range(8) — M1 not closed"
    )


# ---------------------------------------------------------------------------
# Invariant (f) — resolve_project_root memoization + cache_clear
# ---------------------------------------------------------------------------


def test_resolve_project_root_memoized(tmp_path, monkeypatch):
    """`resolve_project_root` memoizes on `(cwd, $HOME)`: a repeat call from
    the same cwd does NOT re-walk. Asserted by counting underlying `_walk_up`
    invocations across two calls — the second must be a cache hit (0 new
    walks). `cache_clear()` is exposed and forces a fresh walk afterward.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    runtime.resolve_project_root.cache_clear()

    calls = {"n": 0}
    real_walk = runtime._walk_up

    def counting_walk(*a, **k):
        calls["n"] += 1
        return real_walk(*a, **k)

    monkeypatch.setattr(runtime, "_walk_up", counting_walk)
    saved = os.getcwd()
    try:
        os.chdir(repo)
        r1 = runtime.resolve_project_root()
        after_first = calls["n"]
        r2 = runtime.resolve_project_root()
        after_second = calls["n"]
    finally:
        os.chdir(saved)

    assert r1 is not None and r1.resolve() == repo.resolve()
    assert r2 == r1
    assert after_first >= 1, "first call should walk at least once"
    assert after_second == after_first, (
        "second resolve_project_root() re-walked — memo not effective "
        f"(walks: {after_first} → {after_second})"
    )

    # cache_clear forces a fresh walk on the next call.
    runtime.resolve_project_root.cache_clear()
    try:
        os.chdir(repo)
        runtime.resolve_project_root()
        after_clear = calls["n"]
    finally:
        os.chdir(saved)
    assert after_clear > after_second, (
        "cache_clear() did not force a re-walk"
    )
    runtime.resolve_project_root.cache_clear()


def test_resolve_project_root_cache_keyed_on_cwd(tmp_path, monkeypatch):
    """The memo key includes cwd: two different repos resolve independently
    (no cross-cwd cache bleed)."""
    repo_a = tmp_path / "a"
    repo_a.mkdir()
    (repo_a / ".git").mkdir()
    repo_b = tmp_path / "b"
    repo_b.mkdir()
    (repo_b / ".git").mkdir()

    runtime.resolve_project_root.cache_clear()
    saved = os.getcwd()
    try:
        os.chdir(repo_a)
        ra = runtime.resolve_project_root()
        os.chdir(repo_b)
        rb = runtime.resolve_project_root()
    finally:
        os.chdir(saved)
    assert ra is not None and ra.resolve() == repo_a.resolve()
    assert rb is not None and rb.resolve() == repo_b.resolve()
    runtime.resolve_project_root.cache_clear()
