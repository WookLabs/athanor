# Contributing to Athanor

## Structure

- `skills/` — SKILL.md files define leader protocols (the actual implementation)
- `agents/` — Agent reference docs (keep in sync with SKILL.md dispatch prompts)
- `docs/` — Design, conventions, roadmap, state tracking
- `.claude-plugin/plugin.json` — Plugin manifest

## Adding a Skill

1. Create `skills/{name}/SKILL.md` with frontmatter (name, description)
2. Follow the Thin Leader pattern — leader dispatches, workers execute
3. Use ATHANOR_RESULT format for worker responses
4. Update CLAUDE.md commands table

## Conventions

See `docs/CONVENTIONS.md` for dispatch packet format, session file I/O,
discovery file naming, and lesson file conventions.

## Testing

Test with: `claude --plugin-dir /path/to/athanor -p "/athanor:{skill} {test input}"`
