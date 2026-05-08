---
skill: build-task-bundle
version: 1.0.0
tier-override: sonnet
inputs:
  - task-file
  - index-detailed
  - file-headers
  - conventions
  - glossary
  - decisions
outputs:
  - bundle-file
breaking-changes-from: null
stability: stable
owners: [librarian]
---

# build-task-bundle

Build a self-contained context bundle for a task. The bundle is read by the Planner first and by every Implementer instance during fan-out. Goal: 95% context coverage in one read.

Full bundle format spec: `docs/09-bundle-format.md`.

## When to use

Invoked at task entry (Step 2 of the journey, per `docs/08-the-journey.md`). Triggered when a task lands in `tasks/open/` with `status: open`. Re-invoked if the task is materially edited before plan approval, or on demand via `bin/librarian bundle <task-id>`.

## Inputs

- **task-file** — `tasks/open/<id>-<slug>.md`. Read frontmatter (especially `scope`, `type`, `files-to-touch` if specified) and body (objective, user story, AC).
- **index-detailed** — `.agents/index/detailed.md` (or `.json`). Source of truth for what files exist and what their headers say.
- **file-headers** — read individual file headers when relevance scoring suggests them. Don't read all of `src/`; rely on the index.
- **conventions** — `local/conventions.md` merged with `base/conventions.md`. Pull only sections relevant to the task's scope.
- **glossary** — `local/glossary.md`. Pull only entries for terms appearing in the task body.
- **decisions** — `memory/decisions/`. Pull ADRs whose scope matches the task's scope or whose subject keywords appear in the task body.

## Procedure

1. Parse task: extract `objective`, `user-story`, `acceptance-criteria`, `scope`, `type`, `files-to-touch` (if specified), and a keyword list from the body.
2. Score files in the index for relevance:
   - **Direct match** (file in `task.files-to-touch`): score 100.
   - **Direct import** (file imported by a `files-to-touch` file): score 80.
   - **Transitive import** (distance 2 from `files-to-touch`): score 50.
   - **Scope match** (file's `@purpose` or `@role` matches `task.scope`): score 60.
   - **Keyword match** (task title/body words in file's `@purpose` or filename): score 40 per keyword, capped at 80.
   - **Header gotchas bonus**: +10 if file has `@gotchas`.
   - **Stability penalty**: -30 if `@stability: deprecated`.
3. Add files to bundle in priority order until budget is reached:
   - `files-to-touch` (explicit, all of them)
   - `direct-import` files
   - `ipc-host` / `ipc-client` files (when task scope touches IPC)
   - `scope-match` ADRs from `memory/decisions/`
   - Directory READMEs touching changed files
   - Conventions sections relevant to scope keywords
   - Glossary terms appearing in task body
   - Related closed tasks (same scope, last 90 days, max 3)
   - Speculative additions (`similar-pattern` files for precedent)
4. Estimate tokens for each file (chars/4). Track running total against `budget.target-tokens` (default 80000, configurable per task).
5. When budget reached:
   - Stop adding to `included`.
   - For each remaining candidate, write a `referenced-but-not-included` entry with `reason:` and a one-line `hint:` (e.g., "Read if you need a precedent for X.").
   - Set `budget.status: trimmed`.
6. Write the bundle:
   - YAML frontmatter per `docs/09-bundle-format.md` schema.
   - Body sections in fixed order: Source files, Docs, Decisions, Related tasks, Conventions, Glossary, Footer (if overflow).
7. Save to `tasks/open/<id>.bundle.md`.
8. Validate the bundle's YAML frontmatter against the schema before returning.

## Outputs

- **bundle-file** — `tasks/open/<id>.bundle.md` with YAML frontmatter (manifest) + markdown body.

## Failure modes

- **Index out of date.** If `index/detailed.md` is older than `src/`'s newest mtime, regenerate the index first via `regenerate-index` skill.
- **Budget overflow without trim.** If you can't fit even the `files-to-touch` files within budget, the task is mis-scoped. Escalate via `messages/channels/escalations.md` to the Planner.
- **Missing task fields.** If `task-file` is missing `objective`, `user-story`, or `acceptance-criteria`, the task is invalid. Escalate to the human who created it (or to the Librarian's task-validation flow).

## Examples

For task 042 ("Add terminal widget", scope: renderer):

```yaml
---
task-id: 042
generated: 2026-05-09T10:30:00Z
generator-version: 1.0.0
budget:
  target-tokens: 80000
  actual-tokens: 76420
  status: ok
included:
  source-files:
    - { path: src/renderer/components/SpatialCanvas.tsx, tokens: 4200, reason: scope-match }
    - { path: src/main/index.ts, tokens: 6800, reason: ipc-host }
    - { path: src/preload/index.ts, tokens: 1200, reason: ipc-client }
    - { path: src/renderer/components/widgets/BrowserWidgetNode.tsx, tokens: 3200, reason: similar-pattern }
  docs:
    - { path: docs/architecture.md, tokens: 3100, reason: scope-match }
    - { path: src/renderer/components/README.md, tokens: 800, reason: dir-readme }
  decisions:
    - { path: memory/decisions/0003-react-flow-over-tldraw.md, tokens: 1200 }
  conventions:
    - section: ipc-naming
    - section: react-component-structure
  glossary:
    - widget
    - node
---
```

## Anti-patterns

- **Reading entire codebase to build bundle.** Use the index. The index is for this purpose.
- **Ignoring token budget.** Bundles over budget hurt downstream attempt quality. Trim and write hints.
- **Pulling whole conventions.md and glossary.md.** Pull only relevant sections / terms.
- **Skipping `referenced-but-not-included` hints.** Trimmed bundles need the overflow list — that's how Implementers know what's available if stuck.

## References

- `docs/09-bundle-format.md` — full bundle format specification.
- `docs/02-structure.md` — file header format used in the index.
- `docs/06-memory.md` — what's in `memory/decisions/` vs `local/conventions.md`.
