# 00 — Overview

## The problem

AI coding tools today were built for **one agent inside one human's workflow**. The infrastructure underneath them — Git, GitHub, PRs, code review, merges — was built for **a small number of humans contributing slowly to a single line of history**.

When you scale to **many agents working in parallel**, both assumptions break:

- A single agent can iterate every minute. Ten can iterate every six seconds. PR-flow throughput collapses.
- Multiple agents attempting the same task should be able to *diverge* — try different approaches — without conflicting on a shared branch.
- Code review by humans doesn't scale to one-review-per-attempt-per-agent.
- Without coordination, agents redo each other's work, undo each other's decisions, and accumulate inconsistencies that humans then untangle.
- Skills, conventions, and lessons learned in one repo don't propagate to others — every project re-discovers the same gotchas.

budai is the operating system that addresses these gaps. It does not replace your AI coding tool; it organizes the way many of them collaborate.

## The shape of the solution

budai imposes a small number of structures and a small number of conventions, then lets agents do their work inside those structures.

**Five roles**, each defined as a markdown file:

- **Planner** — turns a task into an executable spec
- **Implementer** — writes the code from the spec
- **Verifier** — runs tests, captures evidence, attests correctness
- **Judge** — peer-reviews implementations (anonymized), picks winners, integrates
- **Librarian** — keeps the index, docs, memory, and stats fresh; builds context bundles for tasks

**One workflow** ties roles together: task in → bundle built → plan written → human gate → fan-out implementation → peer review → verdict → human gate → sweep → archive. Variations exist for bugs, refactors, and audits.

**Two human gates** at architecture and final-result. Everything between is autonomous.

**Strict separation between mechanism and culture.** The structure (folders, file formats, role definitions) is the mechanism. What agents actually do (which conventions, which skills, which thresholds) is the culture, configured via markdown. Same structure, different culture, different result.

**Framework-agnostic from day one.** Roles, skills, and workflows are pure markdown; runners are thin shims. Today: Claude Code. Tomorrow: Codex, Anthropic SDK, OpenAI SDK, anything that can read a system prompt.

**Cross-repo by default.** A central registry (`dopomogai/budai`) holds canonical skills, roles, and workflows. Each project repo declares which versions it pulls. Improvements propagate. Project-specific extensions live locally.

## Key concepts

- **Bundle** — single self-contained markdown file the Implementer reads to know 95% of what's needed. YAML manifest on top, content below. Token-budgeted; overflow turns into "reference if needed" hints.
- **Council** — per-task folder with attempts, reviews, and verdict. The audit trail. Survives the task.
- **Fan-out** — when more than one Implementer attempts the same task in parallel. Each in an isolated worktree. The Judge picks the winner.
- **Lesson** — a durable observation extracted from runs that should change future behavior. Promoted from per-run to per-role to repo-wide as it recurs.
- **Manifest** — per-repo declaration of which budai version + which skills/roles/workflows are active.
- **Runner** — the shim between budai's role definitions and a specific agent platform (Claude Code, Codex, etc.).

## Who this is for

The primary user is a team running multiple AI agents on a codebase, where:

- The team has at least one human reviewing architecture and final results.
- The codebase is large enough that consistent conventions matter.
- The team works across multiple projects and would benefit from shared agent capabilities.
- The work is high-stakes enough to warrant peer review and a durable audit trail.

The first concrete consumer is CanvasOS (a multi-widget canvas app being built by Dopomogai). The second is a real-client codebase. From there, the registry pattern kicks in.

## Status

Design-stage. The base content, scripts, and runners are not yet written. This repository currently holds the design docs. See [`18-implementation-phases.md`](18-implementation-phases.md) for the build sequence.
