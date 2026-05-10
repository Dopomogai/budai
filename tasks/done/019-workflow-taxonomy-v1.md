---
id: 019
title: Workflow taxonomy v1 — beyond ship-feature
type: feature
scope: workflows
priority: P1
status: done
fan-out: 1
needs-architect: true
plan-approved: true
result-approved: true
trivial: false
depends-on: []
blocks: [022]
sources: [human-strategy-2026-05-09]
created: 2026-05-09T18:00:00Z
created-by: human
updated: 2026-05-10T20:30:00Z
result-commit: ccdb612
workflow: medium-track
bundle-budget: 70000
retry-budget: 2
depends-on-rationale: dropped [009] as dependency at pre-flight 2026-05-10. task-009 is deferred but workflow files (declarative YAML+markdown) can be read by the runner whether dispatch_claude_code is a real subprocess or placeholder. task-019 ships value without 009.
---

# Task 019: Workflow taxonomy v1 — beyond ship-feature

## Objective
Codify nine workflows in `base/workflows/` so the runner can dispatch by `workflow:` field instead of hardcoding the L→P→I→V→J chain. Different work shapes (docs, scaffolding, audits, trivial fixes, granular plan-then-execute) need different role sequences and gate rules; today everything routes through the heaviest path even when it's overkill.

## User story
As a budai operator, when I create a task with `workflow: scaffold-docs` (or `fast-track`, or `estimate-task`), I want the runner to dispatch only the roles that workflow declares, in the declared order, with that workflow's gate rules — so a 5-minute typo fix doesn't need a Librarian bundle and a Judge verdict, and a multi-week strategic audit doesn't have to pretend to be a single-attempt feature.

## Acceptance criteria
- AC1: Nine workflow files exist at `base/workflows/<name>.md`: `ship-feature.md` (canonical baseline; existing if present, otherwise create), `fix-bug.md`, `scaffold-project.md`, `scaffold-docs.md`, `strategic-audit.md`, `prepare-task.md`, `estimate-task.md`, `fast-track.md`, `medium-track.md`. Each has YAML frontmatter declaring `name, roles (ordered list), gate-rules, entry-criteria, exit-criteria, skipped-artifacts, auto-approve-when` and a markdown body explaining when to use it, what's skipped vs ship-feature, and success criteria.
- AC2: `bin/lib/runner.py` reads the task's `workflow:` field, loads the matching workflow file via `bin/lib/resolution.py` (resolves to `base/workflows/<name>.md` or `local/workflows/<name>.md` overlay), and dispatches roles in the declared order. Unknown workflow names raise `ValueError`.
- AC3: `bin/agent run` accepts an optional `--workflow <name>` flag that overrides the task's declared workflow. If task and flag both present, the flag wins; if neither present, default to `ship-feature`.
- AC4: `bin/lib/runner.py`'s gate logic reads each workflow's `gate-rules` block — specifically when human approval is required vs auto-approved (e.g., `fast-track` auto-approves at fan-out 1 + verifier-passed; `ship-feature` requires human at every gate by default).
- AC5: `tasks/TEMPLATE.md` includes the `workflow:` field with a comment listing the nine valid values.
- AC6: `docs/` gets a new `15-workflows.md` (or extends `08-the-journey.md`) explaining the taxonomy with one section per workflow.
- AC7: Tests in `tests/bin/test_runner.py` cover: workflow resolution (base + local overlay), unknown-workflow rejection, dispatch order matches frontmatter, `--workflow` flag override.

## Context
- Source: human strategic ask after journey 2 — "we could have the medium team — planner — implementer and verifier / and then the super fast track — plan — implement (or even do all by one agent)" — plus the broader observation that scaffolding, docs, and strategic-planning work shapes don't fit the five-role mold cleanly.
- Path-2 sketch in journey 2's reflection captured the nine workflows; this task graduates that sketch to real files + dispatch.
- Hard depends on task-009 (real `dispatch_claude_code`). Without a real Claude subprocess, workflow dispatch can't be exercised end-to-end in a verifier worktree. Soft depends on task-018 (stats emission) — `estimate-task` workflow is half-implemented without it but can ship its bundle/plan flow.

## Workflow proposals (pre-Planner — to be refined in the Plan section)

| Workflow | Roles | When | Skipped vs ship-feature | Auto-approve when |
|---|---|---|---|---|
| `ship-feature` | L → P → I → V → J | Default; non-trivial code | (baseline) | never (always-human-gate) |
| `fix-bug` | L → P → I → V → J | Bug fixes | (same roles, Verdict requires regression test) | never |
| `scaffold-project` | L (audit) → P (architect) → I → V (smoke) | Onboarding consumer repo | No follow-up auto-spawn | never (gate on conventions.md) |
| `scaffold-docs` | L (index) → I → V (link-check) | Pure docs | Skip P + J | fan-out 1 + audit-docs clean |
| `strategic-audit` | L (deep index) → P (writes roadmap, spawns sub-tasks) | Plan-the-backlog | Skip I/V/J | never (output is human-reviewed task list) |
| `prepare-task` | L → P | Pre-stage | Halt after plan-approved | n/a (halts before gate) |
| `estimate-task` | L → P (estimate skill) | Cost forecast | No code | always (output is JSON estimate) |
| `fast-track` | I (or P→I) | `trivial: true` | Skip L, V, J | fan-out 1 + verifier-passed-on-similar (stats lookup) |
| `medium-track` | P → I → V | Pre-bundled context, single plausible shape | Skip L, J | fan-out 1 + verifier-passed |

## Plan

### Approach

Codify the three empirically validated workflows (`fast-track`, `medium-track`,
`ship-feature`) as fully-fleshed `base/workflows/*.md` files whose bodies
follow the recommendations in retrospectives 020 and 021. Ship six additional
workflow files for the names enumerated in AC1 — `fix-bug` already exists and
is audited as adequate; the other five (`scaffold-project`, `scaffold-docs`,
`strategic-audit`, `prepare-task`, `estimate-task`) ship as **stubs** with
minimal frontmatter and a "TBD — empirically validate before formalizing"
body. Add a small new module `bin/lib/workflow_schema.py` (mirroring
`task_schema.py`) to parse and validate workflow files; wire the runner to
read `workflow:` from the task and dispatch by the declared role list; add a
`--workflow` flag to `bin/agent run` that overrides the task field. Update
`docs/05-workflows.md` in place rather than creating `docs/15-workflows.md`
(the `15-` slot is already taken by `15-framework-agnostic.md`).

### Decomposition

Single task — one Implementer.

### ADR

Wrote `memory/decisions/0003-workflow-taxonomy-and-gate-rules.md` documenting
the frontmatter schema (additive over existing fields), the closed-set
predicate language for `gate-rules` / `auto-approve-when`, the choice to put
validation in a new `bin/lib/workflow_schema.py`, and the
flag-overrides-task-overrides-default resolution order. Referenced from the
file-level changes below.

### File-level changes

#### Files to create — fully-fleshed workflow files (2 new, 1 audited)

- **`base/workflows/fast-track.md`** (new)
  - Purpose: Workflow shape for trivial fixes — Implementer alone, single
    human gate, no bundle, no verifier worktree. Empirically validated by
    journey 3 (task-020).
  - Frontmatter fields (in order): `workflow: fast-track`,
    `version: 1.0.0`, `applicable-task-types: [bug, refactor]`,
    `default-fan-out: 1`, `default-retry-budget: 1`, `peer-reviewers: 0`,
    `stability: experimental`, `roles: [implementer]`,
    `entry-criteria` (bullets: `trivial: true` OR (`type: bug` AND
    `fan-out: 1` AND no `needs-architect: true`)), `exit-criteria`
    (bullets: regression tests pass, single Implementer writeup present),
    `skipped-artifacts: [bundle, plan, verdict, evidence-files,
    verifier-worktree, adrs]`,
    `auto-approve-when: never` (always single human gate at end),
    `gate-rules: {implementer: human}`, `human-gates: [end-of-implementer]`.
  - Body: copy the bulleted recommendations from
    `tasks/done/020-fast-track-retrospective.md` § "Recommendations for
    fast-track workflow file (input to task-019)" — verbatim with light
    editing into the standard six body sections (Trigger, Role sequence,
    Hand-off contracts, Escalation rules, Auto-spawned follow-ups,
    Variants).
  - Key decisions per ADR 0003: roles is a single-element list; gate-rules
    has one entry; auto-approve-when is `never`.

- **`base/workflows/medium-track.md`** (new)
  - Purpose: Workflow shape for non-trivial single-attempt work where the
    task body lists files explicitly — Planner → Implementer → Verifier;
    no Librarian, no Judge. Empirically validated by journey 4
    (task-021).
  - Frontmatter fields: `workflow: medium-track`, `version: 1.0.0`,
    `applicable-task-types: [feature, refactor, bug]`,
    `default-fan-out: 1`, `default-retry-budget: 2`, `peer-reviewers: 0`,
    `stability: experimental`,
    `roles: [planner, implementer, verifier]`,
    `entry-criteria` (bullets: `needs-architect: true` AND `fan-out: 1`
    AND files-to-touch enumerable from task body),
    `exit-criteria` (bullets: plan + optional ADR + attempt-A writeup +
    patch + verifier report present, regression tests pass),
    `skipped-artifacts: [bundle, verdict]`,
    `auto-approve-when: fan-out-1 AND verifier-passed`,
    `gate-rules: {planner: human, implementer: auto, verifier: human}`,
    `human-gates: [end-of-planner, end-of-verifier]`.
  - Body: copy the bulleted recommendations from
    `tasks/done/021-medium-track-retrospective.md` § "Recommendations for
    medium-track workflow file (input to task-019)" — verbatim with light
    editing into the standard six body sections.
  - Key decisions per ADR 0003: three-element roles list; gate-rules
    halts after Planner and Verifier; Implementer gate is auto (its
    output flows to Verifier without human review — the Verifier IS the
    human's proxy).

- **`base/workflows/ship-feature.md`** (audit, then modify)
  - Current state: exists with frontmatter listing `workflow, version,
    applicable-task-types, default-fan-out, human-gates,
    default-retry-budget, peer-reviewers, stability,
    auto-spawn-follow-ups`. **Missing** the new task-019 fields: `roles`,
    `entry-criteria`, `exit-criteria`, `skipped-artifacts`,
    `auto-approve-when`, `gate-rules`.
  - Modification: add the six new frontmatter fields **after the existing
    block** so the diff is additive:
    - `roles: [librarian, planner, implementer, verifier, judge]`
    - `entry-criteria: ["task type: feature", "no faster workflow
      applies"]`
    - `exit-criteria: ["all ACs pass per Verifier and Judge", "verdict.md
      written", "task moved to done/"]`
    - `skipped-artifacts: []`
    - `auto-approve-when: never`
    - `gate-rules: {librarian: auto, planner: human, implementer: auto,
      verifier: auto, judge: human}` (matches the existing `human-gates:
      [end-of-planner, end-of-judge]`).
  - Body: no change. The existing body (Trigger, Role sequence, Hand-off
    contracts, Escalation rules, Auto-spawned follow-ups, Variants,
    Defaults summary) is already complete and journey-validated.

#### Files to create — stub workflow files (5 new; `fix-bug.md` already exists)

For each of these five workflows, create a minimal file with: frontmatter
declaring `workflow: <name>`, `version: 0.1.0` (pre-1.0 to flag stub
status), `stability: experimental`, the `roles` list per the task's
"Workflow proposals" table, `applicable-task-types`, and a body of
**exactly one section**:

```markdown
## Status

**STUB.** This workflow is named in the v1 taxonomy but has not yet been
empirically validated through a journey. Before using it, run one task end-to-end
with this shape, write a retrospective in `tasks/done/<id>-<name>-retrospective.md`,
and flesh out the body to match the standard six-section format (Trigger,
Role sequence, Hand-off contracts, Escalation rules, Auto-spawned follow-ups,
Variants).

Proposed role sequence per task-019 Workflow proposals table: <copy the
relevant cell>.

Proposed "when to use": <copy the relevant cell>.

Proposed "skipped vs ship-feature": <copy the relevant cell>.
```

The Implementer fills in the `<copy>` placeholders from task-019's table.
Frontmatter `gate-rules` and `auto-approve-when` are set to safe defaults:
`gate-rules: {<each role>: human}`, `auto-approve-when: never`.

The five stub files:

- **`base/workflows/scaffold-project.md`** — roles
  `[librarian, planner, implementer, verifier]`; applicable-task-types
  `[feature]`; for onboarding consumer repos. Skipped: judge,
  auto-spawn-follow-ups.
- **`base/workflows/scaffold-docs.md`** — roles
  `[librarian, implementer, verifier]`; applicable-task-types
  `[refactor, feature]`; for pure documentation work. Skipped: planner,
  judge.
- **`base/workflows/strategic-audit.md`** — roles `[librarian, planner]`;
  applicable-task-types `[audit, research]`; for "plan the backlog"
  work. Output is sub-tasks, not code.
- **`base/workflows/prepare-task.md`** — roles `[librarian, planner]`;
  applicable-task-types `[feature, bug, refactor]`; pre-stages a task
  by halting after `plan-approved`. No `implementer` runs.
- **`base/workflows/estimate-task.md`** — roles `[librarian, planner]`;
  applicable-task-types `[feature, bug, refactor]`; for cost forecast.
  Output is a JSON estimate, not a code change.

#### Files to audit — already present

- **`base/workflows/fix-bug.md`** (exists; audit-only)
  - Audit verdict: the existing file is consistent with AC1's
    proposal-table description (roles L→P→I→V→J, retry-budget 1,
    regression-test follow-up). It does **not** declare the new task-019
    frontmatter fields (`roles, entry-criteria, exit-criteria,
    skipped-artifacts, auto-approve-when, gate-rules`).
  - Modification: add the same six new frontmatter fields, additively:
    - `roles: [librarian, planner, implementer, verifier, judge]`
    - `entry-criteria: ["task type: bug"]`
    - `exit-criteria: ["bug no longer reproduces", "regression test added"]`
    - `skipped-artifacts: []` (when not trivial) or note the trivial-skip
      contract in the body
    - `auto-approve-when: all-ac-pass AND fan-out-1` (bug verdicts often
      qualify for auto-approve since AC is "bug doesn't reproduce")
    - `gate-rules: {librarian: auto, planner: auto-when:trivial,
      implementer: auto, verifier: auto, judge: human}`
  - Body: no change.

#### Files to create — new validation module

- **`bin/lib/workflow_schema.py`** (new)
  - Purpose: Pure-function module mirroring `bin/lib/task_schema.py`.
    Parses workflow markdown files, validates frontmatter schema,
    evaluates gate-rule predicates.
  - Header comment (`@purpose`, `@why`, `@role`, `@exports`, `@uses`,
    `@stability: experimental`, `@gotchas`) per local Python conventions.
  - Exports:
    - `@dataclass WorkflowSpec` with fields matching the v1 schema:
      `name: str`, `version: str`, `roles: list[str]`,
      `applicable_task_types: list[str]`, `default_fan_out: int`,
      `human_gates: list[str]`, `default_retry_budget: int`,
      `peer_reviewers: int`, `stability: str`,
      `auto_spawn_follow_ups: list[dict]`, `entry_criteria: list[str]`,
      `exit_criteria: list[str]`, `skipped_artifacts: list[str]`,
      `auto_approve_when: str`, `gate_rules: dict[str, str]`,
      `body: str`.
    - `VALID_PREDICATE_ATOMS: frozenset[str] = {"fan-out-1",
      "verifier-passed", "trivial", "all-ac-pass", "no-new-adr",
      "single-attempt"}` — closed set per ADR 0003.
    - `VALID_GATE_MODES: frozenset[str] = {"human", "auto"}` plus the
      `auto-when:<predicate>` prefix form.
    - `parse_workflow_file(path: Path) -> WorkflowSpec` — splits
      frontmatter from body via the same `_strip_frontmatter` pattern
      used in `runner.py`; YAML-loads frontmatter; constructs the
      dataclass with safe defaults for missing optional fields.
    - `validate_workflow_spec(spec: WorkflowSpec) -> list[str]` — returns
      list of error strings; empty means valid. Checks: `name` matches
      regex `^[a-z][a-z0-9-]*$`; every entry in `roles` is non-empty;
      `gate_rules` keys are a subset of `roles`; every `gate_rules` value
      parses as a valid gate mode; `auto_approve_when` parses as
      `never` or a predicate; `default_fan_out >= 1`.
    - `parse_predicate(s: str) -> list[str]` — splits on ` AND ` and
      returns atom list; raises ValueError on unknown atoms.
    - `evaluate_predicate(predicate: str, context: dict) -> bool` — takes
      a context dict (keys: `fan_out: int`, `verifier_passed: bool`,
      `trivial: bool`, etc.) and evaluates the predicate.
  - Key decisions per ADR 0003: closed-set predicate atoms, AND-only
    composition in v1, gate-rules keys must be subset of roles.
  - Header `@gotchas`: VALID_PREDICATE_ATOMS must stay in lock-step with
    ADR 0003 § 2. If you change one, change the other.

#### Files to modify — wire the runner

- **`bin/lib/runner.py`**
  - Change 1: extend `RunSpec` (currently lines 31-41) to add
    `workflow_name: str | None = None`. The runner consults this field
    to know which workflow file to load.
  - Change 2: new function `load_workflow(spec: RunSpec, manifest:
    Manifest) -> WorkflowSpec`. Reads the workflow name from the
    spec (or task frontmatter, or defaults to `ship-feature`), resolves
    via `resolve(spec.repo_root, "workflows", name, manifest)`,
    parses + validates via `workflow_schema.parse_workflow_file` and
    `validate_workflow_spec`. Raises `ValueError(f"Unknown workflow:
    {name}. Available: {list_available(...)}")` if the resolver returns
    None or validation fails.
  - Change 3: new function `read_workflow_from_task(repo_root: Path,
    task_id: str, manifest: Manifest) -> str | None`. Reads the task
    file frontmatter, returns the `workflow:` value if present, else
    None. Uses `task_schema.parse_frontmatter` for consistency.
  - Change 4: new function `resolve_workflow_name(spec: RunSpec,
    manifest: Manifest) -> str`. Resolution order per ADR 0003:
    `spec.workflow_name` → task frontmatter `workflow:` → default
    `"ship-feature"`.
  - Change 5: a new orchestration helper `dispatch_roles(spec: RunSpec,
    workflow: WorkflowSpec, manifest: Manifest) -> int` that iterates
    `workflow.roles` in order. For each role: compose system prompt,
    dispatch, then consult `workflow.gate_rules[role]` to decide
    `human` halt vs `auto` continue vs `auto-when:<predicate>` evaluate.
    For Phase 0 (per the runner placeholder note), this can be a stub
    that prints "would dispatch <role> with gate <mode>" and returns 0
    — but the wiring + ValueError-on-unknown must be real and tested.
    The actual subprocess dispatch is gated on task-009.
  - Note: per F028, callers of `select_inputs` must pass
    `layout=manifest.tasks_layout` explicitly. `dispatch_roles` should
    follow this convention.
  - Specific lines: insert new functions after `seed_worktree_inputs`
    (currently ends line 153) and before `close_journey`. Extend
    `RunSpec` dataclass at lines 31-41.

- **`bin/agent`**
  - Change 1: add a new argparse argument to `p_run` (currently lines
    78-90): `p_run.add_argument("--workflow", help="Workflow name
    override; defaults to task's 'workflow:' field or 'ship-feature'.")`
  - Change 2: in `cmd_run` (lines 22-69), pass
    `workflow_name=args.workflow` into the `RunSpec(...)` constructor
    (lines 47-54).
  - Change 3: after the existing `role_path` lookup and before
    composing the prompt, call `resolve_workflow_name(spec, manifest)`
    and `load_workflow(spec, manifest)` to fail fast on unknown
    workflow names. Print the resolved workflow to stderr for operator
    visibility.

- **`tasks/TEMPLATE.md`**
  - The frontmatter already has `workflow: ship-feature` at line 19.
    Modification: change to
    `workflow: ship-feature  # one of: ship-feature, fix-bug,
    fast-track, medium-track, scaffold-project, scaffold-docs,
    strategic-audit, prepare-task, estimate-task` (kept on one line
    or split with YAML-comment-friendly formatting).

- **`docs/05-workflows.md`**
  - **Decision: extend `05-workflows.md` in place, do NOT create
    `docs/15-workflows.md`.** Rationale: the `15-` slot is already
    occupied by `15-framework-agnostic.md`. AC6 names `15-workflows.md`
    as a candidate but the doc number sequence is meaningful; adding
    a doc out-of-sequence disrupts the index. The current
    `05-workflows.md` already lists four workflows (ship-feature,
    fix-bug, refactor, audit-repo); extending it to nine + the new
    fields is in-scope for that doc's existing structure.
  - Modification 1: in the "Frontmatter" subsection (currently
    lines 24-52), add the six new fields (`roles`, `entry-criteria`,
    `exit-criteria`, `skipped-artifacts`, `auto-approve-when`,
    `gate-rules`) to the example block and to the field reference
    list. Reference ADR 0003.
  - Modification 2: rename the heading "The four default workflows"
    (line 64) to "The nine default workflows" and add subsections
    for the new five fleshed/stubbed workflows: `fast-track`,
    `medium-track`, `scaffold-project`, `scaffold-docs`,
    `strategic-audit`, `prepare-task`, `estimate-task`. Each
    subsection has the frontmatter block + a 2-4-sentence body
    pointing at the workflow file and (for stubs) noting "not yet
    empirically validated."
  - Modification 3: in the existing `refactor` section, keep it as-is
    but note that `refactor`-classified tasks may also use
    `medium-track` when scope is small. (The user's task body lists
    nine workflows; `refactor` is the existing tenth that
    `05-workflows.md` covers but task-019 doesn't enumerate. Leave
    it; it's still a valid workflow.)
  - Modification 4: new subsection "Gate rules and predicates"
    describing the closed-set predicate language; reference ADR 0003.

- **`tests/bin/test_runner.py`**
  - Add new test class / section (after the existing
    `test_close_journey_*` block) covering AC7's four scenarios:
    1. `test_load_workflow_resolves_base_path` — given a workflow
       file at `base/workflows/medium-track.md`, `load_workflow`
       returns a valid `WorkflowSpec` with `roles =
       ["planner", "implementer", "verifier"]`.
    2. `test_load_workflow_prefers_local_overlay` — when both
       `base/workflows/fast-track.md` and
       `.agents/local/workflows/fast-track.md` exist, `resolve`
       returns the local path (verified via the existing `resolve`
       contract); `load_workflow` then loads from there.
    3. `test_load_workflow_rejects_unknown_name` — for a workflow
       name with no matching file, `load_workflow` raises
       `ValueError` with the available names in the message.
    4. `test_resolve_workflow_name_precedence` — `--workflow` flag
       (passed via `spec.workflow_name`) wins over task frontmatter
       `workflow:`, which wins over default `ship-feature`.
    5. `test_workflow_dispatch_order_matches_frontmatter` — given a
       workflow with `roles: [a, b, c]`, the runner's dispatch_roles
       attempts each role in that order (verified by mocking the
       dispatch call and asserting call order).
  - Helper changes: extend `_make_manifest` if needed, or add a new
    `_setup_workflow_file` helper that writes a minimal valid
    workflow markdown to a given path.
  - Add a sibling test file `tests/bin/test_workflow_schema.py`
    covering: parse_workflow_file roundtrip, validate_workflow_spec
    catches missing required fields, parse_predicate rejects unknown
    atoms, evaluate_predicate handles AND composition,
    gate-rules-keys-subset-of-roles validation.

### Risks and escalations

- **Risk: predicate atoms grow uncontrolled.** Each new atom is runner
  code. Mitigation: ADR 0003 § 2 documents the six atoms in v1 and the
  policy ("encode combinations as new named atoms, not new operators").
  Verifier should flag any added atom not listed in ADR 0003.
- **Risk: ship-feature.md frontmatter change is a "version" bump per
  semver rules.** Adding required fields to a workflow file is arguably
  a major-version change. Mitigation: bump `version: 1.0.0 → 1.1.0`
  (additive — old consumers that ignore new fields still work; the
  fields have safe defaults). Document in `docs/05-workflows.md`
  modification 2.
- **Risk: stub workflows give the false impression they're usable.**
  Mitigation: each stub's body opens with "STUB. This workflow is named
  in the v1 taxonomy but has not yet been empirically validated through
  a journey." and stability is `experimental`. The Implementer must
  preserve this language verbatim.
- **Risk: `--workflow` flag override silently hides task-frontmatter
  bugs.** If an operator passes `--workflow fast-track` on a task
  declaring `workflow: ship-feature`, they may not notice the
  mismatch. Mitigation: print the resolved workflow name (and which
  source it came from — flag, task, or default) to stderr at dispatch
  time. Implementer must surface this.
- **Risk: F028 default-layout silent-mis-route.** The retro for journey
  4 flagged that `select_inputs` defaults to `legacy-four-folder`
  without manifest. Any new callsite added in `dispatch_roles` must
  pass `layout=manifest.tasks_layout` explicitly. Verifier should grep
  for any new `select_inputs` call and confirm.
- **Risk: gate-rules role keys diverge from roles list across
  workflow files.** Mitigation: `validate_workflow_spec` rejects this
  at load time; tested in `test_workflow_schema.py`.
- (none requiring human escalation)

### Acceptance criteria mapping

- **AC1** (nine workflow files exist with required frontmatter and body) →
  covered by the three fleshed files (`fast-track.md`, `medium-track.md`,
  modifications to `ship-feature.md`), the five stub files
  (`scaffold-project.md`, `scaffold-docs.md`, `strategic-audit.md`,
  `prepare-task.md`, `estimate-task.md`), and modifications to the
  existing `fix-bug.md`. All nine files declare the new frontmatter
  schema (per ADR 0003 § 1).
- **AC2** (runner reads task's `workflow:`, loads via
  `bin/lib/resolution.py`, dispatches in declared order; unknown raises
  `ValueError`) → covered by `bin/lib/runner.py` changes 2-5
  (`load_workflow`, `read_workflow_from_task`, `resolve_workflow_name`,
  `dispatch_roles`) plus the new `bin/lib/workflow_schema.py` parser.
  `resolve()` in `bin/lib/resolution.py` already handles the
  `workflows` category (it's category-generic); confirmed by reading
  the resolver — no change needed there.
- **AC3** (`bin/agent run --workflow <name>` overrides task field;
  defaults to `ship-feature`) → covered by `bin/agent` changes 1-3 +
  runner's `resolve_workflow_name`.
- **AC4** (gate logic reads `gate-rules`; auto-approve per workflow
  rule) → covered by `dispatch_roles` in `bin/lib/runner.py` (change 5)
  plus `evaluate_predicate` in `workflow_schema.py`. Per-workflow
  values come from the frontmatter `gate-rules` block.
- **AC5** (`tasks/TEMPLATE.md` includes `workflow:` with valid-values
  comment) → covered by the `tasks/TEMPLATE.md` modification.
- **AC6** (`docs/` updated with workflow taxonomy) → covered by the
  `docs/05-workflows.md` modifications (extending in place rather than
  creating `15-workflows.md` since that slot is taken).
- **AC7** (tests cover resolution, base/local overlay, unknown
  rejection, dispatch order, flag override) → covered by the five new
  tests added to `tests/bin/test_runner.py` plus the new
  `tests/bin/test_workflow_schema.py` file.

### Recommended fan-out

1 — mechanical work: file creation + small runner additions + tests.
Fan-out > 1 would diverge on the workflow file bodies (each Implementer
would re-interpret the retrospective recommendations differently) without
materially improving the result. ADR 0003 pre-resolves the architectural
calls.

### Confidence level

high — empirical inputs (retros 020, 021) directly dictate the bodies of
the two new fleshed workflow files; ADR 0003 closes the four
architectural questions; the runner wiring follows the same pattern as
the existing `resolve(repo_root, "roles", ...)` lookup. Weakest AC is
**AC4** (gate-rule predicate evaluation) because predicate context
extraction touches journey state not fully formalised; mitigated by
keeping the v1 atom set tiny and tested in isolation. Strongest ACs are
**AC1, AC5, AC6** (file authoring with retrospective inputs already
written) and **AC3** (a 4-line argparse change plus precedence ordering).

## Verdict
<!-- Filled in by the Judge/Librarian at close -->
