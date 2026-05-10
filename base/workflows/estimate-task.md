---
workflow: estimate-task
version: 0.1.0
applicable-task-types: [feature, bug, refactor]
default-fan-out: 1
default-retry-budget: 1
peer-reviewers: 0
stability: experimental
roles: [librarian, planner]
entry-criteria:
  - task requires cost forecast before committing to implementation
  - output is a JSON estimate, not code
skipped-artifacts: []
auto-approve-when: never
gate-rules:
  librarian: human
  planner: human
human-gates: [end-of-librarian, end-of-planner]
---

# estimate-task

## Status

**STUB.** This workflow is named in the v1 taxonomy but has not yet been empirically validated through a journey. Before using it, run one task end-to-end with this shape, write a retrospective in `tasks/done/<id>-estimate-task-retrospective.md`, and flesh out the body to match the standard six-section format (Trigger, Role sequence, Hand-off contracts, Escalation rules, Auto-spawned follow-ups, Variants).

Proposed role sequence per task-019 Workflow proposals table: L → P (estimate skill).

Proposed "when to use": Cost forecast before committing to a task. Output is a JSON estimate (tokens, wall-time, human-gates, confidence) rather than a code change.

Proposed "skipped vs ship-feature": Skip Implementer, Verifier, and Judge. No code is written.
