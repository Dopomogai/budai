# 15 — Framework-agnostic runners

budai is **vendor-neutral** by design. Roles, skills, workflows, conventions, and the entire runtime data shape are pure markdown plus YAML — no Claude Code dependency, no OpenAI dependency, no specific SDK in the contract.

The bridge between budai's portable definitions and a specific agent platform is the **runner**: a thin shim that translates "invoke this role on this task" into the platform's native invocation primitives.

This document specifies the runner abstraction: what stays portable, what's runner-specific, and how multiple runners coexist.

## Why framework-agnostic

Three reasons:

1. **No vendor lock-in.** Your investment in budai (defined roles, accumulated skills, repo conventions, lessons learned) survives any change of agent platform. If Claude Code becomes uneconomic, swapping to Codex is a runner-file change, not a rewrite.
2. **Hybrid workflows beat monolithic ones.** Different platforms have different strengths. Claude Opus reasons differently than GPT-5; codex-cli has different tool affordances than Claude Code. A fan-out where one attempt runs Claude and another runs Codex gives you genuinely different perspectives the Judge can rank.
3. **Same OS, different consumers.** When you onboard a client whose security policy disallows third-party SaaS APIs, you swap their runner to a self-hosted one without changing the OS itself. The roles, skills, and conventions are the same; the execution substrate differs.

## Mechanism vs. behavior, applied to runners

Per `01-design-principles.md` principle 1: mechanism in code, behavior in markdown.

For runners, this becomes:

- **Behavior** — what the agent should do (role definition, skills it can invoke, conventions it must follow). Markdown. Lives in `base/` and `local/`.
- **Mechanism** — how to launch a process, capture stdout, translate tool calls, manage tokens. Code (shell, Python, Go — whatever). Lives in the runner shim.

The runner is permitted to be opinionated about platform specifics; the role files are required to stay agnostic. A role file that hardcodes "use Claude Code's `Read` tool" is broken.

## The runner abstraction

A runner is a single markdown file under `.agents/runners/` that declares how to translate budai concepts into a specific platform's primitives. It's read by `bin/agent run` (and similar launchers) at dispatch time.

### File location

```
.agents/runners/
├── claude-code.md          # the only runner shipped at Phase 0
├── codex.md                # Phase 8
├── direct-anthropic.md     # Phase 8
└── direct-openai.md        # Phase 8
```

### File format

```markdown
---
runner: claude-code
version: 0.1.0
launches: cli                # cli | sdk | api
default-tier: sonnet
supported-tiers: [haiku, sonnet, opus]
auth: keychain               # keychain | env-var | oauth | none
---

# Claude Code runner

## Launch
<how to invoke a Claude Code session given a role file and a bundle path>

## System prompt injection
<how the role file's body becomes the session's system prompt>

## Tool translation
<how budai's expected tools map to Claude Code's tool catalog>

## Output capture
<how the session's transcript and diff get persisted to runs/<run-id>/>

## Tool permissions
<how budai's permission model maps to Claude Code's allowlist>

## Tier mapping
<how budai tier names map to model IDs>
```

The body sections are prescriptive: each runner file must answer the same questions in the same order, so the launcher can mechanically dispatch.

## What stays portable across runners

These are runner-agnostic. Writing them assuming a specific runner is a bug.

- **Role files** — system prompt + skill manifest + permissions list. The runner translates the manifest into its tool catalog; the role file stays neutral.
- **Skill files** — procedure, inputs, outputs, failure modes. A skill that says "Read the bundle" is fine; one that says "use Claude Code's Read tool" is not.
- **Workflow files** — role sequence, hand-off contracts, gates. Don't reference platform internals.
- **Conventions, ADRs, glossary, untouchables** — repo policy, not platform.
- **Per-file headers** — purpose, why, role, etc. Don't mention runners.
- **Index format** — `tree.md`, `detailed.md`. Pure markdown.
- **Bundle format** — YAML manifest + concatenated content. No platform calls embedded.
- **Plan format** — the seven required sections, content shape.
- **Task format** — frontmatter + body sections.
- **Memory** — task / role / repo / user layers. The user layer is the only place that can be runner-specific (because it's the runner's memory framework that owns it).

## What's runner-specific

These live in the runner file or in runner-managed locations.

- **How to launch a session.** `claude` CLI invocation? `codex` CLI invocation? Direct SDK call? Long-lived daemon vs. process-per-task? Each runner answers differently.
- **How tools are exposed.** Claude Code has a fixed catalog (Read, Edit, Bash, etc.); Codex may have a different set. The runner maps "what budai expects an Implementer to be able to do" onto "what tools the platform exposes."
- **How permissions are enforced.** Tool allowlists, sandbox boundaries, network restrictions. Each platform has a different model.
- **How the transcript gets captured.** Claude Code emits a JSONL transcript; Codex may emit a different shape. The runner normalizes to budai's `runs/<run-id>/transcript.md` form.
- **How tokens are counted.** Different platforms report token usage differently; the runner normalizes to `meta.json:tokens`.
- **How tier mapping works.** "sonnet" may mean `claude-sonnet-4-6` for Claude Code; for direct-OpenAI it might mean `gpt-5-mini` or similar. The mapping is per-runner.
- **Authentication.** Where credentials live (Keychain, env var, OAuth flow). The runner knows.

## Currently shipped runners

### `claude-code.md` (Phase 0)

The only runner shipped initially. Wraps Anthropic's Claude Code CLI. Reads role files, injects them as system prompts via `--system-prompt`, captures transcripts to `runs/<run-id>/transcript.md`, parses Claude Code's tool-call JSON to populate `meta.json:skill-invocations`.

Tier mapping:
- `haiku` → `claude-haiku-4-5-20251001`
- `sonnet` → `claude-sonnet-4-6`
- `opus` → `claude-opus-4-7`

Auth: macOS Keychain via the `claude` CLI's standard credential flow; or OAuth via `claude auth login` interactive flow.

Permissions: maps role's `permissions:` list to Claude Code's tool allowlist (`--allowed-tools`).

### Future runners (Phase 8)

- **`codex.md`** — wraps OpenAI's Codex CLI. Tier mapping uses GPT-class models. Auth: env var or Codex CLI's own keychain.
- **`direct-anthropic.md`** — direct Anthropic SDK calls, no CLI in between. Useful for non-interactive batch runs and for cases where the CLI's overhead matters. Auth: env var.
- **`direct-openai.md`** — direct OpenAI SDK calls. Same shape as direct-anthropic.

Adding more runners is a matter of writing one markdown file per runner plus a small translation layer in the launcher script. The OS itself doesn't change.

## Multi-runner fan-outs

A fan-out can use different runners for different attempts. Useful for genuine ensemble work — each platform brings different model weights, different tool affordances, different reasoning styles.

Configured via task frontmatter:

```yaml
---
fan-out: 3
fan-out-runners:
  - claude-code           # attempt-A
  - claude-code           # attempt-B
  - codex                 # attempt-C
---
```

When `fan-out-runners` isn't specified, all attempts use the manifest's default runner.

The Judge sees only opaque IDs (`attempt-A`, `attempt-B`, `attempt-C`) — runner identity is part of `mapping.json`, de-anonymized only after the verdict (per `12-isolation-and-fanout.md`).

This means the Judge can't bias toward a specific platform. After the verdict, attribution shows "winner was attempt-C, which ran Codex" — useful data for stats, no impact on the ranking decision.

## Runner stats

`stats/roles.json` and `stats/skills.json` discriminate by runner. Example:

```json
{
  "skills": {
    "peer-review@1.4.2": {
      "by-runner": {
        "claude-code": {"invocations": 60, "success-rate": 0.97},
        "codex": {"invocations": 27, "success-rate": 0.89}
      }
    }
  }
}
```

After enough data accumulates, the Librarian can flag patterns: "the `audit-docs` skill performs 12% better on Claude Code than on Codex; consider tier-override or runner-specific skill variants."

Per-runner skill variants are a Phase 8+ feature; the file format would extend skill frontmatter with optional `runner-variants:` overrides. Out of scope for Phase 0.

## Hybrid workflows

A workflow can specify per-role runner preferences:

```yaml
---
workflow: research
default-runner: claude-code
role-runner-overrides:
  planner: claude-code      # Opus reasoning for planning
  implementer: codex        # GPT-5 for execution
  judge: claude-code        # back to Opus for ranking
---
```

The runner-override is a soft preference; the launcher uses it unless overridden by the manifest's runner constraints (e.g., a client repo that blocks Codex).

## Adding a new runner

The flow:

1. Write `local/runners/<name>.md` in the consumer repo where you want to test it.
2. Implement the section bodies: launch, system-prompt injection, tool translation, output capture, permissions, tier mapping.
3. Run a single role on a synthetic task using the new runner: `bin/agent run --role librarian --task <id> --runner <name>`.
4. Iterate until outputs are well-formed.
5. After ≥10 successful runs across ≥5 different role types, propose for promotion to `base/` via `bin/librarian publish runners/<name>.md`.

Promotion to base requires registry-maintainer review. New runners are higher-stakes than new skills — they're the bridge between budai and a third-party platform.

## What the runner is NOT

- Not the agent. The agent is the running process invoked by the runner.
- Not a place for budai logic. budai's role / workflow / skill logic stays in markdown, runner-agnostic. The runner is plumbing.
- Not a long-lived daemon. Runners are launched per-role-invocation. Long-running state belongs in budai's runtime data, not in runner memory.
- Not a place for product code. The runner doesn't know about CanvasOS or any specific consumer repo. It knows about the platform.
