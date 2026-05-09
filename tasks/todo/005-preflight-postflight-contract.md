---
id: 005
title: Preflight postflight contract
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
blocks: [007, 008, 009, 010, 013, 014]
sources: []
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: fix-bug
bundle-budget: 80000
retry-budget: 2
---

# Task 005: Preflight postflight contract

## Objective
Make `bin/preflight` and `bin/postflight` match their documented contracts or narrow the docs to implemented behavior.

## User story
As a role runner, I want preflight and postflight reports to be trustworthy, so that agents do not build on an invalid repo state.

## Acceptance criteria
- AC1: Preflight checks lockfile/base consistency, git state, untracked files, manifest presence, and strict source headers where applicable.
- AC2: Postflight checks tests, leftover artifacts, untracked outputs, and doc/index staleness where documented.
- AC3: JSON output remains stable and includes clear finding identifiers, severities, and messages.
- AC4: Missing dependencies produce actionable errors.
- AC5: Docs and skill specs match the actual check list.

## Context
- Repo analysis found several promised preflight/postflight checks are not implemented.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
