# Conventions recipes

Common conventions consumer repos often want, formatted for copy-paste into `local/conventions.md`. Use what fits; ignore what doesn't.

These are NOT applied automatically. They're starter content. The base conventions in `base/conventions.md` ship; these recipes are guidance for adapting `local/conventions.md`.

## Recipe: TypeScript + React project

```markdown
## File naming
- React components: PascalCase, one per file (`MyComponent.tsx`).
- Hooks: camelCase with `use` prefix (`useCanvasStore.ts`).
- Utility files: kebab-case (`url-helpers.ts`).
- Test files: same name as source + `.test.ts` suffix, colocated.

## React component structure
- Default export at the bottom.
- Props interface defined above the component.
- Hooks at the top of the function body.
- JSX at the bottom of the function body.
- Memoization (useMemo, useCallback) only when profiling shows need.

## State management
- Zustand for cross-component shared state.
- Local component state (useState) for component-internal concerns.
- No new React Contexts unless the state truly belongs to a tree.

## Side effects
- useEffect with explicit dependencies (no `[]` shortcut for "run once" — use ref-based init pattern).
- Every useEffect that subscribes, starts a timer, or owns a resource MUST return a cleanup function.

## Imports
- External imports first (alphabetical).
- Blank line.
- Internal absolute imports next (`@/...`).
- Blank line.
- Relative imports last (`./...`).
```

## Recipe: Python project

```markdown
## File naming
- Modules: snake_case (`user_service.py`).
- Test files: `test_<module>.py` in the same directory or in `tests/` mirroring source structure.
- Private modules: prefix with `_` (`_internal_helpers.py`).

## Imports
- Standard library first.
- Third-party next.
- Local imports last.
- Within each group: alphabetical.
- Avoid wildcard imports (`from foo import *`).

## Type hints
- Public functions have type hints. Internal helpers can omit if obvious.
- Use `from __future__ import annotations` to defer evaluation.
- Prefer `list[X]` over `List[X]` (3.9+).

## Error handling
- Boundaries (API entry points, CLI entry points, IPC handlers) raise on invalid input.
- Internal functions assume valid inputs.
- Custom exception types for distinct error categories.
- No silent `except: pass`.
```

## Recipe: Go project

```markdown
## File naming
- snake_case for filenames (Go convention).
- One package per directory.
- `_test.go` suffix for test files.

## Error handling
- Errors are values; check explicitly.
- No panics in library code; panic only for unrecoverable startup conditions.
- Custom error types implement `error` interface.
- Wrap errors with `fmt.Errorf("...: %w", err)` to preserve chain.

## Naming
- Exported names: PascalCase.
- Internal names: camelCase (start with lowercase).
- Acronyms in names: all caps (`URL`, not `Url`).
```

## Recipe: Electron app (main + renderer + preload)

```markdown
## IPC channel naming
- kebab-case channels (`terminal:spawn`, `widget:resize`).
- Namespace prefix per subsystem.
- Imperative mood for actions; past tense for events.

## Process boundaries
- Main process: privileged operations (filesystem, native modules, OS dialogs).
- Renderer: UI only; no direct filesystem access.
- Preload: thin contextBridge exposing IPC namespaces; no business logic.

## Native modules
- Run `electron-rebuild` after install.
- Document native deps in package.json with comment marker.
- Native modules import only in main process.
```

## Recipe: cleanup-conscious repos

```markdown
## Cleanup discipline
- Subscriptions, timers, file handles, network connections must be torn down explicitly.
- React: every useEffect that creates a resource returns a cleanup function.
- Background workers: every spawn has a corresponding `.kill()` path.
- Database connections: pool with explicit close on shutdown.
- Tests: teardown what they create; use `beforeEach`/`afterEach` consistently.
```

## How to use these recipes

1. Read your codebase. See which patterns are already followed.
2. Pick the recipes that match your reality (or partially-match — adapt).
3. Copy the relevant sections into `local/conventions.md`.
4. Edit to match your specific patterns.
5. The Librarian's `discover-standards` skill (run during onboarding) drafts conventions from your codebase; combine with these recipes.

## Adding new recipes

When your repo discovers a convention pattern that other budai users would benefit from, propose adding a recipe via PR to the budai registry. Recipes are versioned with the registry; they ship in `base/templates/local-conventions-recipes.md`.
