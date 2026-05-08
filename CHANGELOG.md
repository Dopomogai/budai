# Changelog

All notable changes to budai (the registry) will be documented here. The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

This changelog covers the registry's published content (`base/`) and the design documentation. Per-consumer-repo changelogs are the consumer's responsibility.

Versioning follows semver per `docs/16-skill-versioning.md`. Skills, roles, workflows, and runners each version independently; the registry's own version (in tags like `v0.4.2`) tracks the overall release set.

## [Unreleased]

Phase 1 deliverables in progress: manual single-role validation in CanvasOS.

### Planned

- Apply budai to CanvasOS (consumer-side Phase 0): manifest, sync, AGENTS.md, file headers.
- Manual single-role validation per Phase 1.
- First synthetic task end-to-end.

## [0.2.0] — 2026-05-09

Phase 0 release: design phase closed plus all base/ content and bin/ CLI scripts.

### Added

- `docs/20-permissions-and-security.md` — permission taxonomy, runner enforcement, threat model.
- `docs/21-onboarding.md` — step-by-step adoption guide for existing repos.
- `base/roles/` — five role definition files (planner, implementer, verifier, judge, librarian).
- `base/skills/` — eight skill files (build-task-bundle, peer-review, audit-docs, run-preflight, capture-evidence, discover-standards, regenerate-index, promote-lesson).
- `base/workflows/` — four workflow files (ship-feature, fix-bug, refactor, audit-repo).
- `base/conventions.md` — language-agnostic baseline conventions.
- `base/permissions.md` — role permission baseline with runner translation.
- `base/runners/claude-code.md` — Claude Code runner shim spec.
- `base/templates/` — six templates for consumer repos (AGENTS.md, CLAUDE.md, local-conventions, local-untouchables, local-glossary, local-conventions-recipes).
- `bin/preflight` — repo-state validation script (Python).
- `bin/postflight` — post-run validation script (Python).
- `bin/task` — task management CLI (new, move, list).
- `bin/agent` — agent dispatch CLI (run --role X --task Y --runner Z).
- `bin/librarian` — librarian operations CLI (sync, publish, bundle, index, add-headers, sweep).
- `bin/lib/` — shared Python package (manifest, headers, resolution, runner).
- `bin/requirements.txt` — Python dependencies.

### Notes

- Phase 0 deliverables enable a consumer repo to adopt budai end-to-end. Real validation happens in Phase 1 (manual single-role tests against CanvasOS).
- Several `bin/librarian` subcommands are placeholders for Phase 1+ (sync, publish, bundle, add-headers). The structural scaffolding is in place; real implementations follow.
- All scripts respond to `--help` and `--version` and run without error in smoke tests.

## [0.1.0] — 2026-05-09

Initial public release. Design documentation only; no `base/` content yet.

### Added

- `README.md` with project overview and positioning relative to existing tools.
- `LICENSE` — Apache-2.0.
- `docs/00-overview.md` — what budai is, who it's for, key concepts.
- `docs/01-design-principles.md` — eight design principles (four from Karpathy's stack, four from extended design).
- `docs/02-structure.md` — full `.agents/` directory layout, base/local overlay, frontmatter schemas.
- `docs/03-roles.md` — five-role taxonomy with mission, reads, writes, escalation, compute tier.
- `docs/04-skills.md` — skill model, frontmatter schema, body sections, the eight standard skills.
- `docs/05-workflows.md` — workflow model, four default workflows, hand-off contracts, escalation rules.
- `docs/06-memory.md` — four-layer memory model with promotion paths.
- `docs/07-runtime-data.md` — full schemas for runs, council, messages, stats; backend streaming.
- `docs/08-the-journey.md` — twelve-step task lifecycle, the workhorse doc.
- `docs/09-bundle-format.md` — bundle YAML manifest schema, body structure, token budget logic.
- `docs/10-plan-format.md` — elaborate plan format, seven required sections, worked examples.
- `docs/11-task-format.md` — task frontmatter schema, status state machine, naming, validation.
- `docs/12-isolation-and-fanout.md` — worktree mechanics, opaque IDs, council folder layout, anonymization spec.
- `docs/13-evidence-capture.md` — evidence taxonomy by change type, ac-mapping.json schema.
- `docs/14-failure-loop.md` — failure.md schema, retry budget, cross-role escalation, lesson promotion.
- `docs/15-framework-agnostic.md` — runner abstraction, what stays portable vs runner-specific.
- `docs/16-skill-versioning.md` — semver rules, breaking-change taxonomy, manifest pin syntax, lockfile.
- `docs/17-registry-and-sync.md` — registry layout, librarian sync/publish flows, cross-repo coordination.
- `docs/18-implementation-phases.md` — eight-phase build sequence.
- `docs/19-glossary.md` — canonical terms.
- `docs/decisions/` — nine ADRs documenting load-bearing design choices, plus TEMPLATE.md.
- `examples/manifest-minimal.yaml` and `examples/manifest-full.yaml`.
- `CONTRIBUTING.md` — how to contribute skills, runners, docs, ADRs.

### Notes

- This release is documentation-only. There is no executable content yet. See `docs/18-implementation-phases.md` for the build sequence.
- Cross-references between docs are stable. Future commits filling in `base/`, runners, and scripts will not require doc rewrites.
- Consumer repos cannot adopt budai yet (Phase 0 tooling is the next milestone). The first consumer will be CanvasOS.
