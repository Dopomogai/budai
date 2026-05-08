# Permissions (base)

The permission baseline for the five default roles. Repos can tighten in `local/permissions.md` (e.g., disable `network-fetch` for offline-only work). Repos cannot loosen — the base is the maximum.

Full permission taxonomy and runner enforcement details: `docs/20-permissions-and-security.md`.

## Permission taxonomy

| Permission | Description |
|---|---|
| `read` | Read files within the agent's CWD |
| `write` | Write or edit files within the agent's CWD |
| `write-task-body` | Append plan section to task body in `tasks/open/` |
| `write-decisions` | Create files in `memory/decisions/` |
| `spawn-tasks` | Call `bin/task new` to create new task files |
| `run-preflight` | Execute `bin/preflight` |
| `run-tests` | Execute the repo's test suite via `bin/run-tests` |
| `run-arbitrary-bash` | Execute shell commands not in the bin/ catalog |
| `git-commit` | Commit to the integrating branch |
| `git-worktree` | Manage worktrees (create, remove) |
| `network-fetch` | Make outbound HTTP requests |
| `exec-installed` | Run installed dev tools (linters, formatters) |

Implicit permissions (granted to all roles regardless of declared list):

- Read the role's own frontmatter and body.
- Read the bundle assigned to the current task.
- Read the task definition.
- Write to the role's own `runs/<run-id>/` directory.

Forbidden operations (blocked for all roles):

- Writing to `base/` (registry's responsibility).
- Writing to other agents' worktrees.
- Writing to files outside the repo (`~/.ssh/*`, `/etc/*`).
- Modifying `manifest.yaml` or `manifest.lock.yaml` programmatically.
- Modifying `.git/config` or git internals beyond worktree management.

## Per-role baselines

### planner

```yaml
permissions: [read, write-task-body, write-decisions, spawn-tasks, run-preflight]
```

Reads the bundle, task body, and any referenced files. Writes to the task body (plan section) and to `memory/decisions/` (ADRs). Spawns sub-tasks via `bin/task new` when decomposing. No source code editing.

### implementer

```yaml
permissions: [read, write, run-tests, run-preflight, exec-installed]
```

Reads everything in its worktree. Writes to source files in its worktree. Runs tests. Executes installed dev tools (linters, formatters) for its language. No git-commit (Judge integrates), no network-fetch by default, no spawn-tasks.

### verifier

```yaml
permissions: [read, run-tests, run-preflight, exec-installed]
```

Reads attempts and source. Runs tests and evidence-capture tools (Playwright, etc., via `exec-installed`). No write permission — Verifier doesn't modify source. Does write to `runs/<run-id>/evidence/` and `runs/<run-id>/failure.md` via implicit run-directory permission.

### judge

```yaml
permissions: [read, write, git-commit, spawn-tasks, run-preflight]
```

Reads council/, attempts, reviews, verifier reports. Writes verdict.md. Commits the winning patch (via `git-commit`). Spawns auto-follow-up tasks (test coverage, address-concerns, etc.).

### librarian

```yaml
permissions: [read, write, run-preflight, spawn-tasks]
```

Reads everything. Writes to `docs/`, `index/`, `memory/lessons/`, `stats/`, `messages/`, and bundles in `tasks/open/`. Spawns tasks for improvement work, doc updates, etc. No source code editing.

## Permission combinations and what they enable

A few notable combinations:

- **`read` + `write` (within worktree)** — full source editing. Implementer needs this.
- **`read` + no `write`** — observer-only. Verifier's posture; can't modify source.
- **`write-task-body` without `write`** — can append to task files but not edit source. Planner's posture.
- **`git-commit` without `write` to source** — the rare case. Judge has this; integrates patches without authoring source itself.

## What runners enforce

The runner translates these permissions into platform-specific tool allowlists. Per `docs/15-framework-agnostic.md` and the `claude-code` runner spec:

- `read` → `Read` tool.
- `write` → `Edit`, `Write` tools.
- `run-tests` → `Bash` tool, restricted to `bin/run-tests` invocation.
- `run-preflight` → `Bash` tool, restricted to `bin/preflight` invocation.
- `run-arbitrary-bash` → `Bash` tool fully allowed.
- `exec-installed` → `Bash` tool, restricted to declared dev-tool paths.
- `git-commit` → `Bash` tool allowed for `git commit` commands.
- `git-worktree` → `Bash` tool allowed for `git worktree` commands.
- `network-fetch` → `WebFetch`, `WebSearch` tools.
- `spawn-tasks` → `Bash` tool, restricted to `bin/task new` invocation.

When a permission is missing, the corresponding tool is blocked. Block-list violations should be impossible by construction.

## Local overrides

Consumer repos can tighten permissions in `local/permissions.md`. Examples:

```yaml
# Tighten to disable network for everyone
implementer:
  override-remove: [exec-installed]   # if you have a strict no-shellouts policy

verifier:
  override-remove: [run-tests]        # if you have a non-bash test runner

global:
  forbidden:
    - network-fetch                   # never allow outbound HTTP
```

Tightening is allowed; loosening is not. A `local/permissions.md` that tries to add `network-fetch` to a role that didn't have it gets rejected at validation.

## Consumer repo override mechanics

`bin/agent run` reads:
1. `base/permissions.md` for the baseline.
2. `local/permissions.md` for tightening.
3. Role frontmatter `permissions:` for per-role intersection.

The effective permission set is `(base ∩ role) - local-removals - global-forbidden`. The runner enforces the effective set.

## Future permissions (placeholder)

Anticipated additions in later versions:

- `read-secrets` — explicit access to credential stores (currently blocked entirely; access via env vars or runner-specific credential helpers).
- `read-other-runs` — for Debugger sub-mode of Verifier needing cross-run pattern analysis.
- `write-template-files` — currently restricted to humans; might be needed for future template-generation skills.

These are not in the v1.0.0 baseline; they'll appear in major bumps if needed.
