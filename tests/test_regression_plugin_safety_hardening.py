"""Regression tests for plugin safety hardening.

These prose-level tests pin the safety fixes from the plugin audit:
- Codex CLI prompts must not interpolate user/file content into double-quoted
  shell arguments.
- Heredocs that contain untrusted prompt text must not use fixed delimiters.
- /athanor:work stop-phrase redispatch must be capped.
- /athanor:setup embedded fallback must not resurrect deprecated ghost model keys.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"
SETUP_SKILL = REPO_ROOT / "skills" / "setup" / "SKILL.md"


def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_embedded_fallback_json(content: str) -> dict:
    fallback_start = content.index("#### Embedded fallback")
    fence_start = content.index("```json", fallback_start) + len("```json")
    fence_end = content.index("```", fence_start)
    return json.loads(content[fence_start:fence_end])


def test_codex_invocations_use_prompt_files_not_inline_double_quotes():
    """Codex dispatch must pass prompt text via prompt files + stdin."""
    content = _load(PLAN_SKILL)

    assert 'codex exec --full-auto --ephemeral -o ".athanor/sessions/{session-id}/plan-b.md" < ".athanor/sessions/{session-id}/codex-plan-b.prompt.md"' in content
    assert 'codex exec --full-auto --ephemeral -o ".athanor/sessions/{session-id}/review-of-a.md" < ".athanor/sessions/{session-id}/codex-review-a.prompt.md"' in content

    forbidden_fragments = [
        "codex exec --full-auto --ephemeral -o .athanor/sessions/{session-id}/plan-b.md \\\"Create",
        "codex exec --full-auto --ephemeral -o .athanor/sessions/{session-id}/review-of-a.md \\\"Critically",
        "$(cat .athanor/sessions/{session-id}/plan-a.md)",
    ]
    offenders = [fragment for fragment in forbidden_fragments if fragment in content]
    assert not offenders, (
        "Codex invocation still contains shell-expanded inline prompt fragments: "
        f"{offenders}"
    )


def test_untrusted_codex_heredoc_requires_unique_delimiter():
    """User-controlled Plan B prompt must not rely on a fixed heredoc delimiter."""
    content = _load(PLAN_SKILL)
    plan_b_start = content.index("#### Deep Tier: Planner B (Codex)")
    plan_b_end = content.index("#### Deep Tier Fallback", plan_b_start)
    section = content[plan_b_start:plan_b_end]

    assert "fresh high-entropy" in section
    assert "does not appear anywhere in the user request or" in section
    assert "Never use a fixed delimiter" in section
    assert "<<'{unique-delimiter}'" in section
    assert "ATHANOR_CODEX_PROMPT" not in section


def test_codex_review_paths_are_quoted_and_no_command_substitution_cat():
    """Plan A review must copy file content safely instead of shell-expanding it."""
    content = _load(PLAN_SKILL)
    review_start = content.index("#### Deep Tier: Reviewer B (Codex)")
    review_end = content.index("#### Deep Tier Fallback: Reviewer B", review_start)
    section = content[review_start:review_end]

    assert 'cat ".athanor/sessions/{session-id}/plan-a.md" >> ".athanor/sessions/{session-id}/codex-review-a.prompt.md"' in section
    assert 'cat .athanor/sessions/{session-id}/plan-a.md' not in section
    assert "\n$(cat" not in section
    unquoted_redirects = re.findall(r"< \.athanor/sessions/", section)
    assert not unquoted_redirects


def test_work_stop_phrase_redispatch_is_once_only_and_then_failure():
    """Stop-phrase defense must not allow unlimited worker redispatch."""
    content = _load(WORK_SKILL)
    stop_phrase_section_start = content.index("**Stop-phrase check:**")
    stop_phrase_section_end = content.index("**If success:**", stop_phrase_section_start)
    section = content[stop_phrase_section_start:stop_phrase_section_end]

    assert "re-dispatch ONCE only" in section
    assert "mark the subtask as failure" in section


def test_setup_embedded_fallback_is_valid_json_without_debugger_ghost_keys():
    """The fallback JSON in setup/SKILL.md must be valid and current-template shaped."""
    content = _load(SETUP_SKILL)
    fallback_config = _extract_embedded_fallback_json(content)
    fallback_text = json.dumps(fallback_config)

    assert "debugger" not in fallback_config["models"]
    assert "debugger-tracer" not in fallback_config["models"]
    assert "reviewer" in fallback_config["models"]
    assert "hooks" in fallback_config
    assert "review" in fallback_config
    assert "..." not in fallback_text
