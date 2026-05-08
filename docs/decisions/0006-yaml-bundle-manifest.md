---
adr: 0006
title: YAML manifest at the top of every bundle
date: 2026-05-08
status: accepted
authors: [andrey, dopomogai-agent]
supersedes: null
superseded-by: null
---

# 0006 — YAML manifest at the top of every bundle

## Context

The bundle is the data contract between the Librarian and the Implementer (per `09-bundle-format.md`). It needs to be:

- Readable by an LLM Implementer (markdown content body).
- Inspectable by humans (in code review, in audits).
- Parseable by the runner (for hand-off validation, stats, retention).

Three options were considered:

- **A. Pure markdown.** Just sections with file contents. The Implementer reads it; the runner parses it heuristically.
- **B. JSON envelope.** The whole bundle is a JSON document with a content field. Most parseable; least LLM-friendly (LLMs handle markdown content better than nested JSON strings).
- **C. YAML frontmatter + markdown body.** Same pattern as task files, role files, skill files. Familiar to anyone who's used Jekyll, Hugo, or any markdown-driven system.

A separate concern: token budgets. The bundle has metadata (what's included, what's not, how big) that's expensive to recompute and useful at the boundary. Having it in the file lets the runner check budget compliance without re-scanning the body.

## Decision

Adopt option C: YAML frontmatter + markdown body.

The frontmatter is the manifest:
- Token budget metadata (target, actual, status: ok/trimmed)
- Inclusions, by category, with per-file token counts and inclusion reasons
- Overflow list (what was excluded, with one-line hints)
- Generator version for staleness detection

The body is the concatenated content, in fixed section order.

## Consequences

**Positive:**

- Familiar pattern; consumes no new mental load.
- The Librarian writes both YAML and markdown well; LLMs find this format natural.
- Runner validation is cheap: parse the frontmatter, verify against the schema, done. The body doesn't need re-scanning.
- The Implementer can read the YAML to understand "what's in this bundle" before reading the content. Useful for skipping irrelevant sections.
- Same shape as every other markdown+YAML file in budai. Consistency reduces friction.

**Negative:**

- Frontmatter adds tokens to the bundle. Mitigated: frontmatter for an 80k-token bundle is ~500 tokens, <1%.
- YAML's whitespace-sensitivity occasionally produces hard-to-debug parse errors. Mitigated: validation catches malformed YAML at the boundary; the bundler doesn't ship invalid YAML.

**Neutral:**

- Future tooling (canvas widget, dashboards) reads the YAML for indexing without parsing the body. The frontmatter becomes a cheap source of truth for stats.
- If we ever need to pivot to a richer envelope format (e.g., for multi-modal bundles with images), the YAML frontmatter pattern accommodates additional metadata fields without restructuring.
