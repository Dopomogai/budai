---
workflow: strategic-audit
version: 0.1.0
applicable-task-types: [audit, research]
default-fan-out: 1
default-retry-budget: 1
peer-reviewers: 0
stability: experimental
roles: [librarian, planner]
entry-criteria:
  - task is plan-the-backlog work; output is sub-tasks, not code
skipped-artifacts: []
auto-approve-when: never
gate-rules:
  librarian: human
  planner: human
human-gates: [end-of-librarian, end-of-planner]
---

# strategic-audit

## Status

**STUB.** This workflow is named in the v1 taxonomy but has not yet been empirically validated through a journey. Before using it, run one task end-to-end with this shape, write a retrospective in `tasks/done/<id>-strategic-audit-retrospective.md`, and flesh out the body to match the standard six-section format (Trigger, Role sequence, Hand-off contracts, Escalation rules, Auto-spawned follow-ups, Variants).

Proposed role sequence per task-019 Workflow proposals table: L (deep index) → P (writes roadmap, spawns sub-tasks).

Proposed "when to use": Plan-the-backlog work; output is a human-reviewed task list.

Proposed "skipped vs ship-feature": Skip Implementer, Verifier, and Judge entirely.
