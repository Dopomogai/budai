---
skill: regenerate-index
version: 1.0.0
tier-override: haiku
inputs:
  - src-tree
  - existing-index
outputs:
  - tree-md
  - tree-json
  - detailed-md
  - detailed-json
breaking-changes-from: null
stability: stable
owners: [librarian]
---

# regenerate-index

Walk `src/` reading file headers, emit four index files. Mechanical; cheap; runs frequently.

## When to use

Invoked by the Librarian during the post-task sweep. Also runs on demand via `bin/librarian index`. Required after any change touching source files.

## Inputs

- **src-tree** — current source tree state.
- **existing-index** — `index/detailed.md` if present. Used only for diff comparison; the regeneration always rebuilds from scratch.

## Procedure

1. Walk `src/` (and any other configured source roots) recursively.
2. For each source file (`.ts`, `.tsx`, `.py`, `.go`, `.rs`, etc. — extensions configurable):
   - Parse the header comment block. Extract `@purpose`, `@why`, `@role`, `@exports`, `@uses`, `@stability`, `@gotchas` (if present).
   - If header is missing, flag in the regeneration report. Don't fail; continue.
3. Build `tree.md`: file paths only, hierarchical with indentation. ~1 line per file.
4. Build `tree.json`: machine version of tree.md. `{"src/main/index.ts": {}, "src/preload/index.ts": {}, ...}`.
5. Build `detailed.md`: file paths plus header fields. ~5-7 lines per file.
6. Build `detailed.json`: machine version of detailed.md. Schema:
   ```json
   {
     "src/main/index.ts": {
       "purpose": "Main process entry; window creation, IPC handlers",
       "why": "Electron requires a main process; this is its single bootstrap",
       "role": "implementer",
       "exports": ["createMainWindow"],
       "uses": ["TerminalManager"],
       "stability": "stable",
       "gotchas": "..."
     }
   }
   ```
7. Write all four files to `.agents/index/`.
8. Output a regeneration report: file count, files-with-missing-headers count, time elapsed.

## Outputs

- **tree-md** — `.agents/index/tree.md`.
- **tree-json** — `.agents/index/tree.json`.
- **detailed-md** — `.agents/index/detailed.md`.
- **detailed-json** — `.agents/index/detailed.json`.

## Failure modes

- **Files with missing headers.** Don't fail; flag in the report. The Librarian sweep can use `bin/librarian add-headers --interactive` to fill them in.
- **Source files with malformed headers.** Treat as missing; flag specifically (it's likely a parse error worth the human seeing).
- **Source root not configured.** If `src/` doesn't exist, check for alternate roots in `manifest.yaml` (e.g., `src-roots: [packages/, apps/]`). Failing that, halt with a clear error.

## Examples

`tree.md` excerpt:

```markdown
# Source tree

## src/main/
- src/main/index.ts (245 lines)
- src/main/TerminalManager.ts (189 lines)

## src/preload/
- src/preload/index.ts (87 lines)

## src/renderer/
### src/renderer/components/
- src/renderer/components/SpatialCanvas.tsx (320 lines)
- src/renderer/components/widgets/BrowserWidgetNode.tsx (210 lines)
- src/renderer/components/widgets/TerminalWidgetNode.tsx (185 lines)
```

`detailed.md` excerpt:

```markdown
## src/main/TerminalManager.ts
- @purpose: Owns lifecycle of node-pty processes per terminal widget.
- @why: PTY lifecycle in main for security; renderer talks via IPC.
- @role: implementer
- @exports: TerminalManager
- @uses: node-pty
- @stability: stable
- @gotchas: Must call electron-rebuild on install; native module.
```

## Anti-patterns

- **Reading file bodies, not just headers.** The skill is header-only. Body content is the bundler's concern.
- **Skipping files without headers.** Track them in the report; the Librarian's add-headers flow uses this list.
- **Auto-fixing missing headers.** This skill doesn't write source files. `bin/librarian add-headers` does that, with interactive confirmation.

## References

- `docs/02-structure.md` — file header format.
- `base/skills/audit-docs.md` — runs after regenerate-index to detect drift.
- `base/skills/build-task-bundle.md` — reads detailed.md for relevance scoring.
