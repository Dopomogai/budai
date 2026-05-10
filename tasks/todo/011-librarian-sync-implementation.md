---
id: 011
title: Librarian sync implementation
type: feature
scope: sync
priority: P1
status: open
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [006]
blocks: [012]
sources: [F012]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-10T16:45:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 011: Librarian sync implementation

## Objective
Turn `bin/librarian sync` from a placeholder into a working registry sync command.

## User story
As a consumer repo maintainer, I want `librarian sync` to materialize pinned budai content, so that adopting or upgrading budai is reproducible.

## Acceptance criteria
- AC1: Sync can resolve `registry-source` and pinned `budai-version`.
- AC2: Sync copies registry `base/` into consumer `.agents/base/` without overwriting local policy.
- AC3: Sync writes `.agents/manifest.lock.yaml` with resolved versions.
- AC4: The command has a documented dry-run or preview behavior before destructive replacement.
- AC5: Network and credential requirements are documented.

## Context
- Source finding: F012.

## Priority change (2026-05-10, after journey 4)

Originally P0 because F020 (`registry-source: self` resolution) made every dogfood run require a `.agents/base/` symlink workaround — sync was the long-term fix. **F020 was closed by task-020** (commit `8a869c3`); resolution.py now resolves `base/` at the repo root when `registry-source: self`, so the symlink is gone and dogfood runs work cleanly without sync.

Cross-repo `librarian sync` is now a **phase-6 / cross-repo concern**, not a daily-friction blocker:
- Single-consumer dogfood (budai itself) doesn't need sync.
- New consumer repos (e.g., CanvasOS, future Dopomogai stack) onboard via task-001's pattern, not via `librarian sync`.
- The only forcing function for sync is wanting **pinned, reproducible** budai content across multiple consumers — which is real but not urgent until we have ≥2 active long-running consumers.

**Re-prioritize to P0 when:**
- A second consumer repo is actively running budai journeys and version drift between consumers becomes a real bug, OR
- Onboarding becomes painful enough that "copy the registry by hand" is the friction.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
