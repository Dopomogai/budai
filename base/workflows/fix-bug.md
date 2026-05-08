---
workflow: fix-bug
version: 1.0.0
applicable-task-types: [bug]
default-fan-out: 1
human-gates: [end-of-judge]
default-retry-budget: 1
peer-reviewers: 0
stability: stable
auto-spawn-follow-ups:
  - condition: always
    template: regression-test-<id>
---

# fix-bug

Faster path for defects. Same role sequence as `ship-feature` but with adjustments for the typical bug-fix shape: less architectural ambiguity, more emphasis on regression coverage.

## Trigger

A task lands in `tasks/open/` with `type: bug` and `status: open`.

## Role sequence

Same as `ship-feature` (twelve steps per `docs/08-the-journey.md`), with these specific differences:

- **Step 3 (Planner)**: skipped when `trivial: true`. Bug description doubles as plan; Implementer goes straight to coding.
- **Step 4 (architecture gate)**: skipped if Step 3 was skipped.
- **Step 5 (Router fan-out)**: defaults to 1. Bugs typically have one right answer.
- **Step 7 (Verifier)**: tighter retry budget (`default-retry-budget: 1`). If a fix doesn't work after one retry, it's a more complex investigation; escalate to Planner.

## Hand-off contracts

Same as `ship-feature`. The tighter retry budget changes when escalation kicks in, not the contract shapes.

## Escalation rules

- Implementer's first retry fails → escalate to Planner. The bug fix isn't tracking the actual cause; needs investigation, not more attempts.
- Verifier finds the bug fix introduces a regression elsewhere → escalate to Planner. The fix's blast radius wasn't accounted for.

Otherwise same as `ship-feature`.

## Auto-spawned follow-ups

After verdict approval:

- **Always**: `regression-test-<id>` task (type: refactor). Differs from `ship-feature`'s `test-coverage-<id>` because regression tests target the specific failure mode of the bug, not general test coverage. The follow-up's scope is narrow: write a test that would have caught this bug. The bug remains a candidate for the test suite forever after.

- **Conditional**: outstanding concerns from the verdict.

## Variants

For bugs that turn out to require architectural change (the fix would touch many files or change a contract), the Planner can re-classify the task as `refactor` and the workflow switches mid-flight to `refactor`.

## Defaults summary

```
fan-out: 1
retry-budget: 1                (tighter than ship-feature's 2)
peer-reviewers: 0
human-gates: [end-of-judge]    (architecture gate skipped for trivial bugs)
```

Auto-approve at the result gate uses the same conditions as `ship-feature` (all AC passed, verifier confidence high) — bug fixes often qualify for auto-approve since the AC is "the bug doesn't reproduce" and that's mechanically verifiable.

## Why a separate workflow

Bug fixes have different defaults from feature work. Without a separate workflow, every bug task would start with full Planner ceremony even when the fix is one-line. The workflow specialization saves Planner cycles on the trivial cases while keeping the fallback (re-classify to refactor) for non-trivial ones.
