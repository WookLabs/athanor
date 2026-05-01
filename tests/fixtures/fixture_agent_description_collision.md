---
name: athanor-collider
model: sonnet
description: Codebase exploration and structural inspection (LSP/Serena, Grep/Glob fallback). Dispatched by Athanor skills via inline prompt; also available standalone via @-mention.
tools:
  - Read
  - Grep
---

# Fixture — Agent Description Collision

This fixture file simulates the v0.6.2 regression class: an agent whose
`description` first-60-character prefix collides with an existing real
agent (here: athanor-analyst). The lint check
`agent_descriptions_unique_check` should flag this collision when a
caller adds this file to the agents directory under audit.

The colliding prefix in this fixture is the analyst's prefix.
