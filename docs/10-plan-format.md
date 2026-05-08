# 10 — Plan format

The **plan** is the data contract between the Planner and the Implementer. It's an elaborate, file-by-file specification appended to the task body — detailed enough that an Implementer can execute mechanically without re-deriving anything.

A plan is not a paragraph. It's a structured document that survives audit, supports parallel attempts, and answers downstream questions before they're asked.

## Why plans must be elaborate

Three forces push toward elaborate over terse:

1. **Fan-out diverges on vagueness.** When two Implementers run in parallel on the same task and the plan is vague, they diverge productively (different solutions) and unproductively (different problems). The Judge's peer review can pick the better solution; it can't pick between agents that solved different problems.
2. **Audit requires reconstruction.** Months later, looking at a closed task, the plan should answer "why did we do it this way?" without requiring a re-read of the diff and a guess at the Planner's intent.
3. **Mechanical execution is faster and cheaper.** When the plan specifies "create file X with structure Y", the Implementer at Sonnet can ship without escalating to Opus. Vague plans force the Implementer to make architecture decisions, which means slower runs at higher tier.

The cost of writing an elaborate plan is paid once at Opus (Planner). The savings compound across every Implementer instance and every audit.

## Where the plan lives

Appended to the task body under `## Plan`. The Planner edits the task file in place; the rest of the task body (objective, user story, AC) stays untouched above the plan.

```markdown
---
id: 042
title: Add terminal widget
type: feature
status: planning
...
---

# Task 042: Add terminal widget

## Objective
...

## User story
...

## Acceptance criteria
...

## Plan
<this is what the Planner writes>

```

A plan-approved task is one with `plan-approved: true` in frontmatter, set by the human at the architecture gate (or by auto-approve rules per `05-workflows.md`). Until then, no Implementer spawns.

## Required sections, in order

The Planner writes these seven sections, in this order. Missing sections fail hand-off validation; the Planner is re-invoked.

### 1. Approach

2-4 sentences. The strategic shape of the change. What approach was chosen, and (briefly) why over alternatives.

Not a paragraph of rationale — that goes in an ADR if the choice is meaningful. Not a list of files — that's the next section. Just enough for a future reader to understand intent at a glance.

### 2. Decomposition

One of two formats:

**Single task:**
```markdown
### Decomposition
Single task — one Implementer.
```

**Decomposed:**
```markdown
### Decomposition
Coordinator task. Spawning sub-tasks:
- 042a — Implement TerminalManager in main process
- 042b — Wire IPC channel + preload exposure
- 042c — Build renderer-side TerminalWidgetNode

(Sub-tasks created via `task new` during plan generation; see depends-on chains in their frontmatter.)
```

When decomposed, the parent task's status flips to `coordinator`. The parent doesn't run an Implementer; the sub-tasks do. See "Decomposition output" below for full mechanics.

### 3. File-level changes

The longest and most important section. Two sub-sections:

**Files to create.** For each new file:
- Path
- Purpose (one line — what this file does)
- Exports (names of public symbols)
- Key decisions (architectural choices that shape the file)
- Notes for the file header (what to put in `@gotchas`, `@stability`, etc.)

**Files to modify.** For each changed file:
- Path
- Specific lines or sections to change (line numbers if available; else identifiable section names)
- What the change is
- Why this file (in case it's not obvious from the task)

The level of detail is "an Implementer can read this and start typing." Not pseudocode, but not just "wire it up" either. Concrete enough to be unambiguous; abstract enough that the Implementer chooses the actual code.

### 4. Risks and escalations

Bulleted list. Each bullet:
- The risk
- The mitigation, OR an explicit escalation if mitigation isn't internal

Examples:
- "node-pty is a native module — rebuild step required; flag for postflight."
- "xterm.js sizing under React Flow zoom may misbehave; use ResizeObserver, not the canvas-level zoom."
- "(none requiring human escalation)"

The "none required" form is fine and common; explicit absence beats implicit silence.

### 5. Acceptance criteria mapping

For each AC in the task body, name which file-level change covers it. One line per AC.

```markdown
### Acceptance criteria mapping
- AC1 (terminal renders) → covered by TerminalWidgetNode mount path
- AC2 (commands execute) → covered by IPC roundtrip
- AC3 (multiple terminals independent) → covered by per-id PTY map in TerminalManager
- AC4 (closing widget kills PTY) → covered by unmount cleanup
```

If any AC has no covering change, the plan is incomplete. The Planner either adds the change or escalates that the AC needs revision.

### 6. Recommended fan-out

A single number, with one line of rationale:

```markdown
### Recommended fan-out
1 — mechanical task; fan-out adds cost without diversifying outcomes.
```

```markdown
### Recommended fan-out
3 — architectural ambiguity in how to model the PTY lifecycle; parallel attempts will explore different shapes.
```

The Router uses this when spawning Implementers, unless the task frontmatter explicitly overrides.

### 7. Confidence level

One of: `high`, `medium`, `low`. With one line:

```markdown
### Confidence level
high — no architectural unknowns, prior precedent in BrowserWidgetNode.
```

Low confidence triggers a tighter Verifier retry budget and may auto-escalate to a second Planner review before approval.

## Optional section: ADR

If the Planner makes a meaningful architectural choice, it writes a new ADR to `memory/decisions/<NNNN>-<slug>.md` and adds a section to the plan:

```markdown
### ADR
Wrote `memory/decisions/0042-pty-lifecycle-ownership.md` documenting why
PTY lifecycle lives in the main process rather than the renderer.
```

ADRs are short markdown files (1-2 pages typical) following the standard ADR shape: Context, Decision, Consequences. ADRs are durable and rarely revised; they're reference, not prose.

## Decomposition output

When the Planner decomposes a task, it does NOT spawn Implementers itself. The flow:

1. The plan body becomes a coordinator description (the seven sections, but `Decomposition` lists sub-tasks instead of "single task").
2. For each sub-task, the Planner calls `bin/task new` programmatically:
   - The sub-task's `id:` is `<parent-id><letter>` (e.g., `042a`, `042b`).
   - The sub-task's `depends-on:` lists prior sub-tasks in the chain.
   - The sub-task's `objective:` is copied from the relevant File-level changes section of the parent plan.
3. The parent task's frontmatter status flips to `coordinator`.
4. Each sub-task enters the workflow at Step 1 in its own right.
5. The parent task closes when all sub-tasks close. Its archive entry references each sub-task's verdict.

This means decomposition multiplies workflow invocations but each sub-task is small enough for a single deep attempt.

## Validation

A plan is valid if:

1. All seven required sections are present in the spec'd order.
2. Section 3 (File-level changes) has at least one entry, OR the task is decomposed.
3. Section 5 (AC mapping) lists every AC from the task body.
4. Section 6 (Recommended fan-out) is a positive integer.
5. Section 7 (Confidence) is one of `high`, `medium`, `low`.
6. If decomposed: every sub-task ID listed in Section 2 exists as a real task file.

Validation runs at hand-off (Plan → Router → Implementer). Failed validation re-invokes the Planner with the specific failure as input.

## What the plan is NOT

- **Not pseudocode.** The Implementer chooses the actual code. The plan specifies *what* to write, not *how* to write each line.
- **Not a re-statement of the task.** The objective and AC live in the task body; the plan doesn't repeat them. The plan adds the *how*.
- **Not a justification document.** Why-decisions go in ADRs. The plan body is execution-shaped.
- **Not the Implementer's transcript.** The plan is written by the Planner before implementation; the transcript is what happens during implementation. They're separate artifacts.
- **Not editable by the Implementer.** Once approved, the plan is frozen for that task. If the Implementer believes the plan is wrong, it escalates back to the Planner rather than editing.

## Worked example: feature plan

```markdown
## Plan

### Approach
Add a terminal widget by reusing the existing widget pattern. PTY lifecycle
lives in main process for security; renderer talks via IPC. xterm.js handles
rendering; we own only the React shell and the IPC plumbing.

### Decomposition
Single task — one Implementer.

### File-level changes

#### Files to create
- `src/main/TerminalManager.ts`
  - Purpose: Owns lifecycle of node-pty processes, one per terminal widget instance.
  - Exports: `class TerminalManager`, methods `spawn(id, cwd, shell)`, `write(id, data)`, `resize(id, cols, rows)`, `kill(id)`.
  - Key decisions: keep PTY map private; emit data via callback registered by IPC handler.
  - Header @gotchas: Must call electron-rebuild on install; native module.

- `src/renderer/components/widgets/TerminalWidgetNode.tsx`
  - Purpose: React Flow node rendering xterm.js inside a panel.
  - Imports: @xyflow/react, xterm, xterm-addon-fit, useCanvasStore.
  - State: local xterm instance ref; subscribes to terminal-data IPC events.
  - Lifecycle: mount → ipc.terminal.spawn(id); unmount → ipc.terminal.kill(id).

#### Files to modify
- `src/main/index.ts`
  - Lines ~150-180: register four new IPC handlers (`terminal:spawn`, `terminal:write`, `terminal:resize`, `terminal:kill`).
  - Each delegates to TerminalManager singleton.
  - Hook cleanup on `before-quit`.

- `src/preload/index.ts`
  - Add `terminal` namespace to contextBridge with the four methods + `onData(callback)` event subscription.

- `src/renderer/store/useCanvasStore.ts`
  - Add `TerminalWidgetData` to the `AppNode` discriminated union.
  - Add `addTerminalNode(position)` action.

- `src/renderer/components/canvas/SpatialCanvas.tsx`
  - Register `terminal: TerminalWidgetNode` in the `nodeTypes` map.
  - Add "Add terminal" entry to context menu.

### Risks and escalations
- node-pty is a native module — rebuild step required; flag for postflight.
- xterm.js sizing under React Flow zoom may misbehave; use ResizeObserver, not the canvas-level zoom.
- (none requiring human escalation)

### Acceptance criteria mapping
- AC1 (terminal renders) → covered by TerminalWidgetNode mount path
- AC2 (commands execute) → covered by IPC roundtrip
- AC3 (multiple terminals independent) → covered by per-id PTY map in TerminalManager
- AC4 (closing widget kills PTY) → covered by unmount cleanup

### Recommended fan-out
1 — mechanical task; fan-out adds cost without diversifying outcomes.

### Confidence level
high — no architectural unknowns, prior precedent in BrowserWidgetNode.
```

## Worked example: coordinator plan

For decomposed work, the plan is shorter — file-level details live in the sub-tasks, not the parent.

```markdown
## Plan

### Approach
Implement Supabase realtime sync by introducing a typed event bus, a
client-side subscriber, and a server-side publisher. Three concerns;
three sub-tasks.

### Decomposition
Coordinator task. Spawning sub-tasks:
- 062a — Add typed realtime event bus (shared)
- 062b — Server-side publisher writing to bus
- 062c — Client-side subscriber consuming from bus

depends-on chain: 062a → 062b → 062c.

### File-level changes
See sub-task plans. This parent task does not modify files directly.

### Risks and escalations
- Coordination across three sub-tasks: Librarian flagged for cross-cutting docs sweep after 062c lands.
- Schema drift between server and client subscribers: addressed in 062a by deriving both from the same typed source.

### Acceptance criteria mapping
- AC1 (events propagate) → covered by 062a + 062b + 062c integration
- AC2 (typed events on both sides) → covered by 062a
- AC3 (drops handled gracefully) → covered by 062c

### Recommended fan-out
1 per sub-task — sub-tasks are sequenced; parallelism happens between sub-tasks in different scopes, not within a single sub-task.

### Confidence level
medium — subtle schema-versioning concerns; Planner is satisfied with sub-task 062a's approach but flags it as the riskiest piece.
```
