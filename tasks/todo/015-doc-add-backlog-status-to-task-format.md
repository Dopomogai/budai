---
id: 015
title: Add backlog status to docs/11-task-format.md
type: docs
scope: docs
priority: P3
status: open
fan-out: 1
needs-architect: false
plan-approved: false
result-approved: false
trivial: true
depends-on: []
blocks: []
sources: [T004-judge-followup]
created: 2026-05-09T16:00:00Z
created-by: judge
updated: 2026-05-09T16:00:00Z
workflow: ship-feature
bundle-budget: 8000
retry-budget: 1
---

# Task 015: Add backlog status to docs/11-task-format.md

## Objective
Close the code-vs-doc drift introduced by task-004: `bin/lib/task_schema.py` lists `backlog` in `VALID_STATUSES` and `bin/task` accepts `--status backlog`, but `docs/11-task-format.md` still describes only the original 8-status state machine. Add the `backlog` status row and document its allowed transitions.

## User story
As a contributor reading the canonical task-format spec, I want `backlog` to be documented alongside the other statuses so I'm not surprised when `bin/task --status backlog` works.

## Acceptance criteria
- AC1: `docs/11-task-format.md` lists `backlog` in the status enumeration with a one-line description ("pre-promotion holding state; not yet ready for active work").
- AC2: The state-machine table or transition listing shows `backlog → open` and `backlog → abandoned` as legal transitions, matching `STATUS_TRANSITIONS` in `bin/lib/task_schema.py`.
- AC3: An example task elsewhere in the doc (or a new mini-example) uses `status: backlog` to show it in context.

## Context
- Source: T004-judge-followup. Flagged in `.agents/council/004/verdict.md` as INFO-severity outstanding concern.
- Related code: `bin/lib/task_schema.py` (`VALID_STATUSES`, `STATUS_TRANSITIONS`).
- Related ADR: `memory/decisions/0001-task-cli-layout-and-validation.md` — explicitly defers this doc update to a follow-up.
