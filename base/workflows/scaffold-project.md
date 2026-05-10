---
workflow: scaffold-project
version: 0.1.0
applicable-task-types: [feature]
default-fan-out: 1
default-retry-budget: 2
peer-reviewers: 0
stability: experimental
roles: [librarian, planner, implementer, verifier]
entry-criteria:
  - task is onboarding a new consumer repo to budai
skipped-artifacts: []
auto-approve-when: never
gate-rules:
  librarian: human
  planner: human
  implementer: human
  verifier: human
human-gates: [end-of-librarian, end-of-planner, end-of-implementer, end-of-verifier]
---

# scaffold-project

## Status

**STUB.** This workflow is named in the v1 taxonomy but has not yet been empirically validated through a journey. Before using it, run one task end-to-end with this shape, write a retrospective in `tasks/done/<id>-scaffold-project-retrospective.md`, and flesh out the body to match the standard six-section format (Trigger, Role sequence, Hand-off contracts, Escalation rules, Auto-spawned follow-ups, Variants).

Proposed role sequence per task-019 Workflow proposals table: L (audit) → P (architect) → I → V (smoke).

Proposed "when to use": Onboarding consumer repo to budai.

Proposed "skipped vs ship-feature": No follow-up auto-spawn.
