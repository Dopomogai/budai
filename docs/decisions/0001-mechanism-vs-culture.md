---
adr: 0001
title: Mechanism in code, behavior in markdown
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0001 — Mechanism in code, behavior in markdown

## Context

Multi-agent systems can be built one of two ways:

1. **Code-first.** Agents are configured by editing source files; behavior changes require code changes. Examples: traditional ML pipelines, hand-coded RAG systems, most existing "agent frameworks."
2. **Behavior-first.** Agents are configured by editing markdown; the code is a generic engine that interprets the markdown. Examples: Karpathy's autoresearch (`program.md` shapes agent behavior), Karpathy's agenthub (mechanism is a Go binary; culture is in agent instructions).

The trade-off:

- Code-first lets you do anything but locks you into one team writing the configuration.
- Behavior-first restricts what's expressible but lets non-engineers configure agents and lets the same engine serve many use cases.

For budai, the intended audience extends beyond the engineering team: clients customizing their own setup, AI agents themselves modifying their own configurations, future humans needing to onboard quickly. Behavior-first is the only way to scale beyond the original authors.

## Decision

All agent behavior — roles, skills, workflows, conventions, untouchables, glossary, ADRs, lessons — lives in markdown. The code (scripts in `bin/`, the runner shims in `runners/`) is a generic dispatch layer that reads the markdown and routes work accordingly.

The boundary is strict:
- A role file that imports code or references implementation specifics is rejected at validation.
- A workflow that requires manual merge-conflict resolution between agent branches is rejected (it's a code-shape problem, not a behavior-shape problem).
- A skill that embeds business logic is rejected (business logic belongs in conventions).

## Consequences

**Positive:**

- The same code engine serves any consumer repo. CanvasOS, client repos, future projects all run on the same scripts.
- Behavior changes don't require redeployment. Edit a markdown file, commit, the next agent run picks it up.
- Non-engineers can author roles and skills. The contract is markdown plus YAML, not TypeScript.
- The audit trail is human-readable. You can read the markdown that produced a given agent's behavior at any point in history.

**Negative:**

- Some legitimately code-shaped behaviors (e.g., complex tool translation, runner-specific quirks) end up in the runner shims rather than role definitions. Acceptable; the runners are the explicit code/markdown bridge.
- Markdown gives less type safety than code. We compensate with schema validation at parse time.
- Some behaviors that would be one-line code changes become multi-line markdown structures. The cost is paid for the broader audience.

**Neutral:**

- The boundary between "mechanism" and "behavior" requires periodic revisiting. Some refactoring may move things across the boundary as the system matures.
