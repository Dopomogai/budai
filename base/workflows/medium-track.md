---
workflow: medium-track
version: 1.0.0
applicable-task-types: [feature, refactor, bug]
default-fan-out: 1
default-retry-budget: 2
peer-reviewers: 0
stability: experimental
roles: [planner, implementer, verifier]
entry-criteria:
  - "needs-architect: true AND fan-out: 1 AND files-to-touch enumerable from task body"
  - "OR: complexity: medium — task shape is known, but plan-then-implement-then-verify cadence is warranted"
exit-criteria:
  - plan present in task body (appended by Planner)
  - ADR written if any architectural decision was made
  - attempt-A.md writeup present
  - attempt-A.patch present and applies cleanly to main
  - evidence/ac-mapping.json present
  - all regression tests pass
skipped-artifacts: [bundle, verdict]
auto-approve-when: fan-out-1 AND verifier-passed
gate-rules:
  planner: human
  implementer: auto
  verifier: human
human-gates: [end-of-planner, end-of-verifier]
---

# medium-track

Three-role workflow for non-trivial single-attempt work. Empirically validated by journey 4 (task-021). The middle path between fast-track (1 role, no ceremony) and ship-feature (5 roles, full ceremony).

## Trigger

A task has `needs-architect: true` AND `fan-out: 1` AND the files-to-touch list is enumerable from the task body without an archaeology phase. The operator may also explicitly set `workflow: medium-track` in the task frontmatter.

## Role sequence

1. **Planner** — reads 5–7 source files directly from the task body's context clues. Makes the architectural call. Writes an ADR if the decision blocks downstream tasks or would be re-derived by future agents. Appends the `## Plan` section to the task body. Human reviews plan + ADR.

2. **Human gate 1 (end-of-planner)** — review the plan and any ADR. Approve to continue to Implementer; request revisions to re-run Planner.

3. **Implementer** — reads plan from task body (no bundle provided; plan IS the bundle for medium-track scope). Makes the change in a git worktree branched from main. Writes attempt writeup + patch. Output flows straight to Verifier — no human gate at Implementer exit. (The Verifier IS the human's proxy for code quality.)

4. **Verifier** — verifies the attempt against all ACs. Writes evidence per AC under `evidence/<id>/`. Writes `evidence/ac-mapping.json`. Appends result to verifier report. The Verifier's verdict is final (no Judge at fan-out 1). Human reviews Verifier report.

5. **Human gate 2 (end-of-verifier)** — review Verifier report + evidence. Approve to merge; request retry if Verifier found failures.

No Librarian, no Judge.

**Why Implementer gate is auto:** At fan-out 1, the Verifier reads the same evidence a Judge would read and produces the same verdict. Adding a human gate after Implementer (before Verifier) would interrupt the agent chain with a review that is immediately superseded by the Verifier's more thorough analysis. The human's two gates (Planner exit and Verifier exit) are the accountability checkpoints.

## Hand-off contracts

**Task body → Planner.** Must have: objective, user story, ACs, enough context to identify files-to-touch without a Librarian. If files-to-touch are not inferrable from the task body, escalate to ship-feature for a Librarian bundle.

**Plan → Implementer.** Plan section (appended by Planner to task body) must include: Approach, File-level changes (one entry per file with exact change description), AC mapping, Recommended fan-out: 1. Implementer reads the plan as its bundle substitute.

**Implementer attempt → Verifier.** Deliverables:
- `council/<task-id>/attempts/attempt-A.md` — writeup with files touched, ACs with one-line evidence per AC, test counts, any plan departures flagged.
- `council/<task-id>/attempts/attempt-A.patch` — git diff applying cleanly to main.
- All tests passing (or failures documented).

**Verifier report → Human.** Must include: AC pass/fail per criterion, evidence pointers per AC, confidence level, outstanding concerns. `evidence/ac-mapping.json` validates against the AC list.

## Escalation rules

- **Planner finds more files than expected** — task may need Librarian curation. Planner flags in the plan; human decides: proceed as-is, or re-route to ship-feature.
- **Implementer hits ambiguous spec** — escalate to Planner. Plan needs revision; don't guess.
- **Verifier finds AC unanswerable as written** — escalate to Planner. AC needs revision.
- **Implementer retry budget exhausted** — attempt marked failed. Human decides: re-route to ship-feature for a second attempt with a different approach, or abandon.
- **Architectural decision touches >3 other tasks** — ADR is mandatory, not optional. Planner writes it before plan approval.

## Auto-spawned follow-ups

None automatically. The Verifier's report may include findings that the human promotes to `findings.md`; those findings may spawn follow-up tasks in the normal flow.

For medium-track, the absence of a Librarian sweep means no automatic findings promotion. The human handles this at the end-of-verifier gate.

## Variants

- **medium-track with ADR** — Planner makes an architectural decision that blocks downstream tasks. ADR is written to `memory/decisions/<NNNN>-<slug>.md`. This is the standard medium-track shape; the variant without ADR is when no architectural decision is made.
- **medium-track retry** — Verifier fails attempt-A. Implementer re-runs with `prior-attempt-dir` pointing at attempt-A's writeup. Produces attempt-B.patch. Verifier re-verifies.
- **ship-feature escalation** — mid-flight, the task turns out to need a second Implementer attempt from a different angle. Human re-routes to ship-feature; the existing plan is preserved.

## Not appropriate for

- Trivial fixes (use fast-track).
- Tasks where the architectural shape is contested (use ship-feature so Judge can rank attempts).
- Tasks with `fan-out > 1` (multiple Implementer attempts need a Judge; use ship-feature).
- Tasks where no Planner is available or the task body lacks enough context to write a plan.
- Multi-week strategic work (use strategic-audit to decompose into sub-tasks first).
