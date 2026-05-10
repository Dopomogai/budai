"""Journey-time input seeding and worktree teardown.

Owns the copy, formatting, and cleanup operations that happen around a
dispatch_claude_code call: selecting which source files to seed, copying
them into the worktree's inputs directory, rendering the '## Journey inputs'
block for the system prompt, and removing worktrees at journey close.

Pure functions (select_inputs, format_inputs_block) do only reads and
computation.  Side-effecting functions (seed_worktree, teardown_worktrees)
mutate the filesystem or call subprocesses.

Called by bin/lib/runner.py; downstream consumers include tasks 019 and 022.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .task_schema import layout_folders, load_all_tasks


# Path template for the inputs directory inside a worktree.
# Callers use inputs_dir() rather than formatting this directly.
_INPUTS_SUBDIR_TEMPLATE = ".agents/runs/{run_id}/inputs"


def inputs_dir(worktree_root: Path, run_id: str) -> Path:
    """Return the Path for the inputs directory inside a worktree.

    Args:
        worktree_root: Absolute path to the worktree root.
        run_id: UUID string for this run (from RunSpec.run_id).

    Returns:
        Path to <worktree_root>/.agents/runs/<run_id>/inputs/
    """
    return worktree_root / _INPUTS_SUBDIR_TEMPLATE.format(run_id=run_id)


@dataclass
class SeedPlan:
    """Describes the inputs that will be copied into a worktree at dispatch time.

    All paths are source paths in the primary worktree (or repo_root).
    No copying happens until seed_worktree() is called.

    Attributes:
        task_body: Path to the live task .md file, or None if not found.
        bundle: List of bundle file paths (glob: <task-id>-*.bundle.*.md).
        adrs: List of ADR file paths referenced from the task body's ## ADR section.
        verifier_failure: Path to a prior Verifier's failure.md, or None.
    """

    task_body: Path | None = None
    bundle: list[Path] = field(default_factory=list)
    adrs: list[Path] = field(default_factory=list)
    verifier_failure: Path | None = None


def select_inputs(
    repo_root: Path,
    task_id: str,
    layout: str = "legacy-four-folder",
    prior_attempt_dir: Path | None = None,
) -> SeedPlan:
    """Select journey inputs that exist on disk, without copying them.

    Locates the live task .md (across all configured task folders),
    globs bundle files matching <task-id>-*.bundle.*.md, parses the
    ## ADR section of the task body for memory/decisions/ references,
    and optionally locates a prior verifier failure.md.

    Absent files yield empty fields rather than raising — the caller
    decides whether empty inputs are acceptable.

    Args:
        repo_root: Absolute path to the repository root.
        task_id: Numeric-or-alphanumeric task ID (e.g. "021").
        layout: Task folder layout ("standard" or "legacy-four-folder").
        prior_attempt_dir: Directory containing a previous Verifier's
            failure.md, or None (no retry context).

    Returns:
        SeedPlan with source paths for all inputs found on disk.
    """
    plan = SeedPlan()

    # --- Task body: find <task-id>-<slug>.md across all configured folders ---
    all_tasks = load_all_tasks(repo_root, layout)
    if task_id in all_tasks:
        plan.task_body = all_tasks[task_id]

    # --- Bundle files: glob <task-id>-*.bundle.*.md in tasks/ subfolders ---
    bundle_pattern = f"{task_id}-*.bundle.*.md"
    for folder in layout_folders(layout):
        folder_path = repo_root / "tasks" / folder
        if folder_path.exists():
            plan.bundle.extend(sorted(folder_path.glob(bundle_pattern)))
    # Also check repo root tasks/ directly (in case bundle lives alongside task)
    tasks_root = repo_root / "tasks"
    if tasks_root.exists():
        plan.bundle.extend(sorted(tasks_root.glob(bundle_pattern)))
    # Deduplicate while preserving order
    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in plan.bundle:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    plan.bundle = deduped

    # --- ADRs: parse ## ADR section from the task body ---
    if plan.task_body is not None:
        try:
            body_text = plan.task_body.read_text(encoding="utf-8")
            plan.adrs = _parse_adr_references(repo_root, body_text)
        except OSError:
            pass  # Unreadable task body — skip ADR parsing

    # --- Prior verifier failure ---
    if prior_attempt_dir is not None:
        failure_path = prior_attempt_dir / "failure.md"
        if failure_path.exists():
            plan.verifier_failure = failure_path

    return plan


_ADR_PATH_RE = re.compile(r"memory/decisions/[\w-]+\.md")


def _parse_adr_references(repo_root: Path, body_text: str) -> list[Path]:
    """Extract ADR file references from a task body's ## ADR section.

    Scans text following the first '## ADR' heading (stops at next
    top-level heading). Picks any line matching the pattern
    memory/decisions/<NNNN>-<slug>.md. Only includes paths that
    exist on disk; absent paths are silently skipped per AC6(b).

    Args:
        repo_root: Absolute path to the repository root.
        body_text: Full markdown text of the task body.

    Returns:
        Ordered list of existing ADR Path objects.
    """
    # Locate ## ADR section
    adr_section_match = re.search(r"^##\s+ADR\b", body_text, re.MULTILINE)
    if not adr_section_match:
        return []

    # Extract text from ## ADR to next ## heading (or end)
    after_heading = body_text[adr_section_match.end():]
    next_heading = re.search(r"^##\s+", after_heading, re.MULTILINE)
    if next_heading:
        section_text = after_heading[: next_heading.start()]
    else:
        section_text = after_heading

    result: list[Path] = []
    seen_paths: set[Path] = set()
    for match in _ADR_PATH_RE.finditer(section_text):
        rel_path = match.group(0)
        abs_path = repo_root / rel_path
        if abs_path.exists() and abs_path not in seen_paths:
            seen_paths.add(abs_path)
            result.append(abs_path)

    return result


def seed_worktree(
    worktree_root: Path,
    run_id: str,
    plan: SeedPlan,
) -> list[Path]:
    """Copy inputs from the plan into the worktree's inputs directory.

    Creates <worktree_root>/.agents/runs/<run_id>/inputs/ (with parents)
    and copies each path in the plan via shutil.copy2, which preserves
    mtime so audit timestamps survive. ADRs land in an inputs/decisions/
    sub-folder to preserve their original filenames even when multiple
    ADRs are seeded.

    Args:
        worktree_root: Absolute path to the worktree root.
        run_id: UUID string for this run.
        plan: SeedPlan produced by select_inputs().

    Returns:
        List of destination paths (relative to worktree_root) in the
        fixed order: task body, bundle(s), ADR(s), verifier failure.
        Absent inputs (None / empty list) are skipped without error.
    """
    dest_root = inputs_dir(worktree_root, run_id)
    decisions_dir = dest_root / "decisions"

    dest_root.mkdir(parents=True, exist_ok=True)

    destinations: list[Path] = []

    if plan.task_body is not None:
        dst = dest_root / plan.task_body.name
        shutil.copy2(plan.task_body, dst)
        destinations.append(dst.relative_to(worktree_root))

    for bundle_path in plan.bundle:
        dst = dest_root / bundle_path.name
        shutil.copy2(bundle_path, dst)
        destinations.append(dst.relative_to(worktree_root))

    if plan.adrs:
        decisions_dir.mkdir(exist_ok=True)
        for adr_path in plan.adrs:
            dst = decisions_dir / adr_path.name
            shutil.copy2(adr_path, dst)
            destinations.append(dst.relative_to(worktree_root))

    if plan.verifier_failure is not None:
        dst = dest_root / plan.verifier_failure.name
        shutil.copy2(plan.verifier_failure, dst)
        destinations.append(dst.relative_to(worktree_root))

    return destinations


def format_inputs_block(seeded_paths: list[Path], worktree_root: Path) -> str:
    """Render a '## Journey inputs' markdown block listing seeded paths.

    Produces bullet items with relative paths only — no host-specific
    absolute paths appear in the output.

    Args:
        seeded_paths: List of paths as returned by seed_worktree()
            (already relative to worktree_root, or absolute — both are
            handled). Absolute paths are made relative to worktree_root.
        worktree_root: Absolute path to the worktree root (used only
            when seeded_paths contains absolute paths).

    Returns:
        Markdown string starting with '## Journey inputs\n', or an
        empty string when seeded_paths is empty.
    """
    if not seeded_paths:
        return ""

    lines = ["## Journey inputs", ""]
    for p in seeded_paths:
        # Normalise to relative path
        try:
            rel = p.relative_to(worktree_root)
        except ValueError:
            # Already relative or unrelated path — use as-is
            rel = p
        lines.append(f"- `{rel}`")

    return "\n".join(lines) + "\n"


def teardown_worktrees(
    repo_root: Path,
    worktree_paths: list[Path],
) -> list[tuple[Path, str]]:
    """Remove worktrees via 'git worktree remove --force'.

    Deliberately does NOT touch inputs/ directories — those are preserved
    for audit per ADR 0002 Decision 3. Idempotent: already-removed paths
    return status 'missing' rather than raising.

    Args:
        repo_root: Absolute path to the primary repository root.
        worktree_paths: List of worktree root paths to remove.

    Returns:
        List of (path, status) pairs where status is one of:
        - "removed"  — git worktree remove succeeded.
        - "missing"  — path did not exist; no-op.
        - <error>    — the error message from git (partial failure).
    """
    results: list[tuple[Path, str]] = []

    for wt_path in worktree_paths:
        if not wt_path.exists():
            results.append((wt_path, "missing"))
            continue

        try:
            completed = subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt_path)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
            )
            if completed.returncode == 0:
                results.append((wt_path, "removed"))
            else:
                error_msg = (completed.stderr or completed.stdout).strip()
                results.append((wt_path, error_msg or "unknown error"))
        except OSError as exc:
            results.append((wt_path, str(exc)))

    return results
