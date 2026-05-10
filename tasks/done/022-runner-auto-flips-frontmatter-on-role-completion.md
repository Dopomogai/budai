---
id: 022
title: Runner auto-flips task frontmatter on role completion per workflow gate-rules
type: feature
scope: runner
priority: P0
status: done
fan-out: 1
needs-architect: true
plan-approved: true
result-approved: true
trivial: false
depends-on: [019, 020]
blocks: []
sources: [F015, F025]
created: 2026-05-09T18:00:00Z
created-by: human
updated: 2026-05-11T00:00:00Z
workflow: medium-track
bundle-budget: 50000
retry-budget: 2
result-commit: e3be4b9
---

# Task 022: Runner auto-flips task frontmatter on role completion per workflow gate-rules

## Objective
Stop forcing humans to hand-edit task frontmatter at every workflow gate. Each role in a workflow has a deterministic exit-status (`open → planning` after Librarian, `planning → reviewing-plan` after Planner, etc.); the runner — not the agent, not the human — should perform the flip when a role's exit conditions are met, while still preserving the human approval gate at the steps the workflow declares require human review.

## User story
As a budai operator running a journey, I want frontmatter status, plan-approved, and result-approved fields to flip automatically when a role passes its exit conditions and the workflow's gate-rules don't require human intervention, so the only manual edits I make are the ones I'm actually deciding on (final approve/reject), not paperwork.

## Acceptance criteria
- AC1: After each role's `dispatch_claude_code` returns successfully, the runner reads the workflow's gate-rules to determine the next status; if the role's gate is auto-approve (per workflow), the runner flips `status:` and any associated boolean fields (`plan-approved`, `result-approved`) using `bin/lib/task_schema.py`'s `validate_transition` to ensure legality.
- AC2: When a workflow's gate-rule requires human approval, the runner halts and prints a single-line summary with the path to the artifact to review and the command to flip status manually (`python3 bin/task move <id> <new-status>`). This is the *only* human-frontmatter-edit moment.
- AC3: The auto-flip is logged in `.agents/runs/<run-id>/transitions.json` per role: `{role, exit-status, prev-task-status, new-task-status, timestamp, decision: "auto" | "human-required" | "auto-with-condition: <name>"}`. Audit trail.
- AC4: The runner refuses to flip if the role reported `failed` or escalated; in that case it surfaces the failure path and halts (no silent re-run).
- AC5: Existing `bin/task move <id> <status>` continues to work for human overrides — auto-flip and manual flip share the same code path in `task_schema`.
- AC6: Tests cover: (a) sequential auto-flips through `ship-feature` with all auto-approve gates yield the correct final status, (b) a workflow with a human-required gate halts with the right message, (c) a failed role doesn't trigger a flip, (d) `transitions.json` records the audit trail, (e) `validate_transition` rejects illegal flips even from the runner.
- AC7: F015 and F025 entries in `findings.md` are moved to Promoted with `→ task-022`.

## Context
- Source findings: F015 (CanvasOS retrospective) and F025 (budai journey 2 recurrence). Both document the same problem: 5–7 manual frontmatter flips per journey, all mechanical.
- Hard depends on task-019 (workflow gate-rules) — without per-workflow declarations, the runner has no source of truth for which gates auto-approve.
- Hard depends on task-020 (resolution.py self-source) — workflow file lookup goes through the resolver.
- Soft depends on task-021 (input seeding) — the auto-flipped task file should be in the worktree's seeded inputs so the next role sees the post-flip frontmatter.
- This is the largest single source of friction in journeys today (~7 of ~22 approvals in journey 2 were frontmatter edits). Closing it shrinks per-journey approval count by ~30%.

## Plan

### Approach
Introduce a new pure-function module `bin/lib/transitions.py` that owns the atomic write+move primitive for task frontmatter, the role-to-next-status mapping, the predicate-context build step, and the journey-level `flip_for_role` orchestration verb. `dispatch_roles` in `runner.py` consumes it after each role's dispatch returns: read the gate-rule, optionally evaluate a predicate, then either auto-flip (calling `apply_transition`) or halt with a human-flip command summary. `bin/task move` is refactored to call `apply_transition` so manual and automatic flips share one code path (AC5). Every decision is appended to `.agents/runs/<run-id>/transitions.json`. Fail-closed throughout: any missing predicate input falls back to human-required, never silent auto-approve.

### Decomposition
Single task — one Implementer.

### File-level changes

#### Files to create

- **`bin/lib/transitions.py`** — auto-flip orchestration and pure-function frontmatter mutation.
  - Purpose: single owner of "given role completion and a gate-rule, decide and apply (or halt for) the next status."
  - Exports:
    - `ROLE_EXIT_STATUS: dict[str, str]` — `{librarian: planning, planner: reviewing-plan, implementer: reviewing-result, verifier: reviewing-result, judge: done}`.
    - `@dataclass TransitionDecision` — fields `role, prev_status, new_status, decision ("auto" | "auto-with-condition: <name>" | "human-required" | "role-failed"), gate_mode, predicate (str | None), halted_reason (str | None)`.
    - `apply_transition(repo_root: Path, task_id: str, new_status: str, layout: str, extra_fm_updates: dict | None = None) -> Path` — finds the task file across layout folders, parses frontmatter, runs `validate_transition(old, new)`, mutates `status` + `updated` + any keys in `extra_fm_updates` (typically `plan-approved: True` or `result-approved: True`), re-validates with `validate_frontmatter`, re-validates `depends-on` graph via `validate_dependencies`, writes back atomically, and moves to the new folder per `folder_for_status`. Returns the new path. Raises `ValueError` on illegal transitions or invalid frontmatter.
    - `next_status_for_role(role: str) -> str` — `ROLE_EXIT_STATUS[role]`; raises `KeyError` on unknown role (callers catch and surface).
    - `extra_fm_updates_for_transition(prev_status: str, new_status: str) -> dict` — encodes the boolean-flip rules: when `prev == "reviewing-plan"` and `new == "implementing"`, return `{"plan-approved": True}`; when `new == "done"` (from `reviewing-result` or `coordinator`), return `{"result-approved": True}`; else `{}`.
    - `build_predicate_context(repo_root: Path, task_id: str, run_dir: Path, worktree: Path | None, layout: str) -> dict` — assembles the six-atom context per ADR 0004 §3. Sources:
      - `fan_out` ← task frontmatter `fan-out` (int).
      - `trivial` ← task frontmatter `trivial` (bool).
      - `verifier_passed` ← `worktree/evidence/ac-mapping.json` (or `run_dir/evidence/ac-mapping.json` if worktree is None) — True iff every entry has `verdict == "pass"`. False if file missing or unreadable.
      - `all_ac_pass` ← same source as `verifier_passed`.
      - `no_new_adr` ← `git -C <worktree> diff --name-only origin/main..HEAD -- memory/decisions/` returns empty stdout. If worktree is None or git fails, return False (fail-closed).
      - `single_attempt` ← count of `council/<task-id>/attempts/attempt-*.md` files (in `repo_root`, not worktree) equals 1. False if dir missing.
    - `flip_for_role(spec, workflow: WorkflowSpec, role: str, role_exit_code: int, run_dir: Path, manifest) -> TransitionDecision` — the orchestration verb. Looks up `gate_mode = workflow.gate_rules.get(role, "human")`. If `role_exit_code != 0` returns `TransitionDecision(decision="role-failed", ...)`, writes the record to `transitions.json`, and returns without flipping (AC4). Otherwise:
      - Reads current task status via `parse_frontmatter` (so the decision record's `prev_status` is accurate).
      - Computes `new_status = next_status_for_role(role)` and `extra = extra_fm_updates_for_transition(prev, new_status)`.
      - If `gate_mode == "auto"`: call `apply_transition`, record `decision="auto"`.
      - If `gate_mode == "human"`: do not flip; record `decision="human-required"`, populate `halted_reason` with the manual command (`python3 bin/task move <task-id> <new-status>`).
      - If `gate_mode.startswith("auto-when:")`: parse predicate via `workflow_schema.parse_predicate`, build context via `build_predicate_context`, evaluate via `workflow_schema.evaluate_predicate`. On True → flip + `decision=f"auto-with-condition: {predicate}"`. On False → halt + `decision="human-required"`.
      - Always append a record to `<run_dir>/transitions.json` (AC3).
    - `append_transition_record(run_dir: Path, record: dict) -> None` — read-modify-write the JSON array at `<run_dir>/transitions.json`, creating it if missing.
  - Key decisions: per ADR 0004 — module ownership, role-keyed exit map, fail-closed predicate sources, append-only JSON-array audit trail.
  - Header `@gotchas`: `ROLE_EXIT_STATUS` must stay in lock-step with `task_schema.STATUS_TRANSITIONS`; every value in the map must be reachable from its corresponding role's expected prev-status. Predicate-context sources read from three I/O surfaces (run-dir, worktree, git); each missing-source path must return False, not raise.
  - Header `@stability`: experimental (will be revisited after journey 6).

- **`tests/bin/test_transitions.py`** — unit tests for the new module.
  - Test cases (one per behaviour, behaviour-named):
    - `test_apply_transition_legal_flip_moves_file` — creates a fixture task in `planning`, calls `apply_transition(..., "reviewing-plan")`, asserts file moved to correct folder and `status:` updated.
    - `test_apply_transition_writes_extra_fm_updates` — passes `extra_fm_updates={"plan-approved": True}`, asserts both `status` and `plan-approved` written.
    - `test_apply_transition_rejects_illegal_transition` — fixture in `done`, calls with `"planning"`, asserts `ValueError`.
    - `test_apply_transition_updates_updated_timestamp` — asserts `updated:` differs from pre-call value.
    - `test_apply_transition_idempotent_when_old_equals_new` — same status, no-op without raise.
    - `test_next_status_for_role_known_roles` — all five role names map correctly.
    - `test_next_status_for_role_unknown_raises` — `KeyError`.
    - `test_extra_fm_updates_planner_to_implementing` — `{"plan-approved": True}`.
    - `test_extra_fm_updates_judge_to_done` — `{"result-approved": True}`.
    - `test_extra_fm_updates_other_transitions_empty` — most pairs return `{}`.
    - `test_build_predicate_context_reads_fan_out_and_trivial_from_frontmatter`.
    - `test_build_predicate_context_verifier_passed_true_when_all_pass` — fixture `ac-mapping.json` with all `pass`.
    - `test_build_predicate_context_verifier_passed_false_on_missing_file` — fail-closed.
    - `test_build_predicate_context_verifier_passed_false_on_one_fail` — mixed verdicts → False.
    - `test_build_predicate_context_no_new_adr_true_when_git_returns_empty` — mocked `subprocess.run`.
    - `test_build_predicate_context_no_new_adr_false_when_git_fails` — fail-closed.
    - `test_build_predicate_context_single_attempt_true_with_one_file`.
    - `test_flip_for_role_auto_mode_applies_flip` — fixture workflow `gate-rules: {planner: auto}`, asserts `status` advanced and `transitions.json` has one record `decision="auto"`.
    - `test_flip_for_role_human_mode_halts_without_flipping` — `gate-rules: {planner: human}`, asserts task file untouched and record `decision="human-required"`.
    - `test_flip_for_role_auto_when_predicate_true_flips` — `gate-rules: {planner: "auto-when:fan-out-1"}` with fan-out=1 → flip; record decision contains the predicate string.
    - `test_flip_for_role_auto_when_predicate_false_halts` — same gate, fan-out=2 → halt.
    - `test_flip_for_role_failed_role_writes_record_without_flip` (AC4) — `role_exit_code=1`, asserts no flip and `decision="role-failed"`.
    - `test_flip_for_role_illegal_transition_propagates_valueerror` (AC6e) — fixture with wrong prev-status, asserts `ValueError` from `validate_transition`.
    - `test_append_transition_record_creates_file_if_missing`.
    - `test_append_transition_record_appends_to_existing_array`.
    - `test_sequential_flips_through_ship_feature_yields_done` (AC6a) — runs five `flip_for_role` calls in order with all auto/auto-when gates resolving True; asserts final status `done`.
    - `test_human_gate_workflow_halts_at_first_human_gate` (AC6b) — runs `flip_for_role` on `planner` with `gate-rules: {planner: human}`; asserts halt and subsequent role not flipped.
    - `test_transitions_json_records_audit_trail` (AC6d) — three sequential calls produce three records with all required fields.

#### Files to modify

- **`bin/lib/runner.py`** (lines 258–285, `dispatch_roles`)
  - Import: `from .transitions import flip_for_role, TransitionDecision`.
  - Inside the per-role loop: after the existing print of `[runner] would dispatch <role> with gate <mode>`, simulate a successful role completion (Phase 0 has no real subprocess yet — pass `role_exit_code=0`). Call `flip_for_role(spec, workflow, role, role_exit_code=0, run_dir=make_run_dir(spec), manifest=manifest)`.
  - If the returned `TransitionDecision.decision == "human-required"`: print the halt summary (single line: `[runner] Halt at <role>; review artifact at <path>; run: python3 bin/task move <task-id> <new-status>`) and `return 0` (AC2). Subsequent roles do not run.
  - If `decision == "role-failed"`: print the failure path and `return 1` (AC4).
  - If `decision` starts with `"auto"`: print `[runner] Auto-flipped <task-id>: <prev> → <new> (gate <mode>)` and continue the loop.
  - The function signature gains no new parameters; `manifest` is already passed in.
  - Note: when task-009 lands real dispatch, `role_exit_code` will be the real subprocess exit code; the wiring here is a one-line change at that point.

- **`bin/task`** (lines 223–306, `cmd_move`)
  - Refactor to call `transitions.apply_transition(ctx.repo_root, args.id, args.status, ctx.layout)` and print the returned path.
  - Preserves error handling: catches `ValueError` from `apply_transition` and prints to stderr, returning 1.
  - All transition validation, frontmatter re-validation, dependency re-validation, file-move logic move into `apply_transition` (where they already exist as a contiguous block — net code is mostly relocation, not new logic).
  - Why: AC5 — the runner's auto-flip and the human's manual flip must share exactly one code path.

- **`findings.md`** — move F015 and F025 from Open to Promoted, append `→ task-022` marker to each (AC7). Preserve original entry text verbatim per `local/conventions.md` task-promotion convention.

- **`docs/05-workflows.md`** — add one short paragraph (≤6 lines) under the gate-rules section describing auto-flip behavior, with a link to ADR 0004. The current doc describes gate-rules' declarative shape but says nothing about who consumes them at runtime. Why: anyone reading the workflow doc to understand how gates work needs to find the runtime-consumption side without grep.

### Risks and escalations

- **`verifier-passed` predicate depends on `evidence/ac-mapping.json` written by the Verifier role.** In Phase 0 (task-009 not yet shipped), the Verifier doesn't actually run — `dispatch_claude_code` is a placeholder. The `build_predicate_context` reader returns False when the file is missing, so any `auto-when:verifier-passed` gate halts to human in Phase 0. This is correct (fail-closed) but means the auto-when path is not end-to-end exercised until task-009 lands. Mitigation: unit tests cover the True path with a synthetic `ac-mapping.json` fixture.
- **`no-new-adr` predicate uses `subprocess.run(["git", "diff", ...])`** which adds a process-spawn cost per role. Mitigation: cache the result per run-dir (one git call per journey, not per role). The cache is a module-level dict keyed by `(worktree, run_dir)`; cleared between test cases via fixture teardown.
- **`bin/task move` refactor risk.** The current `cmd_move` has subtle ordering (validate-then-write-then-move). The refactor must preserve atomic semantics: write before move, never the reverse. Mitigation: keep the existing test (`tests/bin/test_task_move.py` or equivalent) green; add one new test for `apply_transition` called directly.
- **`ROLE_EXIT_STATUS` is implicitly the contract for every workflow's `roles:` list.** A workflow with `roles: [auditor]` (a stub that mentions `auditor`) would crash with `KeyError` at the first dispatch. Mitigation: `flip_for_role` catches `KeyError` from `next_status_for_role` and returns a `TransitionDecision` with `decision="human-required"` + `halted_reason="role <X> has no exit-status mapping; add to transitions.ROLE_EXIT_STATUS"`. Surfaces loud, doesn't crash.
- **Concurrent `apply_transition` calls** (two runners on the same task) could race on the read-modify-write. Mitigation: out of scope for v1 (single-runner assumption). Document in `@gotchas`.
- **(none requiring human escalation)**

### Acceptance criteria mapping

- AC1 (auto-flip after dispatch using `validate_transition`) → covered by `runner.py::dispatch_roles` calling `flip_for_role`, which calls `apply_transition`, which calls `validate_transition`.
- AC2 (human-required gate halts with single-line summary + manual command) → covered by `flip_for_role`'s human branch + `dispatch_roles`'s halt print; tested in `test_flip_for_role_human_mode_halts_without_flipping`.
- AC3 (transitions.json audit trail) → covered by `append_transition_record` + schema per ADR 0004 §4; tested in `test_transitions_json_records_audit_trail`.
- AC4 (failed role refuses to flip, surfaces failure path) → covered by `flip_for_role`'s `role_exit_code != 0` branch; tested in `test_flip_for_role_failed_role_writes_record_without_flip`.
- AC5 (manual + auto flip share `apply_transition`) → covered by `bin/task::cmd_move` refactor.
- AC6a (sequential ship-feature auto yields final `done`) → `test_sequential_flips_through_ship_feature_yields_done`.
- AC6b (workflow with human gate halts) → `test_human_gate_workflow_halts_at_first_human_gate`.
- AC6c (failed role doesn't flip) → same as AC4 test.
- AC6d (transitions.json records trail) → `test_transitions_json_records_audit_trail`.
- AC6e (`validate_transition` rejects illegal flips even from runner) → `test_flip_for_role_illegal_transition_propagates_valueerror`.
- AC7 (F015 + F025 moved to Promoted with marker) → `findings.md` edit.

### Recommended fan-out
1 — single coherent module addition with one consumer wired in `runner.py`. Mechanical execution from this plan; fan-out adds cost without diversifying outcomes.

### Confidence level
medium — the module structure, role-exit-status mapping, and `apply_transition` shape are well-pinned (precedent in `task_schema.py` and `journey_state.py`). The weak spot is `build_predicate_context` source plumbing: `verifier-passed` reads from `evidence/ac-mapping.json` whose schema isn't formally documented anywhere yet (Verifier writes it ad-hoc per workflow exit-criteria). Unit tests cover the contract with a synthetic fixture; a future task-009 journey will validate end-to-end. The `no-new-adr` git-diff path is a second mild risk (subprocess spawn + repo-state dependency); fail-closed mitigates correctness risk but real-world firing only happens once a workflow gate uses that atom.

### ADR
Wrote `memory/decisions/0004-auto-flip-frontmatter-and-predicate-context.md` documenting module ownership (`bin/lib/transitions.py`), the role-to-next-status map (role-keyed, hardcoded, static across workflows), the predicate-context source table per atom (with fail-closed semantics for `verifier-passed`, `no-new-adr`, `single-attempt`), and the `transitions.json` append-only-JSON-array schema. The ADR is load-bearing for future workflow additions: any new role must add to `ROLE_EXIT_STATUS`, any new predicate atom must document its source the same way.

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
