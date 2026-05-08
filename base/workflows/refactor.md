---
workflow: refactor
version: 1.0.0
applicable-task-types: [refactor]
default-fan-out: 1
human-gates: [end-of-planner, end-of-judge]
default-retry-budget: 2
peer-reviewers: 2
mandatory-adr-threshold: 2-files
stability: stable
auto-spawn-follow-ups:
  - condition: docs-impact-detected
    template: update-docs-<id>
---

# refactor

For changes that don't add capability but reshape existing code. Heavier review than `ship-feature`; multiple peer reviewers; mandatory ADR for cross-file scope.

## Trigger

A task lands in `tasks/open/` with `type: refactor` and `status: open`.

## Role sequence

Same twelve steps as `ship-feature`, with key differences:

- **Step 3 (Planner)**: mandatory. No skip path. Refactors without architecture review become reverse-engineering puzzles for future readers.
- **Mandatory ADR threshold**: if the refactor touches more than one file, the Planner must write a `memory/decisions/<NNNN>-<slug>.md`. Single-file refactors don't need an ADR.
- **Step 5 (Router fan-out)**: defaults to 1. Multiple parallel attempts at the same refactor diverge unproductively. One deep attempt instead.
- **Step 7-8 (Verifier + Judge)**: where `ship-feature` runs only the Judge, `refactor` defaults to 2 explicit Reviewer instances reviewing independently before the Judge synthesizes. Reviewer disagreement on ranking escalates to human.
- **Step 10 (Librarian sweep)**: heavier `audit-docs` thresholds. Refactors usually break docs; the sweep catches drift more aggressively.

## Hand-off contracts

Same as `ship-feature`. The Reviewers introduce an additional hand-off:
- **Implementer attempt → Reviewers**: each reviewer reads the same anonymized attempt independently.
- **Reviewer reports → Judge**: each reviewer's `ranking-json` and `review-md` go to the Judge for synthesis.

The Judge's verdict explicitly notes whether the reviewers agreed.

## Escalation rules

Same as `ship-feature`, plus:

- Reviewers disagree on ranking → escalate to human. Refactor decisions don't get split-decision rulings.
- Refactor breaks tests in a different subsystem → escalate to Planner. The blast radius wasn't accounted for; might need decomposition.

## Auto-spawned follow-ups

- **Conditional (docs-impact-detected)**: if the Librarian's post-sweep audit-docs finds docs needing updates beyond the auto-fix threshold, opens an `update-docs-<id>` task. Refactors very often trigger this.

No always-spawn follow-up. Refactors don't typically need new test coverage (the existing tests should still pass — that's the point of a refactor).

## Variants

For refactors that turn out to require new capability (you discover during planning that the refactor needs a new abstraction), re-classify as `feature` and switch to `ship-feature`.

For refactors that escalate into architectural overhauls (rewriting a subsystem), decompose into multiple sub-tasks. The parent task stays `refactor` as a coordinator.

## Defaults summary

```
fan-out: 1
retry-budget: 2
peer-reviewers: 2              (vs 0 for ship-feature)
mandatory-adr-threshold: 2-files
human-gates: [end-of-planner, end-of-judge]
```

No auto-approve at the architecture gate for refactors. Refactors should always have human review of the plan because the consequences are durable and hard to revert.

## Why a separate workflow

Refactors are high-stakes changes with no immediate user-visible benefit. The extra ceremony — mandatory Planner, mandatory ADR for cross-file scope, multiple Reviewers — front-loads the discussion. The cost is paid in Opus tokens up front; the savings are years of clearer code afterward.
