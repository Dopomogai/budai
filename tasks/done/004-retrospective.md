# Retrospective: task 004 — second budai journey, dogfooded on budai itself

**Date:** 2026-05-09
**Task:** Wire the manifest's `tasks-layout` field through `bin/task` and add schema/dependency/cycle/transition validation
**Outcome:** ✅ passed (commit `ba890f4` on `main`)
**Roles run:** Librarian → Planner → Implementer → Verifier → Judge (5/5)
**Total agent wall-time:** ~44 min (Librarian ~5m, Planner ~3m, Implementer ~17m, Verifier ~19m, Judge ~6m). Total session wall-clock including human gates: ~90 minutes.

This was the **second** end-to-end manual budai journey, and the **first** dogfooded on budai itself (CanvasOS task 000 was journey 1, on a different stack). Goal: validate that the loop holds across language stacks (TS/React → Python/CLI), surface any new infrastructure gaps that only show when budai consumes itself, and start retiring the manual-glue friction that journey 1 documented.

## What worked

- **The five-role spec held a second time, on a completely different problem shape.** No role escalated, every AC was reachable, no spec contradictions. CLI/Python work moves through the same Librarian → Planner → Implementer → Verifier → Judge pipeline as renderer/TypeScript work — strong evidence the spec is genuinely generic, not accidentally tuned to one stack.
- **The Planner's ADR (`memory/decisions/0001-task-cli-layout-and-validation.md`) earned its keep.** Three coupled decisions (layout discovery, status-vs-folder mapping, validation source-of-truth) were captured in one place. The Implementer didn't have to re-derive them; the Judge had a clean artifact to refer to in the verdict.
- **Status-keyed `move` (vs folder-keyed) was a clean architectural call.** Plan + ADR locked it in early; the Implementer translated it without ambiguity. This is exactly the kind of decision the seven-section format is supposed to surface — would have been lost in a free-form plan.
- **Bundle was lean (15k/84k).** Narrower scope than CanvasOS task 000 (21k), and the headroom let the Librarian include `docs/11-task-format.md` and the full `manifest.py` source without budget pressure.
- **Implementer wrote all 12 tests despite the plan's "task-003 harness pending" caveat — and they ran with stdlib-only pytest.** Good judgment. The plan's caveat turned out to be over-cautious; pytest 9.0.2 with no fixtures was sufficient. We almost shipped no tests on a fence we didn't need.
- **Patch applied cleanly to a fresh main-based worktree.** First time across both journeys that this happened on the first try with no rebase or `--exclude`. The CanvasOS run had `.env` seeding issues; budai has no runtime secrets so this category of friction didn't exist here.
- **Verifier captured *real* CLI smokes**, not just pytest. `evidence/ac{1..5}-cli-smoke/stdout.txt` document end-to-end CLI invocations, which is exactly the right evidence shape for a CLI-fix scope.
- **F002 (encoded token count in bundle filename) applied manually.** `004-task-cli-four-folder-and-schema-validation.bundle.15k.md` reads at-a-glance.
- **Tighter prompts continue to work.** The composed system prompts (~250 lines from `compose_system_prompt`) plus a focused "## Your task" addendum (~150 lines per role) gave each agent everything it needed without padding. Validates the F007 thesis from journey 1.

## What didn't work (new findings → next budai tasks)

- **F020 — `registry-source: self` resolution gap.** First `bin/agent run` returned `Role not found: librarian / Available roles: []`. Root cause: `bin/lib/resolution.py` always looks at `.agents/base/<category>/...` even when the manifest says `registry-source: self`, but budai's authoritative tree lives at `<repo_root>/base/`. Workaround: symlink `.agents/base -> ../base`, gitignore it. Real fix: a `registry-source: self` branch in `resolution.py` that points at `<repo_root>/base/`, and `librarian sync` (task-011) populating `.agents/base/` automatically for non-self consumers. **P0** — every dogfood run is blocked until this is fixed without a manual symlink.
- **F021 — Worktrees don't see uncommitted main-worktree state.** The task move (`tasks/todo/004-* → tasks/in-progress/004-*`), the appended Plan section, the new ADR, the new bundle file — all were uncommitted in the main worktree. Implementer + Verifier worktrees branched from `main`, so they had stale views. Workaround: instructed each agent to read task body / plan / bundle / ADR via absolute paths to the main worktree. Three sites of "absolute-path-injection" in the agent prompts. **P0/P1** — runner should copy these inputs into `.agents/runs/<run-id>/inputs/` (or commit them to a per-task branch) before dispatching downstream roles.
- **F022 — Host UI chip recurrence even with explicit prompt-level guard.** Verifier emitted a `mcp__ccd_session__spawn_task` chip ("a doc-sweep chip has been spawned") despite the prompt explicitly forbidding it. The same finding (`backlog` status not in `docs/11-task-format.md`) was correctly captured in the Verifier report and ac-mapping.json — so the chip was redundant — but it confirms F016's deeper hypothesis: prompt-level guidance isn't enough, **runner-permission denial is the right fix layer**. The claude-code runner spec already supports `--allowed-tools`; task-010 (runner permission enforcement) makes this real.
- **F023 — Judge can't `bin/task new` for follow-ups when the task itself is `bin/task` improvements.** Chicken-and-egg: the Judge wanted to spawn `015`, `016`, `017` follow-ups via the new four-folder-aware `bin/task`, but doing that *before* committing the patch would have created the files in the still-broken `tasks/open/` (and after committing, the Judge's working tree was the post-patch state, where it still works). Workaround: Judge hand-created the three task files. Acceptable, but worth noting. Mitigation pattern: use `bin/task` from the post-commit working tree; or have the runner expose a "use the patched copy" flag.
- **F024 — Tests added two scaffolding files (`tests/__init__.py`, `tests/bin/__init__.py`) beyond the plan's literal files-to-touch.** Defensible (pytest discovery requires them) and transparent in the writeup. But strict AC5 (Implementer's "no source files modified outside the Planner's files-to-touch list" — wait, this is task-000's AC5; task-004's AC5 is about validation) — the Implementer expanded scope by 2 zero-byte files. The plan should pre-list test scaffolding, OR the convention should explicitly allow zero-byte `__init__.py` files when adding a new test directory.
- **F025 — Manual frontmatter flips, again.** ~5 status flips (`planning → reviewing-plan → implementing → reviewing-result → done`), 2 boolean flips (`plan-approved`, `result-approved`). Same problem as journey 1 (F015 / task-005-or-006 territory). Auto-approve criteria + status-flip-on-role-completion would absorb most of these.

## Validations (things this run confirmed empirically)

1. **The five-role spec is stack-agnostic.** It worked end-to-end on Python/CLI just like it worked on TS/React. The bundle's relevance scoring picked the right files in both cases. Strong signal for portability claims.
2. **The Planner's seven-section format produces ADR-worthy artifacts naturally.** When the work has 2+ coupled architectural choices, ADRs fall out of the format. When it doesn't (CanvasOS task 000 was a 3-line bug fix), ADRs are skipped. The format scales correctly with task size.
3. **Stdlib-only pytest is sufficient for unit tests on `bin/lib/*`.** Task-003 (CLI test harness) is an ergonomics bet, not a hard prerequisite. Don't gate future runs on it landing first.
4. **Single human at all gates is sustainable for one task** (this confirms journey 1's finding for a different shape of task). Auto-approve criteria for fan-out: 1 cases that pass clean would handle most of the gates we hit.
5. **Failures from missing infrastructure don't break the journey.** F020 surfaced before role 1; we worked around it in 30 seconds with a symlink. Same as journey 1: knowing what's glue is the point.
6. **Patch isolation works.** The verifier worktree (separate from the implementer's, intentionally) confirmed the patch is self-contained — no hidden state leaks across worktrees.

## Findings → tasks mapping

19 findings carried over from CanvasOS journey 1; 5 new findings this run (F020–F024 plus F025 as a reaffirmation). Status:

| Tier | Findings | Tasks |
|---|---|---|
| Tier 1 (this-run quick wins) | bundle filename `15k.md` | applied directly; was already on the F002→task-007 path |
| Tier 2 (budai changes, this run) | F020 (registry-source resolution), F021 (worktree input seeding), F022 (chip-tool deny via runner), F023 (Judge bin/task chicken-and-egg), F024 (test scaffolding), F025 (manual frontmatter flips, recurrence) | F020 lives in `findings.md` Open section; F021/F022/F023/F024/F025 to be promoted in next sweep |
| Tier 3 (existing dogfood backlog) | tasks 001–014 | unchanged; this run's work was task-004 |
| Auto-spawned by Judge (this run) | tasks 015 (doc add `backlog` status), 016 (subprocess integration tests), 017 (Sweeper regenerate-index) | landed in `tasks/todo/` |

## Comparison with CanvasOS journey 1 (friction count)

| Friction class | CanvasOS task 000 | budai task 004 | Delta |
|---|---|---|---|
| Manual frontmatter flips | ~6 | ~7 (5 status + 2 booleans) | +1 |
| Worktree creates | 2 | 2 | 0 |
| Patch generations | 1 (manual) | 0 (worktrees produced clean diffs) | -1 ✅ |
| Task moves between folders | ~3 | 1 (final archive only) | -2 ✅ |
| .env seeding | 1 (manual `cp`) | 0 (budai has no secrets) | -1 ✅ |
| F020 symlink workaround | 0 | 1 | +1 |
| F021 absolute-path-injection (per role) | 0 | 3 | +3 |
| ADR / test-scaffold inter-worktree copy | 0 | 1 | +1 |
| **Total** | **~13** | **~15** | **+2** |

Net: friction was *slightly* worse this run, driven by F020 (one-time symlink) and F021 (recurring per-role absolute-path-injection). Without those: **~11**. After task-011 (librarian sync — fixes F020) + a runner-side input-seeding step (fixes F021) + auto-approve at fan-out 1 (fixes most of F025): projected friction-count for journey 3 = **~3** (just the unavoidable gate-flip moments).

## Recommendations before journey 3

1. **Land task-011 (librarian sync) and the F020 fix in `bin/lib/resolution.py` first.** These remove the symlink workaround. Together with task-009 (real `dispatch_claude_code`), they make budai's runner truly self-sufficient for dogfood runs.
2. **Add F021 to budai's task queue.** It's not yet on the board; it bit this run hardest after F020. Promote in next findings sweep.
3. **Try fan-out: 2 on journey 3.** Both prior journeys ran fan-out: 1, so anonymized peer review + judge-blind ranking remain unvalidated. Pick a task with multiple plausible shapes (a small refactor, or task-006 manifest parser cleanup) and run it.
4. **Add `audit-docs` as task 018-or-similar.** Several drift items piled up: `backlog` status not in docs (task-015), `dispatch_claude_code` placeholder behavior not documented at the command site, etc. Cheap and parallelizable.
5. **Don't onboard another consumer until task-011 + task-009 land.** Onboarding a third consumer (e.g., the Dopomogai monorepo) without those fixes would propagate the F020 symlink workaround three times. Wait.

## Surprises worth remembering

- **F020 was latent until the first `bin/agent run` against budai itself.** It existed all along (resolution.py always pointed at `.agents/base/`), but the CanvasOS run didn't hit it because CanvasOS *does* keep its base copy under `.agents/base/`. Self-dogfooding is the only context that surfaces this class of bug. Strong argument for budai-on-budai as a permanent CI step once the runner is real.
- **The Implementer's choice to write 12 tests with stdlib-only pytest, ignoring the "depends on task-003" fence in the plan.** This was good judgment. The plan was over-cautious; the agent saw that pytest works fine without a custom harness and shipped tests anyway. Validates that Implementers are allowed to relax a plan's *unnecessary* fences (vs strict files-to-touch, which they correctly held to).
- **The Judge's `git apply --exclude` for the ADR file.** Planner had written the ADR to disk in the main worktree; Implementer copied it into the patch (per instruction); Judge had to apply the patch with the ADR path excluded to avoid re-creating an already-on-disk identical file. F021 directly: if the runner had seeded inputs into the worktree before Implementer dispatch, the Implementer would have read the ADR from its own worktree without needing to copy it across.
- **F022 (chip recurrence with explicit guard) is the strongest argument yet for runner-permission enforcement.** Even when the Verifier was *told* not to use the chip tool, it did anyway. This is no longer a "prompt better" problem — it's a "deny the tool at dispatch" problem. Task-010 (runner permission enforcement) graduates from P1 to P0 in my read.
- **Stats-side: at fan-out 1, the Judge step is 90% paperwork.** The verdict captures the audit trail, but with a passed verifier report and one attempt, there's nothing to choose. Auto-approve at fan-out: 1 + verifier-passed + all-AC-pass would skip 5–10 minutes of agent time per journey. Reasonable optimization once we have ≥3 successful runs of evidence.
