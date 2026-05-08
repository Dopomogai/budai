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
version: 1.2.0
applicable-task-types: [feature]
default-fan-out: 1
human-gates: [end-of-planner, end-of-judge]
default-retry-budget: 2
peer-reviewers: 0                # default 0; set N>0 to add explicit Reviewer roles before Judge
stability: stable
auto-spawn-follow-ups:
  - condition: always
    template: test-coverage-<id>
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

### Body sections

Required, in order:

1. **Trigger.** What signals the workflow should run. Usually: a task lands in `tasks/open/` with a matching `type:`.
2. **Role sequence.** The ordered list of role invocations. Each entry: role name, what it reads, what it writes, what it hands off.
3. **Hand-off contracts.** What the output of role N must look like for role N+1 to consume it. Format checks at the boundary.
4. **Escalation rules.** What conditions escalate to which role. Retry budgets per role.
5. **Auto-spawned follow-ups.** What additional tasks the workflow opens after success.
6. **Variants.** How this workflow differs from related workflows. Cross-references.

## The four default workflows

### `ship-feature`

The canonical full lifecycle. The 12 steps in `08-the-journey.md` are the body of `ship-feature`. That doc is authoritative; this section only summarizes.

Frontmatter:

```yaml
workflow: ship-feature
version: 1.2.0
applicable-task-types: [feature]
default-fan-out: 1
human-gates: [end-of-planner, end-of-judge]
default-retry-budget: 2
peer-reviewers: 0
auto-spawn-follow-ups:
  - condition: always
    template: test-coverage-<id>
```

Use this for any task creating new product capability.

### `fix-bug`

Faster path for defects. Key differences from `ship-feature`:

- **Planner skipped if `trivial: true`.** Bug description doubles as plan. Implementer goes straight to coding.
- **Single Implementer typical.** `default-fan-out: 1`. Bugs usually have one right answer; fan-out doesn't add value.
- **Mandatory regression test in follow-ups.** The auto-spawned follow-up is a regression-test task — different from the `test-coverage` follow-up of `ship-feature` because regression tests target the specific failure mode of the bug, not general test coverage.
- **Tighter retry budget.** `default-retry-budget: 1`. If a fix doesn't work after one retry, it's a more complex investigation; escalate to Planner.
- **One human gate.** End-of-Planner is skipped when trivial; end-of-Judge stays.

```yaml
workflow: fix-bug
version: 1.0.0
applicable-task-types: [bug]
default-fan-out: 1
human-gates: [end-of-judge]
default-retry-budget: 1
peer-reviewers: 0
auto-spawn-follow-ups:
  - condition: always
    template: regression-test-<id>
```

### `refactor`

For changes that don't add capability but reshape existing code. Key differences:

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
