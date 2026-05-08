# 12 — Isolation and fan-out

When more than one Implementer attempts the same task in parallel, each runs in an isolated worktree, submits an attempt anonymously, and the Judge picks the winner blind. This document specifies the mechanics: when fan-out happens, how worktrees work, how anonymization preserves auditability, and how the council folder is shaped.

## When to fan out

Fan-out adds value when the task has architectural ambiguity — multiple plausible approaches, none obviously best. Parallel attempts explore different shapes; the Judge selects.

Fan-out wastes tokens when the task is mechanical — there's one right answer, and multiple agents will converge on it. Fan-out 3 on a "rename this variable" task pays 3× the cost for the same result.

The Planner recommends fan-out per task in its plan output (Section 6 of the plan format, `10-plan-format.md`). Defaults:

- Mechanical tasks: 1
- Tasks with named risks or open architectural questions: 3
- Research tasks (autoresearch-style): 3+, often 5

Fan-out is set in task frontmatter and read by the Router at Step 5 of the journey.

## Worktree-per-implementer isolation

Each Implementer instance runs inside its own git worktree. Worktrees give us file-system isolation without virtual machines or containers — cheap, native, well-understood.

### Mechanics

When the Router fans out N implementers (Step 5 of `08-the-journey.md`):

```bash
# Per implementer instance:
RUN_ID=$(uuidgen)
git worktree add ".agents/runs/$RUN_ID/worktree" HEAD
# The Implementer's CWD is .agents/runs/$RUN_ID/worktree/
# Its agent runner is bound to that path
```

Each worktree is a full checkout of `HEAD` at fan-out time. The Implementer can read, edit, run tests, do anything inside its worktree. It cannot reach into other implementers' worktrees because:

1. Its runtime CWD is bound to its worktree path.
2. Its tool permissions don't include reading paths outside its worktree.
3. The agent runner enforces the boundary.

### Cleanup

Worktrees are torn down by the Judge after integration:

```bash
# After the winning patch is applied to main:
for run_id in $(ls .agents/runs/); do
  git worktree remove ".agents/runs/$run_id/worktree" 2>/dev/null
done
```

The transcript and diff stay in `runs/<run-id>/`; only the working filesystem state goes away.

### Why worktrees and not branches

Branches share the same checkout; an Implementer could `git log` and see what others wrote. Worktrees are filesystem-level isolated. This matches the strict-anonymization premise from `01-design-principles.md` — there's nothing to leak because there's nothing to see.

## Opaque IDs

When the Router dispatches N implementers, it assigns each one an opaque ID: `attempt-A`, `attempt-B`, `attempt-C`. The opaque ID is what appears in council/, in the Judge's review context, and in cross-attempt comparisons.

The opaque ID is **not** the same as the run-id. A run-id (UUID) identifies the agent invocation; the opaque ID identifies the attempt within the council for that task. The mapping lives in `council/<task-id>/dispatch.json` and `mapping.json`.

### Assignment

Letters are assigned in random order, **not** in dispatch order. This prevents the Judge from inferring "attempt-A is the first one, probably from the most-confident implementer." Random assignment + temporal noise on submission times makes ordering uninformative.

### Reset per task

Opaque IDs reset to A, B, C per task. They don't carry across tasks. attempt-A in task 042 has no relation to attempt-A in task 043.

## Council folder

The council folder is the durable record of all attempts, all reviews, and the verdict for one task. Lives at `.agents/council/<task-id>/`.

### Structure

```
council/<task-id>/
├── dispatch.json        # who was dispatched, with what opaque IDs
├── attempts/
│   ├── attempt-A.md     # implementer's writeup, anonymized
│   ├── attempt-A.patch  # the diff
│   ├── attempt-B.md
│   ├── attempt-B.patch
│   └── attempt-C.md
│       attempt-C.patch
├── reviews/             # only present when peer-reviewers > 0
│   ├── review-X.md
│   └── review-Y.md
├── verifier-reports/
│   ├── verifier-A.md
│   ├── verifier-B.md
│   └── verifier-C.md
├── mapping.json         # de-anonymization mapping, written by Router, read by Judge after review
└── verdict.md           # the Judge's output
```

Failed attempts (those that exhausted retry budget) stay in `attempts/` with `status: failed` flagged in their writeup. They're part of the audit record.

### dispatch.json

Schema:

```json
{
  "task-id": 42,
  "fan-out": 3,
  "dispatched-at": "2026-05-08T11:00:00Z",
  "workflow": "ship-feature",
  "instances": [
    {
      "opaque-id": "attempt-A",
      "run-id": "01HX2Y3Z-7f2c-...",
      "model": "claude-sonnet-4-6",
      "runner": "claude-code",
      "started": "2026-05-08T11:00:01Z",
      "tier-on-spawn": "sonnet"
    },
    {
      "opaque-id": "attempt-B",
      "run-id": "01HX2Y3Z-8a9d-...",
      "model": "claude-sonnet-4-6",
      "runner": "claude-code",
      "started": "2026-05-08T11:00:01Z",
      "tier-on-spawn": "sonnet"
    },
    {
      "opaque-id": "attempt-C",
      "run-id": "01HX2Y3Z-9b3e-...",
      "model": "claude-opus-4-7",
      "runner": "claude-code",
      "started": "2026-05-08T11:00:02Z",
      "tier-on-spawn": "opus"
    }
  ]
}
```

Written by the Router at dispatch time. Read by the Librarian for stats aggregation. Not read by the Judge during review (that would leak authorship via model name).

### mapping.json

Schema:

```json
{
  "task-id": 42,
  "mapping": {
    "attempt-A": {
      "run-id": "01HX2Y3Z-7f2c-...",
      "model": "claude-sonnet-4-6",
      "runner": "claude-code"
    },
    "attempt-B": {
      "run-id": "01HX2Y3Z-8a9d-...",
      "model": "claude-sonnet-4-6",
      "runner": "claude-code"
    },
    "attempt-C": {
      "run-id": "01HX2Y3Z-9b3e-...",
      "model": "claude-opus-4-7",
      "runner": "claude-code"
    }
  }
}
```

Identical content to the relevant subset of dispatch.json, kept as a separate file so the Judge can read it cleanly post-review. Written by the Router. Read by the Judge after the verdict is drafted, to de-anonymize for attribution.

## Anonymization specification

What the Judge sees during review:

- File names: `attempt-A.md`, `attempt-A.patch`, etc.
- Inside writeup files: no model name, no runner, no run-id, no instance metadata.
- File timestamps stripped (or normalized to a single value).
- Submission order randomized in the file listing the Judge consumes.

What the Judge does NOT see during review (would leak authorship):

- `dispatch.json` (contains model names per opaque ID).
- `mapping.json` (the de-anonymization).
- Other implementers' run transcripts in `runs/`.
- Filesystem timestamps that would expose dispatch order.

What the Judge sees AFTER drafting verdict:

- `mapping.json` is read in.
- Attribution is added to the verdict (which model produced the winner, which produced each loser).
- The completed verdict.md is the de-anonymized record.

The runner enforces the anonymization boundary by not injecting metadata into the Judge's context until the explicit "de-anonymize" step.

## Attempt file format

Each `attempts/attempt-<X>.md` has fixed structure:

```markdown
---
opaque-id: attempt-A
status: submitted | passed | failed | winner
submitted: 2026-05-08T11:18:32Z
---

# Attempt A

## Summary
<1-2 paragraphs from the Implementer — what they did and why>

## Files touched
- src/main/TerminalManager.ts (created)
- src/preload/index.ts (modified)
- src/renderer/components/widgets/TerminalWidgetNode.tsx (created)
- src/renderer/store/useCanvasStore.ts (modified)

## Notes
<Anything the Implementer wants to flag — design choices, deviations from the plan, gotchas>

## Verifier report
<Filled in by the Verifier — pass/fail per AC, evidence pointers>

## Failure log
<Only present if status: failed — what failed, what was tried>
```

The actual diff lives separately in `attempts/attempt-<X>.patch`. Splitting writeup from diff lets the Judge skim writeups quickly before reading patches in detail.

## Review file format

Only when `peer-reviewers > 0` (`refactor` workflow defaults to 2). Each `reviews/review-<X>.md`:

```markdown
---
reviewer-id: review-X
reviewed-at: 2026-05-08T11:35:12Z
---

# Review X

## Ranking
1. attempt-B
2. attempt-A
3. attempt-C

## Critique per attempt
### attempt-A
<What's good, what's wrong, severity>

### attempt-B
...

### attempt-C
...

## Outstanding concerns
- <issue>: <severity>
```

Reviewers are also anonymized — `review-X`, `review-Y` are opaque to the Judge if the Judge is reading multiple reviewer outputs. (Reviewers don't see other reviewers' output during their own review either; cross-review contamination is avoided.)

## Verdict file format

`verdict.md` schema:

```markdown
---
task-id: 42
verdict-at: 2026-05-08T11:50:08Z
winner: attempt-B
status: integrated | rejected | escalated
---

# Verdict for Task 42

## Winner
attempt-B (de-anonymized: implementer instance 8a9d running claude-sonnet-4-6 via claude-code)

## Why this won
<2-3 paragraphs, anonymized at write-time, de-anonymized in this saved file>

## What the others got wrong
- attempt-A: <de-anonymized> missed the cleanup-on-unmount path; verifier caught the leak.
- attempt-C: <de-anonymized> over-engineered with a sub-PTY pool no AC required.

## Outstanding concerns
- The PTY map's lifecycle on app reload isn't tested — flag for follow-up.

## Recommendation to human gate
Approve. Outstanding concern is non-blocking; auto-spawning a follow-up task: 042-followup-pty-reload.

## Auto-spawned follow-ups
- task 043 — Add automated regression tests for terminal widget (per workflow rule)
- task 044 — Verify PTY cleanup on app reload (from outstanding concern above)

## Stats
- Attempts: 3 (1 winner, 2 losers, 0 failed)
- Total duration (dispatch to verdict): 50m 8s
- Models used: 2× sonnet-4-6, 1× opus-4-7
```

The verdict is what the human sees at the result gate. It's also what archived tasks reference at their `Verdict` section.

## Failed attempts

When all attempts in a fan-out fail past the retry budget, the workflow has a few options:

1. **Judge picks "best of failed."** If one attempt is closer to passing AC than the others, it's marked `status: best-of-failed` and presented to the human gate with the failure context. Human decides whether to accept-with-known-issues, send back for replanning, or abandon.
2. **Escalate to Planner.** If the failure pattern suggests the plan was wrong, escalation goes to Planner, not human. Plan revision spawns a new attempt round.
3. **Mark task failed.** Task frontmatter `status: failed`. Stays in `tasks/open/` until human reviews; then either re-opened with revised plan or moved to `archive/` with `failed` status preserved.

Failed attempts stay in council/. They're durable record. They're also training data: the Librarian's `promote-lesson` skill scans failures for recurring patterns.

## The DAG mental model

From `01-design-principles.md`: divergence is the natural state of agent work; convergence happens at selection.

The council is one node in a per-task DAG: parent task → fan-out → attempts → reviews → verdict → integration. Failed attempts are leaf nodes that don't propagate forward but don't disappear. The Judge's selection draws an edge from one attempt to the integration commit; the others are siblings without edges.

Across many tasks, the codebase's history is a sprawling graph of "attempts considered, attempts merged." Most graphs converge through the Judge's funnel; the council is where divergence is preserved as evidence.

## Audit reconstruction

Given any closed task, an auditor can reconstruct the entire decision trail by reading:

1. `tasks/archive/<id>.md` — the task and the plan.
2. `council/<id>/dispatch.json` — who was dispatched, with what model.
3. `council/<id>/attempts/` — what each attempt produced.
4. `council/<id>/reviews/` — what each reviewer thought.
5. `council/<id>/verdict.md` — what the Judge decided and why.
6. `runs/<run-id>/transcript.md` (per attempt) — the full agent transcript.

No information is lost. Anonymization at review time was a Judge-context-window concern, not a record-keeping concern. The audit trail is fully named.
