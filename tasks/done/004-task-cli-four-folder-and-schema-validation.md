---
id: 004
title: Task CLI four-folder and schema validation
type: feature
scope: bin
priority: P1
status: done
fan-out: 1
needs-architect: true
plan-approved: true
result-approved: true
trivial: false
depends-on: [002, 003]
blocks: [007, 008, 009, 010, 013]
sources: [F009]
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-09T16:00:00Z
workflow: ship-feature
bundle-budget: 84000
retry-budget: 2
---

# Task 004: Task CLI four-folder and schema validation

## Objective
Teach `bin/task` to support the dogfood four-folder layout while preserving the documented standard layout.

## User story
As a maintainer, I want `bin/task` to create, list, move, and validate dogfood tasks, so that task files do not need to be managed manually.

## Acceptance criteria
- AC1: `tasks-layout: legacy-four-folder` makes new tasks land in `tasks/todo/`.
- AC2: `bin/task list` walks `backlog`, `todo`, `in-progress`, and `done`.
- AC3: `bin/task move` moves files across the four folders and updates frontmatter consistently.
- AC4: Standard `tasks/open` and `tasks/archive` behavior still works when the manifest omits `tasks-layout`.
- AC5: Task creation and status moves validate schema, dependencies, cycles, and legal transitions.

## Context
- Source finding: F009.

## Plan

### Approach
Wire the manifest's `tasks-layout` field through to `bin/task` so the CLI is layout-aware, then add a small validation module so `bin/task new` and `bin/task move` both check schema, dependencies, cycles, and transitions before mutating state. Status stays the canonical state; folder is a derived index — this lets `tasks-layout: standard` keep its current bit-for-bit behavior (AC4) while `legacy-four-folder` routes the same statuses to a richer four-folder topology. A new `bin/lib/task_schema.py` module owns validation; `bin/task` becomes a thin orchestrator over `manifest`, `task_schema`, and a layout-aware path helper.

### Decomposition
Single task — one Implementer.

### File-level changes

#### Files to create

- **`bin/lib/task_schema.py`**
  - Purpose: Frontmatter schema, status state machine, and dependency-graph validators used by `bin/task new` and `bin/task move`.
  - Exports:
    - `VALID_STATUSES: list[str]` — canonical list, including the new `backlog` status. Single source of truth; `bin/task` imports from here instead of redefining.
    - `VALID_TYPES: list[str]` — moved from `bin/task` for the same reason.
    - `STATUS_TRANSITIONS: dict[str, set[str]]` — adjacency map encoding the state machine in `docs/11-task-format.md`. Includes `backlog → open`, `open → planning`, `planning → reviewing-plan`, `reviewing-plan → implementing`, `implementing → reviewing-result`, `reviewing-result → done`, plus terminal transitions to `abandoned` / `failed` from any non-terminal state, and `* → coordinator` for parent flips. The Implementer should confirm exact edges against `docs/11-task-format.md` and add a comment block citing the doc.
    - `folder_for_status(status: str, layout: str) -> str` — returns `"backlog" | "todo" | "in-progress" | "done"` for `legacy-four-folder`, or `"open" | "archive"` for `standard`. Pure function, no I/O.
    - `layout_folders(layout: str) -> list[str]` — returns the configured folder names in display order.
    - `parse_frontmatter(text: str) -> dict[str, Any]` — minimal YAML frontmatter parser; reuse `yaml.safe_load` on the fenced block. Returns `{}` if no frontmatter.
    - `validate_frontmatter(data: dict, layout: str) -> list[str]` — returns error strings; empty means valid. Checks: required keys present, `type` in `VALID_TYPES`, `status` in `VALID_STATUSES`, `id` parseable, `title` non-empty, `depends-on` is a list, booleans are bool, timestamps parseable.
    - `validate_transition(old: str, new: str) -> list[str]` — checks `new in STATUS_TRANSITIONS.get(old, set())`. Empty list on `old == new` (idempotent).
    - `load_all_tasks(repo_root: Path, layout: str) -> dict[str, Path]` — walks every configured folder once, parses frontmatter, returns `{task_id: path}`. Used to validate that `depends-on` ids exist and to compute next ID.
    - `validate_dependencies(task_id: str, depends_on: list[str], all_tasks: dict[str, Path]) -> list[str]` — verifies each ID exists; runs DFS to detect cycles; rejects self-loops.
  - Key decisions: pure functions where possible (no `print`, no `sys.exit` — return error lists). The CLI layer in `bin/task` decides exit codes. Cycle detection uses iterative DFS to avoid recursion limits; documented in a comment.
  - File header (`@purpose / @why / @role / @exports / @uses / @stability / @gotchas`): `@stability experimental`. `@gotchas`: state-machine adjacency must stay in lock-step with `docs/11-task-format.md`; if you change one, change the other.

#### Files to modify

- **`bin/lib/manifest.py`**
  - Lines ~30-46 (the `Manifest` dataclass): add `tasks_layout: str = "standard"` after `runtime_backend` (keep alphabetical/logical grouping consistent with surrounding fields).
  - Lines ~50-72 (the `load_manifest` function): add `tasks_layout=data.get("tasks-layout", "standard")` to the `Manifest(...)` constructor call. Validate the value: raise `ValueError(f"Unknown tasks-layout: {value!r}")` if it is not in `{"standard", "legacy-four-folder"}`. Add a module-level constant `VALID_TASKS_LAYOUTS = ("standard", "legacy-four-folder")` near the top so the set is discoverable.
  - Why this file: it is the single point that turns YAML into typed data. Today it silently drops `tasks-layout`; that's the root cause of the four-folder gap (Librarian observation in bundle).

- **`bin/task`**
  - Top imports (lines ~14-18): add `from lib.manifest import find_repo_root, load_manifest` (currently only imports `find_repo_root`). Add `from lib.task_schema import (VALID_STATUSES, VALID_TYPES, folder_for_status, layout_folders, load_all_tasks, validate_frontmatter, validate_transition, validate_dependencies)`.
  - Lines 17-31 (the local `VALID_TYPES` and `VALID_STATUSES` constants): delete — now sourced from `task_schema`. Adds `backlog` to the canonical list as a side effect.
  - `next_task_id()` (lines ~46-56): replace the hardcoded `["open", "archive"]` walk with a walk over `layout_folders(layout)`. Signature becomes `next_task_id(tasks_dir, layout) -> int`.
  - `cmd_new()` (lines ~59-165):
    - Take `layout` and `manifest` from `main()`.
    - Replace `(tasks_dir / "open").mkdir(...)` with a loop creating every folder in `layout_folders(layout)`.
    - Add an optional `--status` flag to the argparser (default `"open"`, choices = `VALID_STATUSES`). Use this status in the frontmatter and to choose the destination folder via `folder_for_status(status, layout)`.
    - After building the frontmatter dict but before writing the file: call `validate_frontmatter(data, layout)` and `validate_dependencies(...)` against the result of `load_all_tasks(repo_root, layout)`. On any error, print all errors to stderr and return `1` without writing the file.
    - Replace `task_file = tasks_dir / "open" / task_filename` with `task_file = tasks_dir / folder_for_status(status, layout) / task_filename`.
  - `cmd_move()` (lines ~168-197):
    - Take `layout` from `main()`.
    - Replace the `["open", "archive"]` lookup with a loop over `layout_folders(layout)`.
    - Parse the existing frontmatter to read `old_status` (use `task_schema.parse_frontmatter`).
    - Call `validate_transition(old_status, args.status)`; on error, print and return `1`.
    - Re-validate the full frontmatter post-edit (`validate_frontmatter`) and re-validate dependencies (in case the move would orphan a not-yet-done dependent — leave actual dependent-blocking to the Router per `docs/11-task-format.md`; here we only ensure depends-on IDs still resolve).
    - Replace the hardcoded archive-routing block (`if args.status in ("done", "abandoned", "failed")...`) with: compute `target_folder = folder_for_status(args.status, layout)`; if `task_file.parent.name != target_folder`, `os.replace` (atomic) the file into the target folder. Also bump the `updated:` timestamp in the frontmatter (currently the script only edits `status:`).
  - `cmd_list()` (lines ~200-222):
    - Take `layout` from `main()`.
    - Replace the single-folder walk with a walk over every folder in `layout_folders(layout)`.
    - Group by status (existing logic) but iterate `VALID_STATUSES` so output ordering is deterministic.
    - When the layout is `legacy-four-folder`, prepend a per-folder section header (`backlog`, `todo`, `in-progress`, `done`) so the human view tracks the file system. Standard layout keeps the current grouping by status only.
  - `main()` (lines ~225-260):
    - After `repo_root = find_repo_root()`, add `manifest = load_manifest(repo_root)` and `layout = manifest.tasks_layout`.
    - Pass `layout` (and `manifest` if needed) into the dispatched `cmd_*` functions. Consider a small `Context` dataclass or just an extra positional arg — Implementer's choice.
  - Argparser changes:
    - `p_new`: add `p_new.add_argument("--status", choices=VALID_STATUSES, default="open")`.
    - No new `move` flag; status remains positional.

- **`tasks/done/.gitkeep`** (no change — confirms the folder exists; Implementer should `mkdir -p tasks/{backlog,todo,in-progress,done}` and add `.gitkeep` to any missing folder. `tasks/in-progress/` and `tasks/todo/` already exist in this repo; verify the others.)

- **`memory/decisions/0001-task-cli-layout-and-validation.md`** (already written by the Planner during this run; do not modify).

#### Tests

Per local convention "Add or update tests before broadening CLI behavior" and per task-003 test harness conventions:

- Add `tests/bin/test_task_cli.py` (or whatever path task-003 establishes; if task-003 has not yet landed at implementation time, the Implementer should sequence: confirm task-003 status; if not done, defer the test file to a small follow-up sub-task and document in result).
- Test cases (one assertion or scenario each, per "Tests are named after behavior"):
  - `test_new_task_lands_in_todo_under_legacy_four_folder`
  - `test_new_task_lands_in_open_under_standard`
  - `test_move_done_routes_to_done_under_legacy_four_folder`
  - `test_move_done_routes_to_archive_under_standard`
  - `test_list_walks_all_four_folders`
  - `test_list_walks_open_only_under_standard`
  - `test_invalid_status_in_new_is_rejected`
  - `test_invalid_transition_in_move_is_rejected`
  - `test_missing_dependency_id_is_rejected`
  - `test_dependency_cycle_is_rejected`
  - `test_unknown_tasks_layout_in_manifest_raises`
  - `test_manifest_without_tasks_layout_defaults_to_standard`

### Risks and escalations

- **AC5 is genuinely four concerns in one bullet (schema, dependencies, cycles, transitions).** All four share the same call sites and the same module, so splitting would force a second pass through the same files. Kept together. Risk: the validation surface still grows the diff substantially. Mitigation: each validator is a pure function under ~30 lines; the dependency walker is a single iterative DFS. If the Implementer finds the diff exceeds the retry budget, escalate back to the Planner for a split rather than shipping partial validation.
- **`backlog` is a new status not currently documented in `docs/11-task-format.md`.** Adding it to `VALID_STATUSES` works at runtime but creates a doc-vs-code drift. Mitigation: leave the doc update to a follow-up doc-sweep task; flag in the result so the Librarian's close sweep promotes a finding. Alternative considered: include the doc edit here. Rejected because it widens the AC scope mid-flight.
- **`bin/task` currently writes frontmatter as a list of pre-formatted lines, not as a YAML dump.** The new `cmd_move` needs to update both `status:` and `updated:` atomically; using regex twice is fragile. Mitigation: the Implementer should switch the move path to parse → mutate dict → re-emit via `yaml.safe_dump`, preserving key order. The new path path (read frontmatter into dict) also feeds `validate_frontmatter`, so it's not extra work. Risk: re-emitted YAML may slightly differ in formatting (quoting, ordering). Mitigation: the test suite asserts on parsed values, not byte-equal text.
- **`tasks/done/` and `tasks/backlog/` may not exist on the dogfood repo.** Verified at plan time: `tasks/in-progress/` and `tasks/todo/` exist; `tasks/done/.gitkeep` exists (per bundle). `tasks/backlog/` is uncertain. Implementer must `mkdir -p` all four under the legacy-four-folder layout and ensure `.gitkeep` is present in any newly created folder so the layout survives a clean checkout.
- **`.agents/index/` does not exist** (Librarian flagged). No relevance signal beyond direct inspection. The Sweeper's `regenerate-index` skill should run at task close; flag in the verdict for the closing Librarian.
- **F020 (registry-source: self resolution gap) is adjacent infrastructure debt.** Out of scope for this task. The validation module reads from disk only; it does not invoke `resolve()` from `bin/lib/resolution.py`, so F020 cannot bite this work. No action.
- **Phase 0 placeholder `bin/lib/runner.py`** is in the bundle for context only. Not modified.

### Acceptance criteria mapping

- **AC1** (`tasks-layout: legacy-four-folder` makes new tasks land in `tasks/todo/`) → covered by the `--status open` default in `cmd_new` plus `folder_for_status("open", "legacy-four-folder") == "todo"` in `bin/lib/task_schema.py`.
- **AC2** (`bin/task list` walks all four folders) → covered by `cmd_list` iterating `layout_folders(layout)` instead of the single hardcoded `tasks/open/`.
- **AC3** (`bin/task move` moves files across folders and updates frontmatter consistently) → covered by `cmd_move` calling `folder_for_status(new_status, layout)` and `os.replace`-ing into the target folder, plus bumping `updated:` alongside `status:` in the YAML re-emit.
- **AC4** (standard `tasks/open` and `tasks/archive` behavior unchanged when manifest omits `tasks-layout`) → covered by the `tasks_layout: str = "standard"` default in `Manifest` plus `folder_for_status("done", "standard") == "archive"` and the `layout_folders("standard") == ["open", "archive"]` mapping. Verified by `test_move_done_routes_to_archive_under_standard` and `test_list_walks_open_only_under_standard`.
- **AC5** (creation and moves validate schema, dependencies, cycles, legal transitions) → covered by the four validators in `bin/lib/task_schema.py` (`validate_frontmatter`, `validate_dependencies` (which subsumes ID-existence and cycle detection), `validate_transition`) called from both `cmd_new` and `cmd_move` before any file mutation.

### Recommended fan-out

1 — the architectural decisions are locked in this plan and ADR 0001. The remaining work is mechanical wire-up plus a contained validation module. Parallel attempts would diverge on style without producing materially different shapes; the Judge would have nothing meaningful to choose between.

### Confidence level

high — every change has a named call site, the state machine and folder mapping are pinned in the ADR, and there is no architectural unknown. The only soft spot is the YAML re-emit in `cmd_move` (currently a regex), which is well within an Implementer's reach.

### ADR

Wrote `memory/decisions/0001-task-cli-layout-and-validation.md` documenting the layout discovery path, the status-to-folder mapping for both layouts, the choice of status-keyed (not folder-keyed) `move`, and the choice of an in-repo Python validation module over JSON Schema for Phase 0.

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
