---
id: 009
title: Real Claude runner dispatch
type: feature
scope: runner
priority: P2
status: open
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
updated: 2026-05-10T16:00:00Z
deferred: true
deferred-reason: host-agent-tool-sufficient-through-journey-4
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

## Deferral context (2026-05-10, after journey 4)

**Status: deferred. Not blocking current usage.**

Through journey 4 (task-021 medium-track, 2026-05-10), the placeholder `dispatch_claude_code` has been sufficient because the **host Claude Code session is itself the runner** — `bin/agent run` prints a placeholder command line; the host session reads it and spawns the role-agent via its `Agent` tool. Four journeys (canvas-000, budai-004, budai-020, budai-021) have shipped real commits this way.

This task graduates budai from "a spec that a host Claude Code session follows" to "a self-contained CLI that orchestrates Claude on its own." That graduation is **only required when** at least one of the following becomes load-bearing:

1. **Unattended runs** — running budai on a schedule (cron, GitHub Actions) without a human at the keyboard.
2. **Multi-host deployment** — running budai on a server, a teammate's machine, or in CI where there's no Claude Code session to host the orchestration.
3. **Real permission enforcement** — task-010 (`--allowed-tools` denial) needs an actual subprocess to enforce against. Today, "permissions" are whatever Claude Code's settings.local.json says.
4. **Automated stats capture** — task-018 (per-role `stats.json` emission) needs the runner to observe its own subprocess's exit code, token count, and timing. Today the host session's Claude (me) writes the journey JSON by hand.

Until one of those four pressures becomes real, the host-Agent-tool pattern is the right shape: cheap, debuggable, human-in-the-loop by default. Re-prioritize this task to P0 the moment any of those four conditions becomes a genuine blocker, not before.

**What stays implicitly blocked while task-009 sleeps:**
- task-010 (runner permission enforcement) — also defers.
- task-018 (stats emission) — can ship the schema and aggregation logic against hand-written records, but token counts will be `null` until a real subprocess is metering them.
- task-019 (workflow taxonomy) — does NOT depend on this. Workflow files can declare role sequences and gate-rules without a real runner; the runner reads them whether dispatch is real or placeholder.

**What still works while task-009 sleeps:**
- Every workflow shape (fast-track, medium-track, ship-feature) on any consumer repo, as long as the human runs it through Claude Code as the host.
- All retrospectives, ADR generation, evidence capture, manual stats records.
- Onboarding new consumer repos (provided each new consumer also runs through a host Claude Code session).

**Re-evaluation trigger:** when planning journey 6+ if any of the four pressures above has surfaced, OR after 5 more journeys in a row without it surfacing (in which case re-confirm the deferral is still right and consider closing this task as "wrong-shape" with a fresh task replacing it).

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
