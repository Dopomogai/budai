---
id: 011
title: Librarian sync implementation
type: feature
scope: sync
priority: P0
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [006]
blocks: [012]
sources: [F012]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 011: Librarian sync implementation

## Objective
Turn `bin/librarian sync` from a placeholder into a working registry sync command.

## User story
As a consumer repo maintainer, I want `librarian sync` to materialize pinned budai content, so that adopting or upgrading budai is reproducible.

## Acceptance criteria
- AC1: Sync can resolve `registry-source` and pinned `budai-version`.
- AC2: Sync copies registry `base/` into consumer `.agents/base/` without overwriting local policy.
- AC3: Sync writes `.agents/manifest.lock.yaml` with resolved versions.
- AC4: The command has a documented dry-run or preview behavior before destructive replacement.
- AC5: Network and credential requirements are documented.

## Context
- Source finding: F012.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
