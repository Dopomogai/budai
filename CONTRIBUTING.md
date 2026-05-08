# Contributing to budai

budai is open source under Apache-2.0. Contributions are welcome — from individuals using budai in their own work, from teams adapting it for client engagements, from anyone who's read the docs and has improvements to propose.

This guide covers what changes go where, how to propose them, and what review looks like.

## What you can contribute

| Change type | Where it goes | Reviewers |
|---|---|---|
| Bug fix in a base skill / role / workflow | PR to this repo | Registry maintainers |
| Improvement to a base skill | PR to this repo, version-bumped | Registry maintainers |
| New skill (general-purpose) | PR adding to `base/skills/` | Registry maintainers + community comment period |
| New runner | PR adding to `base/runners/` | Registry maintainers (high-stakes; extra review) |
| Doc clarification | PR to `docs/` | Anyone who's read the doc; maintainer merge |
| New ADR | PR to `docs/decisions/` | Discussion in PR; maintainer accepts/rejects |
| Bug report | GitHub Issue with label `bug` | Triaged by maintainers |
| Design proposal | GitHub Discussion (preferred) or Issue with label `proposal` | Open discussion |

## What stays out

- Repo-specific content (untouchables, glossary, lessons, ADRs about your decisions). These live in your consumer repo's `local/` directory and `memory/`, not here.
- Runtime data (`runs/`, `council/`, `messages/`, `stats/`). Gitignored by design.
- Anything tied to a single client or proprietary workflow.

If you're unsure whether something belongs here or in your consumer repo, ask in a Discussion first.

## How to propose a base skill / role / workflow change

1. **Develop in your consumer repo first.** Put the new or changed file in your repo's `local/skills/` (or local/roles/, local/workflows/). Use it. Iterate.
2. **Collect evidence.** Run the skill at least 10 times with stable success rate. Look at your repo's `stats/skills.json` to confirm.
3. **Use `bin/librarian publish`** to open a PR against this repo. The script:
   - Validates the file (frontmatter, required sections).
   - Bumps version per semver rules (per `docs/16-skill-versioning.md`).
   - Creates a PR with the diff and a paste of relevant stats.
4. **Respond to review.** Maintainers check: does the change generalize beyond your repo? Is the version bump appropriate? Is the body clear for someone reading cold?
5. **On merge.** Maintainer cuts a release tag. Other consumer repos pick up on next sync.

If you don't have `bin/librarian` (Phase 0+ tooling), do it manually: fork, edit `base/skills/<name>.md`, open a PR with the same content the script would produce.

## How to propose a new runner

Higher stakes than skills — runners are the bridge between budai and a third-party platform. Process:

1. Open a Discussion describing the runner: which platform, why it's worth shipping in base, what's already validated locally.
2. After community feedback, open a PR adding `base/runners/<name>.md` plus a CHANGELOG entry.
3. PR review focuses on: does the runner spec follow the format? Does it handle auth, tool translation, output capture per `docs/15-framework-agnostic.md`? Is there evidence (≥10 runs across ≥5 role types) that it works?
4. Maintainers may request a "preview" period — the runner ships marked `experimental` for a release cycle before stabilizing.

## How to propose a doc change

Doc PRs are lighter weight. For typo fixes, prose clarifications, or factual corrections: just open a PR. Maintainer reviews and merges.

For substantial doc rewrites or new docs:
- Open a Discussion first if the change reshapes how a concept is explained.
- For new docs, follow the numbering scheme (next available 2-digit prefix in `docs/`).

## How to propose an ADR

ADRs document load-bearing design decisions. New ADRs are needed when:

- A foundational mechanism is being changed (rare; revising via supersession).
- A new significant capability requires a documented rationale.
- A community-driven design proposal lands.

Process:

1. Open a Discussion describing the proposed decision.
2. After feedback, open a PR adding `docs/decisions/<NNNN>-<slug>.md` using `docs/decisions/TEMPLATE.md`.
3. Initial status: `proposed`.
4. PR discussion shapes the ADR.
5. On merge, status becomes `accepted`.

ADRs are immutable once accepted. To revise, write a new ADR with `supersedes: <old-ADR-number>` set.

## Code of conduct

We ask contributors to be respectful, patient, and constructive. Disagreements are inevitable; escalations should be technical, not personal.

For reports of misconduct: contact `contact@dpmg.xyz` directly (handled by Dopomogai's organizational owners, not the registry maintainers).

## Maintainers

Initial maintainers:

- `dopomogai-agent` (the AI agent maintaining the registry)
- `andrey` (Andrey Solovei, Dopomogai)

The maintainer list will expand as the project grows. Maintainership is granted by demonstrated sustained contribution; the criteria will be formalized once we've grown past the initial team.

## License

All contributions are licensed under Apache-2.0 (per the LICENSE file). By submitting a PR, you agree to license your contribution under those terms.

## Where to ask questions

- **GitHub Discussions** — design questions, conceptual questions, "is this a bug?" questions.
- **GitHub Issues** — confirmed bugs, feature requests with concrete proposals.
- **Direct contact** (`contact@dpmg.xyz`) — security reports, code-of-conduct issues, organizational matters.

## Thank you

Building budai in the open is more work than building it privately would have been. Contributors make that worthwhile. Thanks for reading.
