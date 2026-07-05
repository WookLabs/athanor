"""Regression tests for v0.11.7 — import-path invariants.

Background (Planner A correction of analyze.md worker B finding):
analyze.md's worker B flagged "scripts/__init__.py missing — latent
ModuleNotFoundError trap" as a B7 issue. Planner A discovered that
both `scripts/__init__.py` AND `scripts/hooks/__init__.py` already
exist (the v0.11.5 release shipped the latent-trap closure). The
B7 sub-step is therefore *not* a production-code fix; it is an
invariant-lock test that ensures future deletion of either
`__init__.py` is caught immediately by the test suite.

What this test does NOT do:
- It does NOT modify production code under `scripts/`.
- It does NOT re-run the v0.11.3/v0.11.5 fixes (those shipped).

What this test DOES do:
- Verifies both `__init__.py` package markers exist as files
  (Python 3 package import contract).
- Verifies `import scripts`, `from scripts import hooks`, and active modules
  under `scripts.hooks` (`_athanor_hook_runtime`, `pretool_dispatcher`,
  `posttool_evidence_sniffer`) all import cleanly via
  `importlib.import_module` (no `ModuleNotFoundError`).

If either `__init__.py` is deleted in the future (refactor,
botched merge, accidental rm), these tests fail RED immediately,
restoring the invariant before the latent trap re-opens.

Test design notes:
- Uses `pathlib.Path` (per subtask constraint) for file-existence
  checks (does not rely on Python's import machinery for the file
  contract — separation of concerns).
- Uses `importlib.import_module` (per subtask constraint) rather
  than top-level `import X` syntax so each criterion reports
  cleanly and one failure does not abort the test collection.
- Test functions are written to PASS on first run because the
  v0.11.5 fix already shipped `__init__.py` for both packages.
  Worker reports `red_status: never_red`; leader-side handler
  routes through Phase 3 test-aware gate per spec-then-tdd
  protocol.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SCRIPTS_HOOKS_DIR = REPO_ROOT / "scripts" / "hooks"


# ---------------------------------------------------------------------------
# File-existence invariants (pathlib-based; no import machinery)
# ---------------------------------------------------------------------------


def test_scripts_package_init_exists() -> None:
    """`scripts/__init__.py` must exist as a regular file.

    Python 3 package import contract: without `__init__.py`,
    `scripts/` would be treated as an implicit namespace package
    (PEP 420), which works for some patterns but breaks the
    explicit `from scripts.hooks import X` form used by hook tests and other
    internal tooling.
    """
    init_path = SCRIPTS_DIR / "__init__.py"
    assert init_path.exists(), (
        f"{init_path} is missing. The v0.11.5 release shipped this "
        "package marker to close a latent ModuleNotFoundError trap. "
        "Restore the file before merging — deletion re-opens the trap."
    )
    assert init_path.is_file(), (
        f"{init_path} exists but is not a regular file. "
        "Package markers must be regular files."
    )


def test_scripts_hooks_package_init_exists() -> None:
    """`scripts/hooks/__init__.py` must exist as a regular file.

    Same Python 3 package-import contract as the parent package.
    Tests under `tests/` use `from scripts.hooks import ...`
    to exercise hook helpers; an implicit-namespace fallback is
    insufficient because sibling test files mix the import styles.
    """
    init_path = SCRIPTS_HOOKS_DIR / "__init__.py"
    assert init_path.exists(), (
        f"{init_path} is missing. The v0.11.5 release shipped this "
        "package marker. Restore before merging."
    )
    assert init_path.is_file(), (
        f"{init_path} exists but is not a regular file. "
        "Package markers must be regular files."
    )


# ---------------------------------------------------------------------------
# Import-resolution invariants (importlib-based; exercises Python's loader)
# ---------------------------------------------------------------------------


def test_scripts_package_import_resolves() -> None:
    """`import scripts` and `from scripts import hooks` must resolve.

    Uses `importlib.import_module` per spec — the equivalent of the
    `import` statement but raises a catchable `ModuleNotFoundError`
    that the test framework reports cleanly per criterion.
    """
    scripts_mod = importlib.import_module("scripts")
    assert scripts_mod is not None
    # Subpackage resolution — this is the form most likely to break
    # if `scripts/__init__.py` is deleted but `scripts/hooks/__init__.py`
    # remains.
    hooks_pkg = importlib.import_module("scripts.hooks")
    assert hooks_pkg is not None


def test_scripts_hooks_active_modules_import_resolve() -> None:
    """Active hook modules and shared runtime helpers must resolve."""
    for module_name in (
        "scripts.hooks._athanor_hook_runtime",
        "scripts.hooks.pretool_dispatcher",
        "scripts.hooks.posttool_evidence_sniffer",
    ):
        module = importlib.import_module(module_name)
        assert module is not None
        assert hasattr(module, "__file__")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
