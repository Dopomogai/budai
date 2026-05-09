---
id: 004
title: Task CLI four-folder and schema validation
type: feature
scope: bin
priority: P1
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [002, 003]
blocks: [007, 008, 009, 010, 013]
sources: [F009]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 004: Task CLI four-folder and schema validation

## Objective
Teach `bin/task` to support the dogfood four-folder layout while preserving the documented standard layout.

## User story
As a maintainer, I want `bin/task` to create, list, move, and validate dogfood tasks, so that task files do not need to be managed manually.

## Acceptance criteria
- AC1: `tasks-layout: legacy-four-folder` makes new tasks land in `tasks/todo/`.
- AC2: `bin/task list` walks `backlog`, `todo`, `in-progress`, and `done`.
- AC3: `bin/task move` moves files across the four folders and updates frontmatter consistently.
- AC4: Standard `tasks/open` and `tasks/archive` behavior still works when the manifest omits `tasks-layout`.
- AC5: Task creation and status moves validate schema, dependencies, cycles, and legal transitions.

## Context
- Source finding: F009.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
