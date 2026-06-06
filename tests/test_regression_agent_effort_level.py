"""Regression — agent frontmatter model ↔ CLAUDE.md §Effort Level.

Context
-------
`docs/STATE.md` flagged `agent-frontmatter-consistency` as ❌ (no
regression lock — the v0.6.2 metadata-corruption class could recur
undetected). The v0.18.3 cleanup audit also found drift: `agents/
executor.md` declares `model: opus` while CLAUDE.md §Effort Level grouped
"Executor / Analyst: standard". The frontmatter is what actually
dispatches, so the doc was wrong.

This test makes CLAUDE.md §Effort Level the documented source of truth for
all 11 native agents and locks every agent's frontmatter model to it —
closing the agent-frontmatter-consistency gap and the executor drift in
one contract. Static text reads only.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
AGENTS_DIR = REPO_ROOT / "agents"
VALID_TIERS = {"opus", "sonnet", "haiku"}


def _agent_names() -> list[str]:
    return sorted(p.stem for p in AGENTS_DIR.glob("*.md"))


def _frontmatter_model(agent_stem: str) -> str | None:
    text = (AGENTS_DIR / f"{agent_stem}.md").read_text(encoding="utf-8")
    parts = text.split("---", 2)
    fm = parts[1] if len(parts) >= 3 else ""
    m = re.search(r"^\s*model:\s*(\S+)\s*$", fm, re.MULTILINE)
    return m.group(1) if m else None


def _claude_effort_map() -> dict[str, str]:
    """Parse CLAUDE.md §Effort Level lines → {agent_name: model_tier}.

    Each bullet is expected as: `- Name / Name / ...: <words> (model)`.
    """
    body = CLAUDE_MD.read_text(encoding="utf-8")
    m = re.search(r"#+\s*Effort Level\s*\n(.*?)(?=\n#|\Z)", body, re.S)
    if not m:
        return {}
    mapping: dict[str, str] = {}
    for line in m.group(1).splitlines():
        lm = re.match(r"\s*-\s*(.+?):.*?\((opus|sonnet|haiku)\)", line)
        if not lm:
            continue
        model = lm.group(2)
        for raw in lm.group(1).split("/"):
            name = raw.strip().lower().replace(" ", "")
            mapping[name] = model
    return mapping


def test_effort_level_covers_all_agents() -> None:
    """MUST — §Effort Level maps every native agent with an explicit tier."""
    effort = _claude_effort_map()
    missing = [a for a in _agent_names() if a not in effort]
    assert not missing, (
        f"CLAUDE.md §Effort Level must list every agent with an explicit "
        f"(opus|sonnet|haiku) tier; missing: {missing}. Format each bullet "
        f"as '- Name / Name: <words> (model)'."
    )


def test_frontmatter_matches_effort_level() -> None:
    """MUST — each agent's frontmatter model equals its §Effort Level tier."""
    effort = _claude_effort_map()
    assert effort, "CLAUDE.md §Effort Level did not parse — check the bullet format."
    for agent, model in sorted(effort.items()):
        fm = _frontmatter_model(agent)
        assert fm == model, (
            f"agents/{agent}.md frontmatter model='{fm}' but CLAUDE.md "
            f"§Effort Level declares '{model}'. Reconcile the drift — the "
            f"frontmatter tier is what actually dispatches."
        )


def test_all_agent_models_are_valid_tiers() -> None:
    """MUST — every agent declares a known reasoning tier."""
    for agent in _agent_names():
        fm = _frontmatter_model(agent)
        assert fm in VALID_TIERS, (
            f"agents/{agent}.md model='{fm}' is not one of {sorted(VALID_TIERS)}."
        )
