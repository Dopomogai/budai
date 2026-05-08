# 14 — Failure loop

When an Implementer's attempt fails the Verifier, it doesn't disappear. It enters the **failure loop** — a structured retry-then-escalate flow that learns from each iteration and feeds findings back into the system. Failed attempts are not garbage; they're evidence and training data.

This document specifies how failures propagate, when retries happen, when escalation kicks in, and how patterns get extracted into durable lessons.

## Why a structured failure loop

Three reasons:

1. **Retries with context outperform retries without.** When an Implementer just re-runs blind on a failure, it tends to repeat the same mistake. When it sees a structured failure report — what failed, why, what was tried — its second attempt diverges meaningfully.
2. **Failures are signal.** A recurring failure mode tells you something about the codebase, the conventions, or the task description. Capturing that signal is how the system gets smarter.
3. **Audit needs the path-not-taken.** "We chose attempt-B" is incomplete without "and here's why attempt-A and attempt-C didn't work." Failed attempts complete the record.

## The failure record: `failure.md`

When the Verifier rejects an attempt, it writes `runs/<run-id>/failure.md` next to the transcript and evidence. Schema:

```markdown
---
run-id: 01HX2Y3Z-7f2c-...
task-id: 42
attempt-id: attempt-A
failed-at: 2026-05-08T11:24:18Z
verifier-tier: sonnet
retry-attempt: 0                    # 0 for first failure, 1 for first retry, etc.
---

# Failure: attempt-A on task 42

## Summary
<1-2 sentences — what failed at the highest level>

## Failed acceptance criteria
- AC2 (commands execute): the IPC roundtrip writes to PTY but doesn't read back. terminal-data event never fires.
- AC4 (closing widget kills PTY): unmount handler runs but PTY map isn't pruned; PTY survives.

## Passed acceptance criteria
- AC1 (terminal renders): widget mounts and xterm initializes.
- AC3 (multiple terminals independent): per-id PTY isolation works for the cases tested.

## Observed behavior
<concrete description of what the system actually does>

## Suspected cause
<verifier's hypothesis>

## Evidence
- evidence/ipc-traces/trace-execute-command.json — shows write but no read-back
- evidence/logs/stdout-close-widget.txt — shows unmount fires but no PTY.kill call

## What was tried
<if this is retry-attempt > 0, what the prior attempt(s) tried>

## Suggested next step
<verifier's suggestion for the retry>
```

The `failure.md` is the input to the next iteration of the same Implementer (with retry budget remaining) or to escalation (when budget is exhausted).

## Retry budget

Each role has a retry budget per task. Configured at three levels, last-wins:

1. Workflow default (e.g., `ship-feature` defaults to 2; `fix-bug` to 1).
2. Per-task override in task frontmatter (`retry-budget: 3`).
3. Per-role override in role frontmatter (rarely set).

When an attempt fails:

1. The runner checks remaining budget for that opaque ID.
2. If budget > 0: re-spawn the Implementer with `failure.md` appended to its inputs. Budget decrements. The new attempt overwrites `attempts/attempt-<X>.md` and `.patch`, but the previous failure is preserved at `runs/<old-run-id>/failure.md`.
3. If budget = 0: mark the attempt as `status: failed` in council. No more retries for that opaque ID; the attempt stays as record.

### Compute tier escalation on retry

The runner escalates compute tier on retry. Default escalation table:

| Original tier | Retry-1 tier | Retry-2 tier |
|---|---|---|
| haiku | sonnet | sonnet |
| sonnet | opus | opus |
| opus | opus | opus |

Reasoning: a Sonnet-class agent failing a task once probably needs heavier reasoning, not the same reasoning again. Opus is the ceiling; further retries don't escalate further.

The Implementer instance retains its opaque ID across retries (attempt-A stays attempt-A). The run-id changes (each retry is a new agent invocation).

## Cross-role escalation

Some failures escalate to a different role rather than retrying the same role:

| Failure pattern | Escalates to | Reasoning |
|---|---|---|
| Implementer reports "spec is ambiguous" | Planner | Spec needs revision, not re-implementation. |
| Verifier reports "AC unanswerable as written" | Planner | AC needs revision. |
| Judge reports "all attempts failed past budget" | human (or Planner if cause is plan-shaped) | Task may be ill-formed. |
| Verifier finds repeated regression of same passing AC across retries | Planner | Plan is destabilizing the system; needs revision. |
| Librarian sweep finds doc drift it can't auto-fix | new task | Doc fix is its own work item. |

Escalation writes to `messages/channels/escalations.md` so the audit trail is intact:

```markdown
## Escalation: task 42, attempt-A

- From: Verifier
- To: Planner
- Reason: AC2 unanswerable as written. The AC says "commands execute" but doesn't define "command" — the Implementer chose shell commands; the test scenario assumed CLI tool invocations.
- Suggested resolution: Planner clarifies AC2 to specify whether shell, CLI tool, or both are in scope.
- Escalated at: 2026-05-08T11:35:00Z
```

The escalation interrupts the failure loop for that opaque ID. The escalating role's status reverts (e.g., Implementer's attempt is set aside; the Planner re-runs; if the Planner produces a revised plan, a fresh implementer round begins with new opaque IDs).

## After-budget behavior

When all of an Implementer's retries are exhausted (budget = 0, all retries failed):

1. The attempt's `status` is set to `failed`.
2. The attempt and its full failure history stay in `council/<task-id>/attempts/`.
3. The Judge's review proceeds with whatever attempts succeeded.
4. If ALL attempts in a fan-out failed: the Judge handles per "all attempts failed" rules from `12-isolation-and-fanout.md`:
   - Pick "best of failed" if one is closer to passing AC than others.
   - Escalate to Planner if pattern suggests plan was wrong.
   - Mark task `failed` and escalate to human.

The retry budget is per-implementer. With fan-out 3 and budget 2, you can have up to 9 total Implementer invocations on a single task before everyone gives up.

## Pattern detection

Failed attempts feed the Librarian's `promote-lesson` skill. After every task closes, the Librarian scans `runs/*/failure.md` for the closing task and recent neighbors:

- **Recurring failure mode.** Same failure message structure across ≥3 different runs in last 30 days → draft a lesson.
- **Recurring root cause.** Same suspected cause across ≥3 runs → draft a lesson with stronger weight.
- **Cross-attempt convergence on a wrong path.** All attempts in a single fan-out fail the same way → draft a lesson AND open an investigation task; the plan was probably wrong.
- **Cross-task pattern.** Same scope, different tasks, similar failures → escalate from lesson to convention candidate.

Patterns are scored by recurrence count, severity (Verifier-reported), and recency. Above a configurable score threshold, the Librarian opens an `update-conventions-<topic>` task or drafts a `lessons/<topic>.md` entry directly.

## Lesson promotion path

Failures → lessons → conventions → registry. Four stages:

1. **Run-local.** A single failure lives in `runs/<run-id>/failure.md`. Not promoted.
2. **Role-scoped lesson.** When 3+ failures share a pattern within a role, the Librarian drafts `memory/lessons/<role>-<topic>.md`. Read by future instances of that role.
3. **Repo-scoped convention.** When a lesson recurs across roles or tasks within a repo, the Librarian drafts an addition to `local/conventions.md` and opens a task for human review.
4. **Registry-scoped proposal.** When the same lesson appears in stats from multiple repos (visible via the backend dashboard), the Librarian drafts a proposed addition to `base/conventions.md` and opens a registry PR.

Each stage gates the next: role-scoped lessons are auto-drafted; repo-scoped requires human review; registry-scoped requires PR review by registry maintainers.

## Skill self-improvement loop

When failures cluster around a specific skill rather than a specific task pattern, the Librarian routes differently:

- Skill success rate < threshold (default 70%) over last N invocations → open `improve-skill-<name>` task.
- Same failure mode in skill output across multiple invocations → flag the skill in stats; drafts revised skill body for human review.

This is the autonomous skill-improvement loop. Improvement tasks run through the regular workflow (`refactor` typically), with the changed skill landing in `local/skills/`. Once stable in local, `bin/librarian publish` proposes it to the registry.

Full skill versioning and propagation mechanics live in `16-skill-versioning.md`.

## What the failure loop is NOT

- Not infinite retry. Budgets are bounded, and escalation routes failures out of the same role.
- Not punitive. Failed attempts don't penalize the Implementer or its model — failed runs are evidence, not grades. Stats track failures for skill quality, not for ranking model identities.
- Not a substitute for upfront planning. The failure loop catches things the plan missed; it doesn't replace planning. A workflow that consistently relies on the failure loop to "find the right answer" is mis-planned.
- Not silent. Every failure produces a `failure.md`. Every escalation writes to `messages/channels/escalations.md`. The audit trail is the contract.
