# AGENTS.md — <PROJECT_NAME>

<!-- TEMPLATE: replace <PROJECT_NAME> and the placeholder content below.
     This file is the entry point for any AI agent landing on this repo.
     It should answer four questions in under 60 seconds of reading:
     1. What is this repo and its current state?
     2. How does the system fit together?
     3. How do we work here?
     4. Why was X built that way?
     Detailed answers live in linked docs; this file orients. -->

## What this repo is

<!-- TODO: 1-2 sentences. Project name, what it does, current phase. -->

<PROJECT_NAME> is <ONE-SENTENCE_DESCRIPTION>.

Current phase: <ALPHA | BETA | PRODUCTION>.

## Where things live

<!-- TODO: top-level map with one line per directory. Update when structure changes. -->

```
<repo-root>/
├── src/                       # product code
├── tests/                     # test suite (or colocated with src)
├── docs/                      # human-facing documentation
├── tasks/                     # budai task files (open/, archive/)
├── memory/                    # decisions, lessons (durable knowledge)
├── .agents/                   # budai operating system
│   ├── manifest.yaml          # what budai version + skills/roles/workflows we use
│   ├── manifest.lock.yaml     # resolved versions for reproducibility
│   ├── base/                  # registry-pulled content (read-only)
│   ├── local/                 # repo-specific overrides + extensions
│   ├── runners/               # claude-code.md (and future runners)
│   └── runtime data           # runs/, council/, messages/, stats/, index/ (gitignored)
└── bin/                       # budai CLI scripts
```

## The two-minute system tour

<!-- TODO: walk a reader through how a real user request becomes a result.
     Concrete enough to give them mental model handles. ~5-7 sentences. -->

<EXAMPLE_FLOW_DESCRIPTION>

## Conventions

See `.agents/local/conventions.md` for repo-specific conventions and `.agents/base/conventions.md` for the language-agnostic baseline.

Key points:
<!-- TODO: top 3-5 conventions an agent needs to know immediately. -->

- ...
- ...
- ...

## Tasks workflow

Tasks live in `tasks/open/`. Status is tracked in frontmatter (`open` → `planning` → `implementing` → `reviewing-result` → `done`).

To start a task: `bin/task new <type>`.
To move a task: `bin/task move <id> <status>`.
To list tasks: `bin/task list`.

Workflow types: `feature`, `bug`, `refactor`, `audit`. Each routes through a different workflow per `.agents/base/workflows/`.

## Pre-flight before declaring done

```bash
bin/preflight        # validates repo state
bin/run-tests        # full test suite
bin/postflight       # validates output (no .orig files, etc.)
```

If any of these fail, the task isn't done.

## Untouchables

<!-- TODO: top-level pointer; details in local/untouchables.md. -->

Things that look weird but must NOT change without discussion. See `.agents/local/untouchables.md`.

## Glossary

<!-- TODO: top-level pointer; details in local/glossary.md. -->

Domain terms specific to this repo. See `.agents/local/glossary.md`.

## Index

For detailed file-by-file information: `.agents/index/detailed.md`.
For a flat tree: `.agents/index/tree.md`.

## Working with budai

This repo uses the [budai](https://github.com/Dopomogai/budai) operating system for multi-agent collaboration. Read [`docs/00-overview.md`](https://github.com/Dopomogai/budai/blob/main/docs/00-overview.md) of the budai docs to understand the framework.

Key concepts:
- **Roles** — Planner, Implementer, Verifier, Judge, Librarian
- **Skills** — reusable procedures (peer-review, audit-docs, etc.)
- **Workflows** — multi-role orchestration (ship-feature, fix-bug, etc.)
- **Bundle** — context file built per-task by the Librarian
- **Council** — multi-attempt fan-out record with verdict

If you're an agent reading this for the first time: read this file end to end, then `.agents/local/conventions.md`, then the task you're assigned. The bundle in `tasks/open/<id>.bundle.md` (built by the Librarian) gives you 95% of what you need.
