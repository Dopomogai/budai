---
id: 008
title: Deterministic bundle assembler and Librarian output
type: feature
scope: bundle
priority: P1
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [007]
blocks: []
sources: [F004, F005, F006, F007]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 008: Deterministic bundle assembler and Librarian output

## Objective
Move mechanical bundle assembly out of agent prose and into deterministic Python tooling.

## User story
As a Planner or Implementer, I want Librarian bundles to be deterministic and concise, so that agent tokens are spent on judgment rather than file embedding.

## Acceptance criteria
- AC1: Bundle assembly is handled by a Python helper that reads selected files, writes code fences, counts tokens, and emits bundle metadata.
- AC2: The Librarian produces structured file picks and notes rather than manually assembling the bundle body.
- AC3: `## Notes from Librarian` is appended to the task body when high-value findings are discovered during bundling.
- AC4: `bin/agent` or the relevant prompt path supports quiet default output and opt-in verbose reports.
- AC5: `build-task-bundle.md` contains self-contained relevance heuristics.

## Context
- Source findings: F004, F005, F006, F007.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
