"""Regression — registered-agent frontmatter model ↔ CLAUDE.md §Effort Level.

Context
-------
`docs/STATE.md` flagged `agent-frontmatter-consistency` as ❌ (no
regression lock — the v0.6.2 metadata-corruption class could recur
undetected). The v0.18.3 cleanup audit also found drift: `agents/
executor.md` declared `model: opus` while CLAUDE.md §Effort Level grouped
"Executor / Analyst: standard".

v0.18.7 plugin-diet de-registers the 7 inline-only pipeline roles
(analyst, cleaner, critic, executor, planner, researcher, reviewer) to
pure reference docs (no `name:`/`model:` frontmatter) — they are dispatched
INLINE by skills, the registered type had 0 adoption, and registering them
contradicted the collision guard. Only the 4 leader-dispatchable agents
(learner, releaser, ci-watcher, codex-dispatcher) stay registered.

These tests therefore lock the model tier for the REGISTERED agents only
(those with a `name:` field) and verify the 7/4 reference-vs-registered
partition. Static text reads only.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
AGENTS_DIR = REPO_ROOT / "agents"
VALID_TIERS = {"opus", "sonnet", "haiku"}

# v0.18.7 partition: de-registered reference docs vs leader-dispatchable types.
REFERENCE_DOC_AGENTS = {
    "analyst", "cleaner", "critic", "executor", "planner", "researcher", "reviewer",
}
REGISTERED_AGENTS = {"learner", "releaser", "ci-watcher", "codex-dispatcher"}


def _frontmatter(agent_stem: str) -> str:
    text = (AGENTS_DIR / f"{agent_stem}.md").read_text(encoding="utf-8")
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def _has_name(agent_stem: str) -> bool:
    return bool(re.search(r"^\s*name:\s*\S+", _frontmatter(agent_stem), re.MULTILINE))


def _registered_agent_stems() -> list[str]:
    """Agent files that are REGISTERED types (carry a `name:` field)."""
    return sorted(p.stem for p in AGENTS_DIR.glob("*.md") if _has_name(p.stem))


def _frontmatter_model(agent_stem: str) -> str | None:
    m = re.search(r"^\s*model:\s*(\S+)\s*$", _frontmatter(agent_stem), re.MULTILINE)
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


def test_pipeline_agents_are_reference_docs_not_registered() -> None:
    """MUST (v0.18.7) — the 7 inline-only pipeline roles carry NO name:; the 4
    leader-dispatchable agents keep name:. Every agent is in exactly one bucket.
    """
    for stem in sorted(REFERENCE_DOC_AGENTS):
        assert not _has_name(stem), (
            f"agents/{stem}.md must be a reference doc (no name: frontmatter) — "
            f"skills dispatch it INLINE; the registered type had 0 adoption and "
            f"contradicted the collision guard (v0.18.7 diet)."
        )
    for stem in sorted(REGISTERED_AGENTS):
        assert _has_name(stem), (
            f"agents/{stem}.md must stay a registered agent (name: present) — it "
            f"is dispatched as a type by the leader / ceremony / lfg."
        )
    all_stems = {p.stem for p in AGENTS_DIR.glob("*.md")}
    assert all_stems == REFERENCE_DOC_AGENTS | REGISTERED_AGENTS, (
        f"unexpected agent set; diff: "
        f"{all_stems ^ (REFERENCE_DOC_AGENTS | REGISTERED_AGENTS)}"
    )


def test_effort_level_covers_registered_agents() -> None:
    """MUST — §Effort Level maps every REGISTERED agent with an explicit tier."""
    effort = _claude_effort_map()
    missing = [a for a in _registered_agent_stems() if a not in effort]
    assert not missing, (
        f"CLAUDE.md §Effort Level must list every registered agent with an "
        f"explicit (opus|sonnet|haiku) tier; missing: {missing}. Format each "
        f"bullet as '- Name / Name: <words> (model)'."
    )


def test_effort_level_only_lists_registered_agents() -> None:
    """MUST — §Effort Level must NOT list de-registered reference docs.

    A reference doc has no dispatch tier; listing it in §Effort Level would be
    an over-claim and would have no frontmatter model to reconcile against.
    """
    effort = _claude_effort_map()
    registered = set(_registered_agent_stems())
    stray = sorted(set(effort) - registered)
    # Allow only names that map to an actual registered agent file.
    stray = [a for a in stray if (AGENTS_DIR / f"{a}.md").exists()]
    assert not stray, (
        f"CLAUDE.md §Effort Level lists non-registered agent(s) {stray}; "
        f"de-registered reference docs (no name:) must not appear there."
    )


def test_frontmatter_matches_effort_level() -> None:
    """MUST — each registered agent's frontmatter model equals its §Effort tier."""
    effort = _claude_effort_map()
    assert effort, "CLAUDE.md §Effort Level did not parse — check the bullet format."
    for agent in _registered_agent_stems():
        fm = _frontmatter_model(agent)
        assert fm == effort.get(agent), (
            f"agents/{agent}.md frontmatter model='{fm}' but CLAUDE.md "
            f"§Effort Level declares '{effort.get(agent)}'. Reconcile the drift — "
            f"the frontmatter tier is what actually dispatches."
        )


def test_all_registered_agent_models_are_valid_tiers() -> None:
    """MUST — every registered agent declares a known reasoning tier."""
    for agent in _registered_agent_stems():
        fm = _frontmatter_model(agent)
        assert fm in VALID_TIERS, (
            f"agents/{agent}.md model='{fm}' is not one of {sorted(VALID_TIERS)}."
        )
