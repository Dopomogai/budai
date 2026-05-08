# 20 — Permissions and security

This document specifies budai's permission model, threat model, and the security guarantees the system provides — versus what's left to the runner, the org's infrastructure, or organizational policy.

Security in a multi-agent system is layered. budai's contributions are: per-role permission scoping, worktree isolation, audit-trail completeness, and redaction at the streaming boundary. Other layers (network access, credential storage, code-signing, key-rotation) are runner or org concerns.

## Permission taxonomy

Permissions are declared in role frontmatter as a list:

```yaml
---
role: implementer
permissions: [read, write, run-tests, run-preflight]
---
```

The vocabulary is intentionally small. New permissions are added cautiously — every permission is something a runner has to enforce, and every runner that ships needs to handle every permission consistently.

| Permission | What it grants | Typical roles |
|---|---|---|
| `read` | Read files within the agent's CWD (its worktree, for Implementers; the repo root for others) | All roles |
| `write` | Write or edit files within the agent's CWD | Implementer, Librarian (for index/docs/stats files), Judge (for verdict.md) |
| `write-task-body` | Append plan section to task body in `tasks/open/` | Planner |
| `write-decisions` | Create files in `memory/decisions/` | Planner |
| `spawn-tasks` | Call `bin/task new` to create new task files | Planner (for decomposition), Librarian (for follow-ups) |
| `run-preflight` | Execute `bin/preflight` | All roles (mandatory first step) |
| `run-tests` | Execute the repo's test suite via `bin/run-tests` (or equivalent) | Implementer, Verifier |
| `run-arbitrary-bash` | Execute shell commands not pre-defined in the bin/ catalog | Implementer (sometimes), Debugger sub-mode of Verifier |
| `git-commit` | Commit to the integrating branch (used only by Judge for integration) | Judge |
| `git-worktree` | Manage worktrees (create, remove) | Router (when fan-out spawns) |
| `network-fetch` | Make outbound HTTP requests | None by default; explicit opt-in per task |
| `exec-installed` | Run installed dev tools (linters, formatters) within their declared scope | Implementer, Verifier |

Permissions compose. A role with `read` and `write` can edit files; without `write`, it can only read.

### Implicit permissions

Some operations are always allowed regardless of declared permissions:

- Reading the role's own frontmatter and body
- Reading the bundle assigned to the current task
- Reading the task definition
- Writing to the role's own `runs/<run-id>/` directory (transcript, evidence)

These are operational requirements; restricting them would prevent the role from functioning at all.

### Forbidden operations

Some operations are blocked for all roles:

- Writing to `base/` — that's the registry's responsibility, not the consumer's
- Writing to other agents' worktrees — enforced by filesystem isolation
- Writing to files outside the repo (e.g., `~/.ssh/*`, `/etc/*`)
- Modifying `manifest.yaml` or `manifest.lock.yaml` programmatically (humans only)
- Modifying `.git/config` or other git internals beyond worktree management

Block-list violations should be impossible by construction (worktree isolation, runner permission enforcement). When they happen, it's a runner bug.

## Runner enforcement

Each runner translates budai permissions into the platform's enforcement primitives.

### Claude Code

Maps to `--allowed-tools` flag and the runner's CWD constraint:

| Permission | Claude Code mechanism |
|---|---|
| `read` | `Read` tool allowed |
| `write` | `Edit`, `Write` tools allowed |
| `write-task-body` | `Edit` tool allowed; runner-side validation that path matches `tasks/open/` |
| `run-preflight` | `Bash` tool allowed but restricted to `bin/preflight` invocation |
| `run-tests` | `Bash` tool allowed but restricted to `bin/run-tests` invocation |
| `run-arbitrary-bash` | `Bash` tool fully allowed |
| `git-commit` | `Bash` tool allowed for `git commit` and related |
| `network-fetch` | `WebFetch`, `WebSearch` tools allowed |
| `exec-installed` | `Bash` tool allowed for declared dev-tool paths |

Restricted-bash permissions wrap the actual command in a runner-side guard: when the role declares `run-tests`, the agent can `Bash run-tests` but not arbitrary commands. The guard rejects everything else.

### Future runners (Codex, direct SDK)

Each implements its own translation. The `runners/<name>.md` file specifies the mapping in its body. Cross-runner consistency is the registry maintainers' responsibility — when a new permission is added to budai, every shipped runner gets updated to handle it.

## Worktree isolation as a security boundary

Per ADR 0003 and `12-isolation-and-fanout.md`, each Implementer in a fan-out runs inside a `git worktree`. The worktree boundary is the strongest filesystem-level isolation budai provides:

- Implementer can't read other implementers' worktrees (different paths, runner constrains CWD)
- Implementer can't see sibling fan-out attempts during work (paths are not visible)
- Cleanup happens at Judge integration; no stale worktrees survive

This is also why strict anonymization (ADR 0004) is implementable: the Judge's context is the council folder, which contains only opaque IDs and content. The mapping back to identities lives in `mapping.json`, read post-verdict.

## Threat model

### What budai protects against

1. **Agent scope creep.** An agent goes off-script and tries to modify files outside its declared permissions. *Mitigation:* permission system + runner enforcement + worktree CWD.
2. **Cross-attempt influence.** One Implementer reads another's work during fan-out, biasing its output. *Mitigation:* worktree isolation makes the other work invisible.
3. **Reviewer bias from authorship.** The Judge prefers a specific model or runner regardless of attempt quality. *Mitigation:* strict anonymization + opaque IDs.
4. **Lost decision history.** Months later, nobody remembers why a choice was made. *Mitigation:* council folder, ADRs, verdicts, audit trail.
5. **Stale documentation.** Docs claim the system does X when the code does Y. *Mitigation:* `audit-docs` skill, Librarian sweep.
6. **Recurring failure modes.** The same bug ships three times. *Mitigation:* `promote-lesson` skill, lesson promotion path, conventions updates.
7. **Secret leakage in transcripts.** Tokens, credentials, paths get echoed in the run transcript and streamed to the backend. *Mitigation:* redaction at streaming layer; configurable per-repo redaction patterns.
8. **Skill regression on update.** A patch labeled compatible breaks consumers. *Mitigation:* per-version stats, lockfile, rollback procedures.

### What budai does NOT protect against

1. **Compromised agent platform.** If Claude Code itself is compromised, budai can't help. *Out of scope:* runner / vendor responsibility.
2. **Stolen API tokens.** Token stored in Keychain leaks via OS-level compromise. *Out of scope:* OS / runner credential management.
3. **Malicious skill content.** A registry contributor publishes a skill that exfiltrates data. *Mitigation:* registry-PR review + community signal — but not a hard guarantee.
4. **Social engineering of human gates.** A clever Planner output convinces the human to approve something they shouldn't. *Mitigation:* none platform-level — human discretion is the final gate.
5. **Side-channel inference.** Timing analysis, token-count analysis, etc., that infers things about other agents' work. *Mitigation:* none platform-level; mitigated by anonymization preventing the most obvious inferences.
6. **Collusion across registry forks.** Multiple forks coordinate on bad patterns. *Mitigation:* none architecturally; expected behavior is that the canonical registry remains trustworthy via maintainer discipline.
7. **Resource exhaustion.** A runaway agent consuming tokens. *Mitigation:* retry budgets, fan-out limits — but not unbounded defense.
8. **Network-level attacks.** Runner-to-platform traffic interception. *Mitigation:* TLS — runner / network responsibility.

The threat model deliberately excludes adversarial outsiders and adversarial registry contributors at the platform level. budai's security posture is "trustworthy contributors making honest mistakes." For higher-stakes deployments (client code, regulated workspaces), additional layers are needed:

- Self-hosted backend instead of the central one
- Private registry forks with stricter PR review
- Network egress controls at the runner level
- Audit log retention beyond budai's defaults

## Secret handling

Three layers of secret handling:

1. **At rest** — secrets live wherever the runner stores them (Keychain on macOS for Claude Code; env vars for direct SDK; whatever the platform uses). budai doesn't touch secrets at the storage layer.
2. **In transit (within budai)** — secrets that appear in transcripts get redacted by the streaming layer per `07-runtime-data.md`. Built-in patterns cover common cases (API tokens, GitHub PATs, SSH paths). Repos extend the patterns in `local/conventions.md` under "Sensitive data."
3. **At the boundary** — when streaming to the backend, redaction applies. The backend retains the redacted form. Re-deriving the original from the backend is not possible.

What's NOT redacted by default:

- Code that happens to contain example secrets (test fixtures, mocked credentials)
- Internal IDs that aren't sensitive but might look it
- Filenames

Repos with strict requirements should add their patterns to `local/redact-patterns.md` (Phase 0+) so redaction is comprehensive.

## Audit trail completeness

Every decision is reconstructible from on-disk artifacts:

- What was attempted: `council/<task-id>/attempts/`
- Who attempted it: `council/<task-id>/dispatch.json` + `mapping.json`
- What the Verifier said: `council/<task-id>/verifier-reports/`
- What the Reviewers said (if any): `council/<task-id>/reviews/`
- What the Judge picked and why: `council/<task-id>/verdict.md`
- The full transcripts: `runs/<run-id>/transcript.md`
- The captured evidence: `runs/<run-id>/evidence/`

Combined with git history (commits, branches, tags, repo state at any point), there's enough record to reconstruct any past decision in detail.

For regulated environments where audit retention has legal requirements, the runtime backend's retention policy needs to match. The default 365-day retention may be insufficient; configure per-deployment.

## What is NOT a security feature

Some patterns can look like security but are really about correctness or observability:

- **Anonymization at peer review.** A reviewer-bias mitigation, not a privacy mechanism. Authorship is preserved everywhere except the Judge's review context.
- **Stats tracking.** Helps detect skill regressions, not malicious behavior.
- **Lesson promotion.** Improves the system over time; not a security boundary.

Confusing these makes the security model harder to reason about. budai's security is the permission system + worktree isolation + redaction + audit trail. Other features serve other purposes.

## Reporting security issues

For security issues in budai itself: contact `contact@dpmg.xyz` directly. Don't open public Issues for unpatched vulnerabilities.

For issues in a specific runner: report to that runner's maintainer (Anthropic for Claude Code, OpenAI for Codex, etc.). budai's runner shims are thin; most security concerns at the runner layer are platform-vendor concerns.
