# Conventions (base)

Language-agnostic baseline conventions shipped with budai. Consumer repos extend or override in `local/conventions.md` per `docs/02-structure.md` overlay rules.

These conventions are deliberately minimal. They capture practices that hold across virtually all software repos, regardless of language, framework, or domain. Repo-specific patterns belong in `local/conventions.md`.

## File naming

- **Files use kebab-case by default** (`my-module.ts`, not `myModule.ts`).
- **Exceptions for language idioms:** Python files use `snake_case.py`. Go files follow Go community style. React component files use `PascalCase.tsx` (in repos that ship React). Repo's `local/conventions.md` declares the exception.
- **One concept per file.** A file should have one primary export or one cohesive set of related exports. Files exporting unrelated things should split.
- **Tests live next to source** unless the language ecosystem strongly prefers otherwise. `foo.ts` + `foo.test.ts` colocated. Some ecosystems prefer `__tests__/` folders; the repo's `local/conventions.md` decides.

## Error handling

- **Throw at boundaries; pass through internally.** External API entry points, IPC handlers, CLI entry points throw on invalid input. Internal functions assume their preconditions.
- **No silent failures.** Every catch block does something — logs, returns a structured error, retries, or re-throws. Catch-and-ignore is a bug.
- **Errors are typed where the language supports it.** Don't throw bare strings; throw error objects with structured fields.
- **Don't catch `Error` (or equivalent base type) at boundaries.** Catch specific types; let unrecognized errors propagate.

## Naming

- **Identifiers describe what the thing is, not where it's called from.** `processOrder` not `handleOrderClick`.
- **Booleans use predicate prefixes.** `isReady`, `hasAccess`, `canEdit`. Avoid bare-noun booleans (`ready`, `access`).
- **Functions name what they return** (`getUserById`, `findActivePolicies`) or what they do (`renderTemplate`, `validateInput`). Avoid `do`, `process`, `execute` prefixes that don't add information.
- **Avoid Hungarian notation.** `userName` not `strUserName`. The type system carries types.

## Documentation

- **Header comments explain why, not what.** What the file does is in `@purpose`; why it exists is in `@why`. Avoid header comments that just restate the file name.
- **Inline comments explain non-obvious decisions.** Don't comment self-explanatory code. Do comment "this looks weird because of X" — those comments save future readers.
- **Public API has docstrings/JSDoc.** Internal helpers don't need them.
- **README per directory of meaningful size.** A directory with 5+ files of related code has a `README.md` explaining what's in it.

## Configuration

- **No config in code.** Magic constants get extracted to a config file or env var.
- **Default behavior is explicit.** A function that takes optional parameters has documented defaults. Behavior that depends on an env var has a documented fallback.
- **Secrets never in source.** `.env` is gitignored; `.env.example` shows the variables without values.

## Testing

- **Tests are named after behavior, not implementation.** `"throws when input is empty"` not `"calls validate with empty arg"`.
- **Test files mirror source structure.** `src/foo/bar.ts` → `src/foo/bar.test.ts`.
- **One assertion concept per test.** Multiple `expect(...)` calls are fine when they verify one behavior; split when they verify different ones.
- **Test independent state.** No shared state between tests; teardown what each test creates.

## Logging

- **Structured logs.** Level (debug/info/warn/error), timestamp, structured fields. Avoid `console.log("Got " + value)`.
- **Logs at boundaries.** Log when entering a public API; log when leaving (success or failure). Internal calls don't need logs.
- **Errors include context.** "Failed to fetch user" is incomplete; include the user ID, the request ID, the underlying error.

## Imports

- **External imports first** (alphabetical), blank line, **internal absolute imports next**, blank line, **relative imports last**.
- **Avoid deep relative imports.** `../../../foo` is a smell; reach for an absolute import or a re-export.
- **Don't re-export speculatively.** Re-exports add complexity; use them only when they simplify a public API.

## Comments

- **Don't comment obvious code.** A comment over a 3-line function that names the function is noise.
- **Comment surprising decisions.** A workaround for a specific bug, a non-obvious performance optimization, a constraint that's not visible in the code.
- **Don't leave commented-out code.** Delete it; git keeps history. Commented-out code rots and confuses.

## Concurrency

- **Cleanup on unmount/destruction.** Subscriptions, timers, owned resources must release. Don't rely on garbage collection.
- **Idempotent operations where possible.** A function that's safe to call twice is easier to reason about than one with state.
- **Race conditions are explicit.** If your code has a race, document it. Hidden races are bugs.

## Versioning (for shared content)

- **Semver for skills, roles, workflows, runners.** Per `docs/16-skill-versioning.md`.
- **Manifest pinning is explicit.** Don't pin `latest` in production manifests.

## What this file is NOT

- Not a style guide. Style (indentation, spacing, line length) is enforced by linters, not conventions.
- Not language-specific. Each language ecosystem has its own additional conventions; those go in `local/conventions.md` (or in language-specific repo's local).
- Not opinionated about taste. The conventions above are baseline minimums; teams can extend.

## How to extend

In your consumer repo's `local/conventions.md`, add sections per concern. Examples:

```markdown
# Conventions (local — CanvasOS)

## React component structure
- Default export at the bottom.
- Props interface above the component.
- Hooks at the top of the function body.

## IPC channel naming
- kebab-case channels (`terminal:spawn`, not `terminalSpawn`).
- Namespace prefix per subsystem.

## State management
- Zustand for shared state. No new contexts.
- ...
```

Local conventions take precedence on conflict (per `02-structure.md` resolution rules).
