# 04 — Skills

A **skill** is a named, versioned, reusable procedure that one or more roles can invoke. Skills are the unit of capability reuse in budai — across roles within a repo, and across repos via the registry.

## What a skill is, what it isn't

Three closely-related concepts often get conflated:

- **Role** — an agent type with a mission, permissions, and a default model. A role *has* skills.
- **Skill** — a procedure. A role *invokes* skills to do its work.
- **Workflow** — an orchestration of multiple roles. A workflow *sequences* role invocations; the roles inside use skills.

A skill is NOT:

- A role. Roles are heavier; they have system prompts and identities. A skill is a procedure invoked by an existing role.
- A workflow. Workflows orchestrate multiple roles; a skill stays within one role's invocation.
- A general-purpose program. Skills are agent-readable procedures, not arbitrary code.
- A place for business logic. Conventions, untouchables, and glossary are repo policy. A skill is repo-agnostic execution — the same `peer-review` skill works in CanvasOS and in any client repo.

## Skill file format

A skill is a markdown file with YAML frontmatter and a body. Lives at `base/skills/<name>.md` (canonical, pulled from the registry) or `local/skills/<name>.md` (repo-specific override or extension).

### Frontmatter

```yaml
---
skill: peer-review
version: 1.4.2
tier-override: opus              # optional: override role's default tier
inputs:
  - council-attempts-dir
  - conventions-md
outputs:
  - review-md
  - ranking-json
breaking-changes-from: 1.3.0     # null or absent if no breaking changes
stability: stable                # stable | experimental | deprecated
owners: [judge, reviewer]        # which roles are allowed to invoke
---
```

Field reference:

- **skill** — name, kebab-case. Must match the filename (`peer-review.md`).
- **version** — semver. See "Versioning" below.
- **tier-override** — optional. Forces a specific compute tier regardless of the invoking role's default. See "Tier override".
- **inputs** / **outputs** — named slots, not type signatures. The body specifies format and source for each.
- **breaking-changes-from** — set when this version made a breaking change relative to the listed prior version. Used by the Librarian to flag manifest inconsistencies in consumer repos.
- **stability** — affects how aggressively the Librarian recommends the skill for new tasks. Experimental skills can be invoked but get a warning in the run log.
- **owners** — roles allowed to invoke this skill. Other roles asking for the skill get a permission error.

### Body sections

Required, in order:

1. **When to use.** One paragraph. The trigger condition. If a role needs to ask "should I invoke this skill?", this section answers.
2. **Inputs.** For each input named in frontmatter: type, source (where the role gets it from), required vs. optional, default if optional.
3. **Procedure.** Numbered steps. Concrete, executable. No "consider whether..." — either do it or don't.
4. **Outputs.** For each output named in frontmatter: format, where it gets written, what consumes it next.
5. **Failure modes.** Common failures and what to do. "If X, escalate to Y. If Z, retry once with adjusted parameters."
6. **Examples.** At least one worked example showing inputs → procedure → outputs.

Optional but recommended:

7. **Anti-patterns.** What this skill is sometimes mistakenly invoked for and why that's wrong.
8. **References.** Pointers to related skills, workflows, or ADRs.

## Versioning

Semver. Three change classes:

- **Patch** (1.4.2 → 1.4.3) — clarifications, edge-case handling, prompt tweaks. No I/O contract change. Drop-in compatible.
- **Minor** (1.4.x → 1.5.0) — new optional input, new output field, new owner role. Backward compatible — old callers continue working.
- **Major** (1.x → 2.0.0) — input/output contract changes, removed inputs, semantics changes. Breaking. Requires manifest update in consumer repos.

When a skill goes major, set `breaking-changes-from:` in the new version's frontmatter pointing at the last pre-break version. The Librarian uses this to flag manifest inconsistencies.

### Manifest interaction

A repo's `manifest.yaml` pins skill versions. Pin syntax follows npm-style ranges:

```yaml
included:
  skills:
    peer-review: ^1.4.0          # accept patches and minors; reject majors
    add-widget: 2.0.1            # exact pin
    build-task-bundle: ~1.4.2    # patches only
```

Major bumps in the registry don't auto-propagate to repos pinned with `^` — the Librarian flags them as available updates and the human chooses when to bump.

### Stats are versioned

Skill invocations are recorded with their version. `stats/skills.json` discriminates by `skill@version`. This lets the Librarian compare success rates across versions and answer "did the v1.4 → v1.5 update actually help?" without conflating data from different versions.

## Promotion

A new or improved skill starts at `local/skills/<name>.md` in some repo. After it proves out (the Librarian's quality threshold is configurable; default: ≥10 successful invocations with stable success rate), `bin/librarian publish skills/<name>.md` opens a PR against the registry to promote it into `base/`.

Full mechanics in `17-registry-and-sync.md`. Short version: the registry has the same overlay model as a consumer repo — `local/skills/` becomes the proposed addition; PR review and merge make it canonical; consumer repos pick it up on next `librarian sync`.

## Tier override

A skill can declare `tier-override:` to run at a different compute tier than its invoking role's default.

Example: the Librarian role defaults to Sonnet (per `03-roles.md`). The `regenerate-index` skill is purely mechanical — pattern-matching headers and emitting JSON. Sonnet is overkill. The skill declares:

```yaml
---
skill: regenerate-index
tier-override: haiku
---
```

When the Librarian invokes `regenerate-index`, the runner spawns a Haiku call for that step regardless of the Librarian's default. Cost stays low without sacrificing reasoning where it counts.

The reverse case also exists: a skill that needs heavier reasoning than its invoking role's default. The `peer-review` skill declares `tier-override: opus` even though Judges run at Sonnet for integration — peer review is the moment that needs the most reasoning.

Tier override is a per-skill design choice, not a runtime knob. Skills that consistently need a different tier should declare it; skills that follow the role's default should leave `tier-override:` unset.

## Standard skills shipped in `base/`

The skills below are part of `base/skills/` in the registry. Every consumer repo gets them via `librarian sync`. Each has its own file with the full format spec; the descriptions here are summary only.

### `build-task-bundle` (owners: librarian)

Reads a task definition + the detailed index + file headers, scores files for relevance, pulls top matches plus relevant ADRs, conventions, and glossary entries. Produces `tasks/open/<id>.bundle.md` — a self-contained markdown file with YAML manifest and concatenated content. Token-budgeted; overflow turns into "reference if needed" hints.

This is the most-invoked skill in budai. It runs once per task, before the Planner or Implementer ever sees the task. Bundle quality is the largest predictor of downstream attempt quality.

Full bundle format spec: `09-bundle-format.md`.

### `peer-review` (owners: judge, reviewer)

Reads anonymized attempts from `council/<task-id>/attempts/`, ranks them with rationale, writes `council/<task-id>/reviews/review-<X>.md`. The skill is the canonical implementation of the anonymization-with-traceability principle from `01-design-principles.md` — input strips authorship, output stays in council where the verdict can de-anonymize for posterity.

Tier override: `opus`. This is the moment that needs the most reasoning.

### `audit-docs` (owners: librarian)

Compares prose claims in docs against current code. Detects:

- File header mismatches (rename, signature change)
- Directory README contradictions
- Top-level `architecture.md` references to deleted symbols
- ADRs contradicted by current code

High-confidence findings (renames, removed exports) are auto-fixed. Low-confidence findings (architectural rephrasing) open tasks for the regular workflow to address.

### `run-preflight` (owners: any role)

The lightweight wrapper around `bin/preflight`. Verifies repo state before any agent work begins. Required first step in every role's workflow — if preflight fails, the role aborts with a structured error rather than building on rotten ground.

Tier override: `haiku`. Pure pattern matching.

### `capture-evidence` (owners: verifier)

Captures the right evidence for the change type. Specialized by scope:

- Backend / pure logic: test runner output
- IPC changes: replayed IPC trace from a smoke test
- FE component: Playwright headed run, screenshots, DOM diff, console errors
- Visual changes: screenshot comparison
- Performance-sensitive: before/after timing

Output goes to `runs/<run-id>/evidence/`. The Judge sees evidence summaries; the human gate can drill into the full evidence tree.

Full spec: `13-evidence-capture.md`.

### `discover-standards` (owners: librarian)

Run once when budai is first applied to a repo. Walks the codebase and extracts implicit conventions — naming patterns, error-handling idioms, import organization, file layout. Writes findings to `local/conventions.md` for human review and finalization.

Borrowed conceptually from buildermethods/agent-os; budai's implementation is multi-agent-aware and writes to the same `conventions.md` the rest of the system reads, rather than to a separate standards file.

### `regenerate-index` (owners: librarian)

Walks `src/` reading file headers; emits `index/tree.md`, `index/tree.json`, `index/detailed.md`, `index/detailed.json`. Runs in the Librarian sweep on every task close, plus on demand.

Tier override: `haiku`.

### `promote-lesson` (owners: librarian)

Scans `runs/` for recurring patterns. When the same failure mode appears ≥3 times, drafts a lesson entry for `memory/lessons/<topic>.md`. Lessons start at role scope; if cross-role recurrence pattern emerges, drafts a `conventions.md` addition. Cross-repo recurrence (visible via the registry's stats) drafts a `base/conventions.md` proposal.

This is the system's auto-improvement loop. All promotions are drafts — the Librarian opens improvement tasks rather than directly mutating the convention layer. Humans gate the merge.

## Adding a new skill

The flow:

1. Identify a procedure that's currently inlined into a role's body or duplicated across roles.
2. Create `local/skills/<name>.md` in the repo where you discovered the pattern.
3. Declare frontmatter; write the body following the section spec above.
4. Update the role files that should be allowed to invoke it (`skills:` list in role frontmatter).
5. Use the skill for ≥10 invocations across real tasks.
6. If success rate is stable, run `bin/librarian publish skills/<name>.md` to propose it for the registry.
7. Once merged, set `local/skills/<name>.md` to point at the base version (or remove the local override) so future updates flow through the registry.

The flip side — deprecating a skill — lives in `16-skill-versioning.md`.

## What you should NOT put in a skill

- **Repo-specific configuration.** That's `local/conventions.md` or `local/glossary.md`. A skill that reads `local/conventions.md` is fine; a skill whose body hardcodes a convention is not.
- **One-off task instructions.** That belongs in the task itself or in the plan section.
- **Decision logic that depends on org policy.** Org policy is too repo-specific to encode in a portable skill. Lift the decision into the role file or the task body, and have the skill execute mechanically.
- **A multi-role orchestration.** That's a workflow. If your "skill" needs to hand off between roles, you've actually written a workflow. See `05-workflows.md`.
