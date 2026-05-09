---
id: 006
title: Manifest parser and example compatibility
type: bug
scope: bin
priority: P1
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [002, 003]
blocks: [007, 008, 009, 010, 011]
sources: []
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: fix-bug
bundle-budget: 80000
retry-budget: 2
---

# Task 006: Manifest parser and example compatibility

## Objective
Align manifest examples, docs, and parser behavior so real manifests parse predictably.

## User story
As a consumer repo maintainer, I want manifest fields and examples to match what the CLI accepts, so that adopting budai does not require reverse-engineering parser quirks.

## Acceptance criteria
- AC1: Pinned roles in examples parse correctly.
- AC2: Fields such as `tasks-layout`, `registry-source`, `src-roots`, workflow defaults, and lockfile expectations are represented in parser structures.
- AC3: Minimal and full example manifests round-trip through parser tests.
- AC4: Invalid manifest items produce clear validation errors.

## Context
- Repo analysis found `examples/manifest-full.yaml` uses pinned role mappings that the current parser stringifies incorrectly.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
