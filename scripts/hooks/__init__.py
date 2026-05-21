"""athanor Stop hook scripts (v0.11.5).

This package contains the runtime hook entry points referenced from
`hooks/hooks.json`. Files inside (`stop_verify_claims.py`,
`hook_state.py`, `sentinel_helper.py`) are invoked by Claude Code as
plain `python3` subprocess targets via the `${CLAUDE_PLUGIN_ROOT}` path
expansion fixed in v0.11.4.

This `__init__.py` exists so `from scripts.hooks import ...` resolves
cleanly when tests import the modules directly instead of running them
through subprocess. v0.11.5 closes the latent import-path trap surfaced
by the 2026-05-21 analyze session (LOW-6).
"""
