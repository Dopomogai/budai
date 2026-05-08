# 01 — Design principles

Eight principles, in priority order. When two pull against each other, the higher-numbered one yields to the lower-numbered one.

## 1. Mechanism in code, behavior in markdown

The platform (folder structure, file formats, scripts) is the mechanism. What agents actually do (which roles exist, which skills they have, what conventions they follow) is the behavior. Mechanism is fixed; behavior is markdown that can change without touching code.

This is the autoresearch principle from Andrej Karpathy: you don't program the Python files; you program the `program.md` files. budai applies it broadly. Every role, skill, workflow, and convention is markdown. Scripts are dumb dispatchers.

**Why it matters:** the same mechanism serves CanvasOS, Иша's project, and every future client repo. The behavior layer customizes per repo without forking the platform.

## 2. DAG of attempts, not linear merge

When more than one Implementer attempts a task, they don't share a branch. Each works in an isolated worktree, produces its own attempt, and the Judge picks the winner at integration time. Failed attempts stay in `council/` as the audit record and as future training data — they're not garbage-collected.

This is from Karpathy's agenthub: divergence is the natural state of agent work; convergence happens at selection, not at branching.

**Why it matters:** parallel attempts are a feature, not a problem to merge away. The cost of running three implementers is paid once; the win is that the Judge gets to choose, and the losers' diffs become evidence for "what doesn't work here."

## 3. Anonymized peer review with full traceability

When the Judge reviews attempts, it sees them as `attempt-A`, `attempt-B`, `attempt-C` — no model name, no role instance ID, no metadata that could bias the judgment. The de-anonymization mapping lives in the same `council/<task-id>/` folder so the verdict can attribute correctly after the fact.

From Karpathy's llm-council: anonymization is the only design choice that meaningfully reduces self-favor in cross-model evaluation.

**Why it matters:** it makes peer review a real signal, not a popularity contest. And the audit trail means every decision is reconstructible — including knowing which model + role + skill + version produced the winner.

## 4. Generic platform, opinionated culture

The platform doesn't know what success looks like. It can't, because it works for any task type. So success criteria, escalation rules, peer-review thresholds, what gets logged — all live in the agents' instructions and in the repo's `local/` configuration. The platform just enables; agents and conventions adjudicate.

**Why it matters:** the same budai installation can run a feature workflow on CanvasOS and a research workflow on an ML codebase. Same mechanism. Different culture. Configured in markdown.

## 5. Roles are documents, instances are runtime

A role is a markdown file: system prompt, skill manifest, permissions, escalation rules. An instance is a running agent with that role. Many instances of the same role can run concurrently — that's what fan-out is.

**Why it matters:** changing how all Implementers behave is one file edit. Splitting a role into specialized variants is one file copy. The role count stays small (currently five) without forcing one-size-fits-all.

## 6. Skills are composable units

A skill is a named, reusable procedure (peer-review, build-task-bundle, capture-evidence, audit-docs, run-preflight). Roles declare which skills they have. New roles are composed by mixing existing skills; new skills can be added without touching roles.

Skills are versioned and shareable across repos via the registry. A peer-review improvement made for CanvasOS ships to every project on the next sync.

**Why it matters:** the unit of reuse across roles and across repos is small enough to actually be reused. Roles are heavy and project-specific; skills are light and portable.

## 7. Memory is layered

Four layers, with promotion paths upward:

| Layer | Lifetime | Examples |
|---|---|---|
| Task | Per-run | Transcript, diff, verdict |
| Role | Persistent, role-scoped | "Implementers: never edit `*.orig` files" |
| Repo | Persistent, repo-wide | "We use React Flow, not tldraw" |
| User | Persistent, cross-repo | Personal preferences |

Lessons start at task level. Recurring patterns get promoted to role-level by the Librarian. Cross-role recurrence promotes to repo-level (`conventions.md`). Cross-repo recurrence (visible in the registry) becomes a candidate for the base culture.

**Why it matters:** the system gets smarter over time without manual curation. Failures become signal automatically.

## 8. Everything visible is derived

Dashboards, indexes, agent stats, repo maps, READMEs bundles — all auto-generated from source-of-truth markdown. No widget keeps state. No view has its own database.

A human editing markdown directly is a first-class citizen. There's no sync drift because there's nothing to sync — the markdown is the truth and everything else is a projection.

**Why it matters:** transparency, debuggability, no second source of truth to keep aligned. When you don't trust the dashboard, you read the markdown.

## What these principles forbid

- A role file that imports code or references implementation specifics. (Violates 1.)
- A workflow that requires manual merge-conflict resolution between agent branches. (Violates 2.)
- A peer-review step where the reviewer sees authorship before judging. (Violates 3.)
- A platform feature that hard-codes "every task must have an architect plan." (Violates 4.)
- A persistent agent identity that survives across runs and accumulates state. (Violates 5.)
- A capability that can only be invoked by one specific role and is not a documented skill. (Violates 6.)
- A "lessons learned" doc that is hand-curated by humans only. (Violates 7.)
- A widget or dashboard that maintains its own state separate from markdown. (Violates 8.)

These are the load-bearing constraints. The rest of the design — the five roles, the bundle format, the registry — is a working implementation of these principles, not the principles themselves. If a better implementation appears, the principles say to take it.
