---
id: 003
title: Package CLI and add test harness
type: feature
scope: bin
priority: P0
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [001]
blocks: [004, 005, 006]
sources: []
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 003: Package CLI and add test harness

## Objective
Make the Python CLI dependency setup and validation path reliable from a fresh checkout.

## User story
As a contributor, I want a documented install path and tests for the CLI, so that commands fail because of code defects rather than missing local dependencies.

## Acceptance criteria
- AC1: CLI dependencies have a documented install/dev setup.
- AC2: Unused requirements are removed or justified.
- AC3: Unit tests cover manifest normalization, header parsing, path resolution, and other shared helpers.
- AC4: Smoke tests cover the main CLI entrypoints.
- AC5: A local test command or CI workflow is documented.

## Context
- `./bin/preflight --json` currently fails in a fresh environment when `PyYAML` is missing.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
