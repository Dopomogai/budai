---
id: 013
title: First-class audit workflow
type: feature
scope: workflow
priority: P1
status: open
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [004, 005]
blocks: []
sources: [F011]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 013: First-class audit workflow

## Objective
Make audit tasks invokable directly instead of only as an implied sweeper behavior.

## User story
As a maintainer onboarding a repo, I want to run `audit-docs` as a first-class audit task, so that stale docs can be addressed before feature work begins.

## Acceptance criteria
- AC1: `type: audit` and `workflow: audit-repo` have a documented executable path.
- AC2: Audit workflow skips Implementer, Verifier, and Judge where appropriate.
- AC3: Librarian audit output writes findings into the task body and messages/ops when available.
- AC4: Follow-up task spawning rules for high/medium/low findings are documented.

## Context
- Source finding: F011.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
