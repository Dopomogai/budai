---
id: 010
title: Runner permission enforcement and security truth
type: feature
scope: runner
priority: P0
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [009]
blocks: []
sources: []
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 010: Runner permission enforcement and security truth

## Objective
Either implement documented runner permission enforcement or downgrade security claims to match reality.

## User story
As a security-conscious adopter, I want runner permissions and docs to agree, so that I can reason accurately about budai's security boundary.

## Acceptance criteria
- AC1: Runner resolves role permissions into actual allowed tool configuration where supported.
- AC2: Restricted Bash, CWD/path validation, and forbidden write protections are implemented or explicitly marked as future work.
- AC3: Security docs distinguish enforced guarantees from planned safeguards.
- AC4: Tests cover permission resolution and blocked/allowed command decisions.

## Context
- Repo analysis found security docs describe enforcement that the current runner does not implement.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
