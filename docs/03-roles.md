# 03 — Roles

budai ships with five roles. They're chosen to be the smallest set that covers an end-to-end task without forcing one-size-fits-all. New roles can be added by writing markdown; the five below are the default that ships in `base/`.

## The five

| Role | Mission | Compute tier |
|---|---|---|
| **Planner** | Read task, design approach, decide decomposition, recommend fan-out | Opus |
| **Implementer** | Write code from a clean spec + bundle | Sonnet (default), Opus on retry |
| **Verifier** | Run tests, capture evidence, attest correctness | Sonnet |
| **Judge** | Peer-review attempts (anonymized), pick winner, integrate | Opus at review, Sonnet at integrate |
| **Librarian** | Maintain index/docs/memory/stats; build task bundles; flag drift | Sonnet |

The Librarian is on Sonnet rather than Haiku because the bundling skill needs to reason about file relevance, and the audit-docs skill needs to spot semantic mismatches between docs and code. Haiku is fine for purely mechanical sub-skills (index regeneration, header parsing) which can be invoked as separate sub-tasks at the cheaper tier.

## Mission-by-role

### Planner

**Input:** task definition + bundle.

**Output:** plan section appended to the task body, structured as:
- Approach (2-4 sentences)
- Decomposition (single task or list of sub-tasks to spawn)
- File-level changes (file-by-file: create / modify, with descriptions)
- Risks and escalations
- Acceptance criteria mapping (which AC is covered by which change)
- Recommended fan-out
- Confidence level

The Planner may write a new ADR to `memory/decisions/` if a meaningful architectural choice is being made. It may also call `task new` to spawn sub-tasks if it decomposes the work; in that case the parent task becomes a coordinator.

**Reads:** task, bundle, existing ADRs, conventions.

**Writes:** task body (plan section), `memory/decisions/`, sub-task files (when decomposing).

**Escalates to:** human (architecture gate).

### Implementer

**Input:** task + plan + bundle.

**Output:** a diff in its assigned worktree.

**Workflow:** runs preflight; reads bundle; applies plan; runs tests locally; writes a transcript to `runs/<run-id>/`; submits its attempt to `council/<task-id>/attempts/` tagged with its opaque ID.

**Reads:** task, plan, bundle, conventions, untouchables.

**Writes:** code in its worktree only. Cannot read other implementers' worktrees during fan-out.

**Escalates to:** Planner (if the spec is ambiguous).

### Verifier

**Input:** an attempt's diff + the task's acceptance criteria.

**Output:** a verifier report with pass/fail per AC, captured evidence appropriate to the change type.

**Evidence skills:**
- Pure logic: test runner output
- IPC changes: replayed IPC trace from a smoke test
- FE component: Playwright headed run, screenshots, DOM diff, console errors
- Visual: screenshot comparison
- Performance-sensitive: before/after timing measurements

**Reads:** attempt diff, task, acceptance criteria, src/ as needed.

**Writes:** `runs/<run-id>/evidence/`, verifier report appended to attempt.

**Escalates to:** Implementer (with failure.md), then Planner if Implementer can't recover within retry budget.

### Judge

**Input:** all attempts in `council/<task-id>/attempts/` (anonymized), reviewer reports if any.

**Output:** verdict.md + integrated diff applied to main.

**Workflow:**
1. Read attempts blind; rank them with rationale.
2. (Optional) read reviewer reports if multiple reviewers; synthesize.
3. Pick the winner; explain why; explain what others got wrong.
4. List outstanding concerns.
5. Auto-spawn follow-up tasks (test coverage, addressed concerns).
6. De-anonymize for the verdict file.
7. Apply the winning diff; commit.

**Reads:** attempts, reviews, mapping.json, verifier reports.

**Writes:** `council/<task-id>/verdict.md`, follow-up task files, the integrating commit.

**Escalates to:** human (final-result gate).

### Librarian

The longest-running and most-invoked role. Three modes:

**Per-task mode (Briefer):** invoked at task start. Runs `build-task-bundle` skill. Output: `tasks/open/<id>.bundle.md`.

**Per-task mode (Sweeper):** invoked at task end. Runs `audit-docs`, regenerates index, updates stats, posts daily delta to `messages/channels/ops.md`.

**Scheduled mode:** runs on commit hook or timer. Detects skill-quality drops, recurring lesson patterns, doc drift. Auto-opens improvement tasks when thresholds breach.

**Reads:** everything.

**Writes:** `index/`, `docs/`, `memory/lessons/`, `stats/`, `messages/channels/ops.md`, new task files.

**Escalates to:** none — Librarian's outputs are non-blocking; concerning findings open tasks for the regular workflow to address.

## Role file format

Every role file has frontmatter + body. Frontmatter declares technical configuration; body is the system prompt.

```markdown
---
role: implementer
description: Writes code from a clean spec
model-default: sonnet
model-escalation: opus       # used on retry after a failed attempt
permissions: [read, write, run-tests, run-preflight]
skills: [run-preflight, capture-evidence]
escalation:
  ambiguous-spec: planner
  failed-retries-exceeded: planner
---

# Implementer

You receive a task, a plan, and a bundle. You produce a diff that meets the
acceptance criteria.

## Principles
- Apply the plan as specified. Do not add scope.
- Read the bundle first; only Read additional files if the bundle indicates them.
- Run preflight before starting.
- ...

## Workflow
1. ...
```

The frontmatter is parsed by the runner. The body is injected as the system prompt.

## Why five roles, not nine

Earlier drafts proposed nine: architect, router, implementer, reviewer, chairman, tester, debugger, librarian, auditor. Collapses made:

- Architect + Router → **Planner.** Both interpret tasks and decide approach. Splitting was bureaucratic.
- Reviewer + Chairman → **Judge.** Single-instance peer review + integration. Multi-reviewer cases are workflow choices, not role splits.
- Tester + Debugger → **Verifier.** Same competency in two phases (verify pass; investigate fail).
- Auditor → folded into **Librarian.** Audit is a Librarian skill (`audit-docs`, future `audit-tasks`).

Five roles, two human gates. Easy to subdivide later if a specific repo or workflow needs it. Easy to add new roles for non-code work (marketing-writer, sales-responder) when the time comes — the platform doesn't constrain to five.

## Why the Librarian is Sonnet, not Haiku

The bundling skill scores file relevance by reading headers and reasoning about which subsystem the task touches. Pure pattern matching at Haiku misses cross-cutting tasks. The audit-docs skill compares prose against code and flags semantic drift; Haiku flags too many false positives. Sonnet handles both well at acceptable cost.

Mechanical sub-skills (header parsing, index regeneration, stat aggregation) can be invoked as separate sub-tasks at Haiku. The role default is Sonnet; specific skill invocations override.

## Compute tier override

Skills can override the role's default tier in their frontmatter:

```markdown
---
skill: regenerate-index
tier-override: haiku
---
```

When the Librarian invokes `regenerate-index`, the runner spawns a Haiku call for that step regardless of the Librarian's default. This is how cost stays low without sacrificing reasoning where it counts.
