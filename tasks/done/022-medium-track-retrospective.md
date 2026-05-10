# Retrospective: task 022 — third medium-track journey

**Date:** 2026-05-11
**Task:** Runner auto-flips task frontmatter on role completion per workflow gate-rules
**Outcome:** ✅ passed (commit `e3be4b9` on main; pre-flight fix `bac50c5`)
**Workflow:** `medium-track` (Planner → Implementer → Verifier; no Librarian, no Judge)
**Roles run:** 3 of 5
**Agent wall-time:** ~27 min (planner 3.5min opus, implementer 12.8min sonnet, verifier 10.9min sonnet; 144 tool calls; 298,219 tokens)
**Total session wall-clock incl. human gates:** ~3.25 hours

This was the **third medium-track journey** — the first to dispatch via the J5 workflow taxonomy file (`base/workflows/medium-track.md`) and the first to expose a real bug in a prior journey's deliverable.

## What worked

- **Self-improvement loop holding.** J4 added input seeding; J5 codified workflows. J6 used both: every role dispatch printed `[agent] workflow: medium-track (from task frontmatter)` AND `[runner] Seeded 1 input(s) into worktree:`. The deliverables compound.
- **Plan-then-Implement-then-Verify cadence held.** Planner produced ADR 0004 documenting the predicate-context source plumbing — the exact J5-flagged weak spot. Implementer executed mechanically. Verifier checked literal ADR conformance (5/5 sub-checks pass).
- **`apply_transition` as the single code path.** Both `bin/task move` (manual) and the runner's auto-flip now call the same function. AC5 enforced cleanly; the refactor reduced `cmd_move` from ~60 to ~10 lines (relocation, not new logic).
- **Fail-closed semantics.** `build_predicate_context` returns False for every missing-source path: missing `evidence/ac-mapping.json` → `verifier_passed=False` → halt for human. Matches ADR 0003 fail-loud principle.
- **94/94 tests pass.** 28 new in `test_transitions.py` covering each behavior, with explicit AC6a/b/c/d/e markers. 66 regression tests still green.
- **Implementer self-bounded scope correctly with TWO honest plan departures:**
  1. `test_runner.py` updated (not in plan's files-to-touch) — pre-existing test used stub role names not in `ROLE_EXIT_STATUS`; the update was a necessary regression fix forced by the `dispatch_roles` change. Verifier validated as defensible.
  2. AC6a tested with 3-role chain (not 5-role ship-feature) because ship-feature's `planner: human` AND `judge: human` literally make a 5-role all-auto sequence impossible. Verifier confirmed the structural impossibility and that the 3-role variant adequately covers the AC's intent.

## What didn't work / new findings

- **F029 (workflow file YAML parse bug)** — caught at journey-6 pre-flight. `medium-track.md` had unquoted entry-criteria strings with colons; YAML parser crashed; J5's tests missed it because they constructed valid YAML in fixtures rather than parsing the actual shipped files. Fixed inline (commit `bac50c5`). **Smoke-test follow-up is open** — add a `test_workflow_schema.py` test that loads every file in `base/workflows/*.md` via `parse_workflow_file`. Fast-track candidate.

- **F030 (no preloaded inputs in system prompt)** — surfaced by human observation during plan review. Planner spent ~10 Read calls just acquiring context. Task-021's seeding writes files into `inputs/` but the agent still pays Read round-trips. **Proposed task:** budget-aware preloading in `compose_system_prompt` that embeds ~30k tokens of seeded content directly. Medium-track candidate; depends-on task-021 (already shipped).

- **F031 (subagent permission patterns too narrow)** — surfaced by human feedback ("still too many permissions to approve - mostly in the spawned agents"). Spawned subagents issue tool calls that don't match the granular allowlist, especially `git -c user.name=... commit` (doesn't match `Bash(git commit*)`) and compound `&&`/pipe commands. **Proposed fix:** scan transcripts from journeys 4-6 to extract recurring patterns; bulk-update `.claude/settings.local.json`. Fast-track candidate.

- **`auto-when:verifier-passed` not end-to-end exercised in Phase 0.** The Verifier writes `evidence/ac-mapping.json` to its worktree, but `dispatch_claude_code` is still a placeholder; no real Verifier subprocess writes the file at dispatch time. So in Phase 0 the predicate always returns False → halt for human. Correct fail-closed behavior, but the success path won't fire until task-009 lands real subprocess dispatch. Documented in ADR 0004 §3 §Verifier-passed.

## Validations (things this run confirmed empirically)

1. **Medium-track Pareto holds at three data points.** Cost band is now tight: 22-30 min agent / 215-298k tokens / 2 gates / 1 ADR. Three runs on different scopes (runner-state seeding J4, workflow taxonomy J5, frontmatter auto-flip J6).
2. **Workflow files drive dispatch now.** No more human improvising shape. `bin/agent run --role X --task Y` reads `task.workflow`, loads `base/workflows/<name>.md`, dispatches accordingly. The runner's gate-rules consumption is what task-022 added; J7+ will see it auto-flip statuses without human paperwork.
3. **`flip_for_role` works against the J5 predicate language.** Runner reads `gate_rules`, branches on `auto`/`human`/`auto-when:<predicate>`, evaluates predicate via `workflow_schema.evaluate_predicate`, applies `apply_transition` or halts. Tested via 28 unit tests covering every branch.
4. **Findings stream is self-correcting.** F029 (J5 deliverable bug) was caught by the next journey using it. F030 + F031 surfaced via human observation during the journey itself. The system observes itself.

## Comparison across all six journeys

| Metric | J1 ship | J2 ship | J3 fast | J4 medium | J5 medium | **J6 medium** |
|---|---|---|---|---|---|---|
| Task | canvas-000 | budai-004 | budai-020 | budai-021 | budai-019 | **budai-022** |
| Roles run | 5 | 5 | 1 | 3 | 3 | **3** |
| Agent time | ~50min | ~50min | ~16min | ~30min | ~23min | **~27min** |
| Tokens | ~250k | ~306k | ~50k | ~215k | ~271k | **~298k** |
| Tool calls | n/a | 174 | 41 | 83 | 139 | **144** |
| Human gates | 6 | 6 | 1 | 2 | 2 | **2** |
| Worktrees | 2 | 2 | 0 | 2 | 2 | **2** |
| ADRs written | 0 | 0 | 0 | 1 | 1 | **1** |
| Files touched | 8 | 13 | 7 | 7 | 14 | **8** (+1 pre-flight) |
| Tests added | n/a | 12 | 9 | 15 | 30 | **28** |
| Findings emitted | 19 | 8 | 1 | 1 | 0 | **3** |

**Trend:** medium-track stable. The findings-emitted count rebounded from J5's zero — the system is self-observing again, partly via human observations during the journey (F030, F031) plus the runtime bug (F029).

## What's compounding journey-over-journey

- **J3 → J4:** fast-track validated.
- **J4 → J5:** seeded inputs available; runner reads task workflow (taxonomy on disk).
- **J5 → J6:** workflow files drive dispatch; predicate language locked.
- **J6 → J7 onward:** auto-flip closes ~30% of gates per journey. From J7 forward, every medium-track journey should see fewer than 2 gates if `auto-when:verifier-passed` ever fires (it won't until task-009 lands subprocess Verifier).

## Findings → tasks mapping

- **F015:** ✅ closed by this commit. Promoted with `→ task-022` marker.
- **F025:** ✅ closed by this commit. Promoted with `→ task-022` marker.
- **F029:** new finding (workflow YAML smoke test gap). Fast-track follow-up: smoke test for shipped workflow files.
- **F030:** new finding (preload inputs into prompt). Medium-track candidate.
- **F031:** new finding (subagent permission patterns too narrow). Fast-track candidate.

## Recommendations for next journey (J7)

Three sharp options:

- **F031 fix (subagent permissions)** — fast-track candidate. Audit transcripts, bulk-update `.claude/settings.local.json`. Closes the human-feedback friction of "too many permission prompts" that's been recurring since J3. **Highest immediate UX leverage.**
- **F029 follow-up (workflow smoke test)** — fast-track candidate. ~5 lines of test code. Closes a real CI gap.
- **F030 fix (preload inputs)** — medium-track candidate. Saves ~5-10 Read calls per dispatch from J7 onward. Depends-on task-021 (shipped).

If picking one as J7: **F031** — direct human-friction reduction, and J7 will be the first journey to feel its effect (every spawned subagent in J7 will use the updated patterns).

If picking two and bundling: ship F029 + F031 as a single fast-track sweep journey ("workflow YAML smoke test + permission allow-list audit") — both tiny mechanical sweeps, both close real gaps.

## Surprises worth remembering

- **The first downstream-discovered bug.** F029 was a real defect in J5's deliverable. It surfaced because J6's pre-flight used the J5 deliverable in production (via the runner's `[agent] workflow: medium-track` path). The Verifier in J5 didn't catch it because tests built fixtures rather than parsing shipped files. **Lesson:** for any module that parses files-on-disk, add a smoke test that parses the actual files-on-disk, not just synthetic ones. This is now F029's follow-up.
- **The plan was almost too thorough.** ADR 0004 documented every predicate-context source explicitly per atom. Implementer executed mechanically; departures were both forced by external structural constraints (test fixture role names, ship-feature's gate-rules), not by ambiguity in the plan. Confidence was medium going in; in hindsight high.
- **First time the journey trampled itself in a good way.** Pre-flight discovered F029 in J5's deliverable; that fix landed before J6's main feature commit. Dogfooding catches drift the moment new code enters production.
- **Journey time is not converging downward.** J5 was 23 min; J6 was 27 min. The taxonomy is stable, but the verifier still does N file reads + evidence captures per AC, which scales with AC count. Real time savings will come from F030 (preload inputs) — that's the next bottleneck after manual frontmatter flips.

## Things to test next time

- **Auto-flip actually firing in a real journey.** J6 added the wiring; J7 should be the first journey to observe `[runner] Auto-flipped 023: implementing → reviewing-result (gate auto)` in the dispatch output (assuming gate-rules in `medium-track.md` say `implementer: auto`, which they do). Confirm the runner actually does this end-to-end.
- **`transitions.json` populated with real records.** Should land at `.agents/runs/<run-id>/transitions.json` after J7's first role completion. Inspect the schema in production.
- **F029 fix actually catches future bugs.** When the smoke test ships, it should catch any future workflow file with malformed YAML at CI time, not at runtime.
