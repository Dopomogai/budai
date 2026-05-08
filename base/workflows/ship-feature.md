---
workflow: ship-feature
version: 1.0.0
applicable-task-types: [feature]
default-fan-out: 1
human-gates: [end-of-planner, end-of-judge]
default-retry-budget: 2
peer-reviewers: 0
stability: stable
auto-spawn-follow-ups:
  - condition: always
    template: test-coverage-<id>
---

# ship-feature

The canonical full lifecycle. The twelve steps in `docs/08-the-journey.md` ARE the body of `ship-feature`. That doc is authoritative; this file points at it.

## Trigger

A task lands in `tasks/open/` with `type: feature` and `status: open`.

## Role sequence

Per `docs/08-the-journey.md`:

1. **Step 0** — Task entry (human or programmatic)
2. **Step 1** — Router moves to `planning`
3. **Step 2** — Librarian builds bundle
4. **Step 3** — Planner produces elaborate plan (skipped if `needs-architect: false`)
5. **Step 4** — Human gate: architecture review (auto-approves if `trivial: true` AND `fan-out: 1` AND no new ADR)
6. **Step 5** — Router fans out implementers (per `fan-out:` field)
7. **Step 6** — Implementers code in parallel (worktree-isolated)
8. **Step 7** — Verifier verifies each attempt with evidence
9. **Step 8** — Judge synthesizes verdict (anonymized review)
10. **Step 9** — Human gate: final result review (same auto-approve rule)
11. **Step 10** — Librarian sweeps (audit-docs, regenerate-index, promote-lessons, update-stats)
12. **Step 11** — Backend stream
13. **Step 12** — Archive

## Hand-off contracts

Per `docs/05-workflows.md`:
- Bundle → Planner: bundle YAML validates against `09-bundle-format.md`.
- Plan → Router → Implementer: plan section validates against `10-plan-format.md`.
- Attempt → Verifier: writeup + patch present, patch applies cleanly.
- Verifier report → Judge: `ac-mapping.json` validates, every AC has evidence.
- Verdict → integrator: required sections present, attribution de-anonymized.

Failed validation re-invokes the producing role with a structured error.

## Escalation rules

- Implementer "ambiguous spec" → Planner.
- Verifier "AC unanswerable as written" → Planner.
- Judge "all attempts failed past budget" → human (or Planner if cause is plan-shaped).
- Verifier finds repeated regression of same passing AC across retries → Planner.

Escalations write to `messages/channels/escalations.md` and re-route the workflow accordingly.

## Auto-spawned follow-ups

After verdict approval at the human gate:

- **Always**: `test-coverage-<id>` task (type: refactor) covering the new feature's regression test surface. The follow-up uses the `fix-bug` workflow's faster path since it's mostly mechanical.

- **Conditional**: outstanding concerns above severity `medium` from the verdict become individual `address-<concern-slug>-<id>` tasks. The Judge's verdict lists these explicitly.

## Variants

This workflow is the most general; other workflows are specializations:

- `fix-bug` — faster path for defects (skip Planner if trivial, mandatory regression test follow-up).
- `refactor` — heavier review (mandatory ADR for cross-file scope, multiple peer reviewers).
- `audit-repo` — Auditor + Librarian only, no Implementer.

## Defaults summary

```
fan-out: 1                     (override per task via frontmatter)
retry-budget: 2                (Implementer retries with tier escalation)
peer-reviewers: 0              (Judge alone reviews; refactor uses 2)
human-gates: [end-of-planner, end-of-judge]
```

For tasks with `trivial: true` AND `fan-out: 1` AND no new ADR, the architecture gate auto-approves. The result gate auto-approves on additional condition (all AC passed, verifier confidence high).
