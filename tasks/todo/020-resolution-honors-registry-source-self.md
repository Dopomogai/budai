---
id: 020
title: resolution.py honors registry-source self (resolves base/ at repo root)
type: bug
scope: bin
priority: P0
status: open
fan-out: 1
needs-architect: false
plan-approved: false
result-approved: false
trivial: false
depends-on: []
blocks: [019]
sources: [F020]
created: 2026-05-09T18:00:00Z
created-by: human
updated: 2026-05-09T18:00:00Z
workflow: fix-bug
bundle-budget: 50000
retry-budget: 2
---

# Task 020: resolution.py honors registry-source self (resolves base/ at repo root)

## Objective
When a manifest declares `registry-source: self`, `bin/lib/resolution.py` must look up base files at `<repo_root>/base/<category>/<name>.md` instead of `<repo_root>/.agents/base/<category>/<name>.md`. Today the runner can never find any roles/skills/runners/workflows when budai dogfoods itself, because budai's authoritative registry tree lives at `base/` at the repo root, not under `.agents/base/`. This forced a manual `.agents/base -> ../base` symlink in journey 2 (gitignored as F020 workaround).

## User story
As a budai maintainer dogfooding the system on itself, I want `python3 bin/agent run --role librarian --task <id>` to resolve the librarian role on a fresh clone with no manual setup, so onboarding budai-on-budai (or any future self-hosted consumer) is one `bin/budai init` command away from running.

## Acceptance criteria
- AC1: `bin/lib/resolution.py:resolve()` reads the manifest's `registry-source` field. When `self`, base lookups go to `<repo_root>/base/<category>/<name>.md`. When `<other>` (a registry URL or local path), base lookups go to `<repo_root>/.agents/base/<category>/<name>.md` (existing behavior preserved for consumer repos).
- AC2: `list_available()` walks the correct base path per `registry-source`.
- AC3: `is_local()` and `is_base_only()` continue to work; their semantics depend on `local/` (unchanged).
- AC4: A new helper `_base_dir(repo_root: Path, manifest: Manifest) -> Path` encapsulates the branch logic so all four functions use a single source of truth. No string-keyed branching repeated in each function.
- AC5: The `.agents/base -> ../base` symlink workaround is removed; `.gitignore` line for it is removed; F020 entry in `findings.md` is moved to Promoted with `→ task-020`.
- AC6: Tests in `tests/bin/test_resolution.py` cover: (a) self with valid base/ at repo root resolves correctly, (b) self with missing base/ category returns None, (c) non-self path uses `.agents/base/` (existing behavior), (d) local/ overlay still wins over base/ regardless of registry-source.
- AC7: `python3 bin/agent run --role librarian --task <any-existing-task>` succeeds on budai's main without the symlink in place.

## Context
- Source finding: F020 in `findings.md`.
- Journey 2 retrospective documents the discovery and workaround at `tasks/done/004-retrospective.md`.
- This blocks task-019 (workflow taxonomy) — `base/workflows/<name>.md` resolution depends on this fix; without it, the dispatch-by-workflow logic can't find workflow files via the canonical resolver.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
