# Athanor Organization Operating Model

This document defines the company-like operating model used by Athanor when an issue,
proposal, incident, or improvement request enters the system.

The model is intentionally read-only by default. It maps existing Athanor commands and
knowledge artifacts into an explicit office/stage graph, so future work can be routed,
reviewed, verified, released, and learned from without adding live listeners, registered
agents, external telemetry, or irreversible automation.

## Operating Principles

- Every stage has one accountable owner role and a receipt requirement.
- Leaders coordinate work and record decisions; they do not mutate user files by default.
- Research and planning must leave enough evidence for later review.
- Verification and release are separate from execution.
- Lessons become policy only through a promotion loop owned by learning governance.

## Machine-Readable Model

<!-- athanor:organization-operating-model v=1 -->

```json
{
  "schema_version": 1,
  "model_id": "athanor-organization-operating-model",
  "last_reviewed": "2026-06-18",
  "safety": {
    "mutates_files_by_default": false,
    "external_telemetry": false,
    "auto_runtime_launch": false,
    "default_live_listener": false,
    "registered_agent_additions": 0,
    "irreversible_actions": 0
  },
  "offices": [
    {
      "id": "product-intake",
      "title": "Product and Intake Office",
      "roles": [
        "intake-lead",
        "requirements-steward"
      ]
    },
    {
      "id": "research",
      "title": "Research Office",
      "roles": [
        "research-lead",
        "debug-analyst"
      ]
    },
    {
      "id": "architecture",
      "title": "Architecture Office",
      "roles": [
        "planner",
        "critic",
        "design-reviewer"
      ]
    },
    {
      "id": "execution",
      "title": "Execution Office",
      "roles": [
        "executor",
        "codex-dispatcher"
      ]
    },
    {
      "id": "qa-verification",
      "title": "QA and Verification Office",
      "roles": [
        "reviewer",
        "verification-lead"
      ]
    },
    {
      "id": "release",
      "title": "Release Office",
      "roles": [
        "releaser",
        "ci-watcher"
      ]
    },
    {
      "id": "learning-governance",
      "title": "Learning Governance Office",
      "roles": [
        "learner",
        "cleaner",
        "policy-steward"
      ]
    }
  ],
  "stages": [
    {
      "id": "intake",
      "order": 1,
      "title": "Intake",
      "office": "product-intake",
      "owner_role": "intake-lead",
      "entry_criteria": [
        "A user request, issue, incident, or improvement proposal exists."
      ],
      "required_artifacts": [
        "Captured request summary",
        "Known constraints and requested outcome"
      ],
      "exit_criteria": [
        "The work item has an initial scope, priority, and routing decision."
      ],
      "escalation_conditions": [
        "The request changes safety posture, asks for irreversible automation, or lacks a clear owner."
      ],
      "receipt_required": true,
      "leader_write_scope": "infrastructure-only",
      "command_mappings": [
        "/athanor:setup"
      ]
    },
    {
      "id": "triage",
      "order": 2,
      "title": "Triage",
      "office": "product-intake",
      "owner_role": "requirements-steward",
      "entry_criteria": [
        "The intake record is available."
      ],
      "required_artifacts": [
        "Impact classification",
        "Risk classification",
        "Routing notes"
      ],
      "exit_criteria": [
        "The item is accepted, deferred, rejected, or escalated with a recorded reason."
      ],
      "escalation_conditions": [
        "The item conflicts with existing policy or requires live runtime capability."
      ],
      "receipt_required": true,
      "leader_write_scope": "none",
      "command_mappings": []
    },
    {
      "id": "requirements",
      "order": 3,
      "title": "Requirements",
      "office": "product-intake",
      "owner_role": "requirements-steward",
      "entry_criteria": [
        "The item has passed triage."
      ],
      "required_artifacts": [
        "Acceptance criteria",
        "Non-goals",
        "Open questions or assumptions"
      ],
      "exit_criteria": [
        "The expected behavior and validation method are concrete enough to plan."
      ],
      "escalation_conditions": [
        "Acceptance criteria cannot be stated without new user input."
      ],
      "receipt_required": true,
      "leader_write_scope": "artifact-only",
      "command_mappings": [
        "/athanor:discuss"
      ]
    },
    {
      "id": "research",
      "order": 4,
      "title": "Research",
      "office": "research",
      "owner_role": "research-lead",
      "entry_criteria": [
        "Requirements are stable enough to investigate."
      ],
      "required_artifacts": [
        "Source notes",
        "Comparable systems",
        "Evidence ledger references"
      ],
      "exit_criteria": [
        "The decision space and tradeoffs are documented."
      ],
      "escalation_conditions": [
        "Evidence contradicts the requested direction or the work depends on unstable external facts."
      ],
      "receipt_required": true,
      "leader_write_scope": "artifact-only",
      "command_mappings": [
        "/athanor:analyze",
        "/athanor:debug"
      ]
    },
    {
      "id": "planning",
      "order": 5,
      "title": "Planning",
      "office": "architecture",
      "owner_role": "planner",
      "entry_criteria": [
        "Research and requirements identify a feasible path."
      ],
      "required_artifacts": [
        "Implementation plan",
        "Risk list",
        "Verification plan"
      ],
      "exit_criteria": [
        "The plan is sequenced, scoped, and testable."
      ],
      "escalation_conditions": [
        "The plan requires a new runtime, new registered agent, or irreversible mutation path."
      ],
      "receipt_required": true,
      "leader_write_scope": "artifact-only",
      "command_mappings": [
        "/athanor:plan"
      ]
    },
    {
      "id": "design-review",
      "order": 6,
      "title": "Design Review",
      "office": "architecture",
      "owner_role": "design-reviewer",
      "entry_criteria": [
        "A plan exists and the blast radius is known."
      ],
      "required_artifacts": [
        "Design notes",
        "Rejected alternatives",
        "Interface or gate contract"
      ],
      "exit_criteria": [
        "The design is approved, revised, or stopped with a recorded decision."
      ],
      "escalation_conditions": [
        "The design changes command semantics, persistence, trust boundaries, or CI policy."
      ],
      "receipt_required": true,
      "leader_write_scope": "artifact-only",
      "command_mappings": []
    },
    {
      "id": "execution",
      "order": 7,
      "title": "Execution",
      "office": "execution",
      "owner_role": "executor",
      "entry_criteria": [
        "Design review is complete or explicitly waived with a reason."
      ],
      "required_artifacts": [
        "Code or documentation changes",
        "Focused tests",
        "Updated local artifacts"
      ],
      "exit_criteria": [
        "The implementation is complete enough for independent verification."
      ],
      "escalation_conditions": [
        "Execution discovers scope growth, ambiguous ownership, or unsafe default behavior."
      ],
      "receipt_required": true,
      "leader_write_scope": "infrastructure-only",
      "command_mappings": [
        "/athanor:work"
      ]
    },
    {
      "id": "verification",
      "order": 8,
      "title": "Verification",
      "office": "qa-verification",
      "owner_role": "verification-lead",
      "entry_criteria": [
        "Execution has produced artifacts to verify."
      ],
      "required_artifacts": [
        "Test output",
        "Gate output",
        "Known residual risk"
      ],
      "exit_criteria": [
        "Required checks pass or failures are documented with next action."
      ],
      "escalation_conditions": [
        "A failure affects release safety, evidence integrity, or command routing."
      ],
      "receipt_required": true,
      "leader_write_scope": "none",
      "command_mappings": [
        "/athanor:review"
      ]
    },
    {
      "id": "release",
      "order": 9,
      "title": "Release",
      "office": "release",
      "owner_role": "releaser",
      "entry_criteria": [
        "Verification has passed or the risk exception is explicit."
      ],
      "required_artifacts": [
        "Changelog entry",
        "CI gate reference",
        "Release or merge decision"
      ],
      "exit_criteria": [
        "The release state is recorded and consumers can find the new behavior."
      ],
      "escalation_conditions": [
        "CI is unavailable, required checks are missing, or the release path mutates external state."
      ],
      "receipt_required": true,
      "leader_write_scope": "infrastructure-only",
      "command_mappings": [
        "/athanor:lfg"
      ]
    },
    {
      "id": "postmortem",
      "order": 10,
      "title": "Postmortem",
      "office": "learning-governance",
      "owner_role": "learner",
      "entry_criteria": [
        "Release, failure, or abandonment has produced a learning opportunity."
      ],
      "required_artifacts": [
        "What changed",
        "What failed or surprised us",
        "Candidate lesson"
      ],
      "exit_criteria": [
        "The lesson is recorded, rejected, or promoted to a candidate policy."
      ],
      "escalation_conditions": [
        "The same failure repeats or the lesson implies a new mandatory gate."
      ],
      "receipt_required": true,
      "leader_write_scope": "artifact-only",
      "command_mappings": []
    },
    {
      "id": "memory-update",
      "order": 11,
      "title": "Memory Update",
      "office": "learning-governance",
      "owner_role": "policy-steward",
      "entry_criteria": [
        "A postmortem lesson or stable policy update exists."
      ],
      "required_artifacts": [
        "Updated memory artifact",
        "Promotion state",
        "Retirement or cleanup note when applicable"
      ],
      "exit_criteria": [
        "Future similar work can reuse the decision, policy, or gate result."
      ],
      "escalation_conditions": [
        "A memory update would hide unresolved risk or create stale policy."
      ],
      "receipt_required": true,
      "leader_write_scope": "artifact-only",
      "command_mappings": [
        "/athanor:lfg-goal"
      ]
    }
  ],
  "promotion_loop": {
    "states": [
      "incident",
      "lesson",
      "candidate_policy",
      "policy",
      "gate_candidate",
      "gate",
      "retired"
    ],
    "owner_office": "learning-governance"
  },
  "required_refs": [
    "README.md",
    "CLAUDE.md",
    "docs/package-knowledge-index.md",
    "docs/harness-decision-ledger.md",
    "docs/architecture/2026-06-18-workflow-loop-harness-p26-research.md",
    "docs/organization-operating-model.md",
    "docs/organization-work-item-registry.md",
    "docs/organization-stage-receipts.md",
    "docs/policy-promotion-ledger.md",
    "docs/organization-score.md",
    "schemas/organization-operating-model-report.schema.json",
    "schemas/organization-work-item-registry-report.schema.json",
    "schemas/organization-stage-receipt.schema.json",
    "schemas/organization-stage-receipt-report.schema.json",
    "schemas/policy-promotion-ledger-report.schema.json",
    "schemas/organization-score-report.schema.json",
    "skills/lfg/SKILL.md",
    "skills/lfg-goal/SKILL.md",
    "scripts/gates/organization_operating_model.py",
    "scripts/gates/organization_work_item_registry.py",
    "scripts/gates/organization_stage_receipt.py",
    "scripts/gates/policy_promotion_ledger.py",
    "scripts/gates/organization_score.py"
  ]
}
```

## Per-cycle overlay (relocated from lfg / lfg-goal skills)

`/athanor:lfg` and `/athanor:lfg-goal` align each run/cycle with this model
instead of restating it inline. The detail below was relocated here so the
hot-path skills carry only a short pointer.

**How the pipeline maps.** The existing LFG 9-step pipeline is routed through
the office/stage graph above: intake, requirements, research, planning,
design-review, execution, verification, release, postmortem, and
memory-update. `/athanor:lfg-goal` treats the same graph as the lifecycle for
goal work — intake/triage shape the goal, requirements/research stabilize the
next cycle, planning/design-review approve execution, verification/release
check the shipped result, and postmortem/memory-update feed learning
governance. The overlay clarifies accountable owner roles and keeps the
existing receipt obligations explicit; it does **not** add a default live
listener, registered agents, or external telemetry, and each cycle stays
receipt-driven.

**Organization-stage handoff (preview-only by default).** Once the relevant
LFG/cycle evidence (or a validator-backed cycle receipt) exists, an
organization-stage handoff can be recorded through
`scripts/gates/organization_stage_receipt.py`. The adapter is preview-only
unless `--emit` is present (omit `--emit` to preview without writes), and it
mutates work-item state only with `--apply-work-item-update`.

**Policy promotion.** Goal-level or postmortem lessons that should become
operating policy or a gate must flow through `docs/policy-promotions/*.json`
and be validated with `scripts/gates/policy_promotion_ledger.py` before being
treated as active policy. Do not treat prose lessons as policy without that
promotion state.
