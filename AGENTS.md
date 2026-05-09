# AGENTS.md - budai

## What this repo is

budai is an operating system for fleets of AI agents working on a codebase. This repo is both the public registry for budai content and, via `.agents/manifest.yaml`, a dogfood consumer of budai itself.

Current phase: early scaffold. Some behavior is specified in docs, some is scaffolded in Python CLI scripts, and some is still placeholder work tracked in `tasks/todo/`.

## Where things live

```
<repo-root>/
├── base/                 # registry roles, skills, workflows, runners, conventions, templates
├── bin/                  # Python CLI entrypoints and shared helpers
├── docs/                 # design and operations documentation
├── examples/             # sample manifests and adoption notes
├── tasks/                # dogfood task files: backlog/, todo/, in-progress/, done/
├── .agents/              # dogfood manifest and local repo policy
├── findings.md           # inbox of observed findings before promotion
└── AGENTS.md             # this orientation file
```

## The two-minute system tour

The public design explains budai's desired workflow: Librarian builds a bundle, Planner writes a plan, Implementer codes, Verifier captures evidence, Judge integrates, and Librarian sweeps. The current repo is not fully automated yet. For now, improvement ideas start in `findings.md`, get promoted to `tasks/todo/`, and then should be handled through the role workflow as tooling matures.

## Conventions

Read `.agents/local/conventions.md` before changing this repo. Key points:

- Keep registry content at the repo root; `.agents/` is dogfood configuration.
- Be explicit about whether docs describe working code or future/spec behavior.
- Dogfood tasks use the four-folder layout.
- Do not opportunistically fix technical findings while creating task scaffolding.

## Tasks workflow

Tasks live in `tasks/todo/` until work begins. Move active work to `tasks/in-progress/` and completed work to `tasks/done/`. `tasks/backlog/` is for deferred work that is accepted but not ready to schedule.

Each task file has frontmatter with `id`, `title`, `type`, `priority`, `status`, `depends-on`, and source finding references where relevant.

## Pre-flight before declaring done

Current validation is still being stabilized. Run the available checks where possible:

```bash
./bin/preflight --json
./bin/postflight --json
```

If dependency setup is missing, document the failure in the task evidence instead of pretending the check passed.

## Untouchables

See `.agents/local/untouchables.md`.

## Glossary

See `.agents/local/glossary.md`.
