# 06 — Memory

Memory in budai is **layered** — four scopes with different lifetimes and different consumers, with explicit promotion paths upward. Lessons that prove out get promoted; obsolete entries get pruned. The system gets smarter over time without manual curation.

This document specifies the four layers, what lives in each, who reads them, and how content moves between them.

## The four layers

| Layer | Lifetime | Where it lives | Examples |
|---|---|---|---|
| Task | Per-run | `runs/<run-id>/`, `council/<task-id>/` | Transcripts, diffs, verdicts, failure reports |
| Role | Persistent, role-scoped | `memory/lessons/<role>-<topic>.md` | "Implementers: never edit `*.orig` files" |
| Repo | Persistent, repo-wide | `memory/decisions/`, `local/conventions.md`, `local/glossary.md`, `local/untouchables.md` | "We use React Flow, not tldraw"; "term: widget = node on canvas" |
| User | Persistent, cross-repo | `~/.claude/memory/` (or runner-specific) | Personal preferences, working style across all repos |

Memory layers are meant to be read in order from most-specific to least-specific when an agent is making a decision. The Implementer, when starting a task, reads its task layer (the bundle, the plan), then its role layer (lessons for Implementers), then the repo layer (conventions, glossary, untouchables), then user layer if relevant.

## Layer 1: Task

Task-layer memory is everything produced during a single task's lifecycle: transcripts, diffs, evidence, verdicts. Lives in `runs/<run-id>/` and `council/<task-id>/` per `07-runtime-data.md`.

**Lifetime.** Bounded by the task. Transcripts and evidence are streamed to the backend; council artifacts (attempts, reviews, verdict) stay locally as long as the repo wants them, then get pruned by retention policy. The backend retains a copy.

**Read by.** Roles in the same task — the Verifier reads the Implementer's transcript; the Judge reads the Verifier's report. Across tasks, only the Librarian reads task-layer memory (when promoting lessons or auditing).

**Not memory in the colloquial sense.** Task-layer memory is more like *trace data* — the system's state during a single execution. We treat it as memory because lessons originate here and get promoted upward.

## Layer 2: Role

Role-layer memory captures patterns that apply to a specific role across many tasks. Lives in `.agents/memory/lessons/<role>-<topic>.md`.

### File format

```markdown
---
lesson: implementer-orig-files
role: implementer
created: 2026-04-12
last-recurred: 2026-05-08
recurrence-count: 5
severity: medium
status: active                  # active | promoted | obsolete
---

# Implementers: never edit `.orig` files

## Context
Tasks involving merges or conflict resolution sometimes leave behind
`<file>.orig` artifacts. Five Implementer instances across three tasks
have made the mistake of editing these as if they were source files.

## What to do
- Treat `*.orig` as gitignored merge artifacts.
- If preflight reports `*.orig` files in `src/`, escalate; don't touch them.
- The correct path is the un-suffixed version of the file.

## Why
`.orig` files are git-merge backups. Editing them does nothing because
they aren't the version git is tracking. The change appears to land but
silently has no effect on the next checkout.

## Promotion candidacy
This lesson recurs across tasks; if it recurs once more in a different
scope, it should be promoted to a repo-level convention (likely a line
in conventions.md under "merge artifacts").
```

### Lifecycle

- **Created** by the Librarian's `promote-lesson` skill when 3+ failures of the same pattern accumulate across runs.
- **Read** by all instances of the named role at task start, automatically injected into role context.
- **Updated** when the same pattern recurs (Librarian increments `recurrence-count`, updates `last-recurred`).
- **Promoted** when cross-role recurrence appears, OR when severity escalates. Promotion creates a draft entry in `local/conventions.md` and opens a human-review task.
- **Obsoleted** when the underlying cause is removed (e.g., `.orig` files added to gitignore globally, preflight script enforces). The Librarian marks `status: obsolete`; the file stays as record but isn't read into role context.

### Read scope

A role reads only lessons matching its role name (or shared lessons tagged with multiple roles). The Implementer reads `implementer-*.md`; the Planner reads `planner-*.md`. This keeps role context windows manageable.

## Layer 3: Repo

Repo-layer memory is durable knowledge that applies to everyone working in this codebase, agent or human. Four sub-categories:

### Decisions (ADRs)

Architectural Decision Records. Live in `.agents/memory/decisions/<NNNN>-<slug>.md`.

```markdown
---
adr: 0003
title: Use React Flow over tldraw for canvas widgets
date: 2026-04-19
status: accepted              # proposed | accepted | superseded | deprecated
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

## Context
We initially built the canvas on tldraw v2 because it shipped a more
complete shape system. After three weeks of work, two patterns emerged:
[...]

## Decision
We're migrating from tldraw to React Flow (@xyflow/react).

## Consequences
Positive:
- ...
Negative:
- ...
Neutral:
- ...
```

ADRs are immutable once accepted. To revise a decision, write a new ADR with `supersedes:` set to the prior ADR's ID. The prior ADR's `superseded-by:` is updated as a small exception to immutability — the rest of its content stays.

ADRs are written by Planners during planning when a decision is meaningful, OR by humans during architecture reviews, OR by the Librarian when extracting an implicit decision from accumulated practice.

### Conventions

`.agents/local/conventions.md` (merged with `base/conventions.md` per the overlay model). Sections-style markdown:

```markdown
# Conventions

## File naming
- React components: PascalCase, one per file (`MyComponent.tsx`)
- Hooks: camelCase with `use` prefix (`useCanvasStore.ts`)
- ...

## Error handling
- Throw at boundaries; pass through internally.
- ...

## IPC naming
- kebab-case channels (`terminal:spawn`, not `terminalSpawn`)
- ...
```

Conventions are read by every role at task start. The bundler's `build-task-bundle` skill pulls only the *relevant sections* into bundles based on the task's scope — pulling the whole file into every bundle wastes tokens.

### Glossary

`.agents/local/glossary.md`. One entry per term:

```markdown
# Glossary

## widget
A node on the canvas. Each widget is a React Flow node with a `type:` discriminator and `data:` payload.

## node
Same as widget. We use both terms; in conversation prefer "widget", in code prefer "node" (matches React Flow's API).

## ...
```

The bundler pulls only terms appearing in the task body. The whole glossary doesn't go into every bundle.

### Untouchables

`.agents/local/untouchables.md`. Things that look weird but must not change without explicit human approval:

```markdown
# Untouchables

## webSecurity: false in BrowserWindow
This is intentional. We need cross-origin webview interop for the canvas browser widget. See ADR 0001 and the security analysis in docs/security.md.

## The keyboard trap in src/preload/index.ts:42-58
This blocks accelerator events from reaching webview content. Removing it breaks the spatial canvas's keyboard handling. See task 023 for the original incident.
```

Untouchables are read by every role making a non-trivial change. Specifically, the bundler's overflow logic deprioritizes pulling untouchable-related code into the speculative tier — but if the task explicitly touches an untouchable area, the relevant untouchable entry is always included, even on overflow.

## Layer 4: User

User-layer memory is cross-repo, runner-specific, persistent. Lives in `~/.claude/memory/` (or wherever the runner's framework keeps its own memory — see `15-framework-agnostic.md`).

Examples:
- "User prefers terse summaries; skip pleasantries."
- "User works in Pacific time; daily summaries should fire at 17:00 PT."

User-layer memory is opaque to budai itself — budai doesn't read it. The runner reads it as part of the agent's framework-level context, separate from budai's role-specific instructions. Budai's role files are deliberately silent on user-specific preferences; those live in the user's own memory system.

## Promotion paths

```
runs/<id>/failure.md  →  memory/lessons/<role>-<topic>.md
                  (when 3+ recurrences in same role)

memory/lessons/<role>-<topic>.md  →  local/conventions.md (draft)
                  (when cross-role recurrence OR severity escalation)

local/conventions.md (entry)  →  base/conventions.md (proposed via PR)
                  (when same convention emerges in 2+ repos)
```

Each promotion is gated:

- Run → Role: auto, by Librarian, for purely role-internal lessons.
- Role → Repo: drafted by Librarian, requires human review (a `update-conventions-<topic>` task).
- Repo → Registry: drafted by Librarian, opens a PR against the registry, requires registry-maintainer review.

## Demotion / pruning

Memory entries that are no longer relevant get pruned:

- **Lessons** marked `status: obsolete` are kept on disk but excluded from role context. The Librarian reviews obsolete lessons monthly; if they remain obsolete for 90 days, they're moved to `memory/archived-lessons/`.
- **Conventions** that contradict current practice (per `audit-docs` findings) are flagged for human review, not auto-removed.
- **ADRs** are never deleted. Superseded ADRs stay; they document the history of decisions.
- **Glossary entries** for terms no longer in use are flagged for review.
- **Untouchables** are removed only by explicit human action — never auto-pruned.

## What memory is NOT

- Not the same as state. State is the system's current configuration (manifest, role files, conventions). Memory is the accumulated *learnings*.
- Not the same as logs. Logs are agent-process traces. Memory is what's worth keeping past a single run.
- Not the same as the index. The index is a navigation aid (where files live, what they do). Memory is *why* we built things this way and *what* we've learned along the way.
- Not unbounded. Pruning policies keep each layer tractable. Promotions and demotions reshape what's active.
