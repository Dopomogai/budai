---
skill: peer-review
version: 1.0.0
tier-override: opus
inputs:
  - council-attempts-dir
  - task-file
  - conventions-md
  - verifier-reports
outputs:
  - review-md
  - ranking-json
breaking-changes-from: null
stability: stable
owners: [judge, reviewer]
---

# peer-review

Anonymized review of multiple attempts. Used by the Judge directly, or by Reviewer instances when `peer-reviewers > 0` in the workflow.

The skill is the canonical implementation of the anonymization-with-traceability principle from ADR 0004. Input strips authorship; output stays in council where the verdict can de-anonymize for posterity.

## When to use

Invoked when the Judge (or Reviewer) needs to rank attempts in a council. After all Implementer attempts have been submitted and verified.

## Inputs

- **council-attempts-dir** — `council/<task-id>/attempts/`. Contains `attempt-A.md`, `attempt-A.patch`, `attempt-B.md`, etc. Files are anonymized by name.
- **task-file** — the task body. Provides AC and plan to evaluate against.
- **conventions-md** — `local/conventions.md` merged with `base/conventions.md`. Style and patterns to evaluate against.
- **verifier-reports** — appended to each attempt's writeup. AC pass/fail with evidence.

## Procedure

1. Read attempts. The runner does NOT inject `mapping.json` or `dispatch.json` into your context. Filenames use opaque IDs (`attempt-A`, `attempt-B`, ...).
2. For each attempt, evaluate independently:
   - Did all AC pass per the verifier report?
   - How does the implementation quality compare:
     - Does it match conventions?
     - Is the code well-organized?
     - Are there fewer files / cleaner control flow / better naming where the differences matter?
     - Are there outstanding concerns the verifier flagged?
3. Rank attempts. Comparative criteria:
   - All AC passing > some AC failing.
   - Cleaner adherence to conventions > deviations from them.
   - Smaller, focused diff > larger, sprawling diff (when both meet AC).
   - Better outstanding-concern handling > more ignored concerns.
4. Write `review-md` to `council/<task-id>/reviews/review-<X>.md`:
   - Frontmatter: `reviewer-id` (an opaque ID for the reviewer), `reviewed-at`.
   - Ranking: ordered list of opaque IDs.
   - Critique per attempt: what's good, what's wrong, with severity.
   - Outstanding concerns: any issues the verifier missed.
5. Write `ranking-json` to `council/<task-id>/reviews/ranking-<X>.json`:
   - Machine-readable rank order for the Judge to synthesize across multiple reviewers (when `peer-reviewers > 0`).

## Outputs

- **review-md** — markdown critique per attempt + overall ranking.
- **ranking-json** — machine-readable: `{"ranked": ["attempt-B", "attempt-A", "attempt-C"], "rationale-per-attempt": {...}}`.

## Failure modes

- **All attempts identical.** If two attempts have nearly identical diffs, you can't pick on merit. Note this in the review; pick on minor differentials (a chosen variable name, a comment placement) and flag low confidence.
- **Verifier reports contradict each other.** If two attempts show conflicting evidence on the same AC (one verifier says pass, another says fail for what looks like the same code path), escalate to the Judge to investigate.
- **All attempts fail AC.** Flag in your review; the Judge will handle "best of failed" or escalation to human.

## Examples

For task 042 with three attempts:

```markdown
---
reviewer-id: review-X
reviewed-at: 2026-05-09T11:35:12Z
---

# Review X

## Ranking
1. attempt-B
2. attempt-A
3. attempt-C

## Critique per attempt

### attempt-A
- Pros: clean separation between TerminalManager (main process) and TerminalWidgetNode (renderer); IPC contract well-named.
- Cons: doesn't handle the unmount-during-spawn race condition — if a widget closes before its PTY initializes, the unmount path doesn't see the spawn promise. Severity: medium.

### attempt-B
- Pros: same architecture as A but explicitly handles unmount-during-spawn via a cancellation token in the spawn promise.
- Cons: terminal-data event subscription leaks if the component re-renders before unmount. Severity: low (defensive cleanup catches it).

### attempt-C
- Pros: tries an interesting approach with a sub-PTY pool for resource sharing.
- Cons: the pool design isn't called out by AC and adds significant complexity for unclear benefit. Over-engineered. Severity: high.

## Outstanding concerns

- All three: PTY cleanup on app reload (Cmd+R) isn't tested. Should be a follow-up regardless of which wins.
```

```json
{
  "ranked": ["attempt-B", "attempt-A", "attempt-C"],
  "rationale-per-attempt": {
    "attempt-B": "Cleanest fit; handles edge case A misses",
    "attempt-A": "Good architecture; missing edge case",
    "attempt-C": "Over-engineered; AC didn't ask for resource pooling"
  }
}
```

## Anti-patterns

- **Reading mapping.json before the review.** Breaks anonymization. The runner enforces it.
- **Picking based on attempt order.** Opaque IDs are randomly assigned; A is not "first."
- **Vague critique.** "attempt-B because it was cleaner" is rejected. Specify what's cleaner.
- **Re-implementing in the review.** Don't propose alternative code. The Judge picks among submitted attempts; if none are good enough, that's a different escalation path.

## References

- `docs/12-isolation-and-fanout.md` — anonymization specification, council folder layout.
- `docs/decisions/0004-strict-anonymization.md` — why anonymization is strict at review time.
- `base/roles/judge.md` — how the Judge consumes peer-review output.
