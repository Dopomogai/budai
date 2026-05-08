---
skill: audit-docs
version: 1.0.0
tier-override: sonnet
inputs:
  - changed-files-list
  - src-tree
  - docs-tree
  - file-headers
outputs:
  - drift-findings
  - auto-fix-patches
  - follow-up-tasks
breaking-changes-from: null
stability: stable
owners: [librarian]
---

# audit-docs

Detect drift between prose claims and current code. High-confidence drift is auto-fixed; low-confidence drift opens tasks for human review.

## When to use

Invoked by the Librarian during the post-task sweep. Also invoked in the daily scheduled run with stricter thresholds.

## Inputs

- **changed-files-list** — files modified in the closing task (or recent commits in scheduled mode).
- **src-tree** — current source tree state.
- **docs-tree** — `docs/` directory plus all README.md files.
- **file-headers** — `index/detailed.md`, the source of truth for what each file claims to do.

## Procedure

1. For each file in `changed-files-list`:
   - Read its current header. Compare against the index entry. If the file changed materially (signature change, exports added/removed) but the header didn't update, flag.
   - Auto-fix simple cases: rename in `@exports`, update `@uses` if imports changed.
   - Open task for non-trivial cases: rewriting `@purpose` or `@why` based on observed behavior changes.
2. For each directory containing changed files:
   - Read the directory's `README.md` (if present).
   - Check claims: "this directory contains X" — is X still here? "Each Y does Z" — does Z still hold?
   - Auto-fix simple cases: removed-file references.
   - Open task for non-trivial cases: architectural prose contradicted by current code.
3. For top-level docs (`docs/architecture.md`, `docs/00-overview.md`, etc.):
   - Grep for symbols mentioned in the doc. Verify they exist in current code.
   - Flag deleted symbols as findings.
   - Auto-fix only when the change is unambiguous (renames). Open tasks for everything else.
4. For ADRs in `memory/decisions/`:
   - Check that the decision the ADR documents is still in effect. Look for code patterns that contradict it.
   - Don't auto-fix ADRs (they're immutable once accepted). Open task for human review if a contradiction is found — the resolution is either updating the code (the ADR still stands) or writing a superseding ADR (the decision changed).
5. Compile findings:
   - **Auto-fix patches**: high-confidence diffs to apply (renames, removed-symbol references).
   - **Follow-up tasks**: low-confidence findings opened as `update-docs-<topic>` tasks.
6. Write findings summary to `messages/channels/ops.md` for the next sweep.

## Outputs

- **drift-findings** — list of {file, finding, confidence, suggested-action}.
- **auto-fix-patches** — patches applied directly to files (committed in the same sweep).
- **follow-up-tasks** — tasks opened via `bin/task new` for human-reviewed fixes.

## Failure modes

- **Index out of date.** Regenerate `index/detailed.md` first; don't audit against stale index.
- **Symbol grep ambiguous.** A symbol name appears in multiple files; can't determine which is the real "delete." Open a task; let human disambiguate.
- **Doc references something never existed.** A claim that no symbol matches. Could be aspirational text or a typo. Flag for review; don't auto-remove (might be intentional).

## Examples

For a task that renamed `BrowserWidgetShapeUtil` to `BrowserWidgetNode`:

```markdown
## audit-docs findings — task 042

### Auto-fixed (3 patches)
- `docs/architecture.md`: replaced `BrowserWidgetShapeUtil` → `BrowserWidgetNode` (3 occurrences).
- `src/renderer/components/shapes/BrowserWidget/README.md`: updated symbol name.
- `index/detailed.md`: regenerated (header reflects rename).

### Opened follow-up tasks (1)
- `update-docs-canvas-engine.md` (low confidence): `docs/architecture.md` describes "tldraw integration" but code has migrated to React Flow. Architectural prose needs rewrite — beyond a simple rename.

### No-action findings (1)
- `memory/decisions/0003-react-flow-over-tldraw.md`: the migration ADR is still accurate. No update needed; the rename is consistent with the decision.
```

## Anti-patterns

- **Auto-fixing low-confidence cases.** When in doubt, open a task. Wrong auto-fixes are harder to recover from than missed audit findings.
- **Ignoring ADR contradictions.** ADRs document why decisions were made; code that contradicts an ADR signals a process gap. Surface it for human review.
- **Skipping the daily sweep when per-task sweeps run.** The daily sweep catches cross-task patterns the per-task sweep misses.
- **Editing ADRs.** ADRs are immutable. If a decision changed, write a superseding ADR.

## References

- `docs/06-memory.md` — ADR lifecycle and conventions structure.
- `docs/02-structure.md` — file header format.
- `base/skills/regenerate-index.md` — runs before audit-docs to ensure fresh index.
