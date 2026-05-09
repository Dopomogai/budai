---
id: 007
title: Deterministic token and bundle basics
type: feature
scope: bundle
priority: P1
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [004, 005, 006]
blocks: [008]
sources: [F001, F002, F003]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 007: Deterministic token and bundle basics

## Objective
Replace approximate bundle token behavior with deterministic counting and token-aware naming.

## User story
As a Librarian, I want accurate token counts and discoverable bundle filenames, so that bundle budgets are visible and reliable.

## Acceptance criteria
- AC1: Token counting uses a real tokenizer helper instead of `chars / 4`.
- AC2: Default bundle budget is updated to `84000` wherever defaults are defined or documented.
- AC3: Bundle filenames include rounded token count as `<id>-<slug>.bundle.<NNk>.md`.
- AC4: Bundle discovery resolves tokenized bundle filenames by glob.
- AC5: Tests cover token counting fallback/behavior and bundle naming.

## Context
- Source findings: F001, F002, F003.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
