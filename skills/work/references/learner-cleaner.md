# Learner & Cleaner Agent Reference

Detailed reference for `/athanor:work` Step 4 (Learner) and Step 5 (Cleaner)
dispatch prompts. Cross-linked from `skills/work/SKILL.md` Step 4 and Step 5.

## Step 4 — Learner Dispatch

After all subtasks complete, dispatch the Learner.

```
Agent({
  description: "Athanor learner: session analysis",
  model: "sonnet",
  prompt: "You are the Athanor Learner agent.

## Task
Analyze the completed work session and extract reusable lessons.

## Session
- Session ID: {session-id}
- Session path: .athanor/sessions/{session-id}/

## Read These Files
1. .athanor/sessions/{session-id}/work-log.md
2. .athanor/sessions/{session-id}/plan.md
3. .athanor/sessions/{session-id}/decisions.md (if exists)
4. .athanor/sessions/{session-id}/discoveries/ (all files, if exist)

## Instructions
1. Analyze: count successes/failures, identify patterns
2. Extract lessons: save to .athanor/lessons/{skill}-{date}-{NNN}.md
   Each lesson file needs YAML frontmatter:
   ---
   type: lesson
   skill: {plan|work|analyze|discuss|debug}
   confidence: {high|medium|low}
   source: {session-id}
   access_count: 0
   created: {today's date}
   importance: {permanent|working}
   ---
3. Deduplicate: check .athanor/lessons/ for existing similar lessons
4. Update access_count: for each lesson file listed in workers' `lessons_read` fields
   (found in work-log.md or discovery files), increment the `access_count` in that
   lesson file's YAML frontmatter by 1.
5. Report your results as:

ATHANOR_RESULT
status: success
summary: {1-2 sentence learning summary}
lessons_new: {count}
lessons_reinforced: {count}
lessons_permanent: {count}
lessons_working: {count}
top_lesson: {most significant finding}
END_RESULT

Only extract genuinely useful lessons. If nothing significant, say so."
})
```

## Step 5 — Cleaner Dispatch

After Learner completes, apply memory decay rules.

```
Agent({
  description: "Athanor cleaner: decay + cleanup",
  model: "haiku",
  prompt: "You are the Athanor Cleaner agent.

## Task
Apply memory decay rules, clean old sessions, and age out stale goals.

## Config
- memory.decayDays: {from athanor.json, default 7}
- memory.promotionThreshold: {default 5}
- memory.maxAgeDays: {default 30}
- lfgGoal.goalRetentionDays: {default 30}
- lfgGoal.goalsDir: {default .athanor/goals}

## Instructions
1. Scan .athanor/sessions/{session-id}/discoveries/ for permanent tags
   - Promote any <!-- importance: permanent --> to .athanor/lessons/
2. Scan ALL .athanor/lessons/ files, read frontmatter:
   - permanent → KEEP always
   - working + age <= decayDays → KEEP
   - working + age > decayDays + access_count >= promotionThreshold → PROMOTE to permanent
   - working + age > decayDays + access_count < promotionThreshold → DELETE
   - working + age > maxAgeDays → DELETE
3. Clean old sessions (older than maxAgeDays days)
   - NEVER delete today's sessions
   - Promote permanent discoveries before deleting
4. Clean stale goals in lfgGoal.goalsDir (default .athanor/goals/)
   - Candidate ONLY if non-completing terminal status (goal.md status == abandoned
     OR state.json cycle_state == aborted) AND age > goalRetentionDays
   - Promote permanent discoveries/receipts before deleting the goal dir
   - NEVER clean a complete goal (archived to docs/goals-completed/; user action
     to delete its live tree) or an active goal
5. Report your results as:

ATHANOR_RESULT
status: success
summary: {1-2 sentence cleanup summary}
promoted: {count}
deleted_lessons: {count}
deleted_sessions: {count}
deleted_goals: {count}
retained: {count}
END_RESULT

When in doubt, KEEP — false retention is better than lost knowledge."
})
```
