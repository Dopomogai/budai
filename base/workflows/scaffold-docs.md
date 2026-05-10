---
workflow: scaffold-docs
version: 0.1.0
applicable-task-types: [refactor, feature]
default-fan-out: 1
default-retry-budget: 2
peer-reviewers: 0
stability: experimental
roles: [librarian, implementer, verifier]
entry-criteria:
  - task is pure documentation work (no code changes)
skipped-artifacts: []
auto-approve-when: never
gate-rules:
  librarian: human
  implementer: human
  verifier: human
human-gates: [end-of-librarian, end-of-implementer, end-of-verifier]
---

# scaffold-docs

## Status

**STUB.** This workflow is named in the v1 taxonomy but has not yet been empirically validated through a journey. Before using it, run one task end-to-end with this shape, write a retrospective in `tasks/done/<id>-scaffold-docs-retrospective.md`, and flesh out the body to match the standard six-section format (Trigger, Role sequence, Hand-off contracts, Escalation rules, Auto-spawned follow-ups, Variants).

Proposed role sequence per task-019 Workflow proposals table: L (index) → I → V (link-check).

Proposed "when to use": Pure docs work with no code changes.

Proposed "skipped vs ship-feature": Skip Planner and Judge.
