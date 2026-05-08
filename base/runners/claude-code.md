---
runner: claude-code
version: 0.1.0
launches: cli
default-tier: sonnet
supported-tiers: [haiku, sonnet, opus]
auth: keychain
---

# Claude Code runner

The runner shim for Anthropic's Claude Code CLI. Translates budai role definitions and skill invocations into `claude` CLI calls; captures outputs into budai's runtime data shape.

This is the only runner shipped at Phase 0. Future runners (`codex`, `direct-anthropic`, `direct-openai`) follow the same body-section spec.

## Launch

The runner is invoked by `bin/agent run --role <role> --task <task-id> --runner claude-code`. The dispatch flow:

1. Resolve the effective role definition (base + local overlay).
2. Resolve the effective tool permissions (base + local overlay + role frontmatter).
3. Determine the working directory:
   - For Implementers and Verifiers in fan-out: a fresh `git worktree` at `runs/<run-id>/worktree/`.
   - For all other roles: the consumer repo root.
4. Compose the system prompt (see "System prompt injection" below).
5. Compose the initial user message (the task body + bundle path + plan if applicable).
6. Invoke:

   ```bash
   claude \
     --system-prompt "$(cat /tmp/budai-systemprompt-<run-id>.md)" \
     --model <resolved-model-id> \
     --allowed-tools "<resolved-tool-list>" \
     --max-turns 100 \
     --working-dir "<cwd>" \
     --output-format json \
     <input-file>
   ```

7. Capture stdout to `runs/<run-id>/transcript.jsonl` (Claude Code's native JSONL format).
8. Post-process: convert JSONL to `runs/<run-id>/transcript.md` for human readability; extract diff via `git diff` from the worktree; populate `runs/<run-id>/meta.json`.

The temporary system prompt file is cleaned up after the run completes.

## System prompt injection

The runner constructs the system prompt by concatenating:

1. The role file's body content (after frontmatter; from `Mission` section onward).
2. The relevant subset of `base/conventions.md` + `local/conventions.md` (sections matching the task's scope).
3. The relevant subset of `local/untouchables.md` (entries matching task scope).
4. Glossary entries for terms appearing in the task body.
5. Per-tool usage hints (Claude Code-specific guidance: "Use Read for file content; use Edit for changes; etc.").

The composed system prompt is written to a temp file and passed via `--system-prompt`.

The role frontmatter (`permissions`, `skills`, `escalation`) is NOT injected as text — it's used to configure the runner itself (tool allowlist, available skills via `/skill` invocations).

## Tool translation

Claude Code's standard tool catalog maps to budai's permissions:

| budai permission | Claude Code tools |
|---|---|
| `read` | `Read`, `Glob`, `Grep` |
| `write` | `Edit`, `Write`, `MultiEdit` |
| `write-task-body` | `Edit` (with runner-side validation: path must be `tasks/open/<id>.md`) |
| `write-decisions` | `Write` (with runner-side validation: path must be `memory/decisions/`) |
| `spawn-tasks` | `Bash` (restricted to `bin/task new` command) |
| `run-preflight` | `Bash` (restricted to `bin/preflight` command) |
| `run-tests` | `Bash` (restricted to `bin/run-tests` or repo's configured test command) |
| `run-arbitrary-bash` | `Bash` (fully allowed) |
| `git-commit` | `Bash` (allowed for `git commit`, `git checkout`, `git apply`) |
| `git-worktree` | `Bash` (allowed for `git worktree` subcommands) |
| `network-fetch` | `WebFetch`, `WebSearch` |
| `exec-installed` | `Bash` (restricted to declared paths from `local/conventions.md`) |

The `--allowed-tools` flag is the union of all tools mapped by the role's effective permissions. Runner-side path validation (for `write-task-body`, `write-decisions`, etc.) is implemented as a wrapper around `Edit` and `Write` that rejects writes to disallowed paths.

For permissions like `run-preflight` and `run-tests` that require restricted Bash, the runner wraps Bash with a guard:

```python
# Wrapping logic in bin/lib/runner.py
def restrict_bash(cmd: str, allowed_prefixes: list[str]) -> bool:
    return any(cmd.startswith(prefix) for prefix in allowed_prefixes)
```

If the Bash command is rejected, the runner returns an error to the agent indicating the permission gap. The agent can either escalate or work around (typically by adjusting its approach).

## Output capture

Claude Code emits a transcript as JSONL on stdout. Each line is a structured event: user input, assistant message, tool call, tool result.

The runner:

1. Pipes stdout to `runs/<run-id>/transcript.jsonl`.
2. Captures stderr to `runs/<run-id>/runner-errors.log`.
3. Records exit code in `runs/<run-id>/meta.json`.
4. Post-run conversion:
   - Parse `transcript.jsonl` into a markdown transcript (`runs/<run-id>/transcript.md`).
   - Extract skill invocations from tool-call patterns; populate `runs/<run-id>/meta.json:skill-invocations`.
   - For Implementers and Verifiers: compute `git diff` from the worktree; save as `runs/<run-id>/diff.patch`.
   - For Implementers: copy or move the writeup and patch into `council/<task-id>/attempts/`.
   - For Verifiers: copy evidence directory into `council/<task-id>/verifier-reports/`.

The JSONL is preserved as the raw record; the markdown is the human-readable view. Both stay locally; both stream to the backend.

## Tool permissions

Per `docs/20-permissions-and-security.md`, the runner enforces:

1. **Allowlist enforcement.** `--allowed-tools` strictly limits which Claude Code tools the agent can invoke.
2. **Path validation.** For permissions that constrain *where* writes can happen (`write-task-body`, `write-decisions`), the runner wraps `Edit`/`Write` to validate the path before passing through.
3. **Command restriction.** For permissions that allow Bash but constrain the commands (`run-preflight`, `run-tests`, etc.), the runner wraps Bash with a guard.
4. **CWD enforcement.** The agent's CWD is bound to the worktree (or repo root for non-Implementers). Reading paths outside CWD is blocked at the OS level via the `--working-dir` flag.

When the runner blocks a tool call, it returns a structured error to the agent so the agent knows what was disallowed. The agent can then escalate or adjust.

## Tier mapping

| budai tier | Claude Code model ID |
|---|---|
| `haiku` | `claude-haiku-4-5-20251001` |
| `sonnet` | `claude-sonnet-4-6` |
| `opus` | `claude-opus-4-7` |

These IDs follow Anthropic's release cadence; updates to the registry's claude-code runner happen as new models ship.

When a role's frontmatter declares `model-default: sonnet`, the runner resolves to `claude-sonnet-4-6`. When a skill's frontmatter declares `tier-override: haiku`, the runner spawns a separate Haiku-tier call for that skill (rather than using the role's default).

## Authentication

Default auth flow: Claude Code's standard credential mechanism on macOS uses the system Keychain. The runner doesn't manage credentials directly — it relies on the `claude` CLI being authenticated via:

```bash
claude auth login
```

The user runs this once per machine; the CLI stores credentials in Keychain. The runner inherits the credential by invoking `claude` (which finds the cred via the standard CLI auth flow).

For non-interactive environments (CI, batch runs):

```bash
ANTHROPIC_API_KEY="..." claude --no-interactive ...
```

The `--no-interactive` flag and explicit env-var auth let the runner work in non-interactive contexts. The runner reads `ANTHROPIC_API_KEY` from the environment if present; otherwise falls back to Keychain.

## Limitations and known issues

- **Long-running tasks.** Claude Code sessions have a default max-turn limit (configurable, but with implicit budget caps). For very long Implementer runs, the budget may run out. Mitigation: split the task (decompose at planning time).

- **Tool result truncation.** Claude Code truncates tool results above a size threshold. For Verifier capturing large evidence files, the runner must reference paths rather than embedding contents in transcript.

- **Stdout buffering.** When piping JSONL on stdout, very large outputs can hit OS pipe buffer limits. The runner uses non-blocking I/O with periodic flushing.

- **Worktree creation cost.** Each Implementer worktree is a full checkout. For very large repos, this is slow. Mitigation: shallow clones; consider sparse-checkout for repos > 1GB.

These limitations are inherited from Claude Code's CLI design and the OS layer; budai doesn't work around them at the runner level. They're documented for repo operators to plan around.

## Future improvements

- Streaming budget management — kill long-running runs that exceed budget mid-flight rather than waiting for max-turn.
- Parallel sub-skill invocations — when a role invokes multiple skills, spawn them concurrently via separate Claude Code processes.
- Caching — cache role-prompt + bundle composition so re-invocations on the same task pay less I/O.

These are not in the v0.1.0 baseline; they'll arrive in subsequent versions of the runner shim as we accumulate operational experience.
