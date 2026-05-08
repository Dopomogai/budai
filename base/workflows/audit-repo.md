---
workflow: audit-repo
version: 1.0.0
applicable-task-types: [audit]
default-fan-out: 1
human-gates: [end-of-audit]
default-retry-budget: 0
peer-reviewers: 0
stability: stable
auto-spawn-follow-ups:
  - condition: findings-above-threshold
    template: address-finding-<id>
---

# audit-repo

For periodic health checks of the repo. No code changes; the output is a report. Findings can spawn follow-up tasks for the regular workflows.

## Trigger

A task lands in `tasks/open/` with `type: audit` and `status: open`. Or scheduled (e.g., monthly cron) creates the task automatically.

## Role sequence

This workflow is structurally different from `ship-feature`. There's no Implementer, no Judge, no integration step. Just an audit cycle.

1. **Step 0** — Task entry (human or scheduled).
2. **Step 1** — Router moves to `planning`. Skips Planner.
3. **Step 2** — Librarian builds bundle (lighter than usual; emphasis on conventions, docs, ADRs, prior audit reports).
4. **Step 3** — Auditor runs. The Auditor is a Librarian variant invoked through this workflow's role definition (`base/roles/librarian.md` handles it via skill dispatch, not a separate role file).
5. **Step 4** — Auditor writes findings to `tasks/open/<id>.md` under `## Findings`.
6. **Step 5** — Findings are summarized to `messages/channels/ops.md`.
7. **Step 6** — Human gate: review findings.
8. **Step 7** — Auto-spawn follow-ups for findings above severity threshold.
9. **Step 8** — Task archives.

## Hand-off contracts

Lighter than `ship-feature`:
- Bundle → Auditor: bundle includes conventions, untouchables, glossary, prior audit reports. No source files unless a specific audit area requires them.
- Auditor's findings → human gate: each finding has severity (low/medium/high), description, evidence pointer, recommended action.

## Escalation rules

- Auditor finds a security-severity issue → escalate to human immediately (don't wait for the gate). Post to `messages/channels/escalations.md`.
- Auditor's findings exceed N=10 high-severity (configurable) → escalate to human. Suggests the repo has accumulated debt; full follow-up workflow needed beyond per-finding tasks.

## Auto-spawned follow-ups

- **High-severity findings**: each becomes an `address-finding-<id>` task with the appropriate type (`bug`, `refactor`, etc.) per the auditor's recommendation.
- **Medium-severity findings**: batched into a `triage-audit-<date>-medium` task (type: refactor) for human prioritization.
- **Low-severity findings**: noted in the audit report; no follow-up tasks unless the count is unusually high.

## Variants

For specific audit foci, separate workflows could be authored:
- `security-audit` — security-only scope.
- `performance-audit` — perf-only scope.
- `docs-audit` — docs-only scope, lightweight.

These would be local-scoped workflows in `local/workflows/` if needed; not shipped in `base/`.

## Defaults summary

```
fan-out: 1
retry-budget: 0                (audits don't retry; one shot per scheduled run)
peer-reviewers: 0
human-gates: [end-of-audit]
```

## Why a separate workflow

Audits don't fit the ship-feature shape. There's no plan, no fan-out, no winner to pick. The output is a report, not a code change. A separate workflow shape lets the Auditor focus on what audits do best (drift detection, recommendation generation) without forcing the ship-feature scaffolding around it.

## Audit findings format

Findings live in the task body under `## Findings`:

```markdown
## Findings

### High severity
- F1: `.env` is tracked in git history.
  - Evidence: `git log --all --full-history -- .env` returns commits.
  - Recommended action: rotate all secrets; remove from history with git filter-repo; add to .gitignore.
  - Auto-spawning: address-finding-F1-001 (type: bug, urgent).

### Medium severity
- F2: 12 source files missing budai headers.
  - Evidence: `bin/librarian regenerate-index --report` shows count.
  - Recommended action: run `bin/librarian add-headers --interactive`.
  - Auto-spawning: triage-audit-2026-05-09-medium (batched).

### Low severity
- F3: Some directory READMEs are slightly stale (3 files).
  - Evidence: audit-docs sweep.
  - Recommended action: covered by next per-task sweep; no separate task.
```

Each finding is named (F1, F2, F3, ...) for cross-referencing in subsequent tasks and discussions.
