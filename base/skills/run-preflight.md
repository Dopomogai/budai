---
skill: run-preflight
version: 1.0.0
tier-override: haiku
inputs:
  - repo-root
outputs:
  - preflight-report
breaking-changes-from: null
stability: stable
owners: [planner, implementer, verifier, judge, librarian]
---

# run-preflight

Validate repo state before any agent work. The thin wrapper around `bin/preflight`.

If preflight fails, the calling role aborts with a structured error rather than building on rotten ground. This is the mandatory first step in every role's workflow.

## When to use

Invoked at the start of every role's workflow. Required.

## Inputs

- **repo-root** — the directory the calling role is operating in. For Implementers and Verifiers in fan-out, this is their isolated worktree (`runs/<run-id>/worktree/`). For everyone else, it's the consumer repo's root.

## Procedure

1. Execute `bin/preflight` from `repo-root`.
2. Capture stdout, stderr, exit code.
3. Parse output into a structured report:
   - `passed: true | false`
   - `findings: list of {check, severity, message}`
4. Return the report.

The preflight script's checks (Phase 0 baseline; expandable):

- No `.orig` files in source.
- `.env` not tracked in git.
- AGENTS.md exists at repo root.
- `.agents/manifest.lock.yaml` matches `.agents/base/` content (no manual base/ edits).
- All source files in `src/` have headers (the six required fields present, even if some are minimal).
- No untracked files outside `.gitignore` patterns.
- The git working tree is in a known state (no rebase in progress, no merge conflicts).

For Implementer / Verifier in worktrees, the checks are scoped to the worktree (the consumer repo's full state isn't validated).

## Outputs

- **preflight-report** — `{ passed: bool, findings: [{check, severity, message}] }`.

## Failure modes

- **`bin/preflight` script doesn't exist.** Phase 0 hasn't been completed in this consumer repo. The calling role aborts with a clear "budai not installed" error.
- **Findings present.** The report includes the findings; the calling role decides whether to abort. Default behavior: abort if any finding has severity `error`. Severity `warning` is reported but doesn't block.
- **`bin/preflight` hangs.** Default timeout 30 seconds. If exceeded, the runner kills the process and reports timeout.

## Examples

```json
{
  "passed": false,
  "findings": [
    {"check": "no-orig-files", "severity": "error", "message": "Found 3 .orig files: src/main/index.ts.orig, src/renderer/store/useCanvasStore.ts.orig, src/renderer/components/shapes/BrowserWidget/BrowserWidgetNode.tsx.orig"},
    {"check": "env-not-tracked", "severity": "error", "message": ".env is tracked in git"},
    {"check": "headers-present", "severity": "warning", "message": "12 source files missing header (run bin/librarian add-headers)"}
  ]
}
```

The calling role aborts because of the two `error` findings; the warning is logged but not blocking.

## Anti-patterns

- **Skipping preflight.** Mandatory first step; the runner enforces it.
- **Treating warnings as errors.** Warnings inform; don't reject runs over them. (The audit-docs sweep handles non-blocking issues.)
- **Adding repo-specific checks to base preflight.** Base preflight runs everywhere; repo-specific checks belong in `local/preflight-extensions.sh` (Phase 0+).

## References

- `docs/02-structure.md` — what `bin/preflight` validates.
- `docs/14-failure-loop.md` — what happens when preflight fails (calling role aborts; not a retry-eligible failure).
