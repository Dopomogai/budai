# 13 — Evidence capture

A Verifier doesn't just say "tests passed." It produces **evidence** — captured artifacts that prove an attempt meets acceptance criteria, sized appropriately for the change. Evidence is what the Judge reviews; evidence is what the human gate inspects when an automated verdict needs scrutiny.

This document specifies the evidence taxonomy: which types of changes produce which evidence, where it lives, and how downstream roles consume it.

## Why evidence beyond pass/fail

Three reasons:

1. **A passing test is necessary but not sufficient.** A change can pass tests and still break things in subtle ways — a regression in a non-tested path, a visual change nobody asked for, a performance cliff. Evidence captures the surrounding context.
2. **The Judge needs differentiable input.** When ranking three attempts that all pass tests, the Judge needs *something* to differentiate them. Evidence — screenshots, trace timing, console logs — gives the Judge handholds for ranking.
3. **The human gate needs scannable artifacts.** "All AC passed" is a one-line claim. The human can't verify that without re-running everything. Evidence makes the verification scannable: "AC2 says the menu opens; here's the screenshot showing it opens."

## File structure

Evidence lives in the run-specific directory:

```
.agents/runs/<run-id>/evidence/
├── ac-mapping.json         # which AC is covered by which evidence file
├── tests/
│   ├── unit-output.txt     # raw test runner output
│   └── unit-summary.md     # parsed pass/fail per test
├── ipc-traces/
│   └── trace-<scenario>.json
├── screenshots/
│   ├── before-<scenario>.png
│   └── after-<scenario>.png
├── dom-snapshots/
│   └── after-<scenario>.html
├── console/
│   └── browser-console.txt
├── network/
│   └── requests-<scenario>.har
├── timing/
│   └── perf-<scenario>.json
└── logs/
    └── stdout-<scenario>.txt
```

Not every directory exists for every change. The `capture-evidence` skill populates only the relevant ones based on change scope.

## Evidence by change type

The `capture-evidence` skill picks the right capture flow per change. Inferred from the task's `scope:` field plus a scan of the diff to detect what actually changed.

### Backend / pure logic

**What the change does:** modifies functions, types, business logic with no UI surface.

**Evidence captured:**
- Unit test output (raw + parsed summary).
- Coverage delta if a coverage tool is configured.
- Type-check output (e.g., `tsc --noEmit`).

**Where it lives:** `evidence/tests/`.

**What's NOT captured:** screenshots, IPC traces, network captures. Pure logic doesn't need them.

### IPC changes

**What the change does:** adds, modifies, or removes IPC channels (Electron main↔renderer or similar).

**Evidence captured:**
- Smoke-test scenario that exercises the IPC roundtrip.
- IPC trace JSON: each invocation logged with channel name, args, return value, timing.
- Process-level output capture (main process stdout, renderer console).

**Where it lives:** `evidence/ipc-traces/` + `evidence/console/` + `evidence/logs/`.

**Capture mechanism:** the smoke test is run with an IPC interceptor wrapping `ipcMain.handle` / `ipcRenderer.invoke`. The interceptor logs to a file in the evidence directory.

### Frontend component changes

**What the change does:** adds or modifies a React component, a UI affordance, a visual element.

**Evidence captured:**
- Playwright test run (headed, video-recorded if the test fails).
- Screenshots before/after the component's main interaction.
- DOM snapshot of the component's tree post-interaction.
- Browser console log (errors get flagged).
- Network log if the component does fetches.

**Where it lives:** `evidence/screenshots/` + `evidence/dom-snapshots/` + `evidence/console/` + `evidence/network/`.

**Default scenarios:** mount, primary interaction (click, type, drag — depends on component), unmount. Custom scenarios per task can be specified in the task frontmatter:

```yaml
evidence-scenarios:
  - mount
  - open-context-menu
  - resize-via-handle
  - close
```

### Visual / styling changes

**What the change does:** modifies CSS, themes, layout — no behavior changes.

**Evidence captured:**
- Screenshots before/after for a fixed viewport.
- Pixel-diff highlights (image-diff comparison with default tolerance).
- Theme-switching scenarios if relevant.

**Where it lives:** `evidence/screenshots/` with `before-`, `after-`, `diff-` prefixes.

**Pixel-diff threshold:** default 0.1% of pixels different. Configurable per task. Above threshold, the diff image is flagged as a "visible change" — the Verifier doesn't reject (visible changes are often the point), but the Judge sees the highlight.

### Performance-sensitive changes

**What the change does:** touches code paths flagged in conventions as performance-critical, or task body explicitly says "performance" / "optimization."

**Evidence captured:**
- Timing measurements before/after for the relevant scenario (median + p95 over N runs, default N=20).
- Memory snapshots if applicable (heap before/after a session).
- Frame-time histograms for animation-touching changes.

**Where it lives:** `evidence/timing/`.

**Decision rule:** if median timing improves by ≥5% with no regression at p95, evidence supports the AC. If timing regresses by ≥5% at p95, the Verifier flags it even if no AC required performance — a regression in performance-sensitive code is a finding.

### Database / migration changes

**What the change does:** modifies schema, adds columns, runs migrations.

**Evidence captured:**
- Migration up + down test output (run forward, run backward, run forward again).
- Row-count comparison before/after on a fixture dataset.
- Query-plan analysis if the change touches indexed columns.

**Where it lives:** `evidence/tests/` + `evidence/logs/`.

**Decision rule:** down-migration must succeed cleanly. If it doesn't, the migration is unshippable regardless of forward-test pass.

### Documentation changes

**What the change does:** modifies docs, READMEs, comments.

**Evidence captured:**
- Markdown lint output.
- Internal link check (no broken references).
- Spelling/typo flag (informational, not blocking).

**Where it lives:** `evidence/tests/`.

**Note:** documentation changes don't go through the standard fan-out / Verifier path most of the time. They're typically handled by the Librarian's `audit-docs` skill in a sweep. But when a task explicitly is a doc change, this evidence type applies.

## ac-mapping.json

The mandatory evidence index. Maps each acceptance criterion to the evidence files that support it.

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
        "evidence/ipc-traces/trace-execute-command.json",
        "evidence/logs/stdout-execute-command.txt"
      ],
      "verdict": "pass"
    },
    "AC3": {
      "claim": "Multiple terminals are independent",
      "evidence": [
        "evidence/ipc-traces/trace-three-terminals.json"
      ],
      "verdict": "pass"
    },
    "AC4": {
      "claim": "Closing the widget kills the PTY",
      "evidence": [
        "evidence/logs/stdout-close-widget.txt",
        "evidence/ipc-traces/trace-close-widget.json"
      ],
      "verdict": "pass"
    }
  },
  "additional-findings": [
    {
      "severity": "info",
      "note": "PTY cleanup on app reload not tested by AC; flagged for follow-up."
    }
  ]
}
```

This file is what the Judge reads first. The Verifier writes it; the runner enforces that every AC has at least one evidence pointer.

## How the Judge consumes evidence

1. Read `ac-mapping.json` per attempt.
2. Sample one or two evidence files per AC to validate the Verifier's claims aren't fabricated.
3. Compare evidence across attempts when ranking — e.g., screenshot quality, timing measurements, console-error count.

The Judge does NOT re-verify everything. The Verifier is trusted; spot-checks confirm trust.

## How the human gate consumes evidence

The human reviewing a verdict sees:

- The verdict itself (`council/<id>/verdict.md`).
- A summary table from `ac-mapping.json` linking each AC to its evidence files.
- One-click access to evidence files (via the canvas widget or the file system).

Default: the human samples evidence for any AC that's non-trivial. If the verdict's confidence is low, the human dives deeper.

## Streaming to backend

The evidence directory is gitignored locally. It streams to the ultimate-widget backend (per `07-runtime-data.md`) where it's stored long-term and made queryable across repos.

What's streamed:

- `ac-mapping.json` (always — it's structured)
- Screenshots and DOM snapshots (compressed)
- Test output text (always — small)
- Network HARs (only if AC explicitly references network behavior; otherwise cleaned up)
- Timing JSON (always — small, valuable for trend analysis)

What's NOT streamed (kept local, then deleted):

- Playwright video recordings unless the test failed
- Heap snapshots above a size threshold
- Network HARs that exceed size threshold without explicit AC reference

The backend retains streamed evidence per its retention policy (default 365 days).

## Local retention

`.agents/runs/<run-id>/evidence/` is kept locally for the duration of the run. Once the task archives, the directory is preserved if the run was the winner (linked from the verdict) and removed otherwise.

A monthly Librarian sweep reclaims disk by removing evidence directories older than a configurable threshold (default 30 days), provided the streamed backend record is intact.

## Failure capture

When the Verifier rejects an attempt, the evidence directory is preserved untouched as part of the failure record. The Implementer's retry sees the same evidence directory referenced in the `failure.md` (per `14-failure-loop.md`), which is critical for understanding why the prior attempt was rejected.

## What evidence is NOT

- Not a substitute for the test suite. Tests are evidence; evidence is broader (screenshots, traces, timing). The test suite still needs to exist.
- Not a substitute for the Verifier's judgment. Evidence supports a claim; the Verifier interprets evidence into a pass/fail per AC.
- Not unbounded. Capture is targeted by change type. Capturing everything for every task wastes time and storage.
- Not the same as logs. Logs (in `runs/<run-id>/logs/`) are agent-process logs; evidence is task-result-shaped artifacts.
