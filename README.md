# budai

**An operating system for fleets of AI agents working on a codebase.**

budai is a vendor-neutral, open-source framework that organizes how multiple agents plan, implement, peer-review, and ship code together — with full audit, runtime telemetry, and cross-repo skill sharing. It's the layer above your AI coding tool: works alongside Claude Code, Codex, and others rather than replacing them.

## Status

**Early. Design-stage.** This repository currently contains design documentation. The base content (`base/`), runner shims (`runners/`), and CLI scripts (`bin/`) will land in subsequent commits as we work through the implementation phases. Read [`docs/18-implementation-phases.md`](docs/18-implementation-phases.md) for the build sequence.

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

## Read in order

1. [`docs/00-overview.md`](docs/00-overview.md) — what this is and why
2. [`docs/01-design-principles.md`](docs/01-design-principles.md) — the eight principles
3. [`docs/02-structure.md`](docs/02-structure.md) — the `.agents/` tree
4. [`docs/03-roles.md`](docs/03-roles.md) — the five roles
5. [`docs/08-the-journey.md`](docs/08-the-journey.md) — task lifecycle end to end
6. [`docs/18-implementation-phases.md`](docs/18-implementation-phases.md) — build sequence
7. [`docs/19-glossary.md`](docs/19-glossary.md) — terms

## License

[Apache-2.0](LICENSE).

## Origin

budai is part of the dopomogai brand line — sibling to `oragai` (agent orchestration) and `dopomogai` (the platform itself). The name is the Ukrainian imperative "build" rendered as a brand.
