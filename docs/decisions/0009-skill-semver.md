---
adr: 0009
title: Semver for skills, roles, and workflows
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0009 — Semver for skills, roles, and workflows

## Context

Cross-repo content sharing (per `17-registry-and-sync.md`) means that updates to a skill in the registry can affect every consumer repo on next sync. Without versioning discipline, a skill update could silently break consumers.

Three options were considered:

- **A. No versioning.** Latest is always pulled. Simplest; fragile. Used by some early agent frameworks.
- **B. Date-based versioning.** Versions are timestamps. Simple, but no information about whether a change is breaking.
- **C. Semver.** Major.Minor.Patch with breaking-change semantics. Familiar from npm, cargo, and most package ecosystems.

Semver requires discipline (you have to actually distinguish breaking from non-breaking changes) but the payoff is:

- Consumer repos can pin to a major version and trust they won't break.
- Patches and minors auto-propagate with confidence.
- Migration windows for major bumps are explicit.

Date-based and unversioned alternatives don't give the same predictability; consumer repos would have to either accept all updates blind or freeze indefinitely.

## Decision

Adopt semver for skills, roles, workflows, and runners.

Rules:

- **PATCH** — clarifications, edge cases, prompt tweaks. No I/O contract change.
- **MINOR** — new optional input/output, new owner role. Backward compatible.
- **MAJOR** — input/output contract change, removed inputs, semantics shift. Breaking.

When a major bump ships, set `breaking-changes-from:` in frontmatter pointing at the last pre-break version. CHANGELOG includes a migration guide.

Manifest pin syntax follows npm-style: `^1.4.0` accepts patches and minors; `~1.4.0` accepts patches only; `1.4.0` is exact.

Lockfile (`manifest.lock.yaml`) records resolved versions for reproducibility.

## Consequences

**Positive:**

- Consumer repos get bug fixes and improvements automatically (caret pins) without breakage risk.
- Major bumps are explicit, gated by manifest update. Migration windows are clear.
- Stats discriminate by version; A/B comparison of skill changes is straightforward.
- Familiar to anyone who's used a package manager. No new learning curve for contributors.

**Negative:**

- Versioning discipline requires honest assessment of "is this a breaking change?" The "when in doubt, bump higher" rule helps but won't catch everything.
- Lockfile becomes a real artifact to maintain (similar to package-lock.json or Cargo.lock).
- More overhead for trivial fixes — you have to bump version and write CHANGELOG entry even for typo fixes.

**Neutral:**

- Multi-version coexistence (per `16-skill-versioning.md`) gives a transition window for major bumps. Old major versions can stay in the registry alongside new ones.
- Rollback is well-defined: hot-fix patches OR mark a bad version as deprecated and let consumers resolve down.
- Forks of the registry are versioned independently. Consumer repos can pin to any registry source.
