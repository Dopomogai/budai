# budai

**An operating system for fleets of AI agents working on a codebase.**

budai is a vendor-neutral, open-source framework that organizes how multiple agents plan, implement, peer-review, and ship code together — with full audit, runtime telemetry, and cross-repo skill sharing. It's the layer above your AI coding tool: works alongside Claude Code, Codex, and others rather than replacing them.

## Status

**v0.1.0 — design release.** This release contains the complete design specification (20 design docs, 9 ADRs, sample manifests). Phase 0 — the executable content (`base/`, `runners/`, `bin/`) — is the next milestone. See [`docs/18-implementation-phases.md`](docs/18-implementation-phases.md) for the build sequence and [`CHANGELOG.md`](CHANGELOG.md) for what's planned next.

## Who this is for

You should look at budai if:

- You have **multiple AI agents** working on the same codebase and want them to coordinate without stepping on each other.
- You want **anonymized peer review** between agents (one agent's work judged by another, blind to authorship).
- You want **cross-repo skill sharing** — write a peer-review skill once, ship it to every project that subscribes.
- You want **runtime telemetry** — what each agent did, how long, with what model, with what success rate, queryable across projects.
- You want a **framework-agnostic** contract — the same role definitions running on Claude Code today, Codex tomorrow, direct API the day after.

You should look elsewhere if:

- You want a single agent that knows your codebase conventions. Try [buildermethods/agent-os](https://github.com/buildermethods/agent-os) — different layer of the stack, well-executed, complementary to budai.
- You want an IDE-integrated coding assistant. Use Claude Code, Cursor, or similar directly.

## Quick concepts

- **Roles** — agent types with distinct missions: Planner, Implementer, Verifier, Judge, Librarian. Defined as markdown.
- **Skills** — reusable procedures any role can invoke. Versioned. Shareable across repos.
- **Workflows** — named multi-role procedures that orchestrate a task end to end.
- **Council** — durable record of multi-attempt work: the attempts, the reviews, the verdict.
- **Bundle** — single self-contained context file the Implementer reads to know everything about a task.
- **Manifest** — per-repo declaration of which budai version, which skills, which roles to pull from the registry.

## Reading order

If you have 30 minutes, read these seven first — they cover the load-bearing concepts:

1. [`00-overview.md`](docs/00-overview.md) — what this is and why
2. [`01-design-principles.md`](docs/01-design-principles.md) — the eight principles
3. [`02-structure.md`](docs/02-structure.md) — the `.agents/` tree
4. [`03-roles.md`](docs/03-roles.md) — the five roles
5. [`08-the-journey.md`](docs/08-the-journey.md) — task lifecycle end to end
6. [`18-implementation-phases.md`](docs/18-implementation-phases.md) — build sequence
7. [`19-glossary.md`](docs/19-glossary.md) — terms

## Full doc index

### Foundations
- [`00-overview.md`](docs/00-overview.md) — what budai is, who it's for
- [`01-design-principles.md`](docs/01-design-principles.md) — eight principles, four from Karpathy
- [`02-structure.md`](docs/02-structure.md) — `.agents/` directory layout, base/local overlay
- [`03-roles.md`](docs/03-roles.md) — five-role taxonomy with compute tiers

### The behavior layer
- [`04-skills.md`](docs/04-skills.md) — skill model, frontmatter schema, the eight standard skills
- [`05-workflows.md`](docs/05-workflows.md) — workflow model, four default workflows, hand-off contracts
- [`06-memory.md`](docs/06-memory.md) — four-layer memory with promotion paths
- [`07-runtime-data.md`](docs/07-runtime-data.md) — runs, council, messages, stats; backend streaming

### Lifecycle and contracts
- [`08-the-journey.md`](docs/08-the-journey.md) — twelve-step task lifecycle (the workhorse doc)
- [`09-bundle-format.md`](docs/09-bundle-format.md) — bundle YAML manifest, body structure, token budget
- [`10-plan-format.md`](docs/10-plan-format.md) — elaborate plan format, seven required sections
- [`11-task-format.md`](docs/11-task-format.md) — task frontmatter schema, status state machine
- [`12-isolation-and-fanout.md`](docs/12-isolation-and-fanout.md) — worktrees, opaque IDs, council folder
- [`13-evidence-capture.md`](docs/13-evidence-capture.md) — evidence taxonomy by change type
- [`14-failure-loop.md`](docs/14-failure-loop.md) — failure.md schema, retry budget, lesson promotion

### Distribution and portability
- [`15-framework-agnostic.md`](docs/15-framework-agnostic.md) — runner abstraction
- [`16-skill-versioning.md`](docs/16-skill-versioning.md) — semver, manifest pinning, lockfile
- [`17-registry-and-sync.md`](docs/17-registry-and-sync.md) — registry layout, librarian sync/publish

### Operations and adoption
- [`20-permissions-and-security.md`](docs/20-permissions-and-security.md) — permission taxonomy, runner enforcement, threat model
- [`21-onboarding.md`](docs/21-onboarding.md) — step-by-step adoption guide for an existing repo

### Reference
- [`18-implementation-phases.md`](docs/18-implementation-phases.md) — eight-phase build sequence
- [`19-glossary.md`](docs/19-glossary.md) — canonical terms

### Architectural Decision Records
- [`decisions/0001-mechanism-vs-culture.md`](docs/decisions/0001-mechanism-vs-culture.md)
- [`decisions/0002-five-roles-not-nine.md`](docs/decisions/0002-five-roles-not-nine.md)
- [`decisions/0003-worktree-isolation.md`](docs/decisions/0003-worktree-isolation.md)
- [`decisions/0004-strict-anonymization.md`](docs/decisions/0004-strict-anonymization.md)
- [`decisions/0005-base-overlay-not-submodule.md`](docs/decisions/0005-base-overlay-not-submodule.md)
- [`decisions/0006-yaml-bundle-manifest.md`](docs/decisions/0006-yaml-bundle-manifest.md)
- [`decisions/0007-elaborate-plan-format.md`](docs/decisions/0007-elaborate-plan-format.md)
- [`decisions/0008-framework-agnostic-runners.md`](docs/decisions/0008-framework-agnostic-runners.md)
- [`decisions/0009-skill-semver.md`](docs/decisions/0009-skill-semver.md)
- [`decisions/TEMPLATE.md`](docs/decisions/TEMPLATE.md) — copy-paste form for new ADRs

### Examples
- [`examples/manifest-minimal.yaml`](examples/manifest-minimal.yaml) — start here for a new consumer repo
- [`examples/manifest-full.yaml`](examples/manifest-full.yaml) — reference manifest exercising every field
- [`examples/README.md`](examples/README.md) — adoption walkthrough

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Contributions welcome — bug fixes, skill improvements, runner additions, doc clarifications, design proposals.

For coordination, use GitHub Discussions for design questions and Issues for confirmed bugs.

## License

[Apache-2.0](LICENSE).

## Origin

budai is part of the dopomogai brand line — sibling to `oragai` (agent orchestration) and `dopomogai` (the platform itself). The name is the Ukrainian imperative "build" rendered as a brand.
