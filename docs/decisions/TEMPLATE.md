---
adr: NNNN
title: <short statement of the decision>
date: YYYY-MM-DD
status: proposed                # proposed | accepted | superseded | deprecated
authors: [<name>, ...]
supersedes: null                # ADR number this replaces, or null
superseded-by: null             # ADR number that replaces this, or null
---

# NNNN — <short statement of the decision>

## Context

<What's the situation? What forces are pulling on the decision? What
options were considered and why are they on the table?>

<Be honest about the trade-offs. ADRs that read as "the obvious choice
was X" don't help future readers understand why other paths weren't
taken.>

## Decision

<What we're going to do. Be concrete. Reference the docs that specify
the mechanics in detail rather than restating them here.>

<If the decision is multi-part, enumerate the parts.>

## Consequences

**Positive:**

- <What gets better as a result of this decision>

**Negative:**

- <What gets worse, or what we're now constrained from doing>
- <Mitigations, if any>

**Neutral:**

- <Side effects that aren't clearly positive or negative but matter>
- <Open questions or future decisions enabled by this one>

---

# Notes for ADR authors

- ADRs are immutable once accepted. To revise, write a new ADR with `supersedes:` set to the prior ADR's number.
- An ADR's prior `superseded-by:` field can be updated when a new ADR replaces it — that's the only mutation allowed post-acceptance.
- Keep ADRs short. 50-100 lines typical. If you need more, you probably need a doc, not an ADR.
- Reference the relevant design docs by filename (e.g., `09-bundle-format.md`) rather than duplicating their content.
- "Status: proposed" is for ADRs being discussed but not yet committed to. Move to "accepted" when the decision lands.
