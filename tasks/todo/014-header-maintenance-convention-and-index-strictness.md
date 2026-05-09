---
id: 014
title: Header maintenance convention and index strictness
type: feature
scope: headers
priority: P2
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [005]
blocks: []
sources: [F014]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 014: Header maintenance convention and index strictness

## Objective
Make source header maintenance explicit and make index generation strict enough to detect incomplete headers.

## User story
As a Librarian, I want source headers to stay accurate when code changes, so that bundles and audits use trustworthy metadata.

## Acceptance criteria
- AC1: `base/conventions.md` says stale source headers are bugs when code changes invalidate them.
- AC2: `base/roles/implementer.md` surfaces header maintenance as part of implementation workflow.
- AC3: Header parsing treats all required fields as required, not only `@purpose`.
- AC4: Generated index paths are repo-relative.
- AC5: Tests cover missing, partial, and complete headers.

## Context
- Source finding: F014.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
