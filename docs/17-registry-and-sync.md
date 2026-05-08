# 17 — Registry and sync

The **registry** is the central git repo holding canonical `base/` content — skills, roles, workflows, runners, and shared conventions — used by every consumer repo. This very repo (`https://github.com/Dopomogai/budai`) is the registry.

This document specifies how consumer repos pull from the registry (`librarian sync`), how local skills get promoted to the registry (`librarian publish`), and how the registry coordinates updates across many consumer repos.

## The registry layout

The registry repo's content layout mirrors what consumer repos pull into their `.agents/base/`:

```
budai/                       # this repo
├── README.md
├── LICENSE
├── docs/                    # design docs (this directory)
├── base/                    # the canonical content (Phase 0+)
│   ├── roles/
│   │   ├── planner.md
│   │   ├── implementer.md
│   │   ├── verifier.md
│   │   ├── judge.md
│   │   └── librarian.md
│   ├── skills/
│   │   └── ...
│   ├── workflows/
│   │   └── ...
│   ├── runners/
│   │   └── claude-code.md
│   ├── conventions.md
│   └── permissions.md
├── archived/                # legacy versions kept for reference
└── CHANGELOG.md
```

Every release of the registry is a tag (`v0.4.2`, `v0.5.0`, etc.). Consumer repos pin against tags, not arbitrary commits.

## Consumer repo manifest

Each consumer repo (e.g., CanvasOS, a client codebase) has `.agents/manifest.yaml`:

```yaml
budai-version: 0.4.2          # registry tag

included:
  roles:     [planner, implementer, verifier, judge, librarian]
  skills:    [build-task-bundle, peer-review, audit-docs, run-preflight, capture-evidence, discover-standards, regenerate-index, promote-lesson]
  workflows: [ship-feature, fix-bug, refactor, audit-repo]
  runners:   [claude-code]

overrides:
  conventions: local/conventions.md   # merge with base

local-only:
  skills:    [add-widget, add-ipc-channel]   # CanvasOS-specific
  workflows: []

human-gates:
  - end-of-planner
  - end-of-judge

defaults:
  fan-out: 1
  retry-budget: 2
  bundle-budget: 80000
```

The manifest is the single source of truth for "what this repo's `.agents/base/` should contain." `librarian sync` reads it and materializes.

## `librarian sync` — pull from registry

The pull flow:

```bash
$ bin/librarian sync
```

Steps:

1. Read `.agents/manifest.yaml`.
2. Look up the registry's tagged release matching `budai-version:`.
3. For each item in `included:`, fetch the corresponding `base/<dir>/<name>.md` from the registry at that tag.
4. Resolve version pins (e.g., `peer-review: ^1.4.0` → registry's latest 1.x.y).
5. Write resolved files into the consumer repo's `.agents/base/`. (Tracked in git for reproducibility.)
6. Update `.agents/manifest.lock.yaml` with the resolved versions.
7. Output a summary: what changed since last sync, what's available to update.

`librarian sync` is idempotent. Running it twice in a row produces no diff.

### Sync output example

```
budai sync — pulled from dopomogai/budai @ v0.4.2

Updated:
- base/skills/peer-review.md         1.4.6 → 1.4.7   (patch)
- base/workflows/ship-feature.md     1.2.0 → 1.2.1   (patch)

Available updates (manifest pin doesn't allow auto):
- base/skills/audit-docs.md          1.2.5 → 2.0.0   (major; see CHANGELOG#audit-docs-2-0-0)

Deprecation notices:
- base/skills/discover-standards.md  is marked deprecated; superseded by extract-conventions in 0.5.x

Lock file updated.
Working tree dirty: review the diff and commit.
```

The output is conversational because a human will read it. The sync produces git changes the human reviews before committing.

### When sync runs

- **Manual.** `bin/librarian sync` whenever the human wants.
- **Scheduled.** A weekly cron in `.github/workflows/budai-sync.yml` (or equivalent) runs sync and opens a PR with the changes. The human reviews and merges.
- **Pre-task.** Optionally, the runner runs sync before a task starts to pick up urgent fixes (security patches, regression fixes). Off by default.

## `librarian publish` — promote local to registry

Local content (in `local/skills/`, `local/roles/`, etc.) is repo-specific. Some local content is genuinely repo-specific (e.g., `add-widget` is for CanvasOS). Other local content is generally useful and should propagate to the registry for everyone's benefit.

Promotion flow:

```bash
$ bin/librarian publish skills/peer-review.md
```

Steps:

1. Validate the local file: frontmatter parses, required sections present, semver matches the version in the registry's existing file (or is the next version up).
2. Check stats from the local repo's runtime data: has this version been used ≥10 times with stable success rate?
3. Open a PR against the registry repo. The PR:
   - Title: `skills: peer-review v1.4.7`
   - Body: diff between the registry's current version and the proposed version, with a paste of relevant stats.
   - Branch named `publish/peer-review-1.4.7` from a fork or, if the publishing repo is a registry contributor, directly.
4. Output the PR URL.

The human reviews the PR (this is high-stakes — it affects every consumer repo). On merge:

- Registry CI runs the skill against the registry's own test fixtures (Phase 6+).
- A new release tag is cut with the appropriate semver bump.
- Existing consumer repos with `latest` or `^` pins see the update on their next sync.

### What can be published

Any file under `local/`:

- Skills (`local/skills/<name>.md`)
- Roles (`local/roles/<name>.md`) — rarer, since the five default roles cover most cases
- Workflows (`local/workflows/<name>.md`)
- Runners (`local/runners/<name>.md`) — high-stakes; new runners need extra review
- Conventions sections (subset of `local/conventions.md` proposed for `base/conventions.md`)

### What can NOT be published

- Untouchables (`local/untouchables.md`) — repo-specific by definition.
- ADRs (`memory/decisions/`) — these are records of *this repo's* decisions, not the registry's.
- Lessons (`memory/lessons/`) — same; per-repo learnings. (Cross-repo patterns get promoted via convention proposals.)
- Glossary (`local/glossary.md`) — repo-specific terms.

These categories are intentionally per-repo; promoting them would impose one repo's conventions on others.

## Base/local overlay resolution (recap)

Per `02-structure.md`: when the runner needs a skill named `X`:

1. Check `local/skills/X.md` — if present, use it.
2. Otherwise check `base/skills/X.md` — use it.
3. Otherwise error: skill not found.

Local wins. Same-name in `local/` overrides base; new-name extends base.

This means a local override doesn't fork the registry — the consumer repo can override one specific skill while continuing to receive updates for everything else. The override is durable across syncs because `librarian sync` only touches `base/`, never `local/`.

## Cross-repo coordination

The registry is a coordination point. Three classes of cross-repo signals flow through it:

### Stats aggregation

Consumer repos stream their `stats/` into the ultimate-widget backend (per `07-runtime-data.md`). The backend aggregates per-skill, per-version stats across all consumer repos. The registry's maintainers see:

- Which skills are used most.
- Which versions show success-rate regressions.
- Which deprecated skills still have active use.
- Which skills have local overrides in many repos (signal that the base version isn't right).

Stats inform when to issue patches, when to deprecate, when to start collecting feedback for a major bump.

### Convention proposals

When a lesson reaches cross-repo recurrence (per `06-memory.md` promotion path), the Librarian in the originating repo opens a PR against the registry's `base/conventions.md` proposing the lesson as a shared convention. Other consumer repos' maintainers can comment, agree, or block.

This is the slowest, most-reviewed change class. A `base/conventions.md` change goes to every consumer repo on next sync — it should be high-confidence.

### Skill self-improvement

When the autonomous skill self-improvement loop (per `14-failure-loop.md`) produces an improved skill in a consumer repo and the human accepts it, `librarian publish` propagates it.

The loop closes: failure data → lesson → improved skill → registry → all consumer repos → reduced future failures.

## Registry maintainer responsibilities

Registry maintainers (initially: dopomogai-agent + Andrey, expanding as the project grows):

1. **Review publish PRs.** Are the changes well-scoped? Does the version bump match the change class? Does the body of the change reflect a real improvement (per the proposing repo's stats)?
2. **Cut releases.** After accepted PRs merge, tag a release (`v0.4.3`, etc.). Update CHANGELOG.
3. **Communicate breaking changes.** Major bumps need a migration guide in CHANGELOG and ideally a heads-up in the dopomogai community channels.
4. **Respond to incidents.** If a release causes regressions across multiple consumer repos, hot-fix or rollback per `16-skill-versioning.md`.
5. **Curate `archived/`.** Move long-deprecated content out of `base/` to keep the active surface area small.

Maintenance overhead is low for stable periods (most weeks: a few patch PRs, one minor release). It spikes around major releases and during community growth.

## Forks

The registry is Apache-2.0; anyone can fork. A fork:

- Has its own release cadence and tags.
- Can diverge — different opinions on roles, different default workflows.
- Consumer repos can pin to a fork by changing `manifest.yaml`'s registry source.

Forks are healthy. They let opinionated communities evolve their own variants without forcing the canonical registry to absorb every preference.

## What the registry is NOT

- Not a hosted service. It's a git repo. Consumer repos pull via standard git operations.
- Not a runtime dependency. The registry is read at sync time; budai itself runs on whatever's already in `.agents/base/`. A consumer repo can survive registry downtime indefinitely.
- Not a lock-in. Apache-2.0 license, fork-friendly, vendor-neutral by design.
- Not a substitute for repo-local judgment. The registry provides defaults; each consumer repo decides what to use, what to override, and what to extend.
