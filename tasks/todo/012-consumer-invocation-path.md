---
id: 012
title: Consumer invocation path
type: feature
scope: onboarding
priority: P2
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [011]
blocks: []
sources: [F010]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 012: Consumer invocation path

## Objective
Define and implement how consumer repos invoke budai CLI scripts after sync.

## User story
As a consumer repo maintainer, I want stable budai command paths, so that preflight, postflight, task, and librarian commands do not depend on brittle absolute paths.

## Acceptance criteria
- AC1: The chosen invocation model is implemented: synced copy, wrapper, symlink, or another explicit mechanism.
- AC2: Onboarding docs show exact commands for a consumer repo.
- AC3: The approach works for local development and non-interactive automation.
- AC4: The approach does not create multiple conflicting sources of truth for registry code.

## Context
- Source finding: F010.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
