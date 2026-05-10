---
workflow: prepare-task
version: 0.1.0
applicable-task-types: [feature, bug, refactor]
default-fan-out: 1
default-retry-budget: 1
peer-reviewers: 0
stability: experimental
roles: [librarian, planner]
entry-criteria:
  - task requires pre-staging; workflow halts after plan-approved
  - no Implementer runs in this workflow
skipped-artifacts: []
auto-approve-when: never
gate-rules:
  librarian: human
  planner: human
human-gates: [end-of-librarian, end-of-planner]
---

# prepare-task

## Status

**STUB.** This workflow is named in the v1 taxonomy but has not yet been empirically validated through a journey. Before using it, run one task end-to-end with this shape, write a retrospective in `tasks/done/<id>-prepare-task-retrospective.md`, and flesh out the body to match the standard six-section format (Trigger, Role sequence, Hand-off contracts, Escalation rules, Auto-spawned follow-ups, Variants).

Proposed role sequence per task-019 Workflow proposals table: L → P; halts after plan-approved.

Proposed "when to use": Pre-stage a task by building bundle + plan so the Implementer can be dispatched later (e.g., in a different session or after human scheduling).

Proposed "skipped vs ship-feature": Skip Implementer, Verifier, and Judge. Workflow ends at plan approval.
