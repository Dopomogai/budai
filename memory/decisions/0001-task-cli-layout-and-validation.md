# ADR 0001 — Task CLI layout selection and validation surface

- Status: accepted
- Date: 2026-05-09
- Source: task-004

## Context

`bin/task` hardcodes `tasks/{open,archive}/` while the dogfood manifest declares `tasks-layout: legacy-four-folder` and the local conventions specify `tasks/{backlog,todo,in-progress,done}/`. The CLI ignores the manifest entirely. F009 promoted this to task-004.

Three coupled questions had to be answered together:

1. How does `bin/task` discover *which* layout to use?
2. What does the four-folder layout look like in terms of status-to-folder mapping?
3. AC5 also asks for schema, dependency, cycle, and legal-transition validation at create + move. Where does that logic live, and what is its source of truth?

We need a decision now because tasks 007, 008, 009, 010, and 013 all depend on task-004; their plans assume `bin/task` works.

## Decision

**1. Layout discovery.** `bin/lib/manifest.py:Manifest` gains a `tasks_layout: str = "standard"` field. `load_manifest()` reads `tasks-layout` from the YAML root (kebab-case key, snake_case attribute — consistent with existing `budai_version`). Recognized values: `"standard"` (default; equals current two-folder behavior) and `"legacy-four-folder"` (the dogfood layout). Unknown values raise. `bin/task` calls `load_manifest()` once at startup and threads the layout into all subcommands.

**2. Status-to-folder mapping (legacy-four-folder).** The CLI is *status-driven*. `bin/task move <id> <new-status>` flips the frontmatter and the file's parent folder is a derived function of the new status. The mapping:

| Status | Folder |
|---|---|
| `backlog` | `tasks/backlog/` |
| `open` | `tasks/todo/` |
| `planning` | `tasks/in-progress/` |
| `reviewing-plan` | `tasks/in-progress/` |
| `implementing` | `tasks/in-progress/` |
| `reviewing-result` | `tasks/in-progress/` |
| `coordinator` | `tasks/in-progress/` |
| `done` | `tasks/done/` |
| `abandoned` | `tasks/done/` |
| `failed` | `tasks/done/` |

`backlog` is added to `VALID_STATUSES` as a pre-promotion holding state. `bin/task new` defaults `status: open` (lands in `todo/` under four-folder; `open/` under standard). Operators can pass `--status backlog` to drop directly into the backlog folder.

For the standard layout the mapping reduces to: `done | abandoned | failed → tasks/archive/`, everything else → `tasks/open/`. This matches today's behavior exactly, satisfying AC4.

**3. CLI shape.** `bin/task move` keeps its current signature: `bin/task move <id> <new-status>`. We do *not* add a folder-keyed alternative. Status is the canonical state; folder is the index. This keeps the legacy two-folder code path bit-for-bit identical and avoids a second API surface.

**4. Validation source of truth.** A new module `bin/lib/task_schema.py` holds:

- A `TaskFrontmatter` `TypedDict` (or `dataclass` — Implementer's choice) enumerating required + optional keys, types, and the legal status set.
- `validate_frontmatter(data, layout) -> list[str]` — returns a list of human-readable error strings; empty list means valid.
- `validate_transition(old_status, new_status) -> list[str]` — enforces the state machine from `docs/11-task-format.md`.
- `validate_dependencies(task_id, depends_on, all_tasks) -> list[str]` — verifies every referenced ID exists across all four (or two) folders and detects cycles via DFS on the depends-on graph.

`docs/11-task-format.md` remains the human-readable contract. The Python module is the executable enforcement. Both must agree; the doc is normative when they diverge. JSON Schema was rejected for Phase 0 — adds a dependency (`jsonschema`) and YAML→JSON adapter for negligible benefit at this scale.

## Consequences

- `bin/task` grows from a flat single-file script to a script + a sibling validation module. Acceptable; matches the local convention "shared Python modules live under `bin/lib/`".
- The status state machine is now enforced. Existing manual frontmatter edits that violate transitions will fail at the next `bin/task move`. Mitigation: validation errors are warnings-on-list and hard-fail-on-create/move, but `bin/task list` keeps rendering invalid tasks (so operators can spot the drift).
- The four-folder layout is a true superset of the two-folder layout — every status that exists in standard exists in legacy-four-folder, just with a different folder. This means findings, related-tasks, and any future tooling can use status as the lingua franca and treat folder as an implementation detail.
- `backlog` becomes a recognized status. `docs/11-task-format.md` does not currently list it; task-004 must add it to the state machine doc OR explicitly leave that to a follow-up doc-sweep task. Planner choice: leave the doc sweep to a follow-up — task-004 already touches enough surface area.
- The `bin/task` `next_task_id()` scan must walk all configured folders (two or four). A small layout-aware path helper handles this.

## Alternatives considered

- **Folder-keyed move (`bin/task move <id> --to in-progress`)**: rejected. Two parallel APIs (status-keyed and folder-keyed) double the surface area and create ambiguity when status and folder disagree.
- **JSON Schema for validation**: rejected for Phase 0; revisit if a non-Python consumer ever needs to validate task frontmatter.
- **Splitting AC5 into a follow-up**: rejected. Schema, dependencies, cycles, and transitions all share the same call sites (`cmd_new`, `cmd_move`) and the same `bin/lib/task_schema.py` module. Splitting would force a second pass over the same files within weeks. The validation logic itself is small (a few hundred lines).
