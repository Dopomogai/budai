---
adr: 0005
title: Base/local overlay, not git submodule, for cross-repo content sharing
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0005 — Base/local overlay, not git submodule, for cross-repo content sharing

## Context

Multiple consumer repos (CanvasOS, client repos) need to share canonical content (skills, roles, workflows) while also having repo-specific extensions and overrides. Three options were considered:

- **A. Git submodule.** `.agents/` is a git submodule pointing to the registry repo. Local extensions live alongside in a sibling directory.
- **B. Base/local overlay.** `.agents/base/` is read-only, materialized from the registry by `librarian sync`. `.agents/local/` holds repo-specific content. Resolution rule: local wins on same-name lookup.
- **C. Backend-mediated.** A server holds canonical content; consumer repos pull at runtime. No git relationship.

Submodules are notoriously fiddly: detached-HEAD states, easy to forget to update, conflicts when both sides change the same file, opaque diff in the parent repo. The registry's content evolves; consumer repos shouldn't have to deal with submodule state every time.

Backend-mediated introduces a runtime dependency. budai should keep working when the network is down.

## Decision

Adopt option B: base/local overlay.

Mechanics:

- The registry's content is materialized into `.agents/base/` by `librarian sync` (a CLI operation, not a runtime call).
- `base/` is read-only locally — never edited by hand.
- `local/` is the consumer repo's own files, edited freely.
- Resolution: when looking up a skill/role/workflow named X, check `local/<dir>/X.md` first, fall back to `base/<dir>/X.md`. Local wins.
- Both `base/` and `local/` are committed to the consumer repo's git, so the state is reproducible from any commit.
- A `manifest.lock.yaml` records the exact resolved versions for reproducibility (similar to package-manager lockfiles).

## Consequences

**Positive:**

- No submodule state to manage. The base content is just files; if you lose them, run `librarian sync` to restore.
- Reproducibility: any commit hash gives an exact snapshot of what `base/` and `local/` looked like.
- Conflict-free: registry updates only touch `base/`, never `local/`. Consumer repos can't conflict with the registry on shared filenames because `local/` is theirs.
- Network-independent: budai works without the registry being reachable. Sync requires network; running doesn't.
- Clear mental model: base = read-only, local = yours. No ambiguity about ownership.

**Negative:**

- More committed files than submodule (the entire `base/` directory is in every consumer repo). Acceptable; markdown is small.
- `librarian sync` is an explicit step; if you forget to run it, you stay on old content. Mitigated by scheduled syncs and pre-task sync option.
- The lockfile becomes a real artifact to manage, with all the usual lockfile-vs-manifest reconciliation considerations.

**Neutral:**

- Forks of the registry are easy: just point `manifest.yaml` at a different registry source.
- Migrating to a different sharing model (e.g., backend-mediated) later is straightforward — the local artifacts are already self-contained.
