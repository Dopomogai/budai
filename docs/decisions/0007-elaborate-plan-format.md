---
adr: 0007
title: Elaborate file-by-file plan format, not free-form prose
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0007 — Elaborate file-by-file plan format, not free-form prose

## Context

The plan is what the Planner produces and the Implementer executes (per `10-plan-format.md`). Two general approaches were considered:

- **A. Free-form prose.** The Planner writes a few paragraphs explaining the approach. The Implementer reads and figures out the file-level details. Faster to write, more flexible.
- **B. Elaborate structured format.** The Planner produces a file-by-file specification with required sections (approach, decomposition, file-level changes, AC mapping, etc.). Slower to write, much more detailed.

Three forces argued for B:

1. Fan-out diverges on vagueness. With multiple Implementers running in parallel on the same task, vague plans cause divergence in *both* productive (different solutions) and unproductive (different problems) ways. Peer review can pick the better solution; it can't pick between agents that solved different problems.
2. Audit reconstruction. Months later, looking at a closed task, "why did we do it this way?" should be answerable from the plan alone, without re-reading diffs and inferring intent.
3. Mechanical Implementer cost. With elaborate plans, the Implementer can run on cheaper tier (Sonnet) because architectural decisions are pre-made. Free-form prose forces the Implementer to escalate to Opus to make those decisions.

The user explicitly requested elaborate plans during design: "this need to be an elaborate plan with all of the file by file changes to make and each new file to create with description of what should be there as well as any other rationale."

## Decision

Adopt option B: elaborate file-by-file plan format.

Required sections:
1. Approach (2-4 sentences)
2. Decomposition (single task or sub-task list)
3. File-level changes (per-file: create/modify, structure, decisions)
4. Risks and escalations
5. Acceptance criteria mapping (each AC traced to a change)
6. Recommended fan-out
7. Confidence level

Optional: ADR section if a meaningful architectural choice is being made.

Validation enforces section presence and AC coverage at hand-off.

## Consequences

**Positive:**

- Fan-out attempts converge on the same problem and diverge productively on solutions.
- Audit reconstruction is direct: read the plan, you know what was attempted and why.
- Implementers run on cheaper tier; cost stays low without sacrificing reasoning.
- AC coverage is mechanically verifiable; tasks with missing AC mapping fail validation.
- The plan section is itself an artifact future readers learn from — junior contributors can see how senior plans are shaped.

**Negative:**

- The Planner's job is heavier. More tokens spent at Opus (the Planner's tier).
- Trivial tasks have a lot of plan ceremony. Mitigated: trivial tasks (`trivial: true`) get auto-approve at the architecture gate; for the smallest changes the plan can be terse.
- Elaborate plans encourage over-specification. Mitigated: the format requires "concrete enough to be unambiguous; abstract enough that the Implementer chooses the actual code." Pseudocode is explicitly out of scope.

**Neutral:**

- The cost is paid once (Planner) and the savings compound across every Implementer instance and every audit. Net cost is favorable for fan-out > 1 and for any task that gets revisited.
- Plan format can evolve over time; v2 of the plan format will be a major bump that requires consumer-repo migration.
