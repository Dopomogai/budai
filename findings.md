# budai findings inbox

The flat findings log for budai. Things observed during runs that should become improvement tasks but aren't yet. Promoted to `tasks/todo/` on triage.

Each entry: short title, date observed, source, one-line context, proposed fix. Severity indicates rough priority (P0 blocks runs, P1 hurts quality, P2 nice-to-have).

When promoted, edit the entry to add `→ task-NNN` and move it to the **Promoted** section at the bottom. Don't delete — the trail matters.

When closed as not-actually-a-problem, move to **Dismissed** with a one-line reason.

---

## Open

### F028 — `compose_system_prompt` mixes text composition with filesystem mutation; `select_inputs` default layout could silently mis-route [P2]

- **Date:** 2026-05-10
- **Source:** Journey 4 (task-021 medium-track) — Verifier code-quality observation, also flagged by Implementer in attempt-A.md.
- **Context:** Two coupled concerns from the task-021 implementation:
  - `bin/lib/runner.py::compose_system_prompt` now calls `journey_state.seed_worktree` directly (rather than via the `seed_worktree_inputs` wrapper) to avoid double-seeding when both functions run in the same dispatch sequence. The result is a function named `compose_*` that has a real filesystem side effect — copying files into the worktree. Defensible for task-021 (the alternative was a double-seed), but a code smell. Future readers will be surprised.
  - `bin/lib/journey_state.py::select_inputs` defaults `layout` to `"legacy-four-folder"`. On a consumer repo using `tasks-layout: standard` in its manifest, callers that don't pass `layout=manifest.tasks_layout` will silently look in the wrong folders. Tasks 019 (workflows) and 022 (auto-flip) will both call this function and need explicit `layout` plumbing.
- **Proposed fix:** Two parts. (1) Refactor `compose_system_prompt` to be pure (assemble text only) and move the seeding side effect to a sibling function `prepare_dispatch(spec, manifest)` that callers invoke before `dispatch_claude_code`. The text-composition function then takes the seeded paths as input rather than triggering the seed itself. (2) Either change `select_inputs`'s default to raise on unspecified layout (force callers to be explicit) OR add a one-line note at every call site reminding "pass `layout=manifest.tasks_layout`." The first is safer; the second is cheaper. Defer to whoever ships task-019.

### F027 — Task-body-as-spec ambiguity in fast-track for signature-changing fixes [P2]

- **Date:** 2026-05-10
- **Source:** Journey 3 (task-020 fast-track) — Implementer correctly inferred that `bin/agent` and `bin/lib/runner.py` needed updates when `resolve()`'s signature changed, but the inference relied on the agent reasoning about callers; the task body had only listed 6 files and the Implementer touched 7.
- **Context:** Fast-track skips the Planner, so the Implementer is the only role that sees the change set. For mechanical fixes the task body's enumerated files are usually sufficient. But when a fix changes a function signature, every caller becomes an implicit dependency that the task body may not have listed. The Implementer caught this on task-020; on a more complex change it might miss callers silently.
- **Proposed fix:** When task-019's `base/workflows/fast-track.md` lands, add a step to the Implementer flow: "If your change alters a public function signature, scan the codebase for callers and update them; flag the scope expansion in your writeup. If callers are non-trivial to update, escalate to medium-track (Planner + Implementer + Verifier) instead." Or: only allow fast-track when `trivial: true` is set, where signature changes shouldn't happen.

### F022 — Host UI chip tool used despite explicit prompt-level prohibition (F016 recurrence) [P0]

- **Date:** 2026-05-09
- **Source:** budai task-004 Verifier role spawn. Verifier emitted `mcp__ccd_session__spawn_task` chip ("a doc-sweep chip has been spawned") despite the prompt explicitly forbidding it.
- **Context:** F016 (CanvasOS retrospective) proposed prompt-level guidance against host-harness chip tools. This run tested that hypothesis with explicit text in the Verifier's "## Your task" section: "**No host-harness chip tools** for non-AC findings — those go in the verifier report's 'Non-AC findings' section, NOT into Claude UI chips (F016)." The Verifier still used the tool. The same finding was *also* correctly captured in the verifier report and ac-mapping.json, so no information was lost — but the chip is still emitted, still ephemeral, still invisible to budai's workflow. Confirms F016's deeper claim: prompt-level guidance is insufficient.
- **Proposed fix:** Runner-permission denial. The claude-code runner spec already supports `--allowed-tools`; task-010 (runner permission enforcement) implements it. When that lands, the Verifier (and every other role) should have all `mcp__ccd_session__*` tools omitted from the allow-list. Until then, accept the redundant chip emissions as long as the textual report captures the same finding (which it has in both runs so far). **Promote task-010 from P1 → P0** based on this evidence.

### F023 — Judge can't `bin/task new` for follow-ups when task changes the `bin/task` script [P2]

- **Date:** 2026-05-09
- **Source:** budai task-004 Judge role spawn — needed to spawn three follow-up tasks (015, 016, 017) but the very script being committed was `bin/task`.
- **Context:** Chicken-and-egg: invoking the pre-patch `bin/task new` would create the file in `tasks/open/` (the legacy layout), not `tasks/todo/` (the new four-folder layout). Workaround: Judge hand-created the three task files using the same frontmatter shape as task-004. Acceptable for this run; minor friction. Will recur any time a task touches `bin/task` itself or other budai infrastructure used during the journey.
- **Proposed fix:** Judge runs `bin/task new` from the post-patch working tree (i.e., after `git apply` and commit). Or: runner exposes a "use the patched copy" flag for follow-up spawning. Or: Judge always hand-writes follow-up files (acceptable but defeats `bin/task new` for this case). Lowest-touch fix: document the post-patch invocation pattern in `base/roles/judge.md` so it's part of the role spec.

### F024 — Tests added two zero-byte `__init__.py` scaffolding files beyond plan's literal files-to-touch [P2]

- **Date:** 2026-05-09
- **Source:** budai task-004 Implementer attempt-A.
- **Context:** Implementer added `tests/__init__.py` and `tests/bin/__init__.py` to make pytest discover the test file. Defensible (pytest discovery requires them on Python ≥3.3 in some configurations; cleaner with them) and transparent in the writeup. But strictly, scope expanded by 2 zero-byte files beyond the plan's enumerated `files-to-touch`. Either the plan should pre-list test scaffolding files when adding a new test directory, OR the convention should explicitly allow zero-byte `__init__.py` files in this case.
- **Proposed fix:** Update `base/conventions.md` (or `base/skills/peer-review.md`) with: "Test directory scaffolding (`__init__.py`, `conftest.py`) is in-scope when adding a new test path the plan calls for, even if the plan doesn't enumerate the scaffolding files. Document additions in the writeup." This codifies what the Implementer did and what the Verifier rightly didn't fail on.

### F026 — Permission scope is too wide; journeys take 20+ approvals; `git push` was auto-allowed [P0]

- **Date:** 2026-05-09
- **Source:** Human feedback after journey 2: "I have approved tooo much of the permissions like 20+ / the run should go without my approvals till the final review / if that is not the git push I am okay to auto allow all / and you did a push without my approvals for some reason."
- **Context:** Two related problems. (a) Claude Code's per-tool prompts hit the user 20+ times per journey for routine local ops (`git status`, `mkdir`, `python3 bin/task`, `mv`, etc.). Each prompt costs context-switch time and burns the user's patience; the journey wall-clock for task-004 was 1h 21m, of which ~30 minutes was approvals + context-shuffle on top of ~50 minutes of pure agent compute. (b) `Bash(git push *)` had silently accumulated in `~/Documents/GitHub/CanvasOS/.claude/settings.local.json` from a prior session, so when the journey 2 retrospective committed and pushed, no prompt fired. The user expected a confirmation; the absence was a real surprise. Even when push is in an "approved plan," it is the highest-blast-radius action and should always re-confirm in real time.
- **Proposed fix:** Two layers. (1) Per-project `.claude/settings.local.json` with **granular allow patterns** for routine local operations and `git push` deliberately *not listed* (falls through to default-ask behavior). **Three Claude Code permission learnings discovered during journey 3:** (a) `deny` is absolute — it blocks entirely with no prompt option, so it's wrong for "ask on this" intent. (b) `allow` patterns are matched first; if a broad pattern like `Bash(git*)` matches a command, `deny` is never consulted, so `Bash(git*)` in allow + `Bash(git push*)` in deny will silently auto-allow push. The fix: list specific git subcommands in allow (`Bash(git status*)`, `Bash(git add*)`, `Bash(git commit*)`, etc.) and omit push. (c) Settings don't reload mid-session — Claude Code restart is needed for changes to take effect. Document this in any future onboarding skill. Both budai and CanvasOS now ship the corrected template at `.claude/settings.local.json` (gitignored — local override). (2) Within budai's own workflow, finding F025 (auto-flip frontmatter on role completion) closes the other half of the approval volume — gate flips become runner-internal, not human-typed.




## Promoted

### F021 — Worktrees branch from `main` and don't see uncommitted main-worktree state [P0] → task-021

- **Date:** 2026-05-09
- **Source:** budai task-004 journey, Implementer + Verifier role spawns.
- **Context:** During a journey, the task move (`tasks/todo → tasks/in-progress`), the appended Plan section, the Planner's ADR, and the bundle file are all uncommitted in the main worktree (intentionally — they churn during the run). When the Implementer creates a worktree branched from `main`, it gets a stale view: the task file is still at its committed location with no `## Plan` body, and the bundle and ADR don't exist on its branch. Workaround for this run: instructed each downstream agent to read task body / plan / bundle / ADR from absolute paths to the main worktree. Three sites of "absolute-path-injection" in agent prompts. Without this guidance, agents would silently work off stale inputs.
- **Proposed fix:** The runner should seed each agent's worktree with the journey inputs before dispatch. Concretely, before calling `dispatch_claude_code`, copy: `<task-file>` (with current uncommitted content), `<bundle-file>`, any ADR(s) referenced by the plan, into `.agents/runs/<run-id>/inputs/` inside the worktree. Then point the agent's "## Your task" addendum at those paths. Alternative: commit the task move + plan to a per-task branch (`task-<id>-coordination`) and create worktrees off that branch instead of `main`. Either approach removes the manual absolute-path-injection.

### F020 — Runner doesn't honor `registry-source: self` (always looks at `.agents/base/`) [P0] → task-020

- **Date:** 2026-05-09
- **Source:** Pre-flight of budai-on-budai task-004 journey. `python3 bin/agent run --role librarian --task 004` returned `Role not found: librarian / Available roles: []`.
- **Context:** `bin/lib/resolution.py` resolves base files at `.agents/base/<category>/<name>.md` unconditionally (line 33). But when a repo declares `registry-source: self` in its manifest, the authoritative tree lives at `<repo_root>/base/`, not under `.agents/`. budai itself ships `base/` at repo root via committed history (`f393d82` etc.) with no path under `.agents/base/`. Result: the runner can never find any roles/skills/runners/workflows when budai runs against itself. Worked around for this run by symlinking `.agents/base -> ../base` (gitignored). This is task-011 territory in part (`librarian sync` should populate `.agents/base/`), but the resolution logic also needs a `registry-source: self` branch that points directly at `<repo_root>/base/`.
- **Proposed fix:** In `bin/lib/resolution.py`, read manifest's `registry-source`; when `self`, look up `<repo_root>/base/<category>/<name>.md` (and optionally still allow `.agents/base/` as a fallback for hybrid setups). Or: have `librarian init` / a future `bin/budai bootstrap` create the symlink/copy automatically as part of self-registration. Either way: stop requiring a manual symlink to dogfood.

### F001 — `chars/4` heuristic for token counting [P1]

- **Promoted:** → task-007 (`tasks/todo/007-deterministic-token-and-bundle-basics.md`)
- **Date:** 2026-05-09
- **Source:** Human review during CanvasOS task 000 Librarian step.
- **Context:** `bin/lib/headers.py` and the `build-task-bundle` skill spec both estimate tokens via `chars / 4`. Real tokenizers exist (`tiktoken` for cl100k_base). Sloppy math means we under- or over-fill bundles.
- **Proposed fix:** Add `bin/lib/tokens.py` with `count_tokens(text: str) -> int` using `tiktoken`. Replace every `chars / 4` site. Add `tiktoken` to `bin/requirements.txt`.

### F002 — Bundle filename should encode token count [P2]

- **Promoted:** → task-007 (`tasks/todo/007-deterministic-token-and-bundle-basics.md`)
- **Date:** 2026-05-09
- **Source:** Human suggestion during CanvasOS task 000 Librarian step.
- **Context:** Bundle files at `tasks/in-progress/<id>-<slug>.bundle.md` give no at-a-glance budget signal. A filename like `<id>-<slug>.bundle.21k.md` would.
- **Proposed fix:** Update `build-task-bundle.md` skill spec output filename rule: `<id>-<slug>.bundle.<NNk>.md` where `<NNk>` is `actual-tokens` rounded to nearest 1k (e.g., `21k`, `84k`). Add `bin/lib/naming.py` helper. Resolver in librarian/planner needs to glob `<id>-<slug>.bundle.*.md` rather than expect a fixed name.

### F003 — Default bundle budget should be 84000 [P2]

- **Promoted:** → task-007 (`tasks/todo/007-deterministic-token-and-bundle-basics.md`)
- **Date:** 2026-05-09
- **Source:** Human decision during CanvasOS task 000 manifest review.
- **Context:** 80000 was a round number; bumping to 84000 gives more headroom for medium-large source files without forcing trims. Hard cap stays at 1.10× = 92400.
- **Proposed fix:** `examples/manifest-minimal.yaml`, `examples/manifest-full.yaml`, `docs/09-bundle-format.md`, and any default in `bin/lib/manifest.py` updated to 84000.

### F004 — Librarian should write `## Notes from Librarian` to task body [P1]

- **Promoted:** → task-008 (`tasks/todo/008-deterministic-bundle-assembler-and-librarian-output.md`)
- **Date:** 2026-05-09
- **Source:** Human suggestion during CanvasOS task 000 Librarian review (the agent surfaced two bugs beyond the task body — `saveProfileAs` missing, `setTopTabBarVisible` confirmed missing — but had no formal place to record them).
- **Context:** Currently Librarian only writes the bundle and posts to `messages/channels/tasks.md` (which doesn't exist outside the spec yet). Findings during scoring evaporate unless the Planner happens to read the bundle's "Librarian notes" appendix. Better: Librarian appends a `## Notes from Librarian` section to the task body itself, so the Planner reads it as part of the task.
- **Proposed fix:** Update `librarian.md` role + `build-task-bundle.md` skill: at the end of bundling, if findings worth surfacing exist, append `## Notes from Librarian` (with frontmatter-stamped `librarian-notes-at: <ISO>`) to the task body. Include unrelated-but-discovered bugs as a sub-list with `### Latent issues spotted` so the Planner can choose to spin them out as follow-ups vs. fold into scope.

### F005 — Bundle assembly should be deterministic, not agent-driven [P1]

- **Promoted:** → task-008 (`tasks/todo/008-deterministic-bundle-assembler-and-librarian-output.md`)
- **Date:** 2026-05-09
- **Source:** Human review of CanvasOS task 000 Librarian tool-call list (agent read 7 source files cover-to-cover to embed them in the bundle body).
- **Context:** The agent's job is judgment (which files matter, what reasons apply). Embedding file content + counting tokens is mechanical. Mixing them wastes agent tokens and risks the agent doing extra analysis (Planner's job) while reading. The agent should produce a `(path, reason)` list + draft `## Notes from Librarian`; a Python step reads the picked files, embeds content with proper code fences, computes precise tokens via tiktoken, writes the bundle file.
- **Proposed fix:** New `bin/lib/bundle.py` with `assemble_bundle(task_path, picks: list[FilePick], notes: str, target_tokens: int) -> Path`. Skill spec rewritten: "1. Score files via index. 2. Output JSON pick list. 3. Call `bin/lib/bundle.assemble`." The agent writes a structured response, not the bundle file itself.

### F006 — Default Librarian output should be silent; verbose is opt-in [P2]

- **Promoted:** → task-008 (`tasks/todo/008-deterministic-bundle-assembler-and-librarian-output.md`)
- **Date:** 2026-05-09
- **Source:** Human review during CanvasOS task 000 Librarian step.
- **Context:** The agent returned a 7-section verbose report by default. Useful first-run; noise after. Steady state: write the bundle + post one line summary; the report is opt-in via `--verbose`.
- **Proposed fix:** `bin/agent` gets `--verbose` flag (default false). When false, the agent prompt says "Don't return a report; the bundle file is the artifact." When true, current behavior. Affects every role, not just Librarian.

### F007 — Skill spec should embed standard relevance heuristics [P1]

- **Promoted:** → task-008 (`tasks/todo/008-deterministic-bundle-assembler-and-librarian-output.md`)
- **Date:** 2026-05-09
- **Source:** Human review during CanvasOS task 000 Librarian prompt construction.
- **Context:** The Librarian invocation needed ~25 lines of per-task hints ("App.tsx is files-to-touch with priority 100", "exclude deprecated tldraw files", etc.) added manually to the prompt. A tighter `build-task-bundle.md` skill spec could embed these heuristics so the agent infers them from task body alone: "If the task body has a `## Context` section, treat the file paths it names as `files-to-touch` candidates. Default-exclude files with `@stability deprecated` from inclusion."
- **Proposed fix:** Rewrite the skill spec's "Procedure" section to be self-contained — agent should need only `task-id` + `bundle-path` to produce a bundle, no per-task prompt scaffolding.

### F008 — `bin/agent dispatch_claude_code` is a Phase 0 placeholder [P0 once we have ≥2 consumers]

- **Promoted:** → task-009 (`tasks/todo/009-real-claude-runner-dispatch.md`)
- **Date:** 2026-05-09
- **Source:** Direct read of `bin/lib/runner.py` during journey planning.
- **Context:** The function prints what it would run and exits 0 — no actual `claude` CLI invocation. We work around by spawning agents via Claude Code's own Agent tool, which only works while a human is running the harness. For unattended runs (cron, CI, multi-task pipeline), real dispatch must work.
- **Proposed fix:** Implement `dispatch_claude_code` per spec: `subprocess.run` of `claude --system-prompt-file <path> --model <id> --working-dir <cwd> --output-format json --max-turns 100 --allowed-tools <list>` with stdout piped to `transcript.jsonl`. Block until exit; return exit code. Honor permissions from role frontmatter for `--allowed-tools`. Preflight check that `claude` is on `$PATH`.

### F009 — `bin/task` doesn't support four-folder layout [P1]

- **Promoted:** → task-004 (`tasks/todo/004-task-cli-four-folder-and-schema-validation.md`)
- **Date:** 2026-05-09
- **Source:** Direct observation during CanvasOS task 000 setup (we hand-created the task file).
- **Context:** `bin/task new` writes to `tasks/open/`; `bin/task move` searches `tasks/open/` then `tasks/archive/`. CanvasOS uses `tasks/{backlog,todo,in-progress,done}/`. Manifest has `tasks-layout: legacy-four-folder` for this case but the script doesn't read it.
- **Proposed fix:** Read `tasks-layout` from `.agents/manifest.yaml` in `bin/task`. If `legacy-four-folder`: new tasks land in `tasks/todo/`, status transitions also do `git mv` between folders, `list` walks all four. Default behavior unchanged when manifest says `tasks-layout: standard` (or omits the key).

### F010 — `bin/preflight` and `bin/postflight` aren't invokable from consumer repos [P2]

- **Promoted:** → task-012 (`tasks/todo/012-consumer-invocation-path.md`)
- **Date:** 2026-05-09
- **Source:** Plan-mode exploration during CanvasOS task 000.
- **Context:** Scripts live in `~/Documents/GitHub/budai/bin/` and consumer repos invoke them via absolute path. Brittle. Either symlink during onboarding, copy via `librarian sync`, or document a one-line wrapper invocation pattern.
- **Proposed fix:** During `librarian sync`, symlink `~/.local/bin/budai-preflight` (etc.) into the consumer's PATH, OR copy `bin/preflight*` into consumer's `bin/` with `bin/lib/` import alias. Document either way in `docs/21-onboarding.md`.

### F011 — `audit-docs` should be invokable as a first-class task, not only in sweeper mode [P1]

- **Promoted:** → task-013 (`tasks/todo/013-first-class-audit-workflow.md`)
- **Date:** 2026-05-09
- **Source:** Human suggestion during CanvasOS task 000 review.
- **Context:** `audit-docs` skill currently runs only in Librarian sweeper mode (after task close). For a freshly onboarded repo with stale docs, we'd want to run it explicitly as task 001 of the consumer. Currently no path to that without inventing a fake "task" to close.
- **Proposed fix:** Add `audit` task type recognition. When `tasks/<status>/<id>-<slug>.md` has `type: audit` and `workflow: audit-repo`, the workflow short-circuits Librarian → Planner → Librarian (skipping Implementer/Verifier/Judge), where the second Librarian invocation runs `audit-docs` + `regenerate-index`. Update `workflows/audit-repo.md` accordingly.

### F012 — Cross-repo `librarian sync` is a Phase 6 placeholder [P0 once we have ≥2 consumers]

- **Promoted:** → task-011 (`tasks/todo/011-librarian-sync-implementation.md`)
- **Date:** 2026-05-09
- **Source:** Direct read of `bin/librarian` during journey planning.
- **Context:** `cmd_sync` prints what it would do. With one consumer (CanvasOS), we manually `cp -R ~/Documents/GitHub/budai/base/. .agents/base/`. Acceptable for one consumer, painful at three.
- **Proposed fix:** Implement per `docs/17-registry-and-sync.md`: clone budai at the pinned tag, copy `base/` into `.agents/base/`, write `.agents/manifest.lock.yaml` with resolved versions. Network-fetch behind permission gate.

### F017 — `git worktree add` should seed gitignored config (`.env`, etc.) from the primary worktree [P1]

- **Date:** 2026-05-09
- **Source:** CanvasOS task 000 smoke test in attempt-A worktree (Supabase calls 401'd because `.env` was absent; `lib/supabase.ts` silently fell back to `MISSING_KEY`, producing misleading "No authentication token" errors that look like fix regressions but are actually env loss).
- **Context:** When the runner creates a worktree for an Implementer or Verifier attempt, gitignored config files (`.env`, `.env.local`, sometimes `.npmrc`, sometimes `local-secrets.yaml`) don't propagate. The agent then runs the app and sees auth errors that aren't its fault. Worse: if these errors look like AC violations, the verdict gets noise.
- **Proposed fix:** When `bin/agent` (or future runner) does `git worktree add <path>`, immediately follow with a copy of the consumer's allow-listed gitignored files. List comes from `.agents/manifest.yaml` under a new key:
  ```yaml
  worktree-seed-files:
    - .env
    - .env.local
  ```
  Defaults to `[.env]` if not specified. Runner refuses to copy anything matching budai's secret-shaped patterns to a non-local destination (defense against path-traversal misconfigurations).

### F018 — Need a Tester role or `run-tests` / `write-tests` skill [P1]

- **Date:** 2026-05-09
- **Source:** Human suggestion during CanvasOS task 000 mid-journey ("we would probably need to add a tester Agent — can run tests, write them if needed, check results").
- **Context:** Currently testing is split awkwardly: Implementer is told to run tests after each change (but it owns code-writing as primary job, so testing is a secondary attention sink); Verifier runs tests on the patched worktree as part of evidence capture (but its primary job is AC-mapping, not test authorship). Neither is positioned to *write missing tests* when AC requires test coverage that doesn't exist. The AC checklist asks for green tests — but new code without tests passes vacuously.
- **Options:**
  - **A. New `Tester` role** — sits between Implementer and Verifier. Reads the plan, the diff, the existing tests; writes missing tests for new code paths; runs the suite; reports pass/fail with diff coverage. Adds a 6th role to the canon — non-trivial.
  - **B. New `write-tests` skill** owned by Implementer. The Implementer's workflow gains a step: "before submitting attempt, invoke `write-tests` to cover any new public code paths that aren't tested." Skill body specifies: read the diff, identify new exports / behavior, draft tests, run them, iterate until green.
  - **C. New `run-tests` skill** more narrowly scoped (just executes), composed with `write-tests` (just authors). Both invokable by Implementer or Verifier. Most flexible but more surface area.
- **Proposed fix:** Lean toward **B** for this iteration (one skill, one owner, one new line in `implementer.md` workflow). Promote to a full Tester role only if a recurring failure pattern (Librarian-tracked) shows Implementers chronically skip test authorship.

### F019 — Latent visual regressions in CanvasOS exposed by fixing broken-on-start [P1, CanvasOS-side, not budai]

- **Date:** 2026-05-09
- **Source:** CanvasOS task 000 smoke test (topbar absent, minimap absent — visible only after the broken-on-start TypeError stopped masking them).
- **Context:** Two pre-existing UI bugs surfaced once the renderer ran cleanly: (a) the top tab bar never appears because `setTopTabBarVisible` is called via `(state: any)` but never declared on the store, so visibility never flips to `true`; (b) the xyflow `<MiniMap>` is presumably not rendered as a child of `<ReactFlow>` in `SpatialCanvas.tsx`. Both are CanvasOS code issues, not budai issues — should become CanvasOS follow-up tasks, not budai findings.
- **Proposed fix (CanvasOS-side):** Two follow-up tasks once task 000 closes:
  - `task-001-fix-topbar-visibility`: Add `isTopTabBarVisible` (default `true`) and `setTopTabBarVisible(value: boolean)` to `CanvasStore` interface + implementation. Drop the `(state: any)` cast at call sites. (Folds in latent bug #1 from the Librarian's notes.)
  - `task-002-add-minimap`: Render `<MiniMap />` from `@xyflow/react` inside `<ReactFlow>` children in `SpatialCanvas.tsx`. Style it per existing canvas chrome.

### F025 — Manual frontmatter flips, recurrence (F015 still unfixed) [P0] → task-022

- **Date:** 2026-05-09
- **Source:** budai task-004 journey — 7 manual frontmatter edits (5 status flips + `plan-approved` + `result-approved`).
- **Context:** F015 from CanvasOS journey 1 already captured this. Reaffirmed here: every gate transition in the five-role workflow forces a hand-edit to the task frontmatter, despite the workflow having a deterministic "after role X passes its gate, set status to Y" rule. The agent that just finished its role *could* flip the frontmatter as part of its output, but role specs vary on whether they should (Planner currently flips `planning → reviewing-plan`, Verifier sets attempt status not task status, Judge flips to `reviewing-result`). Cleanup pattern: every role flips on completion if the human gate isn't enforced; auto-approve criteria short-circuit the next status flip in trivial cases.
- **Proposed fix:** Codify the status transitions in `base/workflows/ship-feature.md` (and other workflow files), and have the runner — not the agent — perform the frontmatter flip when a role's exit conditions are met. This decouples role responsibility (produce artifact + report) from state-machine maintenance (set the next status). Auto-approve criteria for `fan-out: 1 ∧ trivial: true` plus `verifier-passed ∧ all-AC-pass` cases would skip ~half the gates we hit today.

### F015 — Status transitions, gate flips, worktree management should be runner-mechanical, not human-typed [P0] → task-022

- **Date:** 2026-05-09
- **Source:** Human review during CanvasOS task 000 mid-journey.
- **Context:** The journey requires ~6 manual frontmatter edits (`status:` flips at each step, `plan-approved: true`, `result-approved: true`, `updated:` timestamp bumps) and ~2 manual git operations (worktree create per attempt, `git diff main > patch` to produce the attempt patch). These are mechanical glue, not judgment calls. Human-typing them is error-prone and clogs the journey with low-signal commits/edits. They should happen automatically: when the runner dispatches the next role, it knows the previous gate just passed, so it flips the relevant fields itself.
- **Proposed fix:** 
  1. Extend `bin/task move <id> <status>` to also flip the relevant gate flag and bump `updated:` (e.g., `bin/task move 000 implementing` sets `status: implementing`, `plan-approved: true`, `updated: <now>`).
  2. Add `bin/agent` flag `--auto-transition` (default true) that auto-flips status when the agent finishes successfully (Librarian → planning, Planner → reviewing-plan, etc.).
  3. Add worktree management to `bin/agent`: when dispatching Implementer or Verifier, auto-create the worktree at `.agents/council/<task-id>/worktrees/attempt-<X>/` on a new branch `task-<id>-attempt-<X>`, and after the agent exits, auto-generate the patch via `git diff main`.
  4. Worktree cleanup on task close: Judge's commit + auto `git worktree remove` for non-winning attempts (preserve only the winner's worktree until next sweep, then remove).

### F016 — Out-of-scope agent observations should route to budai findings/tasks, not Claude UI chips [P1]

- **Date:** 2026-05-09
- **Source:** CanvasOS task 000 Implementer step (the Implementer agent surfaced a stale `@purpose` line in App.tsx as a Claude-native `spawn_task` chip in the UI).
- **Context:** Spawned agents have access to Claude Code's `mcp__ccd_session__spawn_task` tool, which emits out-of-scope-finding chips into the host UI. The Implementer correctly used it for a drive-by issue — but the chip is ephemeral, lives only in the Claude session, and isn't visible to budai's workflow. Self-evolvement requires findings to land in budai's `findings.md` (and ultimately `tasks/`), not in a host harness. Otherwise observations evaporate.
- **Proposed fix:** Update each role's anti-patterns section: "Don't use `mcp__ccd_session__spawn_task` or other host-harness chip tools for out-of-scope observations. Instead: append to `findings.md` in the consumer repo (or to the attempt writeup's `## Notes / deferred items` section, which the Librarian sweep promotes to `findings.md` automatically). Host UI chips are invisible to the budai workflow." Optionally: deny these tools at runner-permission level (per claude-code runner spec), so agents can't call them even if the model is tempted.

### F014 — Convention should explicitly require file-header updates as part of any code change that invalidates them [P2]

- **Promoted:** → task-014 (`tasks/todo/014-header-maintenance-convention-and-index-strictness.md`)
- **Date:** 2026-05-09
- **Source:** CanvasOS task 000 Planner step (the Planner correctly inferred that `@gotchas` had to be trimmed in three files when the underlying issues were fixed, and listed those header edits as file-level changes — but the convention is implicit, not stated).
- **Context:** The file-header convention is enforced by `bin/librarian index` reading the headers, but nothing tells agents (or humans) that headers must be kept in sync when code changes resolve a `@gotchas` item or change `@exports` / `@uses` / `@stability`. Drift would be caught only by `audit-docs` at sweep time, which is too late.
- **Proposed fix:** Add a section to `base/conventions.md`: "Header maintenance — when a code change resolves a `@gotchas` item, renames an export, alters dependencies, or changes stability, the same diff updates the header. Stale headers are bugs, not docs debt." Surface this rule in the Implementer role file (`base/roles/implementer.md`) under Principles or Workflow so it's part of the system prompt.

### F013 — Self-onboarding: budai itself should be a budai consumer [P1]

- **Promoted:** → task-001 (`tasks/todo/001-self-onboard-budai-on-budai.md`)
- **Date:** 2026-05-09
- **Source:** Human strategic question ("can we just reuse budai itself for the repo improvement?")
- **Context:** budai improvements should run through budai's own five-role workflow (dogfooding). Currently the budai repo has no `.agents/`, no manifest, no headers on `bin/lib/*.py`. Without it, improvement tasks can't use the workflow on budai code.
- **Proposed fix:** Onboard budai-on-budai (mirror what we did for CanvasOS): `.agents/manifest.yaml` with `registry-source: self`, `.agents/local/{conventions,untouchables,glossary}.md` for budai-specific patterns (Python style, semver discipline), `AGENTS.md`, file headers on `bin/lib/*.py`. Once done, every finding above becomes a task that runs through the workflow.

---

## Dismissed

(None yet.)
