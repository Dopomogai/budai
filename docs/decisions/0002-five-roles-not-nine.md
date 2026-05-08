---
adr: 0002
title: Five roles, not nine
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0002 — Five roles, not nine

## Context

Early design drafts proposed nine roles: Router, Architect, Implementer, Reviewer, Chairman, Tester, Debugger, Librarian, Auditor. Each had a distinct mission and could be invoked separately.

Two arguments pulled in opposite directions:

- **More roles = more specialization.** Each role can have a tightly-scoped system prompt, dedicated permissions, focused skill set. Easier for the agent to do its specific job well.
- **Fewer roles = less bureaucratic overhead.** Fewer hand-offs, fewer files to maintain, less room for "is this the Tester's job or the Verifier's job?" confusion.

The user pushed back on nine: "I think less is better here — if the process makes sense really and helps, 9 is ok, but maybe 5 is enough as well — so I think we should experiment with that."

## Decision

Ship five roles by default: Planner, Implementer, Verifier, Judge, Librarian.

Collapses made:

- **Architect + Router → Planner.** Both interpret tasks and decide approach. Splitting them was bureaucratic overhead — one role can do "what's the plan" and "who should execute" in the same invocation.
- **Reviewer + Chairman → Judge.** Single-instance peer review and integration in one role. Multi-reviewer cases are workflow choices (peer-reviewers: 2 in refactor workflow), not role splits.
- **Tester + Debugger → Verifier.** Same competency in two phases. The Verifier verifies on pass; investigates on fail. Compute tier escalates as needed.
- **Auditor → folded into Librarian.** Audit is a Librarian skill (`audit-docs`, future `audit-tasks`). Doesn't need its own role file.

## Consequences

**Positive:**

- Lower maintenance: five role files to keep current, not nine.
- Less inter-role hand-off coordination, fewer hand-off contracts to specify.
- Easier to understand for new contributors and consumers — five roles fit on a single page.
- Easier to reason about workflow shape — the role sequence has fewer permutations.

**Negative:**

- Some role files do "double duty" (Planner does both routing and architecture). Their bodies are slightly longer to cover both modes.
- Specialized variants are harder to introduce — you can't just write a separate role; you'd extend an existing one.

**Neutral:**

- Easy to subdivide later if a specific repo or workflow needs it. Future Phase: marketing-writer, sales-responder, support-agent for non-code work — these can ship as additional roles without disrupting the original five.
- Workflows can spawn multiple instances of the same role for ensemble work (e.g., `refactor` runs 2 Reviewer-style Judges before integration), which preserves specialization without requiring a separate role file.
