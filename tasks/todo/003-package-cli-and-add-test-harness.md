---
id: 003
title: Package CLI and add test harness
type: feature
scope: bin
priority: P2
status: open
fan-out: 1
needs-architect: false
plan-approved: false
result-approved: false
trivial: false
depends-on: []
blocks: []
sources: []
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-10T16:45:00Z
workflow: fast-track
bundle-budget: 60000
retry-budget: 2
---

# Task 003: Package CLI and add test harness

## Objective (rescoped 2026-05-10)
Document the canonical install + test invocation in README, and audit `pyproject.toml` (or equivalent) for unused / undeclared dependencies.

## User story
As a contributor, I want a documented install path and a single command to run all tests, so that I can verify a fresh checkout is healthy without reverse-engineering the test layout.

## Rescope context

This task was originally P0 because journey 1 found `bin/preflight --json` failing in a fresh env (missing `PyYAML`). A lot of its scope has since shipped under other tasks:

- ✅ **Pytest harness exists** — `tests/bin/test_resolution.py`, `tests/bin/test_task_cli.py`, `tests/bin/test_journey_state.py`, `tests/bin/test_runner.py`. 36 tests across 4 files at journey-4 close.
- ✅ **Unit tests cover shared helpers** — manifest, resolution, task_schema, journey_state all tested.
- ✅ **CLI smoke tests exist** — `test_task_cli.py` covers `bin/task` round-trips.
- ❓ **Install path documentation** — needs verification. README may still not say what to install / how.
- ❓ **`pyproject.toml` / requirements honesty** — needs an audit pass.

What remains is mostly **documentation hygiene**: the README needs a "How to develop" section (install command, test command, what `bin/agent run` actually does today vs. eventually). Plus a quick audit of declared deps vs. actually-used.

## Acceptance criteria (revised)
- AC1: README has a "Development setup" section listing the exact install command (e.g., `pip install -r requirements.txt` or `pip install -e .`) and the exact test command (`python3 -m pytest tests/bin/ -v`).
- AC2: `pyproject.toml` and/or `requirements.txt` are audited: any declared dep not imported anywhere is removed or justified in a comment; any imported package not declared is added.
- AC3: README explicitly notes that `bin/agent run` currently uses a placeholder dispatcher (Phase 0; see task-009 deferral context) so contributors don't expect unattended runs.
- AC4: A new `make test` or equivalent shorthand is documented (or the raw `python3 -m pytest` command is the canonical one — pick one and document it).

## Context
- `./bin/preflight --json` failed historically when PyYAML wasn't installed. Need to verify whether this is still true post-journey-4 and add it to AC2's audit.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
