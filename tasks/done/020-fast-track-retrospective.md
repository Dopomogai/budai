# Retrospective: task 020 — first fast-track journey

**Date:** 2026-05-10
**Task:** `bin/lib/resolution.py` honors `registry-source: self`
**Outcome:** ✅ passed (commit `8a869c3` on main)
**Workflow:** `fast-track` (single Implementer; no Librarian/Planner/Verifier/Judge)
**Roles run:** Implementer only (1/5)
**Agent wall-time:** ~16 min (Implementer alone, sonnet, 41 tool calls, 49,932 tokens)
**Total session wall-clock including human gate:** ~25 min

This was the first journey to validate **fast-track** as a real workflow shape — proof that not every change needs the full five-role pipeline. Goal: ship the F020 unblock, capture data on what fast-track skips well vs poorly, and feed that back into task-019's `base/workflows/fast-track.md` design.

## What worked

- **The full five-role chain wasn't needed.** task-020 is a one-branch refactor with crisp ACs. The Implementer read the task body, made the change, wrote 9 tests, and ran them — same throughput as the Implementer step in journey 2, minus all the surrounding ceremony. **No information was lost** by skipping the bundle: the Librarian's job is to surface relevant files, but for a 50-line resolver fix, the Implementer can find the relevant files in its first 3 reads.
- **No worktree needed at fast-track scope.** Fan-out 1 + no Verifier means there's no second worktree to compare against; the Implementer worked in main directly. Saved ~5 commands and 2 commits worth of glue.
- **Single human gate held.** I reviewed the diff, ran tests, and ran the AC7 validation (rm symlink + bin/agent run) in ~5 minutes total. Compared to journey 2's six gates.
- **Implementer self-bounded scope correctly.** Task body listed 6 files; Implementer touched 7 (added `bin/agent` and `bin/lib/runner.py` because the `resolve()` signature change propagated). Flagged in the writeup. Defensible scope expansion — the alternative would have been escalating "the plan misses two callers" and spawning a Planner step, which is the wrong shape for fast-track.
- **Ran 21/21 tests pass on the same diff.** 9 new for `test_resolution.py`, 12 regression from `test_task_cli.py`. The regression check is what matters most — confirms the new manifest field didn't break the task-004 flow.

## What didn't work / new findings

- **F027 (P2) — Task-body-as-spec is sometimes ambiguous in fast-track.** The task body for 020 had pretty good ACs but didn't enumerate `bin/agent` or `bin/lib/runner.py` as files to touch. The Implementer correctly inferred them from "callers of `resolve()`" in the Context paragraph, but the inference relies on the agent reasoning about the codebase. For more complex fast-track tasks, this inference might fail silently. Mitigation: in `base/workflows/fast-track.md`, add a step "Implementer scans for callers of any function whose signature changes; updates them; flags scope expansion in writeup." Or: only fast-track tasks with `trivial: true` set, where signature changes aren't expected.
- **No verifier evidence files for AC7.** AC7 ("`bin/agent run` resolves without the symlink") was verified by *me* manually after commit, not by the Implementer (correctly, per the constraint that the symlink is load-bearing during the Implementer's run). In ship-feature this would have produced an `evidence/ac7-cli-smoke/stdout.txt` file. Fast-track skips evidence capture; the human's manual verification is the only record. Acceptable for a P0 unblock; documented for `fast-track.md`.
- **Journey 1 stats record is incomplete.** The seed I wrote for journey 1 had `null` for several role timings because the data wasn't captured at the time. Going forward, capture every agent-return's `duration_ms` / `tool_uses` / `total_tokens` immediately after each spawn, and write them to `.agents/stats/journeys/<NNN>-<consumer>-<task-slug>.json` in the same response.

## Validations (things this run confirmed empirically)

1. **Fast-track is real for the right task class.** A small mechanical fix with crisp ACs and no architecture decisions runs end-to-end in ~25 min wall-clock, ~50k tokens, 1 human gate.
2. **The five-role spec spans many work shapes; a workflow taxonomy will let each shape pick the right cost.** Journey 2 (full ship-feature) and journey 3 (fast-track) shipped roughly comparable code volume per Implementer-step (1059 vs 246 insertions; 12 vs 9 tests), but the surrounding ceremony differed by 33 minutes / 256k tokens / 5 human gates. That delta is what the workflow taxonomy is supposed to recover.
3. **Implementer alone is enough when the task body is the spec.** No Librarian-curated bundle; the Implementer's first 3 reads (task body + resolution.py + manifest.py) covered everything it needed. **Strong signal that bundle is most valuable when the change touches >5 files or has architectural ambiguity** — not on small mechanical fixes.

## Comparison with journey 2 (ship-feature on task-004)

| Metric | Journey 2 (ship-feature) | Journey 3 (fast-track) | Delta |
|---|---|---|---|
| Roles run | 5 | 1 | -4 |
| Agent wall-time | ~50 min | ~16 min | **-68%** |
| Tokens | ~306k | ~50k | **-84%** |
| Tool calls | 174 | 41 | -76% |
| Human gates | 6 | 1 | -83% |
| Worktrees created | 2 | 0 | — |
| Manual frontmatter flips | ~7 | ~2 (`open → implementing`, `implementing → done`) | -71% |
| Lines added | 1,059 | 246 | (different task scopes) |
| Tests added | 12 | 9 | (comparable per LOC) |

## Findings → tasks mapping

- **F020:** ✅ closed by this commit. Promoted entry already updated.
- **F027:** new finding (task-body-as-spec ambiguity in fast-track). Add to `findings.md` Open section.

## Recommendations for fast-track workflow file (input to task-019)

When task-019 ships, `base/workflows/fast-track.md` should declare:

- **Roles:** `[implementer]` (just one).
- **Entry criteria:** `trivial: true` OR (`type: bug` AND `fan-out: 1` AND no `needs-architect: true`).
- **Skipped artifacts:** bundle, plan, verdict, evidence files, separate verifier worktree, ADRs.
- **Auto-approve when:** never auto-approves the diff itself (always single human gate); but auto-flips status on Implementer-success per task-022's runner logic.
- **Required outputs:** `attempt-A.md` writeup, `attempt-A.patch`, regression-test pass.
- **Not appropriate for:** tasks with multiple plausible architectural shapes; tasks touching >10 files; tasks with `needs-architect: true`; tasks where the AC list itself is fuzzy.

## Surprises worth remembering

- **The Implementer was more efficient at fast-track than at full ship-feature.** 41 tool calls vs 44 in journey 2 — fewer reads, less re-reading of the bundle, more focused execution. Suggests bundle-reading itself adds tool-call overhead even when the bundle is curated.
- **No F021/F022/F023 recurrence this run.** Journey 2 hit several recurring frictions; fast-track avoided most of them simply by not having the roles that triggered them. F021 (worktree input seeding) wasn't hit because no extra worktree exists. F022 (chip recurrence) wasn't hit because the Implementer's prompt explicitly forbade chip tools and the Implementer respected it (different from the Verifier). F023 (Judge `bin/task new` chicken-and-egg) wasn't hit because no Judge.
- **The deny rule still didn't fire on the previous push** — the user has flagged this and Claude Code may need a session restart for settings to reload. To be tested when journey 3 push happens.
