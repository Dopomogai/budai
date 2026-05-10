---
id: 022
title: Runner auto-flips task frontmatter on role completion per workflow gate-rules
type: feature
scope: runner
priority: P0
status: open
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [019, 020]
blocks: []
sources: [F015, F025]
created: 2026-05-09T18:00:00Z
created-by: human
updated: 2026-05-09T18:00:00Z
workflow: ship-feature
bundle-budget: 50000
retry-budget: 2
---

# Task 022: Runner auto-flips task frontmatter on role completion per workflow gate-rules

## Objective
Stop forcing humans to hand-edit task frontmatter at every workflow gate. Each role in a workflow has a deterministic exit-status (`open → planning` after Librarian, `planning → reviewing-plan` after Planner, etc.); the runner — not the agent, not the human — should perform the flip when a role's exit conditions are met, while still preserving the human approval gate at the steps the workflow declares require human review.

## User story
As a budai operator running a journey, I want frontmatter status, plan-approved, and result-approved fields to flip automatically when a role passes its exit conditions and the workflow's gate-rules don't require human intervention, so the only manual edits I make are the ones I'm actually deciding on (final approve/reject), not paperwork.

## Acceptance criteria
- AC1: After each role's `dispatch_claude_code` returns successfully, the runner reads the workflow's gate-rules to determine the next status; if the role's gate is auto-approve (per workflow), the runner flips `status:` and any associated boolean fields (`plan-approved`, `result-approved`) using `bin/lib/task_schema.py`'s `validate_transition` to ensure legality.
- AC2: When a workflow's gate-rule requires human approval, the runner halts and prints a single-line summary with the path to the artifact to review and the command to flip status manually (`python3 bin/task move <id> <new-status>`). This is the *only* human-frontmatter-edit moment.
- AC3: The auto-flip is logged in `.agents/runs/<run-id>/transitions.json` per role: `{role, exit-status, prev-task-status, new-task-status, timestamp, decision: "auto" | "human-required" | "auto-with-condition: <name>"}`. Audit trail.
- AC4: The runner refuses to flip if the role reported `failed` or escalated; in that case it surfaces the failure path and halts (no silent re-run).
- AC5: Existing `bin/task move <id> <status>` continues to work for human overrides — auto-flip and manual flip share the same code path in `task_schema`.
- AC6: Tests cover: (a) sequential auto-flips through `ship-feature` with all auto-approve gates yield the correct final status, (b) a workflow with a human-required gate halts with the right message, (c) a failed role doesn't trigger a flip, (d) `transitions.json` records the audit trail, (e) `validate_transition` rejects illegal flips even from the runner.
- AC7: F015 and F025 entries in `findings.md` are moved to Promoted with `→ task-022`.

## Context
- Source findings: F015 (CanvasOS retrospective) and F025 (budai journey 2 recurrence). Both document the same problem: 5–7 manual frontmatter flips per journey, all mechanical.
- Hard depends on task-019 (workflow gate-rules) — without per-workflow declarations, the runner has no source of truth for which gates auto-approve.
- Hard depends on task-020 (resolution.py self-source) — workflow file lookup goes through the resolver.
- Soft depends on task-021 (input seeding) — the auto-flipped task file should be in the worktree's seeded inputs so the next role sees the post-flip frontmatter.
- This is the largest single source of friction in journeys today (~7 of ~22 approvals in journey 2 were frontmatter edits). Closing it shrinks per-journey approval count by ~30%.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
