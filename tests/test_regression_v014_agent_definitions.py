"""Regression tests for v0.14.0 agent definitions.

Verifies that the 3 new agent definition files (releaser, codex-dispatcher,
ci-watcher) exist, have correct YAML frontmatter structure, follow naming
conventions, and reference their core contractual obligations in the body.

Plan reference: v0.14.0 subtask S7.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents"

# The 3 new agent definitions added in v0.14.0
NEW_AGENTS = [
    "releaser.md",
    "codex-dispatcher.md",
    "ci-watcher.md",
]

AGENT_PATHS = {name: AGENTS_DIR / name for name in NEW_AGENTS}

# Required frontmatter fields for all agent definitions
REQUIRED_FRONTMATTER_FIELDS = ["name:", "description:", "model:", "tools:"]

# Regex to extract YAML frontmatter between --- delimiters
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)


def _read_agent(name: str) -> str:
    """Read agent file content, assert it exists and is non-trivial."""
    path = AGENT_PATHS[name]
    assert path.exists(), f"{path} does not exist"
    text = path.read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) > 200, (
        f"{name} is too small ({len(text.encode('utf-8'))} bytes); "
        f"expected >200 bytes for a valid agent definition"
    )
    return text


def _frontmatter(text: str) -> str:
    """Extract YAML frontmatter from agent definition text."""
    m = _FRONTMATTER_RE.match(text)
    assert m, "Agent file must start with YAML frontmatter (--- ... ---)"
    return m.group(1)


# ---- Existence tests ----


def test_releaser_agent_exists():
    """agents/releaser.md exists and is >200 bytes."""
    _read_agent("releaser.md")


def test_codex_dispatcher_agent_exists():
    """agents/codex-dispatcher.md exists and is >200 bytes."""
    _read_agent("codex-dispatcher.md")


def test_ci_watcher_agent_exists():
    """agents/ci-watcher.md exists and is >200 bytes."""
    _read_agent("ci-watcher.md")


# ---- Frontmatter structure tests ----


@pytest.mark.parametrize("agent_name", NEW_AGENTS, ids=NEW_AGENTS)
@pytest.mark.parametrize("field", REQUIRED_FRONTMATTER_FIELDS)
def test_agent_frontmatter_has_required_fields(agent_name: str, field: str):
    """All 3 agents have name:, description:, model:, tools: in frontmatter."""
    text = _read_agent(agent_name)
    fm = _frontmatter(text)
    assert field in fm, (
        f"{agent_name} frontmatter missing required field '{field}'"
    )


# ---- Naming convention test ----


def test_agent_names_follow_convention():
    """All 3 agent name: fields start with 'athanor-'."""
    for agent_name in NEW_AGENTS:
        text = _read_agent(agent_name)
        fm = _frontmatter(text)
        # Extract the name: value from frontmatter
        m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert m, f"{agent_name} frontmatter has no 'name:' line"
        name_value = m.group(1).strip()
        assert name_value.startswith("athanor-"), (
            f"{agent_name} name field is '{name_value}' — "
            f"must start with 'athanor-' per naming convention"
        )


# ---- Core contract tests ----


def test_codex_dispatcher_mentions_stdin_redirect():
    """codex-dispatcher.md body contains /dev/null reference (stdin safety)."""
    text = _read_agent("codex-dispatcher.md")
    # The core contract is stdin-based prompt passing (not bare positional arg).
    # The body should reference stdin or /dev/null as part of the dispatch pattern.
    lower = text.lower()
    assert "/dev/null" in lower or "stdin" in lower, (
        "codex-dispatcher.md must reference /dev/null or stdin "
        "(core stdin-redirect contract)"
    )


def test_codex_dispatcher_mentions_timeout_clamping():
    """codex-dispatcher.md body contains timeout clamping reference (1-600)."""
    text = _read_agent("codex-dispatcher.md")
    # Must mention the clamping range — either "1-600" or "min=1, max=600"
    # or the clamp() call
    assert re.search(r"(?:1.*600|clamp|timeout.*clamp|min.*1.*max.*600)", text), (
        "codex-dispatcher.md must reference timeout clamping "
        "(1-600 range or clamp function)"
    )


def test_releaser_mentions_version_bump_files():
    """releaser.md body references the 5-file version bump convention."""
    text = _read_agent("releaser.md")
    expected_refs = [
        "plugin.json",
        "marketplace.json",
        "athanor.json",
        "templates/athanor.json",
        "schemas/athanor-config.schema.json",
    ]
    for ref in expected_refs:
        assert ref in text, (
            f"releaser.md must reference '{ref}' "
            f"(5-file version bump convention)"
        )


def test_ci_watcher_mentions_gh_pr_checks():
    """ci-watcher.md body contains 'gh pr checks' (core CI interaction)."""
    text = _read_agent("ci-watcher.md")
    assert "gh pr checks" in text, (
        "ci-watcher.md must contain 'gh pr checks' "
        "(core CI interaction command)"
    )
