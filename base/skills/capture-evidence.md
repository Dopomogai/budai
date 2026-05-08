---
skill: capture-evidence
version: 1.0.0
tier-override: sonnet
inputs:
  - attempt-patch
  - task-acceptance-criteria
  - change-scope
outputs:
  - evidence-dir
  - ac-mapping-json
breaking-changes-from: null
stability: stable
owners: [verifier]
---

# capture-evidence

Capture artifacts proving an attempt meets acceptance criteria, sized to the change type. The Verifier's primary skill.

Evidence taxonomy and per-change-type detail: `docs/13-evidence-capture.md`.

## When to use

Invoked by the Verifier for each submitted attempt. After applying the attempt's patch in a fresh worktree, before writing the verifier report.

## Inputs

- **attempt-patch** — `council/<task-id>/attempts/attempt-<X>.patch`. Diff to apply.
- **task-acceptance-criteria** — the AC section of the task body.
- **change-scope** — task frontmatter `scope:` field, plus what the diff actually touches (used to refine evidence-type selection).

## Procedure

1. Apply `attempt-patch` to a fresh worktree.
2. Determine evidence type(s) from change scope and diff contents:
   - Backend / pure logic — unit tests + type check
   - IPC changes — smoke test + IPC trace + console capture
   - FE component — Playwright + screenshots + DOM diff + console + network (if fetches)
   - Visual changes — screenshot before/after + pixel-diff
   - Performance-sensitive — before/after timing measurements
   - Database / migration — up/down test + row counts + query plans
   - Documentation — markdown lint + link check
3. For each evidence type:
   - Run the relevant capture mechanism.
   - Save outputs to `runs/<run-id>/evidence/<type>/`.
   - Record file paths for ac-mapping.json.
4. Build `ac-mapping.json`:
   - For each AC, identify which captured evidence supports the claim.
   - Map AC → evidence file paths.
   - Set verdict: `pass` if evidence supports; `fail` if evidence contradicts; `unanswerable` if no evidence type covers this AC.
5. Save `ac-mapping.json` to `runs/<run-id>/evidence/ac-mapping.json`.

## Outputs

- **evidence-dir** — `runs/<run-id>/evidence/` populated with subdirectories per evidence type.
- **ac-mapping-json** — `runs/<run-id>/evidence/ac-mapping.json` per the schema in `docs/13-evidence-capture.md`.

## Failure modes

- **Patch doesn't apply.** Worktree is stale relative to main. Report `patch-conflict` finding; Verifier escalates to Router for re-dispatch.
- **Evidence capture infrastructure broken.** Playwright unavailable, test runner errors out, etc. Escalate to Librarian; this is a budai infrastructure problem, not an Implementer failure.
- **No evidence type covers an AC.** Mark AC as `unanswerable` in ac-mapping. The Verifier escalates to Planner; the AC needs revision.

## Examples

For a FE component change (task 042, "Add terminal widget"):

`runs/<run-id>/evidence/screenshots/`:
- `before-mount.png`
- `after-mount.png`
- `after-execute-command.png`
- `after-close-widget.png`

`runs/<run-id>/evidence/dom-snapshots/`:
- `after-mount.html`
- `after-execute-command.html`

`runs/<run-id>/evidence/ipc-traces/`:
- `trace-execute-command.json`
- `trace-close-widget.json`

`runs/<run-id>/evidence/console/`:
- `browser-console.txt`

`runs/<run-id>/evidence/ac-mapping.json`:
```json
{
  "task-id": 42,
  "run-id": "01HX2Y3Z-7f2c-...",
  "ac-coverage": {
    "AC1": {
      "claim": "Terminal renders inside a widget node",
      "evidence": [
        "evidence/screenshots/after-mount.png",
        "evidence/dom-snapshots/after-mount.html"
      ],
      "verdict": "pass"
    },
    "AC2": {
      "claim": "Commands execute in a real PTY",
      "evidence": [
        "evidence/ipc-traces/trace-execute-command.json"
      ],
      "verdict": "pass"
    }
  }
}
```

## Anti-patterns

- **Capturing everything for every change.** Wasteful. Use the right evidence type for the change.
- **Claiming pass without evidence.** Empty `evidence: []` arrays in ac-mapping.json are rejected at hand-off.
- **Capturing flaky evidence.** If a screenshot is non-deterministic across runs (animations, timestamps), wait for stable state or mask the unstable region.
- **Skipping non-AC observations.** If the capture reveals regressions or notable changes outside AC, record them in `additional-findings` so the Judge sees them.

## References

- `docs/13-evidence-capture.md` — full evidence taxonomy by change type.
- `base/skills/run-preflight.md` — runs before capture-evidence to ensure clean worktree.
- `base/roles/verifier.md` — how capture-evidence fits into the Verifier's workflow.
