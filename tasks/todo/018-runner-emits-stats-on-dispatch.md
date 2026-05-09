---
id: 018
title: Runner emits per-role stats.json on every dispatch
type: feature
scope: runner
priority: P1
status: open
fan-out: 1
needs-architect: false
plan-approved: false
result-approved: false
trivial: false
depends-on: [009]
blocks: []
sources: [F026, T004-judge-followup]
created: 2026-05-09T17:30:00Z
created-by: human
updated: 2026-05-09T17:30:00Z
workflow: ship-feature
bundle-budget: 60000
retry-budget: 2
---

# Task 018: Runner emits per-role stats.json on every dispatch

## Objective
Capture real per-role compute numbers (wall time, tool-call count, prompt + completion tokens, model used) on every `bin/agent run` dispatch so future task estimates are AI-led-empirical, not human-team-intuition.

## User story
As a budai operator estimating a new task, I want a stats database keyed by `{type, scope, fan-out, role}` that aggregates real measurements from past journeys, so my estimates are grounded in observed AI cost rather than inherited human-team conventions.

## Acceptance criteria
- AC1: After every `bin/agent run --role <r> --task <id> --tier <t>`, the runner writes `.agents/runs/<run-id>/stats.json` with: `{role, model, started, ended, wall-time-seconds, tool-calls, prompt-tokens, completion-tokens, total-tokens, exit-code}`. Fields the runner can't observe (token counts during a Phase 0 placeholder dispatch) are recorded as `null`, not omitted.
- AC2: After every Judge step on a successful task, the runner writes `.agents/stats/journeys/<NNN>-<consumer>-<task-slug>.json` aggregating the per-role stats files plus task metadata (`task-id`, `task-type`, `task-scope`, `workflow`, `fan-out`, `outcome`, `result-commit`, `findings-captured`, `follow-ups-spawned`).
- AC3: Librarian Sweeper mode reads all journey stats files and produces `.agents/stats/tasks.json` keyed by `{task-type, task-scope}` containing percentile distributions (p50, p90) of wall-time, tokens, and tool-calls per role.
- AC4: An `estimate-task` skill (or shortcut workflow — see task-013 region) takes a draft task and returns a token / time / cost estimate by looking up the matching `{type, scope}` row in `tasks.json` and scaling by complexity heuristics (file count, AC count). Estimates have a confidence interval based on sample size.
- AC5: Existing ac-mapping.json schema and Verifier output are unchanged — this task adds stats emission, not transformations.

## Context
- Source finding: F026 (estimation gap; Judge follow-up).
- Source data already on disk for journeys 001 and 002: `.agents/stats/journeys/001-canvasos-task-000.json` and `.agents/stats/journeys/002-budai-task-004.json`. These are hand-written seed records to validate the schema before the runner ships.
- Hard dependency: task-009 (real `dispatch_claude_code`). Without a real Claude subprocess invocation, token counts can't be captured. AC1's `null` fallback exists so this task can land partially before task-009; full data flow becomes real after.
- Soft dependency: task-007 (deterministic token math via tiktoken). Estimation works without it but is more accurate after.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
