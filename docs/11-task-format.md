# 11 — Task format

A **task** is a markdown file describing a unit of work. It is the input to a workflow; the workflow processes it; the result is an integrated commit (or a report, in the case of audits).

Tasks are the smallest schedulable unit in budai. Everything else — bundles, plans, attempts, verdicts — references a task.

## File location

```
tasks/
├── README.md
├── TEMPLATE.md
├── open/
│   └── <NNN>-<slug>.md         # active or queued
└── archive/
    └── <NNN>-<slug>.md         # shipped or abandoned
```

Open vs. archive is the only durable folder split. Fine-grained status (planning, implementing, reviewing, etc.) lives in frontmatter, not in folders. With multiple agents working in parallel, folder-moves aren't atomic; frontmatter writes are.

A task moves from `open/` to `archive/` exactly once, at archival (Step 12 of the journey).

## Naming

`<NNN>-<slug>.md` where:

- `<NNN>` is the next available numeric ID, zero-padded to three digits (or four when you cross 999).
- `<slug>` is a kebab-case short name derived from the title.

Examples:
- `042-add-terminal-widget.md`
- `043-fix-canvas-zoom-snap.md`
- `100-refactor-store-actions.md`

### Sub-task IDs

When a Planner decomposes, sub-tasks use `<parent-id><letter>`:
- `042a-implement-terminal-manager.md`
- `042b-wire-ipc-channel.md`
- `042c-build-terminal-widget-node.md`

Letters count up: a, b, c, ... z, aa, ab, ... if more than 26 sub-tasks (rare; usually re-decompose at that point).

The bundle file lives next to the task: `042-add-terminal-widget.bundle.md`.

## Frontmatter schema

Locked. The runner validates against this schema at task creation and on every status flip.

```yaml
---
id: 042
title: Add terminal widget
type: feature                    # feature | bug | refactor | research | audit
scope: renderer                  # high-level area of the codebase
status: open                     # see status state machine below
fan-out: 1                       # how many parallel implementer attempts
needs-architect: true
plan-approved: false
result-approved: false
trivial: false                   # affects auto-approve gates
depends-on: [041]
blocks: []                       # tasks that depend on this one (auto-derived)
parent: null                     # parent task ID if this is a sub-task
sub-tasks: []                    # sub-task IDs if this is a coordinator
created: 2026-05-08T10:00:00Z
created-by: andrey               # human name or agent identifier
updated: 2026-05-08T10:00:00Z
workflow: ship-feature           # which workflow processes this
bundle-budget: 80000             # optional: override default token budget
retry-budget: 2                  # optional: override workflow default
---
```

### Field reference

- **id** — numeric ID, must match filename. Sub-tasks use parent-id + letter.
- **title** — human-readable, ≤80 chars.
- **type** — drives workflow selection. Each type has a default workflow per `05-workflows.md`.
- **scope** — high-level area string (e.g., `renderer`, `main`, `store`, `docs`, `infra`). Used by the bundler for relevance scoring.
- **status** — see state machine below.
- **fan-out** — integer ≥ 1. Defaults to the workflow's `default-fan-out`.
- **needs-architect** — when false, Planner is skipped (see `08-the-journey.md` Step 3).
- **plan-approved** / **result-approved** — set to true at human gates (or by auto-approve rules).
- **trivial** — when true, eligible for auto-approve at the architecture gate.
- **depends-on** — list of task IDs that must close before this task can move past `open`.
- **blocks** — auto-derived (the inverse of depends-on). Maintained by the Librarian.
- **parent** / **sub-tasks** — for coordinator decomposition (see `10-plan-format.md`).
- **created** / **updated** / **created-by** — provenance. ISO-8601 UTC.
- **workflow** — which workflow file processes this task. Default = lookup by type.
- **bundle-budget** / **retry-budget** — optional per-task overrides.

## Status state machine

```
open → planning → reviewing-plan → implementing → reviewing-result → done
                                       ↘ abandoned
                                       ↘ failed
```

Coordinator path (when Planner decomposes):

```
open → planning → reviewing-plan → coordinator → done (when all sub-tasks done)
```

| From → To | Who flips | Trigger |
|---|---|---|
| open → planning | Router | Task picked up; Librarian invoked for bundle |
| planning → reviewing-plan | Planner | Plan section appended; awaits human gate |
| reviewing-plan → implementing | Human (or auto-approve) | `plan-approved: true` |
| reviewing-plan → planning | Human | Plan revisions requested; Planner re-runs |
| implementing → reviewing-result | Judge | Verdict written; awaits human gate |
| reviewing-result → done | Human (or auto-approve) | `result-approved: true`; Librarian sweeps |
| reviewing-result → implementing | Human | Result revisions requested; Judge re-runs |
| any → abandoned | Human | Task no longer relevant |
| any → failed | Judge | All attempts failed past retry budget |
| reviewing-plan → coordinator | Planner (during decomposition) | Sub-tasks created |
| coordinator → done | Librarian | All sub-tasks reach done |

Status transitions happen via `bin/task move <id> <status>` to keep audit trails clean. Direct frontmatter edits are technically allowed but bypass logging.

## Body structure

Required sections, in order:

```markdown
# Task <id>: <title>

## Objective
<1-2 paragraphs — what we're trying to accomplish>

## User story
<As a <role>, I want <capability>, so that <outcome>>

## Acceptance criteria
- AC1: <criterion>
- AC2: <criterion>
...

## Plan
<Filled in by the Planner — see 10-plan-format.md>

## Verdict
<Filled in by the Librarian sweep at archival — points to council/<id>/verdict.md>
```

Optional sections (after Plan, before Verdict):

```markdown
## Notes
<Free-form notes from humans or Librarian>

## Discussion
<References to messages/threads/ for material conversations>
```

## Three creation paths (recap)

From `08-the-journey.md` Step 0, all three paths produce the same task file shape:

1. **Human writes it.** `bin/task new <type>` — interactive script.
2. **Planner decomposes a parent task.** Calls `bin/task new` programmatically, sets parent + depends-on.
3. **Librarian opens an improvement task.** During scheduled sweeps when skill quality drops or recurring failures cluster.

Same script, same schema, different callers.

## `bin/task new` flow

The script prompts for fields with sensible defaults per type. Skip-safe (sane defaults):

```
$ bin/task new feature
Title: Add terminal widget
Scope: renderer
User story (As a / I want / so that):
> As a developer, I want a terminal widget on the canvas, so that I can run commands without leaving the app.
Acceptance criteria (one per line, blank to finish):
> Terminal renders inside a widget node
> Commands execute in a real PTY
> Multiple terminals are independent
> Closing the widget kills the PTY
>
fan-out [1]:
needs-architect [yes]:
trivial [no]:
depends-on (comma-separated IDs, or empty):

Created tasks/open/042-add-terminal-widget.md
```

For decomposition (called by Planner), the script accepts flags:
`bin/task new --type=feature --parent=042 --slug=implement-terminal-manager --depends-on=041 --skip-prompts ...`

## Type-specific defaults

| Type | Default workflow | Default fan-out | needs-architect |
|---|---|---|---|
| feature | ship-feature | 1 | true |
| bug | fix-bug | 1 | false (true if marked non-trivial) |
| refactor | refactor | 1 | true |
| research | research | 3 | true |
| audit | audit-repo | 1 | false |

These are scaffolded by the script; the human can override during creation.

## depends-on chains

The Router checks `depends-on` before flipping a task from `open` to `planning`. If any dependency is not yet `done`, the task stays `open`.

The Librarian maintains the `blocks:` field as the inverse — if task 043 depends-on 042, task 042's `blocks: [043]` is auto-set. Used by the canvas widget to render dependency graphs.

Cycles in depends-on are rejected at task creation (the script walks the dependency graph and refuses to create a cycle). Existing cycles caught later by the Librarian flag for human resolution.

## Validation rules

A task is valid if:

1. Frontmatter parses against the schema above.
2. `id` matches the filename.
3. `title` is non-empty.
4. `type` is one of the recognized values.
5. Body has Objective, User story, Acceptance criteria sections (Plan is added by Planner; Verdict by Librarian).
6. `depends-on` references existing task IDs (open or archived).
7. Status transitions follow the state machine.

Validation runs at task creation and at every status flip. Failed validation prevents the transition; the task stays in its prior state.

## Templates

`tasks/TEMPLATE.md` is the canonical empty form. New types can ship templates in `local/task-templates/<type>.md` for repos with strong opinions about task shape.

Per `02-structure.md` resolution rules, template lookup is local first, base second.

## Auto-spawned tasks

Several flows produce tasks programmatically:

- **Workflow auto-spawn follow-ups.** `ship-feature` spawns `test-coverage-<id>`; `fix-bug` spawns `regression-test-<id>`; `audit-repo` spawns `address-finding-<id>` for high-severity findings.
- **Judge outstanding-concerns spawning.** When the verdict lists outstanding concerns above a severity threshold, each one becomes a task.
- **Librarian improvement-task spawning.** When skill quality drops below threshold, the Librarian opens `improve-skill-<name>`.
- **Lesson promotion.** When a lesson reaches repo-level promotion, the Librarian opens an `update-conventions-<topic>` task.

Auto-spawned tasks have `created-by: <agent-name>` and a `spawned-from:` frontmatter field referencing the parent task or the trigger.

## What a task is NOT

- Not a project. Tasks are the smallest unit; epics or projects are conventions on top, not platform features.
- Not a place to embed implementation details. Implementation details live in the plan, the bundle, or the source code.
- Not a discussion thread. Substantive discussion lives in `messages/threads/`; tasks reference threads.
- Not editable by Implementers during implementation. Once `plan-approved: true`, the task body is frozen except for status flips and Librarian-managed fields. Material changes mid-flight require returning to `planning`.
