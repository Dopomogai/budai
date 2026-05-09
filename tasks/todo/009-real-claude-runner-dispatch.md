---
id: 009
title: Real Claude runner dispatch
type: feature
scope: runner
priority: P0
status: todo
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [004, 005, 006]
blocks: [010]
sources: [F008]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T00:00:00Z
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 009: Real Claude runner dispatch

## Objective
Replace placeholder Claude runner behavior with actual CLI dispatch and run capture.

## User story
As a budai operator, I want `bin/agent run --runner claude-code` to launch a real Claude Code run, so that unattended role execution is possible.

## Acceptance criteria
- AC1: Runner checks that `claude` is available before dispatch.
- AC2: Runner invokes Claude with system prompt file, model, working directory, output format, max turns, and resolved allowed tools.
- AC3: Stdout is captured to `runs/<run-id>/transcript.jsonl` and stderr/errors are recorded.
- AC4: Run metadata records role, task, runner, model tier, cwd, exit code, and timestamps.
- AC5: Exit code reflects the underlying runner result.

## Context
- Source finding: F008.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
