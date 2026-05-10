# Retrospective: task 019 — second medium-track journey

**Date:** 2026-05-10
**Task:** Workflow taxonomy v1 — codify fast-track + medium-track + ship-feature as real files; runner reads them
**Outcome:** ✅ passed (commit `ccdb612` on main)
**Workflow:** `medium-track` (Planner → Implementer → Verifier; no Librarian, no Judge)
**Roles run:** 3 of 5
**Agent wall-time:** ~23 min (planner 3.4min opus, implementer 10.1min sonnet, verifier 9.3min sonnet; 139 tool calls; 270,906 tokens)
**Total session wall-clock incl. human gates:** ~3.5 hours (review + side discussion + triage of tasks 002-014)

This was the **second medium-track journey** — confirming the workflow shape's Pareto position empirically with a second data point on a different task scope (workflow taxonomy authoring vs runner-state seeding in journey 4).

This is also the journey that **codifies its own workflow shape as a real file** — task-019's deliverable includes `base/workflows/medium-track.md`. The artifact loops back on itself: the next medium-track journey will read this file rather than improvising from a prior retrospective.

## What worked

- **The runner's seeding code from task-021 fired in production for the first time.** Every role dispatch (Planner, Implementer, Verifier) emitted `[runner] Seeded 1 input(s) into worktree:` showing the task body was copied to `inputs/`. Dogfood feedback loop closing: task-021 added the feature, journey 5 used it. No absolute-path injection in any agent prompt.
- **Plan-then-implement-then-verify cadence held cleanly.** Planner produced ADR 0003 with closed-set predicate language (6 atoms, AND-only) — a small but load-bearing language design decision that could have ballooned into v1.5/2.0 over-engineering if made under deadline. Plan-then-implement separated that decision from execution time pressure.
- **ADR 0003 is doing real work as a constraint.** Implementer claimed compliance ("`VALID_PREDICATE_ATOMS` matches ADR 0003 §2"); Verifier checked literally, byte-for-byte. The ADR is now a contract that the schema module enforces and tests verify. Future workflow additions will be checked against the same atom set.
- **Stub safety property preserved.** The 5 stub workflow files all carry the verbatim `**STUB.** This workflow is named in the v1 taxonomy but has not yet been empirically validated...` banner. Implementer didn't get clever and edit the wording. Verifier confirmed.
- **F028 mitigation followed.** No new `select_inputs` callsite was added in `dispatch_roles` — the Implementer chose not to add seeding to the new dispatch path (correctly — seeding happens elsewhere). Verifier confirmed via grep.
- **66/66 tests green.** 30 new tests across 2 files (23 in `test_workflow_schema.py`, 5 + 2 helper-coupling adjustments in `test_runner.py`). All 36 existing regression tests still pass. Test file shapes match `test_resolution.py` precedent (sys.path bootstrap, tmp_path fixtures).
- **Override resolution is fail-loud, not fail-quiet.** Per ADR 0003 §4: unknown workflow name raises ValueError immediately with available names — no silent fallback to ship-feature. Verifier ran the negative test case.

## What didn't work / new findings

- **AC1 wording vs. plan's stub spec conflict.** AC1 said all 9 files declare 6 new fields; the plan's stub frontmatter spec listed only 5 (no `exit-criteria`). Implementer followed the plan; Verifier flagged as "partial" but voted pass given graceful parser fallback. **Resolution this journey:** clarified ADR 0003 to explicitly state stubs MAY omit `exit-criteria`. **Lesson for future journeys:** when an AC and a plan section conflict, the Verifier should escalate the conflict explicitly rather than absorbing it as a partial — the human can adjudicate quickly. We got lucky here that the conflict was minor.
- **No new findings emitted this run.** First clean journey by that metric since journey 1. Possibly a sign the spec is converging; possibly the run was less deeply self-observed because the Implementer focused on correct execution. Watch this in journey 6 — if findings remain at zero, may indicate insufficient self-observation rather than a bug-free spec.

## Validations (things this run confirmed empirically)

1. **Medium-track is reproducible.** Two journeys (4 and 5) on different task scopes (runner-state seeding vs workflow taxonomy authoring), both ~30min agent / 200-275k tokens / 2 gates / 1 ADR. The shape holds.
2. **Token cost scales with file-surface, not architectural complexity.** Journey 4 changed 7 files for 215k tokens; journey 5 changed 14 files for 271k tokens. Roughly 1.26× more files = 1.26× more tokens. The architectural decision (1 ADR) was about the same cost.
3. **Plan + ADR is strictly more valuable than plan-only when downstream tasks will reference the decision.** ADR 0003's predicate-atom set will be referenced by every future workflow file, every gate-rules validator extension, every new atom proposal. Without ADR 0003, that constraint would be implicit and decay.
4. **The runner can dispatch by workflow name now.** `dispatch_roles` is wired (parses workflow, iterates roles in declared order, evaluates gate-rules per role, raises ValueError on unknown). Real subprocess fork remains task-009 territory — but the *shape* of dispatch is now driven by the workflow file, not the human improvising.
5. **Self-improvement loop continues to hold.** Tasks shipped so far have closed F020 (registry-source-self), F021 (runner seeds inputs), and now formalized fast-track + medium-track. Each journey's deliverable improves the next journey's experience.

## Comparison across all five journeys

| Metric | J1 ship | J2 ship | J3 fast | J4 medium | **J5 medium** |
|---|---|---|---|---|---|
| Task | canvas-000 | budai-004 | budai-020 | budai-021 | **budai-019** |
| Roles run | 5 | 5 | 1 | 3 | **3** |
| Agent time | ~50min | ~50min | ~16min | ~30min | **~23min** |
| Tokens | ~250k | ~306k | ~50k | ~215k | **~271k** |
| Tool calls | n/a | 174 | 41 | 83 | **139** |
| Human gates | 6 | 6 | 1 | 2 | **2** |
| Worktrees | 2 | 2 | 0 | 2 | **2** |
| ADRs written | 0 | 0 | 0 | 1 | **1** |
| Files touched | 8 | 13 | 7 | 7 | **14** |
| Tests added | n/a | 12 | 9 | 15 | **30** |
| Findings emitted | 19 | 8 | 1 | 1 | **0** |

**Trend:** medium-track is now stable at ~30min / ~250k tokens / 2 gates. Fast-track at ~16min / 50k / 1 gate. Ship-feature at 50min / 300k / 6 gates. Three workflows, three Pareto points, real empirical bands.

## Findings → tasks mapping

- No new findings this journey.
- ADR 0003 stub-exit-criteria clarification added in the same journey (post-Verifier, pre-merge).

## Recommendations for next journey

The next journey can pick from several queued tasks. After this one, the choice space looks like:

- **Task-022 (auto-flip frontmatter on role completion)** — now unblocked. Depends on task-019 (workflow gate-rules) which just shipped, and task-020 (resolution) which shipped earlier. **This is the next-largest-impact ship**: closes ~30% of journey gates by removing mechanical frontmatter edits. Likely medium-track shape (one architectural decision: how does the runner decide when to halt vs auto-flip?).
- **Task-018 (stats emission)** — partly shippable without task-009. Schema + aggregation layer can land; token counts stay null until 009.
- **Task-013 (first-class audit workflow)** — `audit-repo.md` exists; first journey to dogfood it would validate it as a real workflow. Workflow shape: `strategic-audit` if we want to dogfood the stub directly.
- **Task-015 / task-017 (small Sweeper / docs fixes)** — fast-track candidates to validate fast-track shape on different scopes.

## Surprises worth remembering

- **Verifier ran longer than Implementer per-token but with similar tool-call count** — Implementer 61 calls / 113k tokens / 607s; Verifier 53 calls / 72k tokens / 558s. The Verifier's calls are heavier per-call: each AC means a pytest invocation + file read + evidence write. Worth knowing for cost models.
- **Opus Planner cost less than expected.** 25 tool calls / 86k tokens / 201s — same band as journey 4's planner (18 calls / 84k tokens / 232s). The opus-Planner-decided ADR adds no tokens to subsequent runs because the ADR is a static file, not re-derived.
- **The implementation closed "improvise-the-workflow-shape" as a class of friction.** From journey 6 onwards, every task with a `workflow:` field will route through `dispatch_roles` reading the declared workflow file. The runner won't improvise. The human won't either (unless overriding via `--workflow` flag). This was the whole point of task-019, and it shipped.
- **First clean-findings journey since journey 1.** Could mean spec is converging; could mean self-observation was lower this run. Worth watching journey 6 to see which.

## Things to test next time

- **Whether `workflow: medium-track` in a task's frontmatter actually causes the runner to dispatch by it.** This journey added the wiring; journey 6 will be the first to observe a real task pulling its workflow shape from the runner instead of from the human's prompt-to-Implementer.
- **Whether the stub workflows' `**STUB.**` banner survives a journey that wants to use one.** If anyone dispatches `--workflow scaffold-docs` (a stub), the runner should load it without crashing but the operator should see the banner clearly.
- **Whether `evaluate_predicate` correctly handles the journey-state context plumbing** when a real auto-approve gate fires (vs. the all-`human` gate-rules of medium-track and fast-track). Task-022 will be the first to actually evaluate predicates against journey state.
