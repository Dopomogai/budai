---
id: 006
title: Manifest parser and example compatibility
type: bug
scope: bin
priority: P2
status: open
fan-out: 1
needs-architect: false
plan-approved: false
result-approved: false
trivial: false
depends-on: []
blocks: [011]
sources: []
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-10T16:45:00Z
workflow: fast-track
bundle-budget: 50000
retry-budget: 2
---

# Task 006: Manifest parser and example compatibility

## Objective (rescoped 2026-05-10)
Audit `examples/` against the current `Manifest` dataclass; ensure every example manifest round-trips through `load_manifest()` cleanly with all current fields.

## User story
As a consumer repo maintainer, I want every example manifest in `examples/` to parse without warnings or silent field drops, so that I can copy one as a starting template and trust it will work.

## Rescope context

This task was originally written when the manifest parser didn't know about half the fields it eventually grew. A lot of the AC2 scope shipped during journeys 2 and 4:

- ✅ **`tasks-layout`** — added by task-004 (commit `ba890f4`). Parser handles `standard` and `legacy-four-folder`.
- ✅ **`registry-source`** — added by task-020 (commit `8a869c3`). Parser defaults to `"self"`.
- ✅ **`bundle-budget`** — present from earlier work; parser reads it.
- ❓ **Pinned roles in `examples/manifest-full.yaml`** — original AC1 said the parser stringifies these incorrectly. **Needs verification** that it still does after task-006 work, OR that the parser was fixed and we just need to update examples.
- ❓ **`src-roots`, workflow defaults, lockfile expectations** — may or may not be in the parser. Audit.

What remains is mechanical: **read every file in `examples/`, run `load_manifest()` on each, fix examples that fail, fix parser if a real example reveals a parser bug**.

## Acceptance criteria (revised)
- AC1: A new `tests/bin/test_examples.py` (or addition to `test_resolution.py`) loads every `*.yaml` in `examples/` via `load_manifest()` and asserts no exceptions, no field-drop warnings.
- AC2: Any example file that fails AC1 is fixed (or moved to `examples/broken/` with a README explaining what's broken and why it's kept).
- AC3: If a real example reveals a parser bug (e.g., the historical pinned-role-stringify issue), the parser is fixed in `bin/lib/manifest.py` and a test case is added.
- AC4: Invalid manifest items still produce clear validation errors — verified by 1-2 negative tests (e.g., missing required field, unknown `tasks-layout` value).

## Context
- Originally noted that `examples/manifest-full.yaml` uses pinned role mappings the parser stringified incorrectly. This may have been fixed during task-004's manifest work; verify before fixing again.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
