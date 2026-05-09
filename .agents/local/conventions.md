# Conventions (local - budai)

These conventions apply when budai is working on itself as a consumer repo.
They extend the registry-level baseline in `base/conventions.md`.

## Repository shape

- This repo is both the budai registry and a dogfood consumer.
- Registry content lives at the repo root in `base/`, `docs/`, `examples/`, and `bin/`.
- Dogfood runtime/configuration lives under `.agents/`; do not duplicate registry `base/` into `.agents/base/` until `librarian sync` defines that behavior.

## Python CLI

- CLI entrypoints live directly under `bin/`; shared Python modules live under `bin/lib/`.
- Keep CLI scripts dependency-light and runnable from a fresh checkout after documented dependency installation.
- Prefer standard-library parsing and structured helpers over ad hoc text edits.
- Add or update tests before broadening CLI behavior.

## Documentation truth

- Docs must distinguish specified behavior, scaffolded placeholder behavior, and working implementation.
- If a script is a placeholder, docs must say so at the command site, not only in changelog notes.
- Examples must use commands and paths that exist in the current repo.

## Tasks

- Dogfood tasks use `tasks/{backlog,todo,in-progress,done}`.
- New promoted findings land in `tasks/todo/`.
- `findings.md` remains the audit trail; promoted entries keep their original text and gain a `-> task-NNN` marker.

## Headers

- Source headers apply to Python files under `bin/` and `bin/lib/`.
- Header work is tracked by task `014`; do not opportunistically add headers outside that task.
