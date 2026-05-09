---
id: 019
title: Workflow taxonomy v1 — beyond ship-feature
type: feature
scope: workflows
priority: P1
status: open
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [009]
blocks: []
sources: [human-strategy-2026-05-09]
created: 2026-05-09T18:00:00Z
created-by: human
updated: 2026-05-09T18:00:00Z
workflow: ship-feature
bundle-budget: 70000
retry-budget: 2
---

# Task 019: Workflow taxonomy v1 — beyond ship-feature

## Objective
Codify nine workflows in `base/workflows/` so the runner can dispatch by `workflow:` field instead of hardcoding the L→P→I→V→J chain. Different work shapes (docs, scaffolding, audits, trivial fixes, granular plan-then-execute) need different role sequences and gate rules; today everything routes through the heaviest path even when it's overkill.

## User story
As a budai operator, when I create a task with `workflow: scaffold-docs` (or `fast-track`, or `estimate-task`), I want the runner to dispatch only the roles that workflow declares, in the declared order, with that workflow's gate rules — so a 5-minute typo fix doesn't need a Librarian bundle and a Judge verdict, and a multi-week strategic audit doesn't have to pretend to be a single-attempt feature.

## Acceptance criteria
- AC1: Nine workflow files exist at `base/workflows/<name>.md`: `ship-feature.md` (canonical baseline; existing if present, otherwise create), `fix-bug.md`, `scaffold-project.md`, `scaffold-docs.md`, `strategic-audit.md`, `prepare-task.md`, `estimate-task.md`, `fast-track.md`, `medium-track.md`. Each has YAML frontmatter declaring `name, roles (ordered list), gate-rules, entry-criteria, exit-criteria, skipped-artifacts, auto-approve-when` and a markdown body explaining when to use it, what's skipped vs ship-feature, and success criteria.
- AC2: `bin/lib/runner.py` reads the task's `workflow:` field, loads the matching workflow file via `bin/lib/resolution.py` (resolves to `base/workflows/<name>.md` or `local/workflows/<name>.md` overlay), and dispatches roles in the declared order. Unknown workflow names raise `ValueError`.
- AC3: `bin/agent run` accepts an optional `--workflow <name>` flag that overrides the task's declared workflow. If task and flag both present, the flag wins; if neither present, default to `ship-feature`.
- AC4: `bin/lib/runner.py`'s gate logic reads each workflow's `gate-rules` block — specifically when human approval is required vs auto-approved (e.g., `fast-track` auto-approves at fan-out 1 + verifier-passed; `ship-feature` requires human at every gate by default).
- AC5: `tasks/TEMPLATE.md` includes the `workflow:` field with a comment listing the nine valid values.
- AC6: `docs/` gets a new `15-workflows.md` (or extends `08-the-journey.md`) explaining the taxonomy with one section per workflow.
- AC7: Tests in `tests/bin/test_runner.py` cover: workflow resolution (base + local overlay), unknown-workflow rejection, dispatch order matches frontmatter, `--workflow` flag override.

## Context
- Source: human strategic ask after journey 2 — "we could have the medium team — planner — implementer and verifier / and then the super fast track — plan — implement (or even do all by one agent)" — plus the broader observation that scaffolding, docs, and strategic-planning work shapes don't fit the five-role mold cleanly.
- Path-2 sketch in journey 2's reflection captured the nine workflows; this task graduates that sketch to real files + dispatch.
- Hard depends on task-009 (real `dispatch_claude_code`). Without a real Claude subprocess, workflow dispatch can't be exercised end-to-end in a verifier worktree. Soft depends on task-018 (stats emission) — `estimate-task` workflow is half-implemented without it but can ship its bundle/plan flow.

## Workflow proposals (pre-Planner — to be refined in the Plan section)

| Workflow | Roles | When | Skipped vs ship-feature | Auto-approve when |
|---|---|---|---|---|
| `ship-feature` | L → P → I → V → J | Default; non-trivial code | (baseline) | never (always-human-gate) |
| `fix-bug` | L → P → I → V → J | Bug fixes | (same roles, Verdict requires regression test) | never |
| `scaffold-project` | L (audit) → P (architect) → I → V (smoke) | Onboarding consumer repo | No follow-up auto-spawn | never (gate on conventions.md) |
| `scaffold-docs` | L (index) → I → V (link-check) | Pure docs | Skip P + J | fan-out 1 + audit-docs clean |
| `strategic-audit` | L (deep index) → P (writes roadmap, spawns sub-tasks) | Plan-the-backlog | Skip I/V/J | never (output is human-reviewed task list) |
| `prepare-task` | L → P | Pre-stage | Halt after plan-approved | n/a (halts before gate) |
| `estimate-task` | L → P (estimate skill) | Cost forecast | No code | always (output is JSON estimate) |
| `fast-track` | I (or P→I) | `trivial: true` | Skip L, V, J | fan-out 1 + verifier-passed-on-similar (stats lookup) |
| `medium-track` | P → I → V | Pre-bundled context, single plausible shape | Skip L, J | fan-out 1 + verifier-passed |

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
