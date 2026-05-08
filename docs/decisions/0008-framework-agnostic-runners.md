---
adr: 0008
title: Framework-agnostic runner abstraction from day one
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0008 — Framework-agnostic runner abstraction from day one

## Context

budai is starting on Claude Code (Phase 0). It would be tempting to write the initial scripts and skills with Claude Code as a hard dependency, defer multi-platform support, and refactor later when needed.

Two arguments against that:

- **Refactoring framework-coupled code is expensive.** The shape of code that assumes one platform is meaningfully different from the shape of code that abstracts the platform away. Refactoring after the fact is a lot of churn.
- **Hybrid workflows are a feature, not a future.** Multi-platform fan-outs (one attempt on Claude, one on Codex) are genuinely interesting from day one — they give the Judge truly different perspectives. Postponing this defers a real capability.

A separate concern: the user's project context. They're building this to support multiple clients with different platform constraints. A SaaS-restricted client may need self-hosted runners; a client comfortable with Claude Code is fine on Anthropic. Same OS, different runners — only possible if the runner abstraction exists from the start.

## Decision

Build the runner abstraction from day one (Phase 0). Even with only one runner shipped initially (`claude-code.md`), all platform-specific concerns route through it.

What this means concretely:

- Role files, skill files, workflow files contain no Claude Code references.
- `bin/agent run` takes a `--runner` flag; the default is `claude-code` but the parameter is always there.
- The runner shim is the only place that knows about Claude Code's CLI specifics (system prompt injection, tool catalog, transcript format).
- Future runners (`codex.md`, `direct-anthropic.md`, etc.) drop in without changing anything else.

## Consequences

**Positive:**

- Multi-runner fan-outs (Phase 8) require new runner files but no changes to existing roles, skills, or workflows.
- Clients with platform constraints can be onboarded by writing one runner file, not by forking budai.
- The discipline of "no Claude Code in role files" forces clean separation from day one. Later refactoring is unnecessary.
- Stats can already be discriminated by runner (per `15-framework-agnostic.md`), so when a second runner ships, A/B comparison is immediate.

**Negative:**

- Slightly more upfront investment in the runner shim than a Claude-Code-only design would need.
- The discipline cost: catching Claude Code references in role/skill bodies during code review, building the validation that rejects them.

**Neutral:**

- The runner file format may evolve as we add platforms. v2 of the runner format would require existing runner files to be updated; the abstraction itself is stable.
- Shipping with only one runner is fine. The abstraction is real even when there's only one implementation; refactoring isn't needed when the second arrives.
