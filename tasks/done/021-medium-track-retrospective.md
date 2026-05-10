# Retrospective: task 021 — first medium-track journey

**Date:** 2026-05-10
**Task:** `bin/lib/runner.py` seeds worktree inputs before role dispatch
**Outcome:** ✅ passed (commit `2cb8975` on main)
**Workflow:** `medium-track` (Planner → Implementer → Verifier; no Librarian, no Judge)
**Roles run:** 3 of 5
**Agent wall-time:** ~30 min (planner 4min opus, implementer 8min sonnet, verifier 18min sonnet; 83 tool calls total; 214,669 tokens)
**Total session wall-clock incl. human gates:** ~4 hours (with significant idle time during review)

This was the first journey to validate **medium-track** as a real workflow shape — the middle path between fast-track (1 role, no ceremony) and ship-feature (5 roles, full ceremony). Goal: empirically confirm that for tasks with one architectural decision worth an ADR but no archaeology phase needed, three roles is the right cost.

## What worked

- **Skipping the Librarian was the right call.** Files-to-touch were crisp from the task body (`bin/lib/runner.py`, `bin/agent`, new `journey_state.py`). The Planner read 6 source files directly in its first pass — same archaeology-coverage as a Librarian bundle would have produced. Saved one role's worth of compute (~50–80k tokens, one human gate). The bundle is most valuable when the task touches >5 files OR has ambiguity about which files matter; task-021 had neither.
- **Skipping the Judge was the right call at fan-out 1.** The Verifier's verdict is the source of truth when there's only one attempt. Judge would have read the same evidence and written a verdict.md saying "passed, recommend merge" — pure ceremony. The human's merge decision IS the Judge call.
- **Planner-as-architect with ADR.** The task had `needs-architect: true` and the Planner produced ADR 0002 capturing three coupled decisions (module boundary, copy semantics, cleanup lifecycle) in one place. The Implementer then implemented mechanically; no second-guessing the architecture. ADR 0002 is also load-bearing for tasks 019 and 022 — they'll read the same file rather than re-deriving the seeding contract.
- **Patch applied cleanly to fresh main-based worktree.** Confirms portability — the change is self-contained and doesn't depend on uncommitted state in the Implementer's worktree. (Ironic and on-brand: the very task that fixes "worktrees don't see uncommitted main state" is itself robust to that problem.)
- **Implementer self-bounded scope correctly with one honest deviation.** Plan said use `seed_worktree_inputs` wrapper from `compose_system_prompt`; Implementer used `seed_worktree` directly to avoid double-seeding. Flagged in writeup. Verifier validated as defensible. Good shape — the Implementer didn't silently deviate, and the Verifier didn't rubber-stamp.
- **15 new tests + 21 regression all pass.** Same shape as journey 2 and 3: pytest-driven, behaviour-named, covers each AC explicitly. The two test files (`test_journey_state.py` 11 tests, `test_runner.py` 4 tests) reflect the module split cleanly.
- **Single architecture decision, single ADR.** The plan-then-execute split kept the architectural choice from being made in code under deadline pressure.

## What didn't work / new findings

- **`compose_system_prompt` is no longer pure.** The Implementer's plan-departure (calling `seed_worktree` directly inside `compose_system_prompt`) means a function named `compose_*` now has a real filesystem side effect — it copies files into the worktree as a byproduct of being called. Verifier flagged this as a code smell; Implementer flagged the same thing in attempt-A.md as a future refactor candidate. Captured as **F028**. The right fix is probably to pull seeding out of `compose_system_prompt` entirely and into a sibling `prepare_dispatch` orchestration function that runs before any text composition.
- **`select_inputs` defaults layout to `legacy-four-folder`.** On a `standard`-layout consumer repo, callers who forget to pass `layout=manifest.tasks_layout` will silently look in the wrong folders. The default exists because budai itself uses `legacy-four-folder` and tests don't construct manifests for layout. But tasks 019 and 022 will both call `select_inputs` and need to be explicit. Captured in F028 as the second concern. The right fix when task-019 ships is probably to require the caller to pass layout explicitly (raise on missing rather than default).
- **Wall-clock 4 hours, agent-active 30 minutes.** Most of the calendar time was the human (me) reviewing each role's output between gates. Two human gates totaled ~30 minutes of focused review + ~3 hours of idle/context-switch time. This is the irreducible cost of "human at every gate" — task-022 (auto-flip frontmatter) addresses paperwork but not review time. The actual lever for shrinking calendar time is **review batching** — review N tasks in a single pass — not workflow optimization.

## Validations (things this run confirmed empirically)

1. **Medium-track is real.** Three roles is the right cost when one architectural decision needs to be made deliberately and the change is non-trivial enough to warrant evidence capture. ~30min agent / 215k tokens / 2 gates / 1 ADR.
2. **The Planner's job in medium-track is "make the architectural call and write the ADR."** No bundle to consume; the Planner is doing the archaeology that a Librarian would have curated, but with the goal of producing a plan rather than a curated bundle. This is fine because for medium-track scope (one decision, ≤7 files), the cost of skipping curation is low.
3. **The Verifier's job in medium-track is "code-review + evidence capture, not ranking among attempts."** With one attempt and no Judge, the Verifier's verdict is final. Made the Verifier's prompt simpler than journey 2 (no comparative language).
4. **Plan + ADR is a strictly better artifact than plan-only for tasks that block downstream work.** Tasks 019 and 022 will both read ADR 0002. If the Planner had written only a plan, that decision would have been buried in the task body — discoverable but not indexed. ADR 0002 is now a first-class file under `memory/decisions/` that any future agent can `grep` for "input seeding" and find.

## Comparison across all four journeys

| Metric | J1 ship-feature | J2 ship-feature | J3 fast-track | J4 medium-track |
|---|---|---|---|---|
| Task | canvas-000 | budai-004 | budai-020 | budai-021 |
| Roles run | 5 | 5 | 1 | 3 |
| Agent wall-time | ~50 min | ~50 min | ~16 min | ~30 min |
| Tokens | ~250k (est) | ~306k | ~50k | ~215k |
| Tool calls | (not captured) | 174 | 41 | 83 |
| Human gates | 6 | 6 | 1 | 2 |
| Worktrees | 2 | 2 | 0 | 2 |
| ADRs written | 0 | 0 | 0 | 1 |
| Tests added | (not captured) | 12 | 9 | 15 |
| Findings emitted | 19 | 8 (F020–F027) | 1 (F027) | 1 (F028) |

Trend: medium-track sits cleanly between fast-track and ship-feature. **About 70% of ship-feature's cost; about 4× fast-track's cost.** The "right" workflow is task-shape-dependent, not "always pick the cheapest" — F028 was caught by the Verifier and would have been missed in fast-track.

## Findings → tasks mapping

- **F021:** ✅ closed by this commit. Already in Promoted section with `→ task-021` marker.
- **F028:** new finding (compose_system_prompt + select_inputs concerns). Added to `findings.md` Open section.

## Recommendations for medium-track workflow file (input to task-019)

When task-019 ships, `base/workflows/medium-track.md` should declare:

- **Roles:** `[planner, implementer, verifier]` (three).
- **Entry criteria:** `needs-architect: true` AND `fan-out: 1` AND files-to-touch is enumerable from task body (no archaeology phase needed). Or: `complexity: medium` for tasks where we know the shape but want a plan-then-implement-then-verify cadence.
- **Skipped artifacts:** bundle (no Librarian), verdict file (no Judge — Verifier's report is final).
- **Required artifacts:** plan (in task body), ADR (if any architectural decision is made), `attempt-A.md` writeup, `attempt-A.patch`, `evidence/ac-mapping.json`, regression-test pass.
- **Auto-approve when:** never auto-approves the merge (always single human gate at the end); auto-flips status on Planner-success and Implementer-success per task-022 logic, with human gate at Verifier-output.
- **Not appropriate for:** trivial fixes (use fast-track), multi-attempt fan-out (use ship-feature), tasks where the architectural shape is itself contested (use ship-feature so Judge can rank attempts).

## Surprises worth remembering

- **The Planner cost more compute than the Implementer.** 84k tokens (planner, opus) vs 75k (implementer, sonnet). This is the opposite of journey 2 where the Implementer did the heavy lifting. The Planner spent its tokens reading 6 source files + writing the ADR + writing the 7-section plan + appending it to the task body. Worth it given ADR 0002's downstream value, but flag for future medium-track runs: opus-Planner is expensive on token-heavy archaeology phases.
- **The Verifier was the longest role by wall-time** (~18 min) despite being sonnet — not because of compute, but because evidence capture for 7 ACs takes a lot of small file writes (per-AC `evidence/<id>/pytest.txt` + `ac-mapping.json` + verifier report append). 31 tool calls. Worth questioning whether the evidence-capture skill could be more compact for medium-track (e.g., one consolidated evidence file rather than per-AC subdirectories). Defer until task-019 to decide.
- **No infrastructure blockers hit this run.** Journey 3 (fast-track) avoided F021/F022/F023 by simply not running the roles that triggered them. Journey 4 (medium-track) ran the Verifier and Planner without recurrence: F022 (chip recurrence) was avoided by explicit prompt prohibition that held this time, F021 (worktree input seeding) is what this task fixes. F023 (Judge `bin/task new`) wasn't hit because no Judge.
- **The whole journey ran end-to-end with two human gates.** Journey 2 had six. Journey 3 had one. The Pareto curve is now clear: each additional gate buys ~one role's worth of additional verification, at the cost of ~30min calendar time per gate.
- **Settings.local.json restart was successful.** This was the first push after the granular allow-list change in journey 3. Permission prompt behavior should be: routine ops auto-allowed, `git push` prompts. Will be tested at the actual push step (next).

## Things to test next time

- **`bin/agent run` with the new `--worktree` flag actually works end-to-end with seeding active.** This run validated the code paths via unit tests; manual journey 5 will be the first to dispatch with `--worktree .agents/council/<id>/worktrees/attempt-A` and observe a real seeded `inputs/` directory.
- **F028's two concerns surface in tasks 019/022.** Watch whether the `select_inputs` default-layout silent-mis-route bites those tasks before the refactor lands.
- **Whether ship-feature is now actually needed or whether everything fits fast-track or medium-track.** If yes, the workflow taxonomy may simplify to two real shapes plus rare ship-feature. Empirical question for journeys 5–10.
