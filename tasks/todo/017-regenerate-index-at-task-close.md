---
id: 017
title: Regenerate .agents/index/ at task close (Sweeper)
type: bug
scope: librarian-sweeper
priority: P2
status: open
fan-out: 1
needs-architect: false
plan-approved: false
result-approved: false
trivial: false
depends-on: []
blocks: []
sources: [T004-judge-followup]
created: 2026-05-09T16:00:00Z
created-by: judge
updated: 2026-05-09T16:00:00Z
workflow: ship-feature
bundle-budget: 16000
retry-budget: 2
---

# Task 017: Regenerate .agents/index/ at task close (Sweeper)

## Objective
`.agents/index/` is empty/missing on the budai dogfood repo. The Librarian role spec says Sweeper mode runs the `regenerate-index` skill at task close to keep relevance signals current. That isn't happening — investigate why and either implement the skill, hook it into the close-of-task workflow, or document why it's deferred.

## User story
As a future Librarian invocation, I want `.agents/index/` to actually exist and be populated so relevance scoring during bundle assembly can use it instead of falling back to direct file inspection.

## Acceptance criteria
- AC1: Root cause identified — is the skill missing, the workflow hook missing, the trigger condition wrong, or all three? Document the finding.
- AC2: Either (a) the `regenerate-index` skill exists, runs at task close, and produces non-empty `.agents/index/` content, OR (b) a clear deferral with a tracked follow-up explaining why this is Phase N+1 work.
- AC3: At least one round-trip test: run the close-task workflow, observe `.agents/index/` was updated.

## Context
- Source: T004-judge-followup. Also flagged by Implementer (attempt-A.md "Flags and out-of-scope observations") and Verifier (non-AC findings, INFO).
- Related: Librarian role spec in `docs/03-roles.md` (Sweeper mode), skill catalog in `docs/04-skills.md`.
- This is infra debt that affects future tasks' bundle quality, not a blocker for any single task.
