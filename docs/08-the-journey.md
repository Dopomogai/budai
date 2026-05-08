# 08 — The journey

The end-to-end lifecycle of a task in budai, from creation to archive. This is the workhorse document — the contract that the five roles, all the file formats, and all the scripts implement.

The default workflow described here is `ship-feature`. Variants (`fix-bug`, `refactor`, `audit-repo`, `research`) differ at specific steps; those differences are noted at the relevant step.

## Step 0 — Task entry

A task enters the system in one of three ways:

1. **Human writes it.** Runs `bin/task new <type>` — interactive script that prompts for title, type, scope, user story, acceptance criteria, fan-out, needs-architect, depends-on. Generates `tasks/open/<NNN>-<slug>.md` with frontmatter and body sections.
2. **Planner decomposes a parent task.** During Step 2, a Planner that decides the work is too large for one execution calls `task new` programmatically for each sub-task. Sub-tasks reference the parent's id in `depends-on`.
3. **Librarian opens an improvement task.** During its scheduled sweep, the Librarian detects a skill-quality drop or recurring failure pattern and creates a task with type `refactor` or `improve-skill`.

All three paths use the same script, produce the same task file shape. The system has one entry point.

## Step 1 — Task moves into planning

Trigger: a task file lands in `tasks/open/` with `status: open` and `plan-approved: false`.

The Router (a Planner sub-skill, not a separate role) flips status to `planning`, posts an assignment to `messages/channels/tasks.md`, and invokes the Librarian to build the bundle.

For variants:
- `fix-bug`: Router skips Planner if `trivial: true` AND `fan-out: 1`. Goes straight to Implementer with the bug description as plan.
- `audit-repo`: Router invokes Librarian + Auditor only; no Implementer.

## Step 2 — Librarian bundles context [Sonnet]

The Librarian runs the `build-task-bundle` skill. Inputs: task, `index/detailed.md`, file headers, ADRs, conventions, glossary.

**Procedure:**
1. Parse task: objective, scope, files-to-touch (if specified), keywords.
2. Score every file in the index for relevance: filename match, header keyword match, dependency proximity to declared files-to-touch.
3. Pull files in priority order until token budget is reached:
   - Files-to-touch (explicit)
   - Direct imports of files-to-touch
   - ADRs in scope
   - Directory READMEs touching the changed area
   - Conventions sections relevant to the task
   - Glossary terms appearing in the task body
   - Related closed tasks (same scope, recent)
   - Speculative additions (similar-pattern files for precedent)
4. Stop adding when budget is reached. Move remaining candidates to `referenced-but-not-included` with one-line `hint:` for each.
5. Write the bundle.

**Output:** `tasks/open/<id>.bundle.md` with YAML frontmatter declaring everything included, what was excluded and why, and the actual token count. Goal: 95% context coverage in one read by the Implementer.

The bundle frontmatter is the contract; the Implementer can rely on the YAML being machine-parseable. See [`09-bundle-format.md`](09-bundle-format.md) for the schema.

## Step 3 — Planner produces an elaborate plan [Opus]

Skipped if `needs-architect: false`.

The Planner reads task + bundle and produces a plan section appended to the task body. Required structure:

- **Approach** (2-4 sentences)
- **Decomposition** (single task or list of sub-tasks to spawn)
- **File-level changes** (file-by-file: which files to create, which to modify, what each change is for)
- **Risks and escalations**
- **Acceptance criteria mapping** (each AC traced to a specific change)
- **Recommended fan-out**
- **Confidence level**

If the Planner decides the task should be decomposed, it does NOT spawn implementers. It writes the plan as a coordinator with sub-task IDs, calls `task new` for each sub-task, and the parent task's status becomes `coordinator`. Each sub-task then enters the workflow at Step 1 in its own right.

The Planner may write a new ADR to `memory/decisions/` if a meaningful architectural choice is being made.

See [`10-plan-format.md`](10-plan-format.md) for the full schema.

## Step 4 — Human gate: architecture review [HUMAN]

The human reviews the plan. Three outcomes:

- **Approve:** flips `plan-approved: true` in frontmatter. Workflow continues.
- **Revise:** writes notes; status returns to `planning`; Planner re-runs with notes appended.
- **Reject:** writes notes; status flips to `abandoned`; task moves to `tasks/archive/`.

**Auto-approve rule:** if the task is tagged `trivial: true` AND `fan-out: 1` AND no new ADR proposed, the plan auto-approves without human review. The human still sees it in the daily delta, can intervene retroactively.

## Step 5 — Router fans out implementers [Sonnet for routing decision]

Trigger: `plan-approved: true`.

The Router reads `fan-out: N` and:
1. Creates `council/<task-id>/` if not exists.
2. For each of N instances, creates a worktree at `runs/<run-id>/worktree/` from main.
3. Writes `council/<task-id>/dispatch.json` with opaque IDs (`attempt-A`, `attempt-B`, ...) mapped to instance metadata (model, runner, run-id, started timestamp).
4. Posts assignments to `messages/channels/tasks.md`.
5. Spawns Implementer instances.

Each Implementer's worktree is its sandbox. It cannot read other implementers' worktrees. This isolation is the strict-anonymization premise — there's nothing to leak because there's nothing to see.

## Step 6 — Implementers code in parallel [Sonnet, Opus on retry]

Each Implementer:
1. Runs `preflight.sh` in its worktree.
2. Reads task + plan + bundle.
3. Applies the plan: creates and modifies files as specified.
4. Runs unit tests locally.
5. Writes transcript to `runs/<run-id>/transcript.md`.
6. Computes diff via `git diff` from worktree state.
7. Submits attempt to `council/<task-id>/attempts/attempt-<X>.md` (writeup) + `attempts/attempt-<X>.patch` (diff).
8. Posts to `messages/channels/review.md`: "attempt-X submitted."

Implementers don't see each other's work. They submit independently. The first to finish doesn't influence the others.

## Step 7 — Verifier verifies each attempt [Sonnet]

For each submitted attempt, a Verifier instance runs:
1. Apply the attempt's patch to a fresh worktree.
2. Run preflight + acceptance criteria tests.
3. Capture evidence appropriate to the change type (see [`13-evidence-capture.md`](13-evidence-capture.md)).
4. Write `runs/<run-id>/evidence/` and a verifier report appended to the attempt's writeup.
5. Mark attempt as passed / failed in `council/<task-id>/`.

**Failure loop:**
- If all of an Implementer's attempts fail acceptance criteria, the Implementer is re-spawned with the original bundle plus its previous diff plus the failure report. Compute tier escalates: Sonnet → Opus.
- Retry budget is configurable; default `max-retries: 2`.
- After budget exhausted, the attempt is marked `status: failed` in council. Stays as record. Lessons are extracted by the Librarian sweep.

## Step 8 — Judge synthesizes [Opus for review, Sonnet for integration]

Trigger: all attempts marked passed or failed.

The Judge:
1. Reads `attempts/` blind. The opaque IDs in filenames don't reveal model or instance metadata. The runner enforces this by not injecting metadata into the Judge's context.
2. (If `peer-reviewers: N > 0`) reads existing reviewer reports from `reviews/`.
3. Ranks attempts. For each: what worked, what didn't.
4. Picks the winner. Writes verdict.
5. Lists outstanding concerns.
6. Auto-spawns follow-up tasks per the workflow's rules:
   - `ship-feature` rule: every shipped feature gets a `test-coverage-<id>` follow-up.
   - Outstanding concerns above a configurable severity threshold become tasks.
7. De-anonymizes by reading `mapping.json`. Attribution goes into `verdict.md`.
8. Applies the winning patch to main; commits.

Verdict format: see [`12-isolation-and-fanout.md`](12-isolation-and-fanout.md).

## Step 9 — Human gate: final result review [HUMAN]

The human reviews the verdict + the integrated commit. Same three outcomes as Step 4 (approve / revise / reject), with the same auto-approve rule for trivial tasks.

On rejection: the integrating commit is reverted; task status returns to `reviewing` with notes; the Judge re-runs.

## Step 10 — Librarian sweeps [Sonnet]

Trigger: `result-approved: true`.

The Librarian runs:
1. **Audit docs.** Diff: which files changed? For each: is the file header still accurate? Is the directory README still accurate? Are there top-level docs (`architecture.md`) referencing now-deleted symbols?
2. **Auto-update high-confidence drift.** Renamed exports, removed files, added IPC channels — these are unambiguously update-able.
3. **Open tasks for low-confidence drift.** Architectural rephrasing, prose rewrites — these become tasks for the regular workflow to address.
4. **Regenerate index.** Walk source tree; rebuild `index/tree.md` and `index/detailed.md`.
5. **Bundle READMEs.** Concatenate all READMEs into `docs/READMEs.md`.
6. **Promote lessons.** Look for recurring patterns in `runs/`; promote to `memory/lessons/` if 3+ recurrences.
7. **Update stats.** Re-aggregate `stats/roles.json`, `stats/skills.json`, `stats/tasks.json`, `stats/repo.json`.
8. **Post daily delta** to `messages/channels/ops.md`.

The sweep produces a single commit. Its message format: `librarian: sweep for task <id>`.

## Step 11 — Backend stream [continuous]

Throughout Steps 1-10, deltas to `runs/`, `council/`, `messages/`, `stats/` are streamed to the ultimate-widget backend. Normalized into:
- `runtime_sessions` — one row per agent run
- `runtime_run_events` — events: `attempt.submitted`, `review.posted`, `verdict.rendered`, etc.
- `runtime_councils` — joins multiple runs under one task
- `runtime_skill_invocations` — per-skill stats roll up here

The backend is the source of truth for cross-repo aggregates. Per-repo `stats/` files are local mirrors regenerated on each sweep.

## Step 12 — Archive

Trigger: end of Step 10.

The task file flips `status: done`, moves from `tasks/open/` to `tasks/archive/`. The bundle file moves with it. Auto-spawned follow-up tasks (test-coverage, addressed concerns) appear in `tasks/open/` and enter the workflow at Step 0.

## Visualization on the canvas

A budai-aware canvas widget reads:
- `stats/roles.json` for active-instance counts and success rates.
- `tasks/open/*.md` for kanban view (status from frontmatter).
- `council/<task-id>/dispatch.json` + `verdict.md` to render the per-task DAG of attempts.
- `messages/channels/` for the live coordination feed.
- `index/detailed.md` for repo-map view with role-ownership coloring.

The widget keeps no state of its own. Every refresh re-reads the markdown.

## What this journey does NOT include

- **Continuous integration / CI.** Not budai's job. The Verifier captures evidence; CI runs separately on the integrating commit.
- **Code search and refactoring.** Tools like ast-grep or jscodeshift are agent skills; budai doesn't ship them.
- **Deployment.** Not budai's scope.
- **Customer-facing changelogs.** Auto-generated from `tasks/archive/` is possible but is a future workflow, not part of the default.
