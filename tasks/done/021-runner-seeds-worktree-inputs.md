---
id: 021
title: Runner seeds worktree with task body, bundle, plan, and ADRs before role dispatch
type: feature
scope: runner
priority: P0
status: done
fan-out: 1
needs-architect: true
plan-approved: true
result-approved: true
trivial: false
depends-on: [020]
blocks: []
sources: [F021]
created: 2026-05-09T18:00:00Z
created-by: human
updated: 2026-05-10T15:00:00Z
workflow: medium-track
bundle-budget: 60000
retry-budget: 2
result-commit: 2cb8975
---

# Task 021: Runner seeds worktree with task body, bundle, plan, and ADRs before role dispatch

## Objective
Eliminate the "absolute-path injection" friction from journey 2: when the runner creates an Implementer/Verifier worktree branched from `main`, the task move + appended Plan section + new ADR + bundle file are all uncommitted in the main worktree, so the worktree can't see them. Today every downstream agent has to be told via prompt to read these via absolute paths back to the main worktree. Move that responsibility into the runner.

## User story
As an Implementer or Verifier agent, when I'm dispatched to my isolated worktree, I want the journey's task body (with current uncommitted plan), bundle, ADR(s), and any other journey-time inputs sitting in `.agents/runs/<run-id>/inputs/` inside my worktree, so I can read them via simple relative paths and operate as if I were a normal session — no absolute-path injection in my prompt.

## Acceptance criteria
- AC1: Before invoking `dispatch_claude_code`, the runner copies into the target worktree's `.agents/runs/<run-id>/inputs/`: (a) the live task `.md` file (current state, including any uncommitted Plan section), (b) the bundle file (filename-glob `<task-id>-*.bundle.*.md`), (c) any ADRs referenced from the plan's `## ADR` section, (d) the verifier's previous `failure.md` if this is a retry dispatch.
- AC2: The composed system prompt includes a `## Journey inputs` block at the top listing the seeded paths (relative to the worktree), so agents read inputs without external coordination.
- AC3: Inputs are copied, not symlinked — the agent's view of the inputs is frozen at dispatch time. Future edits in the main worktree don't leak into in-flight agents.
- AC4: When the journey closes (Judge step), the runner cleans up: `inputs/` directory is left in place for audit (it's under `.agents/runs/`, gitignored), but worktrees are removed via `git worktree remove`.
- AC5: A new `bin/lib/journey_state.py` (or extension to `runner.py`) owns the seed/teardown logic. Pure functions where possible; the runner orchestrates.
- AC6: Tests cover: (a) inputs are copied to the right path, (b) absent inputs are skipped without error (e.g., no ADR exists yet), (c) the seeded files match content on disk in the main worktree at dispatch time, (d) cleanup removes worktrees but preserves `inputs/`.
- AC7: F021 entry in `findings.md` is moved to Promoted with `→ task-021`.

## Context
- Source finding: F021 in `findings.md`.
- Journey 2 retrospective at `tasks/done/004-retrospective.md` documents three sites of absolute-path injection in agent prompts that wouldn't be needed if the runner seeded inputs.
- Soft depends on task-020 (resolution self-source fix) because task-019 (workflows) depends on both, and task-019 wants this seeding to apply to per-workflow input bundles.
- Alternative approach considered: commit the task move + plan to a per-task branch (`task-<id>-coordination`) and create worktrees off that branch. Rejected for v1: per-task branches multiply git noise and don't generalize well to retries (which need a fresh main-based worktree, not a stale coordination branch).

## Plan

### Approach

Introduce a new pure-function module `bin/lib/journey_state.py` that owns input selection, copy semantics, prompt-block formatting, and worktree teardown. `runner.py` orchestrates by calling it just before `dispatch_claude_code` (seed) and at journey close (cleanup). Inputs are hard copies — frozen at dispatch time — landing under `<worktree>/.agents/runs/<run-id>/inputs/`. The composed system prompt gains a `## Journey inputs` block listing the relative paths so downstream agents read inputs without absolute-path injection. See `memory/decisions/0002-runner-input-seeding-ownership.md` for the module-boundary, copy-vs-symlink, and cleanup-lifecycle rationale.

### Decomposition

Single task — one Implementer.

### File-level changes

#### Files to create

- `bin/lib/journey_state.py`
  - **Purpose:** Pure-function library that selects, copies, and cleans up journey-time inputs (task body, bundle, ADRs, prior verifier failure note) for a worktree dispatch. Caller is `bin/lib/runner.py`; downstream consumers will be tasks 019 and 022.
  - **Exports:**
    - `INPUTS_SUBDIR: str = ".agents/runs/{run_id}/inputs"` (or equivalent helper `inputs_dir(worktree, run_id) -> Path`).
    - `@dataclass SeedPlan` — describes the planned copy operations: `task_body: Path | None`, `bundle: list[Path]`, `adrs: list[Path]`, `verifier_failure: Path | None`. Source paths only, no copying yet.
    - `select_inputs(repo_root, task_id, prior_attempt_dir=None) -> SeedPlan` — the picker. Locates the live task `.md` (across all configured task folders via `task_schema.layout_folders`), globs `<task-id>-*.bundle.*.md` (per F002 filename), parses the task body's `## ADR` section for `memory/decisions/<NNNN>-<slug>.md` references, and locates the prior `failure.md` if provided. Returns a `SeedPlan` listing every source path that exists; absent inputs yield empty fields rather than raising.
    - `seed_worktree(worktree_root, run_id, plan) -> list[Path]` — performs the copies. Creates `<worktree_root>/.agents/runs/<run_id>/inputs/` (with parents) and copies each path in the plan into it via `shutil.copy2` (preserves mtime so audit timestamps survive). Returns the list of destination paths, relative to `worktree_root`, in the order: task body, bundle(s), ADR(s), verifier failure. ADRs land in an `inputs/decisions/` sub-folder so multiple ADRs co-exist with their original filenames.
    - `format_inputs_block(seeded_paths: list[Path], worktree_root: Path) -> str` — renders the `## Journey inputs` markdown block. Produces a list of bullet items with relative paths (`.agents/runs/<run-id>/inputs/<task-id>-<slug>.md`, etc.). Empty input list yields an empty string (caller decides whether to include the section).
    - `teardown_worktrees(repo_root, worktree_paths: list[Path]) -> list[tuple[Path, str]]` — runs `git worktree remove --force` on each. Returns a list of `(path, status)` pairs where status is `"removed"`, `"missing"`, or an error message. Does NOT touch `inputs/` directories — those are deliberately preserved for audit.
  - **Key decisions:**
    - Pure functions where possible. The picker and formatter are I/O-light (only file reads + glob); only `seed_worktree` and `teardown_worktrees` mutate the filesystem.
    - Globbing is layout-aware: the picker imports `task_schema.layout_folders` and `task_schema.load_all_tasks` to find the task body, so seeding works under both `standard` and `legacy-four-folder` layouts.
    - ADR parsing is content-based (regex on `memory/decisions/[\w-]+\.md` lines under the `## ADR` heading), not frontmatter-based. Per ADR 0002 §Consequences, this avoids a new frontmatter key.
    - Cleanup is idempotent: re-running `teardown_worktrees` on an already-removed path returns `"missing"`, not an error.
  - **Header notes (`@purpose`, `@why`, etc.):** Per local conventions, header work is tracked by task 014 — do **not** add headers opportunistically. Add only the standard module docstring (`"""..."""`) at top describing purpose in plain prose.

- `tests/bin/test_journey_state.py`
  - **Purpose:** Pytest coverage for the four exported functions. Mirrors the layout established by `tests/bin/test_resolution.py` (sys.path bootstrap from repo root, `tmp_path` fixtures, no fixtures shared across tests).
  - **Test cases (one per behaviour, named after behaviour per base conventions):**
    - `test_select_inputs_finds_task_body_in_in_progress` — seeds `tasks/in-progress/021-foo.md`, asserts `SeedPlan.task_body` points to it.
    - `test_select_inputs_globs_bundle_with_token_count_suffix` — creates `021-foo.bundle.15k.md` and `021-foo.bundle.md`, asserts both appear in `SeedPlan.bundle`.
    - `test_select_inputs_parses_adr_references_from_plan_section` — task body contains an `## ADR` section pointing at `memory/decisions/0002-foo.md`; asserts that ADR appears in `SeedPlan.adrs`.
    - `test_select_inputs_skips_absent_adr_silently` — `## ADR` section references a non-existent file; assert no error and `SeedPlan.adrs == []` (covers AC6(b)).
    - `test_select_inputs_includes_prior_failure_when_supplied` — passes `prior_attempt_dir` containing `failure.md`; asserts `SeedPlan.verifier_failure` is set.
    - `test_seed_worktree_copies_files_to_inputs_subdir` — runs the full seed; asserts files exist at `<worktree>/.agents/runs/<run_id>/inputs/...` (covers AC1, AC6(a)).
    - `test_seed_worktree_content_matches_source_at_dispatch_time` — writes a known string to source, seeds, mutates source after, reads destination, asserts unchanged content (covers AC3, AC6(c)).
    - `test_format_inputs_block_renders_relative_paths` — given a list of seeded paths, asserts the block contains relative paths only (no absolute paths from the host system).
    - `test_teardown_removes_worktree_but_preserves_inputs` — creates a fake worktree dir with `inputs/` inside `.agents/runs/<id>/`, runs teardown; asserts the worktree dir is gone but the `runs/<id>/inputs/` under the *primary* repo is untouched (covers AC4, AC6(d)). Use a stub or skip the actual `git worktree remove` invocation by passing a non-git-tracked tmp dir and asserting the function reports `"missing"` or by patching `subprocess.run`.
    - `test_teardown_idempotent_on_missing_path` — calling teardown on a non-existent path returns `"missing"`, not raises.

#### Files to modify

- `bin/lib/runner.py`
  - **What to change:**
    1. Extend `RunSpec` with two optional fields: `worktree: Path | None = None` and `prior_attempt_dir: Path | None = None`. `worktree` defaults to `cwd` when `None` (preserves existing single-worktree behaviour). `prior_attempt_dir` is the previous Verifier's run dir; supplied only on retry dispatch.
    2. In `compose_system_prompt`, after the existing `pieces` are assembled, call `journey_state.select_inputs(...)` and `journey_state.format_inputs_block(...)`, and **prepend** the resulting `## Journey inputs` block to the role body so it sits at the top (per AC2 — "at the top"). Skip the prepend cleanly when the block is empty.
    3. Add a new function `seed_worktree_inputs(spec: RunSpec, manifest: Manifest) -> list[Path]` that wraps `journey_state.select_inputs` + `journey_state.seed_worktree`. Returns the list of seeded paths (caller logs / passes through).
    4. Add a new function `close_journey(repo_root: Path, worktree_paths: list[Path]) -> list[tuple[Path, str]]` that delegates to `journey_state.teardown_worktrees`. Lives in `runner.py` because it's an orchestration verb tied to the journey lifecycle, not a pure helper.
    5. In `dispatch_claude_code`, call `seed_worktree_inputs(spec, manifest)` before printing the placeholder dispatch line. The current placeholder behaviour (print + return 0) stays — task-009 will replace it. Logging the seeded paths in the placeholder output is enough for now (and aids manual inspection during journey 3).
  - **Why this file:** It's where dispatch happens; seeding has to run between worktree creation (out of scope for this task) and the agent invocation. Putting orchestration here keeps `journey_state.py` testable in isolation.

- `bin/agent`
  - **What to change:**
    1. Add `--worktree <path>` flag to the `run` subcommand (defaults to None → runner uses repo_root, current behaviour).
    2. Add `--prior-attempt-dir <path>` flag (defaults to None) for retry dispatch.
    3. Plumb both flags into `RunSpec(...)` construction in `cmd_run`.
  - **Why this file:** It's the CLI entry point. Worktree path and prior-attempt path are journey-time inputs that the (eventual) workflow runner will pass; for manual journey 3 they're typed by the human or set by a wrapper script.
  - **Note:** Do NOT add worktree-creation logic. Worktree management belongs in a future task (F015 / task-015 territory). This task only consumes a worktree path that already exists.

- `tests/bin/test_runner.py` *(new file — does not yet exist)*
  - **Purpose:** Cover the runner-side glue (`seed_worktree_inputs`, `close_journey`, the prompt-prepend behaviour) end-to-end with `tmp_path`. Existing tests for runner are absent today.
  - **Test cases:**
    - `test_compose_system_prompt_prepends_journey_inputs_block_when_inputs_exist` — creates a fake repo with task body + bundle + ADR, calls `compose_system_prompt`, asserts the output starts with `## Journey inputs` (covers AC2).
    - `test_compose_system_prompt_omits_journey_inputs_block_when_no_inputs` — empty repo (only role body), asserts no `## Journey inputs` block appears.
    - `test_seed_worktree_inputs_creates_inputs_directory_in_worktree` — covers AC1 at the `runner.py` glue layer.
    - `test_close_journey_calls_teardown_for_each_worktree` — patch `subprocess.run`, assert `git worktree remove` is invoked once per path.
  - **Note:** If integrating with `journey_state` is too coupled at this layer, two of these tests can be folded into `test_journey_state.py` and the runner-level tests reduced to a smoke check. Implementer's call.

#### Findings move

- `findings.md`
  - **What to change:** Move the F021 entry from the **Open** section to the **Promoted** section. Append `→ task-021` to its title line (the convention used by F001–F012 and F020). Do not edit the body text.
  - **Why this file:** AC7 explicitly requires it. The Librarian's audit trail expects every promoted finding to land in the Promoted section with the marker.

### Risks and escalations

- **Worktree creation is out of scope but assumed.** This task seeds an *existing* worktree; it does not create one. If journey 3 still creates worktrees by hand, the `--worktree` flag is human-typed. Acceptable for this task; F015 / task-015 owns automated worktree management. (No escalation needed — task body is explicit about scope.)
- **`dispatch_claude_code` is a placeholder (F008).** Real dispatch hasn't landed (task-009). The seeding code runs *before* dispatch, so it works regardless — but verifying end-to-end requires either a real `claude` invocation (task-009 territory) or stub-based tests. Mitigation: tests use stubs; manual journey 3 will exercise the real path once task-009 lands.
- **ADR-section parsing is content-based.** A malformed `## ADR` section (e.g. broken markdown) would silently produce zero ADRs. Mitigation: the picker's behaviour on missing/malformed content is silent-skip per AC6(b); the Planner is responsible for well-formed plan sections, and a missing ADR is recoverable (the agent reads it from the bundle or directly if needed).
- **Bundle filename glob may match more than expected.** If a task accidentally has multiple bundles with different `.<NNk>.md` suffixes, all are seeded. This is intentional (F002 lets us encode token counts in filenames; multiple regenerations may co-exist) — but operators should know the agent reads whichever it picks. Acceptable; document at the seeding call site.
- **Cross-platform `git worktree remove` interaction.** On Windows or repos with non-default `core.fileMode`, `git worktree remove --force` can leave leftovers. Mitigation: `teardown_worktrees` reports the status string; callers can surface partial failures. Out-of-scope for this task to make it bulletproof.
- **No human escalation required.** All architectural ambiguity (module boundary, copy semantics, cleanup lifecycle) is resolved in ADR 0002. The `needs-architect: true` flag was asking for exactly that artifact.

### ADR

Wrote `memory/decisions/0002-runner-input-seeding-ownership.md` documenting the choice of a new `bin/lib/journey_state.py` module (vs. inlining in `runner.py`), copy-not-symlink semantics, and the cleanup-lifecycle decision (preserve `inputs/`, remove worktrees). Three coupled decisions captured in one place because tasks 019 and 022 will read the same ADR when they extend the seeding surface.

### Acceptance criteria mapping

- **AC1** (runner copies task `.md`, bundle, ADRs, prior failure into `<worktree>/.agents/runs/<run-id>/inputs/` before dispatch) → covered by `journey_state.select_inputs` + `journey_state.seed_worktree` + the call to `seed_worktree_inputs(spec, manifest)` from `dispatch_claude_code`. Tested by `test_seed_worktree_copies_files_to_inputs_subdir`.
- **AC2** (composed system prompt has `## Journey inputs` block at the top listing relative paths) → covered by `journey_state.format_inputs_block` + the prepend in `compose_system_prompt`. Tested by `test_compose_system_prompt_prepends_journey_inputs_block_when_inputs_exist`.
- **AC3** (inputs are copied, not symlinked; frozen at dispatch time) → covered by `seed_worktree`'s use of `shutil.copy2` (hard copy). Explicitly captured in ADR 0002 §Decision 2. Tested by `test_seed_worktree_content_matches_source_at_dispatch_time`.
- **AC4** (Judge-step cleanup removes worktrees but preserves `inputs/`) → covered by `journey_state.teardown_worktrees` (worktree removal) and the deliberate non-touch of `runs/<run-id>/inputs/`. Captured in ADR 0002 §Decision 3. Tested by `test_teardown_removes_worktree_but_preserves_inputs`.
- **AC5** (new `bin/lib/journey_state.py` owns seed/teardown logic; pure functions where possible; runner orchestrates) → covered by the module structure described in *Files to create*. Pure: `select_inputs`, `format_inputs_block`. Side-effecting: `seed_worktree`, `teardown_worktrees`. Runner imports and calls.
- **AC6** (tests cover: (a) inputs at right path, (b) absent inputs skipped without error, (c) seeded files match source content at dispatch, (d) cleanup removes worktrees but preserves `inputs/`) →
  - (a) `test_seed_worktree_copies_files_to_inputs_subdir`
  - (b) `test_select_inputs_skips_absent_adr_silently` (and the empty-fields default in `SeedPlan`)
  - (c) `test_seed_worktree_content_matches_source_at_dispatch_time`
  - (d) `test_teardown_removes_worktree_but_preserves_inputs`
- **AC7** (F021 entry moved from Open to Promoted in `findings.md` with `→ task-021` marker) → covered by the *Findings move* file-level change.

### Recommended fan-out

1 — task is mechanical given ADR 0002 has resolved the architectural choices. Two parallel attempts would diverge only on test-shape minutiae, not on shape of solution; fan-out adds cost without diversifying useful outcomes. (Per the Journey 2 retrospective recommendation, fan-out: 2 should be tried on a task with genuine architectural ambiguity — this is not that task.)

### Confidence level

high — module boundary and copy semantics are decided in ADR 0002; every AC traces to a specific change; the precedent (`task_schema.py` sibling pattern) is established and tested in this repo; `journey_state.py` is a new file with no migration cost. The only soft spot is that real-claude dispatch (task-009) hasn't landed, so end-to-end verification waits for journey 3 — but the unit-test surface here is sufficient for AC6 and the placeholder dispatch path will exercise seeding visibly via its log output.

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
