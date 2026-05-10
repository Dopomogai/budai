# 05 — Workflows

A **workflow** is a named multi-role procedure that orchestrates a task end to end. Workflows are how budai answers the question: "for a task of type X, which roles run in what order, with what hand-offs, and what gates?"

## What a workflow is, what it isn't

Distinct from neighboring concepts:

- **Skill** — a procedure inside a single role's invocation. Workflows orchestrate roles; roles invoke skills.
- **Task** — a unit of work. A workflow processes a task; the task itself is the input.
- **Role** — an agent type. A workflow specifies which roles are involved; the roles do the work.

A workflow is NOT:

- A CI pipeline. CI runs after the integrating commit; budai workflows produce the integrating commit.
- A state machine the runner enforces. Workflows are descriptive — the runner reads them and dispatches accordingly. There's no separate state machine to debug.
- A project-management replacement. Tracking, prioritization, and planning across many tasks live wherever your team already does PM work.

## Workflow file format

A workflow is a markdown file with YAML frontmatter and a body. Lives at `base/workflows/<name>.md` (canonical) or `local/workflows/<name>.md` (repo-specific override or extension).

### Frontmatter

```yaml
---
workflow: ship-feature
version: 1.1.0
applicable-task-types: [feature]
default-fan-out: 1
human-gates: [end-of-planner, end-of-judge]
default-retry-budget: 2
peer-reviewers: 0                # default 0; set N>0 to add explicit Reviewer roles before Judge
stability: stable
auto-spawn-follow-ups:
  - condition: always
    template: test-coverage-<id>
roles: [librarian, planner, implementer, verifier, judge]
entry-criteria:
  - "task type: feature"
  - "no faster workflow applies"
exit-criteria:
  - all ACs pass per Verifier and Judge
  - verdict.md written
  - task moved to done/
skipped-artifacts: []
auto-approve-when: never
gate-rules:
  librarian: auto
  planner: human
  implementer: auto
  verifier: auto
  judge: human
---
```

Field reference:

- **workflow** — name, kebab-case. Must match the filename.
- **version** — semver. Same rules as skills (`04-skills.md`).
- **applicable-task-types** — task `type:` values that route through this workflow. A task with no matching workflow falls back to `ship-feature`.
- **default-fan-out** — how many parallel implementer attempts when the task doesn't override.
- **human-gates** — pause points where a human must approve before proceeding. Default two: `end-of-planner` and `end-of-judge`.
- **default-retry-budget** — how many times a role can re-attempt before escalating.
- **peer-reviewers** — number of Reviewer instances run before the Judge. 0 means the Judge alone reviews; N>0 adds explicit anonymized peer review.
- **stability** — same semantics as skills.
- **auto-spawn-follow-ups** — list of templates for tasks the workflow opens after success. Conditions: `always`, `findings-above-threshold`, `tests-missing`, etc.
- **roles** — ordered list of role names. The runner dispatches these roles in declared order. Replaces the implicit five-role chain assumption.
- **entry-criteria** — bulleted predicates (free-text) describing when this workflow is appropriate. Advisory for the human or future router heuristic; not machine-parsed.
- **exit-criteria** — bulleted predicates for what "done" looks like for this workflow. Advisory.
- **skipped-artifacts** — list of artifact names (e.g., `bundle`, `verdict`, `evidence-files`, `adrs`) that this workflow does not produce and should not be expected by downstream roles.
- **auto-approve-when** — top-level rule for whether the workflow ever auto-approves. Either `never` or a predicate expression (see "Gate rules and predicates" below). When `never`, every gate declared in `human-gates` requires human approval.
- **gate-rules** — map of role-name → gate-mode. Each entry: `human`, `auto`, or `auto-when:<predicate>`. The runner consults this after each role finishes to decide whether to halt for human approval or auto-proceed. See ADR 0003 for the predicate language definition. When `gate-rules` and `human-gates` conflict, `gate-rules` wins (it is more specific).

### Body sections

Required, in order:

1. **Trigger.** What signals the workflow should run. Usually: a task lands in `tasks/open/` with a matching `type:`.
2. **Role sequence.** The ordered list of role invocations. Each entry: role name, what it reads, what it writes, what it hands off.
3. **Hand-off contracts.** What the output of role N must look like for role N+1 to consume it. Format checks at the boundary.
4. **Escalation rules.** What conditions escalate to which role. Retry budgets per role.
5. **Auto-spawned follow-ups.** What additional tasks the workflow opens after success.
6. **Variants.** How this workflow differs from related workflows. Cross-references.

## The nine default workflows

### `ship-feature`

The canonical full lifecycle. The 12 steps in `08-the-journey.md` are the body of `ship-feature`. That doc is authoritative; this section only summarizes.

Roles: `[librarian, planner, implementer, verifier, judge]`. Human gates: end-of-planner, end-of-judge. See `base/workflows/ship-feature.md` for full frontmatter.

Use this for any task creating new product capability.

### `fix-bug`

Faster path for defects. Key differences from `ship-feature`:

- **Planner skipped if `trivial: true`.** Bug description doubles as plan. Implementer goes straight to coding.
- **Single Implementer typical.** `default-fan-out: 1`. Bugs usually have one right answer; fan-out doesn't add value.
- **Mandatory regression test in follow-ups.** The auto-spawned follow-up is a regression-test task — different from the `test-coverage` follow-up of `ship-feature` because regression tests target the specific failure mode of the bug, not general test coverage.
- **Tighter retry budget.** `default-retry-budget: 1`. If a fix doesn't work after one retry, it's a more complex investigation; escalate to Planner.
- **One human gate.** End-of-Planner is skipped when trivial; end-of-Judge stays.
- **Auto-approve-when:** `all-ac-pass AND fan-out-1`. Bug fixes often qualify for auto-approve since the AC is "the bug doesn't reproduce" and that's mechanically verifiable.

Roles: `[librarian, planner, implementer, verifier, judge]`. See `base/workflows/fix-bug.md` for full frontmatter.

### `fast-track`

Single-Implementer workflow for trivial fixes. Empirically validated by journey 3 (task-020).

- **One role.** Implementer alone; no bundle, no Verifier worktree, no ADRs.
- **Single human gate.** Human reviews the diff directly after the Implementer submits.
- **Skipped artifacts:** bundle, plan, verdict, evidence-files, verifier-worktree, adrs.
- **Auto-approve-when:** never (always human gate at end).

Roles: `[implementer]`. See `base/workflows/fast-track.md` for full frontmatter and entry criteria.

**Not appropriate for:** tasks with multiple plausible architectural shapes, tasks touching >10 files, tasks with `needs-architect: true`, tasks where AC list is fuzzy.

### `medium-track`

Three-role workflow for non-trivial single-attempt work. Empirically validated by journey 4 (task-021). The middle path between fast-track and ship-feature.

- **Three roles.** Planner → Implementer → Verifier; no Librarian, no Judge.
- **Two human gates.** End-of-Planner (review plan + ADR), end-of-Verifier (review evidence).
- **Implementer gate is auto.** Implementer output flows straight to Verifier. At fan-out 1, the Verifier IS the human's proxy for code quality.
- **Skipped artifacts:** bundle (no Librarian), verdict (no Judge — Verifier's report is final).
- **Auto-approve-when:** `fan-out-1 AND verifier-passed`.

Roles: `[planner, implementer, verifier]`. See `base/workflows/medium-track.md` for full frontmatter and entry criteria.

**Refactor-classified tasks** may use `medium-track` when scope is small (≤7 files, one clear decision to make, no fan-out needed).

### `scaffold-project`

For onboarding a consumer repo to budai. **Not yet empirically validated.** See `base/workflows/scaffold-project.md`.

Roles: `[librarian, planner, implementer, verifier]`. Applicable task types: `[feature]`. Stability: experimental (stub).

### `scaffold-docs`

For pure documentation work with no code changes. **Not yet empirically validated.** See `base/workflows/scaffold-docs.md`.

Roles: `[librarian, implementer, verifier]`. Applicable task types: `[refactor, feature]`. Stability: experimental (stub). Skips Planner and Judge.

### `strategic-audit`

For "plan the backlog" work where the output is a human-reviewed task list, not code. **Not yet empirically validated.** See `base/workflows/strategic-audit.md`.

Roles: `[librarian, planner]`. Applicable task types: `[audit, research]`. Stability: experimental (stub). Skips Implementer, Verifier, and Judge entirely.

### `prepare-task`

Pre-stages a task by running Librarian + Planner and halting after plan-approved. No Implementer runs. Use when you want to queue a well-scoped task for later dispatch. **Not yet empirically validated.** See `base/workflows/prepare-task.md`.

Roles: `[librarian, planner]`. Applicable task types: `[feature, bug, refactor]`. Stability: experimental (stub).

### `estimate-task`

For cost forecasting before committing to a task. Output is a JSON estimate (tokens, wall-time, human-gates, confidence), not code. **Not yet empirically validated.** See `base/workflows/estimate-task.md`.

Roles: `[librarian, planner]`. Applicable task types: `[feature, bug, refactor]`. Stability: experimental (stub).

### `refactor`

For changes that don't add capability but reshape existing code. Key differences from `ship-feature`:

- **Mandatory Planner.** No skip. Refactors without architecture review become reverse-engineering puzzles for future readers.
- **Mandatory ADR if scope > one file.** The Planner writes a `memory/decisions/<NNNN>-<slug>.md` for any cross-file refactor. Single-file refactors don't need an ADR.
- **No fan-out.** `default-fan-out: 1`. Multiple parallel attempts at the same refactor diverge unproductively. One deep attempt instead.
- **Multiple peer reviewers.** Where `ship-feature` runs only the Judge, `refactor` defaults to 2 explicit Reviewer instances reviewing independently before the Judge synthesizes. Reviewer disagreement escalates to human.
- **Heavier post-integration sweep.** Refactors usually break docs; `audit-docs` runs with stricter thresholds.

```yaml
workflow: refactor
version: 1.0.0
applicable-task-types: [refactor]
default-fan-out: 1
human-gates: [end-of-planner, end-of-judge]
default-retry-budget: 2
peer-reviewers: 2
mandatory-adr-threshold: 2-files
```

Note: for small-scope refactors (≤7 files, one architectural decision), `medium-track` is often more appropriate than `refactor`.

### `audit-repo`

For periodic health checks of the repo. Key differences:

- **No Implementer.** Auditor + Librarian only. The output is a report, not a code change.
- **No Judge.** No attempt to integrate; nothing to integrate.
- **One human gate, at the end.** The human reviews findings.
- **Findings can spawn follow-up tasks.** High-severity findings auto-spawn `address-finding-<id>` tasks for the regular `fix-bug` or `refactor` workflows.

```yaml
workflow: audit-repo
version: 1.0.0
applicable-task-types: [audit]
default-fan-out: 1
human-gates: [end-of-audit]
default-retry-budget: 0
peer-reviewers: 0
auto-spawn-follow-ups:
  - condition: findings-above-threshold
    template: address-finding-<id>
```

Note: the Auditor is a Librarian variant invoked through this workflow's role definition, not a separate role file in the default five. If audit work grows in scope, splitting Auditor out of Librarian is a future option.

## Gate rules and predicates

The `gate-rules` field maps each role to a gate mode:

- **`human`** — pause and require human approval before proceeding to the next role.
- **`auto`** — automatically proceed to the next role without human approval.
- **`auto-when:<predicate>`** — evaluate the predicate against the current journey state; if true, auto-proceed; otherwise, halt for human approval.

The `auto-approve-when` field is the workflow-wide default rule. `gate-rules` provides per-role overrides. When both apply, `gate-rules` wins (it is more specific).

### Auto-flip runtime behavior

After each role finishes, the runner reads the gate-rule for that role and calls `bin/lib/transitions.flip_for_role`. For `auto` gates it atomically updates `status:` (and any implied booleans such as `plan-approved` or `result-approved`) via `transitions.apply_transition`, then continues dispatching the next role. For `human` gates it prints a single-line halt message with the manual command (`python3 bin/task move <id> <new-status>`) and stops the loop — no subsequent roles run until the human flips the status. For `auto-when:<predicate>` gates it evaluates the predicate against the current journey state (fan-out, verifier evidence, ADR count, etc.) and auto-flips on True or halts on False. Every decision is appended to `.agents/runs/<run-id>/transitions.json` for audit. Fail-closed semantics apply: any missing predicate-context source counts as False and halts for human approval. See `memory/decisions/0004-auto-flip-frontmatter-and-predicate-context.md` for full source-table and module-ownership rationale.

### Predicate language (v1)

Predicates are atoms or AND combinations of atoms. **No OR, no negation in v1.** The atom set is closed — adding a new predicate requires a runner code change and an ADR update. See `memory/decisions/0003-workflow-taxonomy-and-gate-rules.md` for the full specification.

**Valid atoms (v1):**

| Atom | Meaning |
|---|---|
| `fan-out-1` | Task's effective fan-out is 1 |
| `verifier-passed` | Most-recent Verifier report says all ACs pass |
| `trivial` | Task frontmatter has `trivial: true` |
| `all-ac-pass` | Judge or Verifier confirmed every AC passes |
| `no-new-adr` | No new file under `memory/decisions/` in this run |
| `single-attempt` | Only one Implementer attempt exists |

**Examples:**

```
auto-approve-when: never
auto-approve-when: fan-out-1 AND verifier-passed
gate-rules: {planner: human, implementer: auto, verifier: human}
gate-rules: {planner: auto-when:trivial, implementer: auto, judge: human}
```

If a workflow needs richer logic (e.g., trivial AND fan-out-1 AND no-new-adr), the right answer is to encode the combination as a new named atom in the ADR rather than extending the operator set. This keeps predicate evaluation simple and auditable.

## Hand-off contracts

The output of role N must conform to the input contract of role N+1. budai treats these as data formats, not as "good vibes":

- **Bundle → Planner.** The bundle's YAML frontmatter must validate against the bundle schema (`09-bundle-format.md`). If invalid, the Librarian re-runs `build-task-bundle`.
- **Plan → Router → Implementer.** The plan section appended to the task body must include the required sections (Approach, File-level changes, AC mapping, Recommended fan-out — see `10-plan-format.md`). If sections are missing, Planner re-runs with a "plan format incomplete" note.
- **Implementer attempt → Verifier.** The attempt must be a self-contained patch + writeup at `council/<task-id>/attempts/attempt-<X>.md` + `.patch`. If patch doesn't apply or writeup is missing required sections, Implementer re-runs.
- **Verifier report → Judge.** The verifier report must include AC pass/fail per criterion plus evidence pointers. If incomplete, Verifier re-runs.
- **Verdict → integrator.** The verdict must include winner attribution, rationale, outstanding concerns, follow-up task list. If incomplete, Judge re-runs.

Hand-off validation runs at the boundary, not at end of execution. A role that produces invalid output gets re-invoked with a structured error; it doesn't propagate broken output downstream.

## Escalation rules

Two kinds of escalation:

**Within-role retries.** Each role has a `retry-budget` per task (workflow-default, overridable per-task in frontmatter). Implementer fails AC → re-spawn with failure report → up to budget. After budget exhausted, attempt is marked failed and stays in council as record. Compute tier escalates one notch on retry (Sonnet → Opus).

**Across-role escalation.** Some failures escalate to a different role rather than retrying:

- Implementer hits ambiguous spec → escalate to Planner. The spec needs revision, not the implementation.
- Verifier finds AC unanswerable as written → escalate to Planner. The AC needs revision.
- Judge can't pick a winner (all attempts failed) → escalate to human. The task itself may be ill-formed.
- Librarian sweep finds doc drift it can't auto-fix → escalate to a new task in the regular workflow.

Escalations write to `messages/channels/escalations.md` so the audit trail is intact.

## Composing custom workflows

To add a workflow specific to a repo:

1. Copy a base workflow into `local/workflows/<custom-name>.md`.
2. Modify frontmatter and body as needed.
3. Add to `manifest.yaml` under `local-only.workflows`.
4. Tasks with `type:` matching the workflow's `applicable-task-types:` will route through it.

Per `02-structure.md` resolution rules: when the runner needs a workflow named `<name>`, it checks `local/workflows/` first, then `base/workflows/`. Local wins.

## Workflow vs. sub-task decomposition

A common confusion: when does a complex task become a custom workflow vs. when does it become multiple sub-tasks under the standard workflow?

**Decision rule:** if the orchestration shape changes, it's a workflow. If only the work units change, it's decomposition.

Examples:

- A feature requiring database migration + backend + frontend — same `ship-feature` workflow, three sub-tasks (`042a-migration`, `042b-backend`, `042c-frontend`). The shape is unchanged: each sub-task runs Plan → Implement → Verify → Judge.
- A research task wanting autoresearch-style overnight ratchet loops — different workflow (`research`, future), because the orchestration is "loop until budget exhausted" rather than "ship single attempt."
- A security audit wanting multiple specialized auditors in parallel and synthesis — different workflow (`security-audit`, future), because the role sequence is "fan-out audit, synthesis, human review" rather than the standard.

If unsure: try sub-tasks first. Custom workflows are heavier — you maintain them across budai upgrades.

## Workflow versioning

Workflows follow the same semver rules as skills (`04-skills.md`). Major bumps require manifest updates in consumer repos. The Librarian flags pending workflow updates in the daily sweep.

When a workflow goes major, set `breaking-changes-from:` in frontmatter pointing at the last pre-break version. Common breaking changes:

- Adding a new mandatory role to the sequence (existing tasks won't have inputs that role needs).
- Removing or renaming a hand-off contract field.
- Changing default-fan-out semantics.

Patch and minor bumps (prompt clarifications, new optional auto-spawn templates, retry-budget tweaks) flow through automatically on `librarian sync`.

## What workflows don't decide

Workflows specify role sequence, hand-off contracts, gates. They do NOT specify:

- **Which models to use.** That's the role's `model-default:` plus per-skill `tier-override:`.
- **Which conventions apply.** That's `base/conventions.md` + `local/conventions.md`.
- **Which tasks exist.** That's the task creation flow (`bin/task new`).
- **What success means.** That's per-task acceptance criteria.

This separation keeps workflows generic — one `ship-feature` works for any feature task — and keeps task-specific judgment where it belongs.

## What workflows are NOT

Restated for emphasis:

- Not a CI pipeline. CI gates the integrating commit; workflows produce it.
- Not a tool to enforce process compliance. Workflows describe what *should* happen; they don't punish deviation. The audit trail is the accountability mechanism.
- Not where you encode org policy. Org policy lives in `local/conventions.md`, `local/untouchables.md`, and the role files. A workflow that hardcodes "the CTO must approve everything" is not portable.
- Not a Turing-complete language. Workflows are role sequences with conditions on auto-spawns. If you need branching logic, that's a custom workflow's job, not the platform's.
