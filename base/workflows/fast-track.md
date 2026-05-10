---
workflow: fast-track
version: 1.0.0
applicable-task-types: [bug, refactor]
default-fan-out: 1
default-retry-budget: 1
peer-reviewers: 0
stability: experimental
roles: [implementer]
entry-criteria:
  - "trivial: true"
  - "OR: type: bug AND fan-out: 1 AND no needs-architect: true"
exit-criteria:
  - regression tests pass
  - single Implementer writeup present at council/<task-id>/attempts/attempt-A.md
skipped-artifacts: [bundle, plan, verdict, evidence-files, verifier-worktree, adrs]
auto-approve-when: never
gate-rules:
  implementer: human
human-gates: [end-of-implementer]
---

# fast-track

Single-Implementer workflow for trivial fixes. Empirically validated by journey 3 (task-020).

## Trigger

A task lands with `trivial: true`, OR with `type: bug` AND `fan-out: 1` AND no `needs-architect: true`. The operator may also explicitly set `workflow: fast-track` in the task frontmatter.

## Role sequence

1. **Implementer** — reads task body directly (no bundle), locates relevant files, makes the change, writes tests, writes `attempt-A.md` writeup and `attempt-A.patch`.
2. **Human gate** — single review of the diff. If approved: merge and flip status to `done`. If rejected: Implementer re-runs within retry budget (default 1).

No Librarian, Planner, Verifier, or Judge. The task body IS the spec. The human's diff review IS the verification.

**Step-by-step for the Implementer:**

- Read task body (objective, ACs, context). Treat it as the full spec.
- Locate the relevant files by reading the repo from context clues in the task body. No bundle is provided.
- Scan for callers of any function whose signature changes; update them; flag scope expansion in the writeup.
- Make the change. Write or update regression tests.
- Run the full test suite (`python3 -m pytest` or equivalent). Fix failures.
- Write `council/<task-id>/attempts/attempt-A.md` and `attempt-A.patch`.
- Commit. The human reviews and merges.

## Hand-off contracts

**Task body → Implementer.** The task body must include verifiable ACs. If the ACs are fuzzy (e.g., "make it better"), fast-track is the wrong workflow — escalate to medium-track or ship-feature so a Planner can clarify.

**Implementer → Human.** Deliverables:
- `attempt-A.md` writeup with: summary, files touched, ACs with one-line evidence per AC, test counts, any scope expansions flagged.
- `attempt-A.patch` — git diff applying cleanly to main.
- All tests passing (or failures documented with clear "I think these need new test coverage" note).

No `evidence/` subdirectory per AC. No `verdict.md`. No ADR (architectural decisions are out of scope for fast-track; if an arch decision is needed, the task is the wrong shape).

## Escalation rules

- **Ambiguous spec** — task ACs are fuzzy or the files to touch are non-obvious. Escalate to human; consider re-routing to medium-track with a Planner step.
- **Signature change propagates to >5 callers** — the fix is larger than fast-track scope. Flag in the writeup. Human decides: merge as-is, or re-route to medium-track.
- **Retry budget exhausted** — after 1 retry the attempt is marked failed and stays in council as record. Human decides next step.
- **Architecture decision required** — if the fix requires a choice between approaches, fast-track is inappropriate. Escalate to medium-track.

Do NOT escalate silently. Write the escalation flag in the attempt writeup and in `messages/channels/escalations.md`.

## Auto-spawned follow-ups

None by default. Fast-track does not auto-spawn follow-ups because:
- No Judge or Verifier is present to emit findings.
- The human reviewer handles any follow-up promotion manually.

If the Implementer notices a finding during the fix, it writes it in the writeup under "Findings" and the human promotes it to `findings.md` if warranted.

## Variants

- **fast-track with scope expansion** — Implementer touches files outside the task's explicit list (e.g., callers of a changed function). Acceptable; must be flagged in the writeup.
- **fast-track on `trivial: true` feature** — rare but valid. Same shape; the key constraint is that the ACs are mechanically verifiable and no architecture decision is needed.
- **medium-track escalation** — operator starts with fast-track, Implementer discovers the task is non-trivial, flags it. Human re-routes to medium-track for the next attempt.

## Not appropriate for

- Tasks with multiple plausible architectural shapes.
- Tasks touching more than 10 files.
- Tasks with `needs-architect: true`.
- Tasks where the AC list itself is fuzzy or contested.
- Tasks where the human reviewer doesn't have enough context to verify the diff independently (e.g., highly specialized domain code with no tests).
