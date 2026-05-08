# Examples

Sample manifests and configuration files for consumer repos adopting budai. Copy, adapt, commit.

## What's here

- `manifest-minimal.yaml` — the smallest manifest a consumer repo needs to start. Five default roles, the most-used skills, ship-feature workflow only, claude-code runner.
- `manifest-full.yaml` — a manifest exercising every field. Local overrides, local-only skills, multiple workflows, hybrid runner setup. Use as a reference, not a starting point.

## Quick start for a new consumer repo

1. Copy `manifest-minimal.yaml` to `<your-repo>/.agents/manifest.yaml`.
2. Adjust `budai-version:` to the latest tag of `https://github.com/Dopomogai/budai`.
3. Run `bin/librarian sync` (Phase 0+ tooling).
4. Add `.agents/local/conventions.md`, `.agents/local/untouchables.md`, `.agents/local/glossary.md` with your repo's specifics. Templates ship in `base/local-templates/` once Phase 0 lands.
5. Add `AGENTS.md` and `CLAUDE.md` at the repo root pointing future agents at the design docs.
6. Walk source files, add the six-field header to each (Phase 0 will provide a script for this).
7. Run `bin/preflight` to validate state.
8. Open your first task with `bin/task new feature` and let the workflow run.

The minimal manifest gets you running. As you discover repo-specific patterns, add to `local/` and consider promoting them to the registry per `docs/17-registry-and-sync.md`.

## What's NOT here

- The base/ content itself. That lives in this repo's `base/` directory, materialized into your consumer repo by `librarian sync`.
- Per-language tooling examples. Phase 0 will add `examples/` entries per primary language (TypeScript, Python, Go) showing how preflight scripts and language-specific skills look.
- A full consumer repo example. CanvasOS will become the canonical example once Phase 0 ships there; for now, refer to `https://github.com/Dopomogai/CanvasOS` (private during early development).
