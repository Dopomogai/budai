# 18 — Implementation phases

Eight phases, ordered by dependency. Each phase has explicit deliverables and validation gates. No phase moves on until validation passes. **No time estimates** — agents do the work; sequence and validation matter, hours don't.

## Phase 0 — Scaffold

Build the static structure with no agent runs yet. Pure files and scripts.

**Deliverables:**
- `.agents/` directory tree (skeleton)
- 5 role files in `base/roles/` with placeholder bodies: planner, implementer, verifier, judge, librarian
- Initial skill set in `base/skills/`: `build-task-bundle`, `peer-review`, `audit-docs`, `run-preflight`, `capture-evidence`, `discover-standards`
- 4 workflow files in `base/workflows/`: `ship-feature`, `fix-bug`, `refactor`, `audit-repo`
- `base/conventions.md`, `base/permissions.md` (templates)
- `local/conventions.md`, `local/untouchables.md`, `local/glossary.md` (with TODO markers)
- Scripts in `bin/`:
  - `bin/task new`, `bin/task move`, `bin/task list`
  - `bin/preflight`, `bin/postflight`
  - `bin/librarian index` (regenerates `tree.md` / `detailed.md`)
  - `bin/librarian bundle` (runs the bundling skill with token budgeting)
  - `bin/agent run --role X --task Y --runner claude-code`
- `runners/claude-code.md` (only runner at this phase)
- AGENTS.md and CLAUDE.md at the root of the consumer repo
- File header convention applied to all existing source files (one-time pass)

**Validation:**
- `bin/preflight` passes on a clean repo
- `bin/librarian index` produces a valid index from current files
- `bin/task new feature` creates a well-formed task file
- `bin/agent run --role librarian --task <id>` launches a Claude Code session that reads the role file and produces a bundle (manual eyeball check on bundle quality)

**No agents are coordinating yet.** Each invocation is a single-role test run.

## Phase 1 — Per-role manual validation

For each of the 5 roles, validate in isolation before any orchestration.

**Validation pattern (same per role):**
1. Pick or fabricate a small synthetic task.
2. Manually prepare the role's expected inputs (skip auto-generation).
3. Launch the role: `bin/agent run --role <name> --task <id> --runner claude-code`.
4. Inspect outputs against the role's spec.
5. Refine the role file until 5 consecutive runs produce correct outputs across 5 different inputs.

**Order of validation:**
1. Librarian (build-task-bundle skill) — easiest to eyeball.
2. Planner — feed bundle, verify plan structure matches spec.
3. Implementer — feed plan + bundle, verify diff implements plan.
4. Verifier — feed diff + AC, verify it tests + captures evidence properly.
5. Judge — feed two manually-anonymized attempts, verify it picks correctly + writes verdict in spec.

**Exit gate:** all five role files are stable (no edits required for 5 consecutive runs each), and downstream roles can consume upstream outputs without translation.

## Phase 2 — Manual multi-role chain

End-to-end on one real CanvasOS task, fan-out 1, but you trigger each role manually.

**Deliverables:**
- One end-to-end run with hand-holding at every transition
- Validates: bundle → plan → human gate (you) → implementation → verification → judge → human gate (you) → sweep
- All artifacts written to spec'd locations
- Postflight passes
- The shipped change works in the running app

**Exit gate:** the chain works end to end with manual triggering, no script orchestration yet.

## Phase 3 — Scripted single-task orchestration

The workflow runs itself end to end on one task, fan-out 1.

**Deliverables:**
- `bin/workflow run <workflow-name> <task-id>` drives the chain
- Pause points at human gates (script halts, prompts, resumes)
- Real-time updates to `messages/channels/`
- All intermediate artifacts written

**Exit gate:**
- 5 different tasks complete end to end without manual intervention except at human gates
- Stats files populate correctly
- Council folder is clean and reviewable

## Phase 4 — Fan-out and parallel

Same workflow, but `fan-out: 3` is functional.

**Deliverables:**
- Worktree-per-implementer isolation working
- Anonymization at council-attempts step working
- Judge reading anonymized + de-anonymizing correctly via `mapping.json`
- Failure loop with retry budget functional
- Auto-spawned test follow-ups working

**Exit gate:**
- 3 tasks ship with fan-out 3 successfully
- Council audit trail is complete and reconstructible from artifacts alone
- Judge-picked winners correlate with verifier passes (sanity check)

## Phase 5 — Backend integration

Stream runtime data into the ultimate-widget backend.

**Deliverables:**
- Extend the existing runtime sync engine: new tables `runtime_councils`, `runtime_skill_invocations`, `runtime_workflow_runs`
- Extend event taxonomy: `attempt.submitted`, `review.posted`, `verdict.rendered`, `lesson.promoted`, `skill.invoked`
- `bin/librarian sync-out` pushes deltas to backend
- Backend dashboard view: live agent stats, recent runs, skill quality scores
- Cross-repo aggregation working

**Exit gate:**
- Stats reconstructed from backend match stats from local files
- Dashboard reflects state within 60 seconds of changes
- Skill quality scores actionable (you can see which skills are failing)

## Phase 6 — Registry and cross-repo

Promote `base/` content to its own versioned registry.

**Deliverables:**
- `dopomogai/budai` repo holds versioned base content (this current repo evolves into the registry)
- `bin/librarian sync` pulls from registry into `.agents/base/`
- `bin/librarian publish` opens a PR against the registry to promote a local file
- Manifest schema enforced (semver checks on skill versions)
- Skill versioning + breaking-change checks
- Apply budai to a second repo (Иша's project) to verify portability

**Exit gate:**
- A skill update in the registry propagates to two repos via `librarian sync`
- A skill bumped to a major version triggers a manifest update prompt in pinned repos
- Stats from both repos aggregate cleanly in the backend dashboard

## Phase 7 — Skill self-improvement loop

Autonomous improvement, gated by human review of proposed skill changes.

**Deliverables:**
- Threshold-based skill quality monitoring in the Librarian sweep:
  - Skill success rate < 70% over last N invocations → open improvement task
  - Specific failure mode recurs ≥ 3 times → lesson promotion candidate
  - Workflow average duration > 2× baseline → open investigation task
- Auto-opening of `improve-skill-<name>.md` tasks
- Lesson-promotion pipeline (run-level → role-level → repo-level → registry-level)

**Exit gate:**
- A degraded skill auto-opens an improvement task
- An accepted skill improvement actually moves the success rate (visible in stats)

## Phase 8 — Multi-runner support

Add Codex, direct-Anthropic, and direct-OpenAI runners.

**Deliverables:**
- `runners/codex.md`, `runners/direct-anthropic.md`, `runners/direct-openai.md`
- Per-runner permission and tool-translation handling
- Hybrid fan-outs: one attempt on Claude Code, one on Codex
- Per-attempt model + runner stats

**Exit gate:**
- Same task workflow runs identically with at least 2 different runners
- Stats discriminate by runner; you can see which runner+role combinations work best

## After Phase 8

Phases beyond 8 are speculative and not yet specified:
- Non-code roles (marketing-writer, sales-responder, support-agent)
- Federated registry (multiple registries with namespace resolution)
- Visual workflow editor on the canvas
- Skill marketplace (third-party skill publishing)

These are deferred until experience with Phases 0-8 makes them concrete.
