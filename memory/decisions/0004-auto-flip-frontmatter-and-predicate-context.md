# ADR 0004 — Auto-flip frontmatter on role completion: module ownership, role-status mapping, predicate context sources

- Status: accepted
- Date: 2026-05-10
- Source: task-022

## Context

Task-019 shipped workflow gate-rules with a closed-set predicate language
(ADR 0003 §2). Task-022 now wires the runner to actually consume those
gate-rules: after each role's dispatch returns, the runner must either
auto-flip the task's `status:` (and `plan-approved` / `result-approved`
booleans) or halt for human approval, depending on the gate-rule.

Three coupled decisions arise that future agents will need to navigate, all
of which were flagged as soft spots by the journey-5 Verifier:

1. **Where does the auto-flip code live?** A new module
   (`bin/lib/transitions.py`)? Extension of `task_schema.py`? Inline in
   `runner.py`?
2. **What's the role-to-next-status mapping?** Each role has a deterministic
   exit status, and the mapping differs per workflow
   (`ship-feature` has 5 transitions; `medium-track` has 4; `fast-track`
   has 2). Hardcoded? Workflow-declared? Derived from
   `STATUS_TRANSITIONS`?
3. **What populates the predicate-evaluation context?** Each atom in
   ADR 0003 §2 (`fan-out-1`, `verifier-passed`, `trivial`, `all-ac-pass`,
   `no-new-adr`, `single-attempt`) needs a concrete source. Where does each
   value come from at evaluation time?

## Decision

### 1. New module: `bin/lib/transitions.py`

Mirrors `bin/lib/task_schema.py` / `bin/lib/journey_state.py` /
`bin/lib/workflow_schema.py` precedent. Pure-function module owned by
the runner. Public surface:

- `apply_transition(repo_root, task_id, new_status, layout,
  extra_fm_updates=None) -> Path` — atomically updates a task file's
  frontmatter (`status:`, plus optional booleans like
  `plan-approved: true`) and moves the file to the correct folder per
  `folder_for_status`. Validates the transition with
  `task_schema.validate_transition`; raises `ValueError` on illegal
  transitions. **This is the single code path** that both
  `bin/task move` and the runner's auto-flip call.
- `next_status_for_role(workflow_name, role) -> str | None` — returns
  the deterministic next status for the role completion.
- `build_predicate_context(spec, workflow_spec, role, run_dir) -> dict`
  — assembles the context dict for `evaluate_predicate`.
- `flip_for_role(spec, workflow_spec, role, role_exit_code, run_dir) ->
  TransitionDecision` — the orchestration verb the runner calls. Reads
  gate-rule for the role, computes the decision (auto / human / failed),
  applies the flip if auto, and appends a record to `transitions.json`.

`TransitionDecision` is a small dataclass: `{role, prev_status,
new_status, decision, gate_mode, predicate?, halted_reason?}`. Halting
returns this object without flipping.

**Rationale for a sibling module rather than extending `task_schema.py`:**
the auto-flip is a runner-orchestration verb that knows about workflows
and runs; `task_schema.py` is the pure-function frontmatter library that
neither workflows nor the runner should leak into. Keeping `task_schema`
free of `WorkflowSpec` imports preserves its test boundary (it's tested
without a manifest, without workflows). Mirrors how `journey_state.py`
keeps worktree-seeding out of `manifest.py`.

**Why not inline in `runner.py`?** Two callers (`bin/task move` for
manual overrides and `dispatch_roles` for auto-flips) need the same
atomic write+move primitive. Inline would force `bin/task` to import
from `runner.py`, which transitively imports `manifest.py` and other
runner machinery the CLI move doesn't need.

### 2. Role-to-next-status mapping is hardcoded in `transitions.py`, keyed by role name (not workflow)

`ROLE_EXIT_STATUS: dict[str, str]` is a single static map shared by all
workflows:

```python
ROLE_EXIT_STATUS = {
    "librarian": "planning",
    "planner": "reviewing-plan",
    "implementer": "reviewing-result",
    "verifier": "reviewing-result",
    "judge": "done",
}
```

Plus a boolean-flip rule: when transitioning *out of* `reviewing-plan`
into `implementing` via auto-approve, set `plan-approved: true`. When
transitioning into `done` via auto-approve, set `result-approved: true`.

**Rationale for role-keyed rather than workflow-keyed:** every workflow
that uses a role uses it for the same lifecycle role (the Planner always
produces a plan, the Verifier always verifies). A workflow can't
sensibly redefine "Planner exits to anywhere other than reviewing-plan."
The variation across workflows is which *roles run*, not what each role
*does*. Encoding role-exit-status in `transitions.py` (instead of every
workflow file) keeps workflow files declarative and short.

**Rationale for not in `task_schema.py`'s `STATUS_TRANSITIONS`:** that
table is "what transitions are legal at all"; this map is "what
transition this role triggers on completion." The two are related but
different — `STATUS_TRANSITIONS` allows
`reviewing-plan → planning` (revision loop), but
`ROLE_EXIT_STATUS["planner"]` is unambiguously `reviewing-plan`. They
must agree (Verifier asserts every role-exit transition is in
`STATUS_TRANSITIONS`), but they're not the same data.

**The `verifier → reviewing-result` choice when no Judge runs:** In
medium-track, the Verifier is terminal (no Judge). The Verifier flips
to `reviewing-result`; the human or auto-approve flips to `done`. In
ship-feature, the Verifier also flips to `reviewing-result`, then the
Judge runs *within* `reviewing-result` and itself flips to `done` on
success. Both workflows use the same role-exit-status; the difference is
which roles are scheduled after.

### 3. Predicate-context sources, atom by atom

Every atom in ADR 0003 §2 has exactly one source documented here. The
runner's `build_predicate_context` is the single producer.

| Atom | Source | Falsy fallback |
|---|---|---|
| `fan-out-1` | `int(task_fm.get("fan-out", 1)) == 1` — task frontmatter | False if missing |
| `trivial` | `bool(task_fm.get("trivial", False))` — task frontmatter | False if missing |
| `verifier-passed` | `evidence/ac-mapping.json` in `run_dir` — every entry has `verdict: "pass"` | **False if file missing** |
| `all-ac-pass` | Same source as `verifier-passed` (alias today; may diverge in v2 if Judge becomes a separate source) | False if missing |
| `no-new-adr` | `git diff --name-only main..HEAD -- memory/decisions/` in the worktree returns empty (or run_dir has no `adrs/` artifact) | False if cannot determine (fail closed) |
| `single-attempt` | Count of `council/<task-id>/attempts/attempt-*.md` files equals 1 | False if dir missing |

**Fail-closed semantics throughout.** When a source is unavailable, the
context value is False, which causes `evaluate_predicate` to return
False, which causes the runner to halt for human approval. This matches
ADR 0003's principle of fail-loud-not-silent: missing predicate inputs
should never auto-approve.

**`verifier-passed` is the J5-flagged weak spot.** The Verifier writes
`evidence/ac-mapping.json` into its worktree (per
`base/workflows/medium-track.md` exit-criteria). Task-022's
`build_predicate_context` reads that file *from the verifier's worktree
path*, which the runner knows via `spec.worktree` (set when dispatching
the Verifier). If the Verifier dispatched without a worktree (Phase 0
placeholder mode), or the file is missing or invalid JSON, the predicate
returns False and the runner halts for human approval. **No silent
auto-approve when the Verifier evidence is unreadable.**

### 4. transitions.json — append-only JSON array

Path: `.agents/runs/<run-id>/transitions.json`. Schema per AC3:

```json
[
  {
    "role": "planner",
    "exit_status": "success",
    "prev_task_status": "planning",
    "new_task_status": "reviewing-plan",
    "decision": "human-required",
    "gate_mode": "human",
    "predicate": null,
    "timestamp": "2026-05-10T20:45:00Z"
  },
  ...
]
```

**Write semantics:** read-modify-write the whole array each role.
Append-only JSONL was considered; rejected because journey state files
elsewhere (`evidence/ac-mapping.json`, run manifests) are JSON arrays
not JSONL, and consistency wins over marginal write performance — a
journey emits at most 5 transition records.

When `role_exit_code != 0` (role failed) per AC4, the runner writes
a record with `decision: "role-failed"`, `new_task_status: null`,
and halts. No flip occurs.

## Consequences

**Good:**

- One pure-function module owns frontmatter mutation. Both manual
  (`bin/task move`) and automatic (runner) flips share the same atomic
  write+move primitive — no drift between the two.
- Role-exit-status mapping is one static dict, not five workflow-file
  fields. Adding a new workflow doesn't require declaring the same
  mapping again.
- Every predicate atom has a documented source. Future atoms must
  document their source the same way (this ADR is the precedent).
- Fail-closed semantics throughout: missing inputs → halt for human,
  never silent auto-approve. Matches ADR 0003's fail-loud principle.

**Bad / risks:**

- `ROLE_EXIT_STATUS` is implicitly the contract every workflow's
  `roles:` list relies on. If someone adds a new role (`auditor`,
  `peer-reviewer`) without adding to the map, the runner crashes at
  dispatch time with a clear error — that's acceptable, but flag in
  workflow-authoring docs.
- The predicate-context build step reads files from the run-dir AND
  the worktree AND git. That's three I/O surfaces in one helper; the
  helper has to handle each missing gracefully. Tests must cover each
  missing-source path.
- `verifier-passed` reading from `evidence/ac-mapping.json` couples the
  Verifier's output schema to the runner's auto-flip logic. If task-009
  changes how Verifier writes evidence, this coupling needs to be
  versioned. Today there's only one shape; flag for revisit when a
  second Verifier shape ships.
- `single-attempt` and `no-new-adr` atoms have no consumer in shipped
  workflows yet (fix-bug, fast-track, medium-track, ship-feature). Their
  context plumbing lands in this task but won't fire until a workflow
  references them. Tested via direct unit tests of
  `build_predicate_context`.

## Status

Accepted for task-022. Will be revisited after journey 6 (this task's
journey) and if any of the unused atoms (`single-attempt`,
`no-new-adr`) gets a real consumer in a workflow file.
