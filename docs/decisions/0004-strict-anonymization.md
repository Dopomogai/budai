---
adr: 0004
title: Strict anonymization for peer review with full audit traceability
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0004 — Strict anonymization for peer review with full audit traceability

## Context

When the Judge reviews multiple Implementer attempts, it should rank them on merit, not on attribution biases like "I prefer Opus output" or "the first one is probably the most-confident attempt." Two designs were considered:

- **Loose anonymization.** Identity is shown but the reviewer is instructed to ignore it. Easier to implement; depends on prompt discipline.
- **Strict anonymization.** Identity is literally stripped from the reviewer's context. Harder to implement; doesn't depend on the reviewer's discipline.

Karpathy's llm-council demonstrated that strict anonymization meaningfully reduces self-favor across models. The cost is plumbing — you have to make sure no metadata leaks at any layer.

A separate concern: full traceability. After the verdict, audit needs to know which model produced which attempt, for stats and for accountability.

## Decision

Adopt strict anonymization at the moment of review, with the de-anonymization mapping preserved in the council folder for post-verdict attribution.

Mechanics:

- Attempts are tagged with opaque IDs (`attempt-A`, `attempt-B`, `attempt-C`) randomly assigned at dispatch.
- The Judge's working context contains only opaque IDs — no model names, no run IDs, no chronological ordering hints.
- `dispatch.json` contains the mapping but is NOT read into the Judge's context during review.
- After the verdict is drafted, `mapping.json` is read; attribution is added to the verdict.

The runner enforces the boundary by not injecting metadata into the Judge's context until the explicit "de-anonymize" step.

## Consequences

**Positive:**

- Peer review is a real signal, not a popularity contest among models or runners.
- Full audit trail is preserved — anonymization is at one specific moment, not a record-keeping concern.
- Stats can attribute success rates to specific model + role + skill + version combinations after the fact.
- Reviewer self-discipline isn't load-bearing.

**Negative:**

- More plumbing in the runner: maintain two views of the same data, one anonymized for review and one named for attribution.
- The Judge can't use authorship as a tiebreaker even when it would be useful (e.g., "I trust attempt-A more because it ran on Opus") — that's the point, but it occasionally rejects a real signal.

**Neutral:**

- Random opaque ID assignment (not dispatch-order-based) prevents inferring authorship from ordering. This adds entropy at minimal cost.
- The audit reconstruction guarantee (per `12-isolation-and-fanout.md`) means anonymization doesn't compromise post-hoc analysis.
