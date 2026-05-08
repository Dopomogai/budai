---
skill: promote-lesson
version: 1.0.0
tier-override: haiku
inputs:
  - failure-records
  - existing-lessons
  - existing-conventions
outputs:
  - lesson-drafts
  - convention-proposals
  - improvement-tasks
breaking-changes-from: null
stability: stable
owners: [librarian]
---

# promote-lesson

Scan failure records for recurring patterns. Promote up the memory layers per `docs/06-memory.md`: run-local → role-scoped → repo-scoped → registry-scoped.

## When to use

Invoked by the Librarian during the post-task sweep and the daily scheduled run. Looks at `runs/*/failure.md` from recent task closures.

## Inputs

- **failure-records** — `runs/*/failure.md` from the last 30 days (configurable).
- **existing-lessons** — `memory/lessons/*.md`. Used to detect recurrences against already-tracked patterns.
- **existing-conventions** — `local/conventions.md` and `base/conventions.md`. Used to avoid drafting conventions that already exist.

## Procedure

1. Cluster failure records by pattern:
   - **Pattern key**: tuple of (failed-AC-class, suspected-cause-keywords, role).
   - Two failures share a pattern if their tuples match.
2. For each pattern with ≥3 failures in the last 30 days:
   - Check if a lesson for this pattern already exists in `existing-lessons`.
   - If yes: increment `recurrence-count`, update `last-recurred`, leave content alone.
   - If no: draft a new lesson per the schema in `docs/06-memory.md`:
     ```yaml
     ---
     lesson: <role>-<topic-slug>
     role: <role>
     created: <today>
     last-recurred: <today>
     recurrence-count: 3
     severity: <low | medium | high>
     status: active
     ---
     ```
     Body sections: Context (what failed, what cause), What to do (the rule), Why (the reason), Promotion candidacy (when/if to promote).
3. For lessons with cross-role recurrence:
   - If the same pattern appears in lessons for ≥2 different roles, draft a `convention-proposal` for `local/conventions.md`.
   - Open an `update-conventions-<topic>` task via `bin/task new --type=refactor` for human review.
4. For lessons with cross-repo recurrence:
   - Out of scope at Phase 0 (single-repo). Phase 6+: drafts a registry-level proposal via `bin/librarian publish`.
5. For lessons that haven't recurred in 90+ days:
   - Mark `status: obsolete` in the lesson file.
   - Don't delete; the file stays as record.
6. Output:
   - `lesson-drafts` — list of new lesson files written or existing lessons updated.
   - `convention-proposals` — drafts proposed (not auto-merged).
   - `improvement-tasks` — task IDs opened.

## Outputs

- **lesson-drafts** — files written to `memory/lessons/`.
- **convention-proposals** — list of drafts (write to `local/conventions-proposals/<NNNN>.md` for human review).
- **improvement-tasks** — task IDs in `tasks/open/`.

## Failure modes

- **Failure records lack structured fields.** Older or non-conforming `failure.md` files may be missing the suspected-cause section. Skip them in clustering; flag the gap.
- **All recurrences in a single task.** Three failures within one task's retry budget aren't independent recurrences. Require the failures to span at least 2 tasks before counting.
- **Auto-promotion threshold ambiguity.** The 3+ rule has fuzzy edges (when does "the same pattern" actually match?). When in doubt, don't promote; flag for the next sweep.

## Examples

Three failures across 3 weeks:
- task 042, attempt-A: failed AC4 (PTY cleanup); suspected cause: unmount handler doesn't call kill().
- task 056, attempt-B: failed AC2 (widget memory); suspected cause: useEffect cleanup doesn't run.
- task 071, attempt-A: failed AC3 (event listener leak); suspected cause: subscription not torn down on unmount.

Pattern key: (failed-cleanup-on-unmount, useEffect-cleanup, implementer).

The skill drafts:

```markdown
---
lesson: implementer-cleanup-on-unmount
role: implementer
created: 2026-05-09
last-recurred: 2026-05-09
recurrence-count: 3
severity: medium
status: active
---

# Implementers: tear down subscriptions and timers in useEffect cleanup

## Context
Three Implementer instances across three tasks have shipped components
that subscribed to events, started timers, or held PTY references
without tearing them down on unmount. Verifier caught the leaks each
time.

## What to do
- Every useEffect that subscribes, starts a timer, or owns a resource
  must return a cleanup function.
- For IPC subscriptions: return `() => ipcRenderer.removeListener(...)`.
- For setTimeout/setInterval: return `() => clearTimeout(...)` or
  clearInterval.
- For owned resources (PTY refs, websocket connections): explicitly
  release on cleanup.

## Why
React mounts/unmounts components freely. Without cleanup, leaks
accumulate; the canvas's intended lifecycle behavior breaks.

## Promotion candidacy
Recurrence across multiple roles (this affects Verifier patterns too).
If it recurs once more, propose adding to `conventions.md` under
"React component cleanup."
```

## Anti-patterns

- **Promoting on a single failure.** The 3+ threshold matters. Single failures are noise.
- **Aggressive lesson editing.** Updates to existing lessons should be limited to recurrence-count and last-recurred. Don't rewrite content speculatively.
- **Missing the cross-role signal.** When the same pattern shows up in implementer-X.md and verifier-X.md, it's convention-worthy. Don't keep drafting role-scoped lessons.
- **Skipping the obsolete-marking step.** Stale lessons accumulate. The 90-day threshold is the floor; mark and leave.

## References

- `docs/06-memory.md` — four-layer memory model and promotion paths.
- `docs/14-failure-loop.md` — failure.md schema and the 3+ recurrence rule.
- `base/skills/audit-docs.md` — separate concern (drift, not recurring failures).
