# ADR 0003 — Workflow taxonomy v1: file shape, gate-rule predicates, validation

- Status: accepted
- Date: 2026-05-10
- Source: task-019

## Context

Through journeys 2–4 we empirically validated three workflow shapes that the
runner should be able to dispatch by name:

- `ship-feature` (J1, J2) — full five-role L→P→I→V→J.
- `fast-track` (J3, task-020 retrospective) — Implementer only, single human
  gate, no bundle, no verifier worktree.
- `medium-track` (J4, task-021 retrospective) — Planner → Implementer →
  Verifier; no Librarian, no Judge; one ADR per architectural decision.

Task-019 adds three workflow shapes to `base/workflows/` plus stubs for six
more aspirational shapes (`scaffold-project`, `scaffold-docs`,
`strategic-audit`, `prepare-task`, `estimate-task`, plus the pre-existing
`fix-bug`). The runner needs to read `workflow:` from the task and dispatch
roles accordingly.

Four coupled questions arise that future agents (and journey 5+ retros) will
need to navigate:

1. **What is a workflow file's frontmatter schema?** Today's
   `ship-feature.md` already declares one shape (`workflow, version,
   applicable-task-types, default-fan-out, human-gates,
   default-retry-budget, peer-reviewers, stability, auto-spawn-follow-ups`).
   Task-019 adds new required fields (`roles, gate-rules, entry-criteria,
   exit-criteria, skipped-artifacts, auto-approve-when`). Are these additive
   or replacing? Are the old fields still meaningful?
2. **What predicate language do `gate-rules` use?** Each role gets a gate;
   each gate is `human`, `auto`, or `auto-when:<predicate>`. The predicate
   language has to be small, closed, and parseable — every new predicate is
   new runner code.
3. **Where does workflow-file validation live?** Existing precedent:
   `bin/lib/task_schema.py` validates task frontmatter as a pure-function
   module called from `bin/task`. A sibling `bin/lib/workflow_schema.py`
   keeps the same shape for workflow files.
4. **Override semantics.** `bin/agent run --workflow <name>` should override
   the task's declared workflow. If neither present, the default is
   `ship-feature` (preserves current behaviour).

## Decision

### 1. Frontmatter schema is additive; existing fields keep their meaning

The existing fields (`workflow, version, applicable-task-types,
default-fan-out, human-gates, default-retry-budget, peer-reviewers,
stability, auto-spawn-follow-ups`) remain. Task-019 adds the following new
required fields:

- `roles` — ordered list of role names. The dispatch order. Replaces the
  implicit "five-role chain" assumption in the runner. Example:
  `[planner, implementer, verifier]`.
- `entry-criteria` — bulleted predicates (free-text markdown) describing
  when this workflow is appropriate. Not machine-parsed; advisory for the
  human (or future router heuristic).
- `exit-criteria` — bulleted predicates for what "done" looks like for this
  workflow. Advisory.
- `skipped-artifacts` — list of artifact names (e.g., `bundle`, `verdict`,
  `evidence-files`, `adrs`). Used by the runner to skip producing certain
  outputs that would otherwise be expected.
- `auto-approve-when` — top-level rule for whether the workflow ever
  auto-approves at all. Either `never` (always human-gated at every gate
  declared in `human-gates`) or a predicate (see § 2).
- `gate-rules` — map of role-name → gate-mode. Each entry: `<role>: human`
  or `<role>: auto` or `<role>: auto-when:<predicate>`. The runner consults
  this *after* each role finishes to decide whether to halt for human
  approval or auto-proceed to the next role.

The existing `human-gates` field stays as a coarse summary (which named
gates exist); `gate-rules` is the fine-grained, role-by-role decision rule.
When the two conflict, `gate-rules` wins (it's more specific).

### 2. Predicate language is a small closed set

Predicates are atoms or boolean combinations of atoms. **Atoms supported in
v1**:

- `fan-out-1` — task's effective fan-out is 1.
- `verifier-passed` — most-recent verifier report says all ACs pass.
- `trivial` — task frontmatter has `trivial: true`.
- `all-ac-pass` — Judge or Verifier confirmed every AC.
- `no-new-adr` — no new file under `memory/decisions/` in this run.
- `single-attempt` — only one Implementer attempt exists.

Combination: `<atom> AND <atom>` (comma-separated). No `OR`, no negation in
v1. If a workflow needs richer logic, the right answer is to encode the
combined predicate as a new named atom (e.g., `safe-auto-approve` = trivial
AND fan-out-1 AND no-new-adr) rather than growing the language.

Examples:

- `auto-approve-when: never` — every gate is human.
- `auto-approve-when: fan-out-1 AND verifier-passed` — auto-approve gates
  when both hold.
- `gate-rules: {planner: human, implementer: auto, verifier: human}` —
  human-gate after Planner and Verifier, but Implementer's output flows
  straight to Verifier without pause.

**Rationale for keeping it tiny.** Predicate evaluation is runner code.
Every atom is a function in `workflow_schema.py` that reads task
frontmatter or council state and returns bool. Six atoms is the minimum
viable set covering the three validated workflows plus the six aspirational
stubs. We can add atoms as journey retrospectives identify gaps.

### 3. Validation lives in a new module: `bin/lib/workflow_schema.py`

Mirrors `bin/lib/task_schema.py`. Pure functions:

- `parse_workflow_file(path: Path) -> WorkflowSpec` — reads frontmatter +
  body, returns a dataclass.
- `validate_workflow_spec(spec: WorkflowSpec) -> list[str]` — returns
  list of validation errors (empty means valid).
- `validate_gate_rules(rules: dict, roles: list[str]) -> list[str]` —
  each gate-rules key must be a role in `roles`; each value must be a
  recognized predicate.
- `evaluate_predicate(atom: str, context: dict) -> bool` — closed-set
  predicate evaluator.

The runner calls `parse_workflow_file` + `validate_workflow_spec` at load
time and raises `ValueError` on unknown workflow names or invalid specs.

### 4. Override semantics

Resolution order (first non-None wins):

1. `--workflow <name>` CLI flag on `bin/agent run`.
2. `workflow:` field in task frontmatter.
3. Default to `ship-feature`.

If `--workflow <name>` is supplied but doesn't match any workflow file
resolvable via `resolve(repo_root, "workflows", name, manifest)`, raise
`ValueError` immediately with the list of available workflow names. Same
for an unknown `workflow:` in task frontmatter — fail loud at dispatch
time, do not silently fall back to `ship-feature`.

## Consequences

**Good:**

- The three empirically validated workflows ship as real files; the runner
  no longer hardcodes the L→P→I→V→J chain.
- Adding a new workflow becomes a markdown file + (occasionally) a new
  predicate atom, not a runner code change.
- Future journey retrospectives can promote stubs to fleshed workflows by
  filling in the body, without changing the platform.
- Validation is centralized and testable in isolation.

**Bad / risks:**

- Six stub workflow files exist but have `TBD` bodies. Operators picking
  these up will see "not yet validated empirically" and need to either
  flesh them out before use or escalate. Documented in each stub.
- **Stubs MAY omit `exit-criteria` from frontmatter** (clarification
  added 2026-05-10 post-journey-5). The five stubs shipped without it
  because by definition they have no validated exit criteria yet;
  writing `[]` would be dishonest, and a non-trivial value would lie
  about validation that hasn't happened. The parser defaults to `[]`
  when absent. When a stub is promoted to a fleshed workflow via a
  validation journey, its retrospective MUST list exit-criteria and the
  promotion commit MUST add the field.
- `gate-rules`'s predicate language is intentionally tiny; teams wanting
  richer logic will hit a v1 wall. Acceptable cost for the simplicity
  premium; v2 can extend.
- `auto-approve-when` + `gate-rules` overlap conceptually. The convention
  is: `auto-approve-when` is the workflow-wide default; `gate-rules` is
  the per-role override. Documented in 0003-workflow-taxonomy section of
  `docs/05-workflows.md`.

## Status

Accepted for task-019. Will be revisited after journey 5 (this task's
journey) and after any of the six stubs is promoted to a real workflow.
