---
id: 016
title: CLI integration tests for bin/task via subprocess
type: feature
scope: tests
priority: P2
status: open
fan-out: 1
needs-architect: false
plan-approved: false
result-approved: false
trivial: false
depends-on: [003, 004]
blocks: []
sources: [T004-judge-followup]
created: 2026-05-09T16:00:00Z
created-by: judge
updated: 2026-05-09T16:00:00Z
workflow: ship-feature
bundle-budget: 24000
retry-budget: 2
---

# Task 016: CLI integration tests for bin/task via subprocess

## Objective
Extend `tests/bin/test_task_cli.py` (added in task-004) with end-to-end integration tests that invoke `bin/task` as a subprocess and assert on stdout, stderr, exit code, and resulting filesystem state. Existing tests cover helper functions in isolation; the CLI wrapper itself (`cmd_new`/`cmd_move`/`cmd_list` argparse plumbing, exit-code mapping, output formatting) is currently uncovered.

## User story
As a contributor changing `bin/task`, I want a regression suite that catches breakage in the actual CLI shape (argparse, exit codes, stdout/stderr) without requiring manual smoke runs.

## Acceptance criteria
- AC1: At least one subprocess test per subcommand (`new`, `list`, `move`) that runs `python3 bin/task <args>` in a tempdir-backed mock repo and asserts on `returncode`, `stdout`, `stderr`, and post-state on disk.
- AC2: At least one negative-path test per validation surface — invalid status, illegal transition, missing dependency, dependency cycle — asserts non-zero exit code and an error message on stderr.
- AC3: Tests run under both `tasks-layout: standard` and `tasks-layout: legacy-four-folder` for `cmd_new` and `cmd_move`.
- AC4: Test harness conventions established by task-003 are followed (fixtures, naming, file layout).

## Context
- Source: T004-judge-followup. Flagged in `.agents/council/004/verdict.md` as INFO-severity outstanding concern. Verifier also flagged this as a WARNING in non-AC findings.
- Related code: `bin/task` (CLI entrypoint), `tests/bin/test_task_cli.py` (current unit tests).
- Depends on: task-003 (test harness conventions), task-004 (the CLI surface being tested).
