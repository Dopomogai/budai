---
skill: discover-standards
version: 1.0.0
tier-override: sonnet
inputs:
  - src-tree
  - existing-conventions
outputs:
  - conventions-draft
breaking-changes-from: null
stability: stable
owners: [librarian]
---

# discover-standards

Walk the codebase and extract implicit conventions. Used during onboarding (per `docs/21-onboarding.md`) when applying budai to an existing repo for the first time.

The output is a draft. Drafts are starting evidence, not policy. Humans review and finalize.

## When to use

Invoked once per repo at onboarding (Phase B1 of `docs/21-onboarding.md`). May be re-invoked if the codebase materially changes (e.g., a major refactor or framework migration).

## Inputs

- **src-tree** — current source tree state.
- **existing-conventions** — `local/conventions.md` (if any). The skill won't duplicate existing conventions.

## Procedure

1. Sample files across the codebase. Don't read everything — sample N files per directory (configurable; default 5) prioritizing files with `@stability: stable` headers when present.
2. For each language detected (TypeScript, Python, Go, etc.), extract:
   - **File naming patterns.** Are files `kebab-case`, `camelCase`, `PascalCase`? Are there exceptions (component files vs. utility files)?
   - **Import organization.** Do imports group by source (external / internal)? Alphabetical within groups? Are absolute imports preferred over relative?
   - **Error handling idioms.** Do functions throw, return Result types, return null, log-and-continue? Are there patterns by layer (boundaries throw, internal pass through)?
   - **Test placement.** Are tests colocated (`*.test.ts` next to source) or in a separate directory?
   - **Documentation patterns.** Inline JSDoc/PyDoc? Header comments? README per directory?
   - **Variable naming.** Hungarian notation? `_private` prefix? `is`/`has` prefix for booleans?
3. For shared concerns (cross-language):
   - **IPC channel naming** (if applicable).
   - **Logging format and verbosity.**
   - **Configuration management** (env vars vs config files vs runtime args).
4. Filter findings:
   - Keep patterns observed in ≥80% of relevant files (configurable threshold).
   - Drop patterns that already appear in `existing-conventions` (don't duplicate).
   - Drop patterns that are obvious universals (e.g., "files are utf-8 encoded").
5. Draft `local/conventions.md` content:
   - Use markdown sections per concern category.
   - State each convention as a rule (not a description): "Files use kebab-case" not "files seem to use kebab-case."
   - Include 1-2 examples for each non-obvious convention.
   - Tag uncertain findings with `<!-- CONFIRM: -->` HTML comments for human review.
6. Output the draft. Don't overwrite `local/conventions.md` directly — the human reviews and chooses what to keep.

## Outputs

- **conventions-draft** — markdown content suitable for `local/conventions.md`. Saved to `local/conventions-draft.md` for human review.

## Failure modes

- **Codebase too small for sampling.** Fewer than 10 source files total. Skip the skill; manual conventions authoring is more reliable.
- **Codebase too inconsistent.** No pattern reaches the 80% threshold. Drop the threshold to 60%, output what's there with `<!-- CONFIRM -->` tags on everything.
- **Multi-language repos.** Run the skill per language; output a draft section per language. Don't try to unify conventions across languages.

## Examples

For a TypeScript + React codebase:

```markdown
# Conventions (DRAFT — review before merging)

## File naming
- Components: PascalCase, one per file (`MyComponent.tsx`).
- Hooks: camelCase with `use` prefix (`useCanvasStore.ts`).
- Utility files: kebab-case (`url-helpers.ts`).
- Test files: same name as source + `.test.ts` suffix, colocated.

<!-- CONFIRM: Some hook files use kebab-case (e.g., `use-canvas-store.ts`); is this an exception or transitional state? -->

## Import organization
- External imports first (alphabetical).
- Blank line.
- Internal absolute imports next (`@/...`).
- Blank line.
- Relative imports last (`./...`).

## Error handling
- Boundaries throw (API layer, IPC handlers).
- Internal functions return values; errors bubble through throws.
- React error boundaries catch render errors.
- No silent failures — every catch logs.

## React component structure
- Default export at the bottom.
- Props interface defined above the component.
- Hooks at the top of the function body.
- JSX at the bottom of the function body.
```

## Anti-patterns

- **Drafting overconfident conventions.** Drafts are starting points. Tag uncertainty with `<!-- CONFIRM -->`; the human disambiguates.
- **Inferring conventions from one file.** Sampling matters. A pattern visible only in one file isn't a convention.
- **Including inferred best practices not in evidence.** If the codebase doesn't follow a pattern, don't add it to the draft just because you think it should. The human can add it during review.
- **Auto-merging the draft.** Always write to `local/conventions-draft.md`, never overwrite `local/conventions.md` directly.

## References

- `docs/21-onboarding.md` — when this skill is invoked during adoption.
- `docs/06-memory.md` — how conventions fit into the layered memory model.
- `base/skills/audit-docs.md` — runs after conventions land to verify consistency.
