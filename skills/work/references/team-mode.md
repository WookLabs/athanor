# Team Mode Reference (Wave-Based Parallel Execution)

Detailed reference for `/athanor:work` `--team` mode wave semantics.
Cross-linked from `skills/work/SKILL.md` §Team Mode overview.

When `--team` is specified, subtasks run in parallel waves.

## Wave Grouping (Leader performs this)

Group subtasks into waves based on `depends_on`:

```
Algorithm:
1. remaining = all subtasks
2. wave_number = 1
3. while remaining is not empty:
     wave = subtasks whose depends_on are ALL already completed or in prior waves
     cap wave at waveSize (from athanor.json, default 3)
     if wave is empty → error: circular dependency
     assign wave_number to these subtasks
     move them from remaining to assigned
     wave_number += 1
```

Example:
```
Subtasks: [1(no dep), 2(no dep), 3(dep:1), 4(dep:1,2), 5(dep:4)]
waveSize: 3

Wave 1: [1, 2]       ← no dependencies, run in parallel
Wave 2: [3, 4]       ← depend on wave 1, run in parallel
Wave 3: [5]          ← depends on wave 2
```

## Wave Execution

```
for each wave:
    1. Announce: "Wave {N}/{total}: subtasks [{ids}]"

    2. Dispatch ALL wave subtasks simultaneously:
       - Each gets the same executor dispatch prompt as solo mode
       - PLUS: previous_discoveries from prior waves

    3. Wait for ALL workers in this wave to complete

    4. Process results:
       - Update TodoList for each completed/failed subtask
       - Save discoveries to .athanor/sessions/{id}/discoveries/
       - Append to work-log.md

    5. Build discovery relay for next wave:
       - Read all discovery files from this wave
       - Compress into a brief summary (under 300 words)
       - This summary is injected into next wave workers' prompts

    6. Circuit breaker check:
       - If ALL subtasks in a wave failed → trip
       - Individual failures within a wave don't trip (other workers may succeed)

    7. Handle failures:
       - Failed subtasks: ask user — retry in next wave? skip? abort?
       - If a failed subtask blocks later subtasks: warn user

    8. v0.16.0 multi-status wave semantics — process each non-success
       status per Step 2b rules, then apply the wave-level rules below
       before advancing to the next wave.
```

## Wave-Level Multi-Status Semantics (v0.16.0)

Solo mode processes statuses one subtask at a time (see Step 2b). Team mode
runs subtasks in parallel within a wave, so the leader must additionally
decide what happens to *later waves* when a current-wave worker returns one
of the three new statuses. The rules below are consistent with the solo-mode
semantics in Step 2b — wave grouping only changes the unit of work, not the
status meanings.

**`done_with_concerns` in a wave:**
- The wave **continues normally**. The subtask is marked complete (same as
  solo mode); the wave does not pause.
- The worker's `concerns: [...]` list is appended to the wave's discovery
  relay under a dedicated `## Concerns from Wave {N}` section. Next-wave
  workers receive these concerns in their dispatch packet alongside
  `previous_discoveries` so downstream work can react (e.g., a follow-up
  subtask that touches the same module sees the deprecated-API concern).
- The `recommend_review = true` flag from Step 2b still triggers the
  `/athanor:review` recommendation in the Step 6 final summary.

**`needs_context` in a wave:**
- The current wave **completes** all in-flight workers (do not kill mid-flight
  — same cancellation rule as solo mode). The leader then **pauses dispatch
  of any later wave whose subtasks transitively depend on the
  `needs_context` subtask** until the context is resolved.
- Other in-flight subtasks in the same wave that complete normally
  (`done` / `done_with_concerns` / `blocked`) are processed via their own
  branches and their results are saved.
- Later waves that do NOT depend on the paused subtask MAY proceed (the
  leader walks `depends_on` transitively; only the dependent sub-DAG pauses).
- The user prompt described in Step 2b (`needs_context` handler) is the
  resolution path. On user response, re-dispatch the paused subtask with
  injected context; once it completes, the previously-paused dependent
  waves resume in order.
- Thin Leader compliance carries through to team mode: the leader still
  does NOT read project source to resolve the context request.

**`blocked` in a wave:**
- The blocked subtask is pushed to `blocked_queue[]` (same as solo mode).
  Only the **downstream subtasks that `depends_on` the blocked subtask**
  (transitively) are also marked blocked — this matches solo-mode dependent
  propagation. Other in-flight and later-wave subtasks proceed normally.
- The wave itself does NOT pause; other workers in the same wave continue
  to completion. Later waves that have no dependency on the blocked subtask
  also dispatch normally.
- The `blocked_queue` is drained at the end of the run in Step 3, exactly
  the same as solo mode. The user sees all external blockers together at
  the end rather than per-wave prompts.

## Parallel Dispatch (within a wave)

Dispatch all wave subtasks in a **single message with multiple Agent calls**:

```
// Single message with N parallel Agent calls
Agent({ description: "executor: subtask 1", model: "opus", prompt: "..." })
Agent({ description: "executor: subtask 2", model: "opus", prompt: "..." })
Agent({ description: "executor: subtask 3", model: "opus", prompt: "..." })
```

## Discovery Relay

After each wave, compile discoveries into a relay brief:

```markdown
## Discoveries from Wave {N}

### Subtask {id}: {title}
- {key discovery or change}

### Subtask {id}: {title}
- {key discovery or change}
```

Next wave workers receive this in their dispatch packet under
`previous_discoveries`.

## Team Mode Announcement (per wave)

```
Wave {N}/{total}
├── Subtask {id}: {title} ── dispatching...
├── Subtask {id}: {title} ── dispatching...
└── Subtask {id}: {title} ── dispatching...
```

After wave completes:
```
Wave {N}/{total} complete
├── Subtask {id}: ✓
├── Subtask {id}: ✓
└── Subtask {id}: ✗ (failure reason)
Discoveries relayed: {count} items
```
