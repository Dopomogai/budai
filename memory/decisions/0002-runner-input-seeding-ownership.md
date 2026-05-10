# ADR 0002 — Runner input seeding: module boundary and copy semantics

- Status: accepted
- Date: 2026-05-10
- Source: task-021

## Context

Journey 2 (task-004) surfaced F021: when the runner creates an
Implementer/Verifier worktree branched from `main`, the task move + appended
`## Plan` section + new ADR + bundle file are all uncommitted in the main
worktree, so the worktree branched from `main` can't see them. Three sites of
"absolute-path injection" appeared in agent prompts during journey 2 — every
downstream agent had to be hand-told to read these via absolute paths back to
the main worktree. Without that injection, agents would silently work off
stale inputs.

Task-021 moves that responsibility into the runner: before
`dispatch_claude_code`, copy the task body, bundle, ADRs, and any prior
verifier failure note into the worktree at `.agents/runs/<run-id>/inputs/`,
then point the agent's prompt at those relative paths.

Three coupled questions had to be answered together:

1. **Module boundary.** Does the seed/teardown logic live as new functions in
   `bin/lib/runner.py`, or in a brand-new `bin/lib/journey_state.py`?
2. **Copy vs symlink.** Should the seeded files be hard copies (frozen at
   dispatch time) or symlinks (live view of main-worktree state)?
3. **Cleanup semantics.** When does `inputs/` get removed, and when does the
   worktree itself get removed? Are they the same lifecycle event?

Tasks 019 (workflows) and 022 (per-workflow input bundles) both depend on
this seeding behaviour, so the module shape we pick here is load-bearing
beyond task-021 alone.

## Decision

**1. New module `bin/lib/journey_state.py`, runner orchestrates.** Pure
functions that select, copy, and clean inputs live in `journey_state.py`.
`runner.py` calls them at two points — just before `dispatch_claude_code`
and during journey close. Rationale:

- Mirrors the precedent set by `task_schema.py` (ADR 0001): correctness rules
  in their own module, the CLI/orchestrator is a thin caller.
- Makes the seeding logic unit-testable without spinning up subprocesses or
  fake `claude` binaries; tests touch only the pure-function surface.
- Gives task-019 (workflows) and task-022 (per-workflow input bundles) a
  named import target. Adding more input categories (e.g.
  `workflow.bundle.md`) becomes "extend the picker," not "weave another
  branch through `runner.py`."
- `runner.py` already exceeds the "thin orchestrator" line for its size; we
  decline to make that worse.

**2. Copy, never symlink.** Inputs are read once at dispatch time and copied
into the worktree as ordinary files. Symlinks are rejected for two reasons:

- Frozen-at-dispatch semantics. The agent's view of inputs must not change
  mid-run if the human edits the task body in the main worktree (which they
  routinely do — appending the Verdict section while the next role is still
  in flight is a normal pattern). Symlinks would leak that churn into the
  agent's transcript.
- Cross-worktree symlinks are fragile. `git worktree remove` and
  `git worktree prune` interact poorly with symlinks pointing at the primary
  worktree's tree, and on Windows they require elevated privileges.

The cost of copy semantics is duplication in `.agents/runs/<run-id>/inputs/`,
which is gitignored and bounded by bundle size (≤84k) plus a small task body
and one or two ADRs. Acceptable.

**3. Cleanup semantics: keep `inputs/`, remove worktrees.** The Judge step
(journey close) removes the per-attempt worktrees via `git worktree remove`
but leaves `.agents/runs/<run-id>/inputs/` in place. `runs/` is gitignored
and is the audit trail; preserving inputs there means a future investigator
can reconstruct exactly what the agent was told to read. This matches the
existing handling of `runs/<run-id>/transcript.jsonl` — runs are immutable
post-close, not auto-purged.

## Consequences

- New file `bin/lib/journey_state.py` with no inbound coupling beyond
  `runner.py` and tests. Adding it does not require headers anywhere else
  per local conventions (header maintenance is task-014's scope).
- The composed system prompt grows a `## Journey inputs` block. This is a
  small, structured insertion at the top of the prompt — it does not change
  any existing role definitions.
- ADR detection is *content-based*: `journey_state` parses the task body's
  `## ADR` section to find ADR file references, rather than requiring the
  task frontmatter to enumerate them. This preserves the role contract
  (Planner writes ADRs to `memory/decisions/<NNNN>-<slug>.md` and references
  them in plan text) without adding new frontmatter fields. Path resolution
  is permissive: any line under `## ADR` matching `memory/decisions/[\w-]+\.md`
  is picked up.
- Bundle filenames are globbed (`<task-id>-*.bundle.*.md`) to accommodate the
  F002 "encoded token count" filename convention (`*.bundle.15k.md` etc.).
  If multiple bundles match, all are seeded — the agent reads whichever it
  needs.
- Future `dispatch_claude_code` (task-009 — currently a placeholder) will
  receive a fully seeded worktree, so the real `claude` invocation does not
  need to be reworked when seeding lands.
- Retries are first-class. When a Verifier rejects an attempt, the next
  Implementer dispatch seeds the prior verifier's `failure.md` so the new
  attempt can read what the previous one got wrong, again as a relative path.

## Alternatives considered

- **Per-task coordination branch.** Commit the task move + plan + ADR + bundle
  to a `task-<id>-coordination` branch and create worktrees off that branch.
  Rejected for v1 (per the task body): per-task branches multiply git noise,
  don't generalize well to retries (which need a fresh `main`-based worktree,
  not a stale coordination branch), and require resolving "how does the
  branch get back to `main` at close" which adds journey-mechanics surface
  area. Copy-into-`runs/` keeps git history clean.
- **Symlink the inputs.** Rejected — see Decision §2. Frozen semantics +
  cross-platform fragility outweigh the disk-space savings.
- **Inline the logic in `runner.py`.** Rejected — see Decision §1. Module
  size, testability, and the impending tasks 019/022 all argue for a sibling
  module.
- **`needs-architect: true` + escalate.** The task frontmatter has
  `needs-architect: true`; we considered escalating. Resolved internally
  because the architectural choice is local (one module's worth of surface
  area) and no convention or untouchable conflicts. The ADR is the artifact
  the `needs-architect` flag was asking for.
