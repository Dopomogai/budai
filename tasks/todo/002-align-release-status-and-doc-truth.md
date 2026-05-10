---
id: 002
title: Align release status and doc truth
type: docs
scope: docs
priority: P0
status: open
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
workflow: audit-repo
bundle-budget: 80000
retry-budget: 2
---

# Task 002: Align release status and doc truth

## Objective
Reconcile the public docs so users can tell what is specified, scaffolded, placeholder, and actually runnable.

## User story
As an adopter, I want the README and docs to be honest about current implementation status, so that I do not trust non-working commands or security claims.

## Acceptance criteria
- AC1: README, overview, changelog, examples, onboarding, and phase docs use one consistent release/status story.
- AC2: Placeholder commands and future behavior are clearly labeled at the point where they are mentioned.
- AC3: Examples reference paths and commands that exist or explicitly say they are future work.
- AC4: The changelog remains historically accurate while current docs point to the latest scaffold state.

## Context
- Discovered during repo analysis: README and overview still describe design-only status while changelog claims Phase 0 scaffold content exists.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
