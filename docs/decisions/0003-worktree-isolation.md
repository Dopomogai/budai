---
adr: 0003
title: Worktree-per-implementer for fan-out isolation
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0003 — Worktree-per-implementer for fan-out isolation

## Context

When fan-out spawns N Implementers on the same task, each needs to work in isolation. Three implementation options were considered:

- **A. Branch-per-implementer.** Each instance commits to its own branch in the same checkout. Simplest to implement.
- **B. Worktree-per-implementer.** Each instance runs in a separate `git worktree` — a full filesystem-level checkout. Native git feature, well-supported.
- **C. Subprocess sandbox.** Each instance runs in a sandboxed subprocess with restricted CWD and filesystem boundaries. Most rigorous.

The strict-anonymization principle (ADR 0004) requires that an Implementer cannot read other Implementers' work during fan-out. Branch-per-implementer fails this — a malicious or curious agent could `git log` and see other branches. Subprocess sandbox is overkill for our threat model.

## Decision

Adopt option B: worktree-per-implementer.

Each Implementer runs inside a `git worktree add .agents/runs/<run-id>/worktree HEAD`. Its CWD is bound to that path. Its tool permissions don't include reading paths outside its worktree.

Cleanup happens at Judge integration time: worktrees are removed, but transcripts and diffs in `runs/<run-id>/` survive.

## Consequences

**Positive:**

- Filesystem-level isolation without containers or VMs. Cheap, native, well-understood.
- Matches Claude Code's existing `EnterWorktree` tool — no new platform primitive needed.
- Works equally well for any runner (Codex, direct SDK) — `git worktree` is a git operation, not a runner-specific feature.
- Preserves the audit trail: the worktree is gone but the diff is captured.

**Negative:**

- More disk I/O than branch-per-implementer (full checkout per worktree).
- Cleanup discipline matters — abandoned worktrees waste disk. The Judge's integration step is responsible for cleanup; failures here surface in the postflight check.

**Neutral:**

- Worktrees can't share build artifacts. If the consumer repo has expensive build steps, each implementer pays them independently. Acceptable for the iteration counts we expect (fan-out 1-5 typical).
- Cross-worktree references (e.g., one implementer wanting to "see what the other did") are deliberately impossible. This is a feature, not a bug.
