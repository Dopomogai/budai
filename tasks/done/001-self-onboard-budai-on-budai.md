---
id: 001
title: Self-onboard budai on budai
type: feature
scope: dogfood
priority: P1
status: done
fan-out: 1
needs-architect: true
plan-approved: true
result-approved: true
trivial: false
depends-on: []
blocks: [002, 003]
sources: [F013]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-10T16:30:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
result-commit: 4acbb12
archived-note: Onboarding work completed by parallel agent at commit 4acbb12 before task-001 was archived. Backfilled at journey-4 close as part of schema cleanup sweep.
---

# Task 001: Self-onboard budai on budai

## Objective
Make budai usable as its own consumer repo without duplicating the registry source of truth.

## User story
As a budai maintainer, I want the repo to contain dogfood configuration and task structure, so that improvements can run through budai's own workflow.

## Acceptance criteria
- AC1: `.agents/manifest.yaml` exists with `registry-source: self` and `tasks-layout: legacy-four-folder`.
- AC2: `.agents/local/conventions.md`, `.agents/local/untouchables.md`, and `.agents/local/glossary.md` describe budai-specific policy.
- AC3: Root `AGENTS.md` and `CLAUDE.md` orient future agents to the dogfood workflow.
- AC4: `tasks/{backlog,todo,in-progress,done}` plus `tasks/README.md` and `tasks/TEMPLATE.md` exist.
- AC5: `findings.md` remains the audit trail for promoted findings.

## Context
- Source finding: F013.
- This task is the bootstrap task for all other dogfood backlog items.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
