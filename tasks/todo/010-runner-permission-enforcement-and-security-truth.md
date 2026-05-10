---
id: 010
title: Runner permission enforcement and security truth
type: feature
scope: runner
priority: P2
status: open
fan-out: 1
needs-architect: true
plan-approved: false
result-approved: false
trivial: false
depends-on: [009]
blocks: []
sources: []
created: 2026-05-09T00:00:00Z
created-by: human
updated: 2026-05-10T16:45:00Z
deferred: true
deferred-reason: blocked-by-deferred-task-009
workflow: ship-feature
bundle-budget: 80000
retry-budget: 2
---

# Task 010: Runner permission enforcement and security truth

## Objective
Either implement documented runner permission enforcement or downgrade security claims to match reality.

## User story
As a security-conscious adopter, I want runner permissions and docs to agree, so that I can reason accurately about budai's security boundary.

## Acceptance criteria
- AC1: Runner resolves role permissions into actual allowed tool configuration where supported.
- AC2: Restricted Bash, CWD/path validation, and forbidden write protections are implemented or explicitly marked as future work.
- AC3: Security docs distinguish enforced guarantees from planned safeguards.
- AC4: Tests cover permission resolution and blocked/allowed command decisions.

## Context
- Repo analysis found security docs describe enforcement that the current runner does not implement.

## Deferral context (2026-05-10, after journey 4)

**Status: deferred. Defers alongside task-009.**

This task implements `--allowed-tools` enforcement and CWD/path validation in the budai runner. Today there is **no budai-owned runner subprocess to enforce against** — every role spawn goes through Claude Code's host `Agent` tool, and "permissions" are whatever the host's `settings.local.json` allows (see F026 for the granular allow-list pattern we landed on after journey 3).

This means the security guarantees that `docs/20-permissions-and-security.md` describes are aspirational, not enforced. AC3 calls out exactly that — "distinguish enforced guarantees from planned safeguards." A short-term partial ship of just AC3 (a docs-only honesty pass) is possible without task-009; the full enforcement story has to wait.

**Re-prioritize when:**
- task-009 ships (real subprocess to enforce against), OR
- a consumer repo asks for actual permission boundaries (e.g., a multi-tenant deployment), OR
- the docs-honesty AC3 work alone is needed (then re-scope to a docs-only fast-track task).

See task-009's deferral context for the broader analysis of why the host-Agent-tool pattern is sufficient for current journey-driven dogfood usage.

## Plan
<!-- Filled in by the Planner -->

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
