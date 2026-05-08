# 02 — Structure

The `.agents/` directory is budai's payload in a consumer repo. It contains everything an agent needs to know about how this repo works. This document specifies the layout.

## Top-level: where `.agents/` sits

```
<consumer-repo>/
├── AGENTS.md                ← entry point. Every agent reads this first.
├── CLAUDE.md                ← one-line pointer to AGENTS.md
├── .agents/                 ← budai operating system (this document specifies it)
├── docs/                    ← human-facing documentation
├── tasks/                   ← task definitions
└── src/                     ← product code
```

`AGENTS.md` and `CLAUDE.md` are at repo root because that's where AI coding tools look for them. Everything else lives under `.agents/`.

## The `.agents/` layout

```
.agents/
├── manifest.yaml            ← declares budai version + included skills/roles/workflows
│
├── base/                    ← READ-ONLY; pulled from the budai registry
│   ├── roles/
│   │   ├── planner.md
│   │   ├── implementer.md
│   │   ├── verifier.md
│   │   ├── judge.md
│   │   └── librarian.md
│   ├── skills/
│   │   ├── build-task-bundle.md
│   │   ├── peer-review.md
│   │   ├── capture-evidence.md
│   │   ├── audit-docs.md
│   │   ├── run-preflight.md
│   │   ├── discover-standards.md
│   │   └── ...
│   ├── workflows/
│   │   ├── ship-feature.md
│   │   ├── fix-bug.md
│   │   ├── refactor.md
│   │   └── audit-repo.md
│   ├── conventions.md       ← language-agnostic baseline conventions
│   └── permissions.md       ← role permission baseline
│
├── local/                   ← repo-specific; edited freely
│   ├── roles/               ← overrides (same name as base) or new roles
│   ├── skills/              ← repo-specific skills (e.g., add-widget for CanvasOS)
│   ├── workflows/           ← repo-specific workflow variants
│   ├── conventions.md       ← merged with base/conventions.md
│   ├── untouchables.md      ← things that look weird but must not change
│   └── glossary.md          ← repo-specific terms
│
├── memory/                  ← always local; durable knowledge
│   ├── decisions/           ← ADRs, one .md per decision
│   ├── lessons/             ← what worked, what didn't
│   └── README.md
│
├── runs/                    ← per-run transcripts and diffs (gitignored; backend-streamed)
│   └── <run-id>/
│       ├── meta.json
│       ├── transcript.md
│       ├── diff.patch
│       └── evidence/
│
├── council/                 ← per-task multi-attempt records (gitignored; backend-streamed)
│   └── <task-id>/
│       ├── dispatch.json    ← who was dispatched, with what opaque IDs
│       ├── attempts/
│       │   ├── attempt-A.md
│       │   ├── attempt-B.md
│       │   └── attempt-C.md
│       ├── reviews/
│       │   ├── review-X.md
│       │   └── review-Y.md
│       ├── mapping.json     ← de-anonymization map
│       └── verdict.md
│
├── messages/                ← async coordination (gitignored; backend-streamed)
│   ├── channels/
│   │   ├── tasks.md
│   │   ├── review.md
│   │   ├── ops.md
│   │   └── decisions.md
│   └── threads/
│
├── stats/                   ← auto-generated; machine-readable
│   ├── roles.json
│   ├── skills.json
│   ├── tasks.json
│   └── repo.json
│
├── index/                   ← auto-generated; navigation aids
│   ├── tree.md              ← short index: just file paths
│   ├── tree.json
│   ├── detailed.md          ← expanded index: file paths + headers
│   └── detailed.json
│
├── runners/                 ← thin shims for specific agent platforms
│   ├── claude-code.md
│   ├── codex.md             ← later
│   └── direct-anthropic.md  ← later
│
├── preflight.sh             ← runs before any agent starts work
└── postflight.sh            ← runs after any agent declares done
```

## Resolution rules

### Base/local overlay

When the runtime needs a skill, role, or workflow named `X`:

1. Check `local/<dir>/X.md` — if present, use it.
2. Otherwise check `base/<dir>/X.md` — use it.
3. Otherwise error: skill/role/workflow not found.

Local wins. Same-name in `local/` is an override; new names in `local/` are repo-specific extensions.

### Conventions merging

`base/conventions.md` and `local/conventions.md` are concatenated, with local appended after base. Local conventions override base on conflict (the agent reads top-to-bottom and the later statement wins).

### Untouchables and glossary

Always local; no base equivalent. These are repo-specific by definition.

## Tasks layout

```
tasks/
├── README.md            ← explains the convention
├── TEMPLATE.md          ← copy-paste shape for new tasks
├── open/                ← active or queued tasks (status in frontmatter)
│   └── <NNN>-<slug>.md
└── archive/             ← shipped or abandoned
    └── <NNN>-<slug>.md
```

Status lives in frontmatter, not folders. Folder = lifecycle stage (open vs archive). Frontmatter `status:` = fine-grained state (open / planning / implementing / reviewing / done / abandoned).

Bundle files live next to their task: `tasks/open/042-add-terminal-widget.bundle.md`.

## Tasks frontmatter schema

```yaml
---
id: 042
title: Add terminal widget
type: feature                # feature | bug | refactor | research
scope: renderer              # high-level area
status: open                 # open | planning | implementing | reviewing | done | abandoned
fan-out: 1                   # how many parallel implementer attempts
needs-architect: true
plan-approved: false
result-approved: false
trivial: false               # affects auto-approve gates
depends-on: [041]
created: 2026-05-08T10:00:00Z
created-by: andrey
---
```

## Manifest schema

```yaml
budai-version: 0.4.2
included:
  roles:     [planner, implementer, verifier, judge, librarian]
  skills:    [build-task-bundle, peer-review, capture-evidence, audit-docs, run-preflight]
  workflows: [ship-feature, fix-bug, refactor]
overrides:
  conventions: local/conventions.md
local-only:
  skills:    [add-widget, add-ipc-channel]
runner: claude-code
human-gates:
  - end-of-planner
  - end-of-judge
```

The manifest is the contract between the consumer repo and budai. Everything in `base/` is reproducible from `manifest.yaml` + the registry.

## What lives in git, what doesn't

**In git:**
- `manifest.yaml`
- `base/` (read-only mirror of registry; tracked so checkouts are reproducible)
- `local/`
- `memory/`
- `runners/`
- `preflight.sh`, `postflight.sh`
- File header comments in `src/`
- All READMEs

**Gitignored, streamed to backend:**
- `runs/`
- `council/`
- `messages/`
- `stats/`
- `index/` (regenerated on demand)

The split is durability-vs-runtime. Anything an agent might read to understand the repo is in git. Anything generated as a side effect of agents running is ephemeral.

## File headers in `src/`

Every source file gets a six-field header (one optional):

```ts
/**
 * @purpose <one line — what this file does>
 * @why <one line — why it exists / what problem it solves>
 * @role <agent role that normally owns this>
 * @exports <names>
 * @uses <internal modules>
 * @stability stable | experimental | deprecated
 * @gotchas <only when non-obvious>
 */
```

The Librarian reads these to build `index/detailed.md`. The Briefer skill (run during bundling) uses them to score relevance.

## READMEs

Every meaningful directory in `src/` and `docs/` gets a `README.md` describing what's in it. Aim for 20–30 across the repo. The Librarian regenerates `docs/READMEs.md` (a concatenated bundle) on each sweep.
