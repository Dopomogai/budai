---
id: 021
title: Runner seeds worktree with task body, bundle, plan, and ADRs before role dispatch
type: feature
scope: runner
priority: P0
status: open
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [020]
blocks: []
sources: [F021]
created: 2026-05-09T18:00:00Z
created-by: human
updated: 2026-05-09T18:00:00Z
workflow: ship-feature
bundle-budget: 60000
retry-budget: 2
---

# Task 021: Runner seeds worktree with task body, bundle, plan, and ADRs before role dispatch

## Objective
Eliminate the "absolute-path injection" friction from journey 2: when the runner creates an Implementer/Verifier worktree branched from `main`, the task move + appended Plan section + new ADR + bundle file are all uncommitted in the main worktree, so the worktree can't see them. Today every downstream agent has to be told via prompt to read these via absolute paths back to the main worktree. Move that responsibility into the runner.

## User story
As an Implementer or Verifier agent, when I'm dispatched to my isolated worktree, I want the journey's task body (with current uncommitted plan), bundle, ADR(s), and any other journey-time inputs sitting in `.agents/runs/<run-id>/inputs/` inside my worktree, so I can read them via simple relative paths and operate as if I were a normal session — no absolute-path injection in my prompt.

## Acceptance criteria
- AC1: Before invoking `dispatch_claude_code`, the runner copies into the target worktree's `.agents/runs/<run-id>/inputs/`: (a) the live task `.md` file (current state, including any uncommitted Plan section), (b) the bundle file (filename-glob `<task-id>-*.bundle.*.md`), (c) any ADRs referenced from the plan's `## ADR` section, (d) the verifier's previous `failure.md` if this is a retry dispatch.
- AC2: The composed system prompt includes a `## Journey inputs` block at the top listing the seeded paths (relative to the worktree), so agents read inputs without external coordination.
- AC3: Inputs are copied, not symlinked — the agent's view of the inputs is frozen at dispatch time. Future edits in the main worktree don't leak into in-flight agents.
- AC4: When the journey closes (Judge step), the runner cleans up: `inputs/` directory is left in place for audit (it's under `.agents/runs/`, gitignored), but worktrees are removed via `git worktree remove`.
- AC5: A new `bin/lib/journey_state.py` (or extension to `runner.py`) owns the seed/teardown logic. Pure functions where possible; the runner orchestrates.
- AC6: Tests cover: (a) inputs are copied to the right path, (b) absent inputs are skipped without error (e.g., no ADR exists yet), (c) the seeded files match content on disk in the main worktree at dispatch time, (d) cleanup removes worktrees but preserves `inputs/`.
- AC7: F021 entry in `findings.md` is moved to Promoted with `→ task-021`.

## Context
- Source finding: F021 in `findings.md`.
- Journey 2 retrospective at `tasks/done/004-retrospective.md` documents three sites of absolute-path injection in agent prompts that wouldn't be needed if the runner seeded inputs.
- Soft depends on task-020 (resolution self-source fix) because task-019 (workflows) depends on both, and task-019 wants this seeding to apply to per-workflow input bundles.
- Alternative approach considered: commit the task move + plan to a per-task branch (`task-<id>-coordination`) and create worktrees off that branch. Rejected for v1: per-task branches multiply git noise and don't generalize well to retries (which need a fresh main-based worktree, not a stale coordination branch).

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
