# 21 — Onboarding

A step-by-step guide for adopting budai in an existing repository. From "I have a repo and want multi-agent collaboration" to "the first real task ships."

This document is the practical counterpart to the design docs. It assumes you've at least skimmed `00-overview.md`, `02-structure.md`, and `08-the-journey.md`.

## Prerequisites

Before starting, you should have:

- An existing git repo you want to apply budai to. Adopting on day-one of a new project is fine but the discover-standards step has nothing to extract; for new projects, work without it for a few weeks first.
- An agent platform account (Claude Code is the only supported runner at Phase 0).
- Decided on a registry source. Default: `https://github.com/Dopomogai/budai`. Forks are fine.
- A backend instance for runtime data streaming if you want cross-repo stats. Not required at Phase 0; can be added later.
- A few hours of human time. Onboarding is not autonomous — humans approve plans, review the AGENTS.md, refine local conventions.

## Phase A — Install the OS

### A1. Pre-onboarding cleanup

Run the basic hygiene checks first:

- `.env` not tracked in git (`git ls-files .env` should return nothing).
- No `.orig` files in source.
- `.gitignore` covers the runtime directories budai will create: `.agents/runs/`, `.agents/council/`, `.agents/messages/`, `.agents/stats/`, `.agents/index/`.
- All tests pass on main.

If any of these fail, fix before proceeding. budai inherits the repo's hygiene; rotting starting state will mislead the Librarian's audit.

### A2. Add the manifest

Create `.agents/manifest.yaml` from `examples/manifest-minimal.yaml` in the budai registry:

```yaml
budai-version: 0.1.0          # latest registry tag

included:
  roles: [planner, implementer, verifier, judge, librarian]
  skills:
    - build-task-bundle: ^1.0.0
    - peer-review: ^1.0.0
    - audit-docs: ^1.0.0
    - run-preflight: ^1.0.0
    - capture-evidence: ^1.0.0
    - regenerate-index: ^1.0.0
  workflows:
    - ship-feature: ^1.0.0
    - fix-bug: ^1.0.0
    - audit-repo: ^1.0.0
  runners:
    - claude-code: ^0.1.0

human-gates: [end-of-planner, end-of-judge]

defaults:
  fan-out: 1
  retry-budget: 2
  bundle-budget: 80000
  runner: claude-code
```

Adjust `budai-version:` to whatever the latest released registry tag is.

### A3. Run librarian sync

Run `librarian sync` from the budai CLI (or, equivalently, manually clone the registry tag and copy `base/` into your `.agents/base/`).

Verify:
- `.agents/base/` is populated with roles, skills, workflows, runners, conventions, permissions.
- `.agents/manifest.lock.yaml` is created with resolved versions.
- The base/ content matches the registry tag you pinned.

Commit `.agents/base/`, `.agents/manifest.yaml`, `.agents/manifest.lock.yaml` to git.

### A4. Scaffold local/

Create `.agents/local/` with three files initialized from registry templates:

- `local/conventions.md` — start empty (or with starter recipes from `base/templates/local-conventions-recipes.md`).
- `local/untouchables.md` — start empty.
- `local/glossary.md` — start empty.

We'll fill these in Phase B.

### A5. Add AGENTS.md and CLAUDE.md

At the repo root:

- `AGENTS.md` — copy from `base/templates/AGENTS.md`. Adjust the project-specific sections (project name, primary stack).
- `CLAUDE.md` — copy from `base/templates/CLAUDE.md`. Should be a one-liner pointing to AGENTS.md.

These are the entry points every agent reads first.

### A6. Verify with preflight

Run `bin/preflight`. It should report all green:

- No `.orig` files
- No untracked `.env*`
- `.env` not tracked
- AGENTS.md exists
- `.agents/manifest.lock.yaml` matches `.agents/base/` contents

If preflight fails, fix the issue before proceeding. budai expects clean starting state.

## Phase B — Discover and capture conventions

### B1. Run discover-standards

Invoke the `discover-standards` skill once: `bin/agent run --role librarian --skill discover-standards`. The Librarian walks your codebase and writes findings to `local/conventions.md`. Findings include:

- File naming patterns
- Import organization
- Error handling idioms
- Test placement
- Documentation patterns

The output is a draft. The Librarian's draft is starting evidence, not policy. Review it and edit.

### B2. Refine conventions.md

Open `local/conventions.md`. For each finding the Librarian extracted:

- Confirm it matches your team's actual practice (not just what the codebase happens to look like by accident).
- Sharpen wording. Drafts say "files seem to use kebab-case"; the convention should say "files use kebab-case" or "files use camelCase" — pick one.
- Add conventions the Librarian missed. Things that exist in human heads but not yet in code.

Aim for a tight, opinionated `conventions.md` (50-200 lines typical). Long conventions docs become noise in bundles.

### B3. Identify untouchables

Walk your codebase looking for code that "looks weird but must not change without discussion." Examples:

- A workaround for a specific bug (link to the bug)
- A non-obvious performance optimization
- A platform-specific quirk handler
- A security-sensitive boundary

For each, write an entry in `local/untouchables.md`:

```markdown
## webSecurity: false in BrowserWindow
Intentional. Required for cross-origin webview interop.
See ADR 0001 and src/main/index.ts:42.
```

A repo with 0 untouchables is rare — most have 3-10. If yours has 50+, you might be over-flagging. Pick the highest-stakes ones.

### B4. Define glossary

Open `local/glossary.md`. Add domain-specific terms that future agents would need to know:

- Concepts unique to this codebase ("widget" in CanvasOS, "vendor" in a distribution platform)
- Terms with non-obvious meaning ("active user" — does that mean monthly, weekly, daily?)
- Anything that's caused confusion before

Each entry: term name (H2 heading), 1-2 sentence definition.

### B5. Commit

Commit `local/conventions.md`, `local/untouchables.md`, `local/glossary.md`. These are durable repo policy.

## Phase C — Add file headers

### C1. Run the header-add script

`bin/librarian add-headers --interactive`. The Librarian walks `src/` directory by directory. For each directory:

- Reads existing files
- Drafts a six-field header for each
- Prompts you to confirm or adjust

The interactive flow lets you reject drafts that miss the mark. The script doesn't ship headers without confirmation.

### C2. Verify headers

After the script completes:

- Run `bin/librarian regenerate-index`.
- Inspect `.agents/index/detailed.md`. Every source file should have its `@purpose`, `@why`, `@role` populated.
- If anything is missing or wrong, edit the file directly and re-run the index.

### C3. Commit headers

Commit the header changes as a single batched commit:

```
chore: add budai file headers across src/
```

This is a large diff but a one-time cost.

## Phase D — First task

### D1. Create a synthetic test task

Run `bin/task new feature` and create a small, self-contained task. Something concrete and verifiable, not a refactor or a research task — those have variations onboarding might not exercise.

Good first tasks:
- Add a small UI component
- Add a new IPC channel
- Add a configuration option

Bad first tasks:
- "Refactor X" (too open-ended)
- "Improve performance of Y" (open-ended; needs research)
- "Add OAuth" (too large; touches many files)

### D2. Walk the workflow manually

Don't fully automate the first task. For each step:

1. The Librarian builds the bundle. Inspect it. Is it 95% of what an Implementer would need? If not, why? Iterate on conventions/untouchables/glossary as gaps emerge.
2. The Planner produces a plan. Review it. Does the file-level changes section actually specify what to do? If not, the role file or the plan format needs refinement.
3. (Human gate) Approve.
4. The Implementer codes. Watch the run. Does the Implementer hit unexpected escalations? File the patterns into role memory.
5. The Verifier checks AC. Does evidence capture work for your stack? Adjust `capture-evidence` skill if not.
6. The Judge integrates. Does the verdict format make sense?
7. (Human gate) Approve.

Record observations in `messages/channels/ops.md` as the run progresses. The Librarian's first sweep will pick up patterns.

### D3. The first real task

Once the synthetic task succeeds end-to-end, run a real task from your backlog. Same workflow, less hand-holding. Watch for:

- Steps where you intervene (those signal automation gaps)
- Places where the Implementer asks for clarification (signal: bundle missed something or plan was vague)
- AC misses (signal: test-coverage skill needs tuning)

Iterate. The first 5-10 tasks will surface most of the rough edges.

## Common issues

### "The bundle is missing something the Implementer needs"

The bundler scores by file relevance. If something keeps getting missed:

- Check the file's `@purpose` and `@why` — vague headers score lower.
- Check whether the bundler's `reason:` taxonomy covers your case. If not, propose a new reason via `librarian publish`.
- For one-off cases, the human can edit the bundle's frontmatter to manually pull in additional files. Subsequent runs of the Librarian's `improve-bundle` skill will learn from these manual additions.

### "The Planner's plans are too vague"

Two common causes:

- The Planner's role file is too high-level. Look at `base/roles/planner.md` and the `local/roles/planner.md` override (if any). The mission section should explicitly demand specifics.
- The bundle is missing structure cues — file headers, ADRs, patterns. Without these the Planner can't be specific. Tighten conventions and headers.

### "The Verifier passes things that shouldn't pass"

Check the `capture-evidence` skill output. The Verifier should be capturing evidence per AC. If it's claiming pass without evidence, the skill needs adjustment.

For now (Phase 0), evidence capture is partly manual; Phase 4 fan-out scenarios surface these issues fast.

### "The Judge is picking the wrong attempts"

In strict anonymization mode, the Judge sees only the attempt content. If it's picking poorly:

- Check that the attempts genuinely differ. If two are nearly identical, the Judge may pick on noise.
- Check the verdict's rationale. The Judge should explain *why* — vague verdicts mean the attempts didn't differ on the dimensions that matter.
- Increase peer-reviewers (workflow setting) for higher-stakes tasks.

### "Sync conflicts when two repos publish the same skill update"

Out of scope for Phase 0 (single-repo). Phase 6+ when registry has multiple contributors. For now, the registry has one maintainer, no conflicts possible.

## What budai is NOT

- Not a magic bullet. The first 10 tasks need close attention. Budgeted patience pays back.
- Not zero-cost. Tokens cost money; multi-agent fan-outs cost more than single-agent runs. Allocate budget consciously.
- Not a replacement for human judgment. Humans approve architecture and final results. budai removes mechanical work; it doesn't remove decisions.
- Not Phase 0 itself. Onboarding takes time and iteration. Phase 0 means "the OS is installed"; Phase 1+ means "the OS is working well for this team."

## Onboarding for non-code repos

Out of scope for Phase 0. Future phases will define onboarding patterns for marketing repos, sales-ops repos, support-ops repos. The role taxonomy, skill taxonomy, and workflow taxonomy will need extension — none of the five default roles fit "send an email to a customer" cleanly.

For now: onboard code repos, validate the model, then expand.
