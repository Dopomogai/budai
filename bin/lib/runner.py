"""Runner dispatch.

Reads the runner spec for a given runner name, composes the system
prompt and tool allowlist, invokes the underlying CLI.

Phase 0 only supports claude-code as the runner. Future runners
(codex, direct-anthropic, direct-openai) plug in via the same
interface.
"""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .manifest import Manifest, load_manifest
from .resolution import _base_dir, list_available, resolve
from . import journey_state
from .workflow_schema import WorkflowSpec, parse_workflow_file, validate_workflow_spec
from .task_schema import parse_frontmatter
from .transitions import flip_for_role, TransitionDecision


# Tier → model ID mapping for claude-code runner
CLAUDE_CODE_TIERS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}


@dataclass
class RunSpec:
    repo_root: Path
    role_name: str
    task_id: str
    runner_name: str = "claude-code"
    tier: str = "sonnet"
    cwd: Path | None = None
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    worktree: Path | None = None
    prior_attempt_dir: Path | None = None
    workflow_name: str | None = None


def compose_system_prompt(spec: RunSpec, manifest: "Manifest | None" = None) -> str:
    """Compose the system prompt from role body + relevant overlays.

    When manifest is provided its registry-source field determines which base
    directory is searched for roles and conventions.  When None, the manifest
    is loaded from disk.

    When spec.worktree is set, a '## Journey inputs' block is prepended at
    the top of the prompt listing files seeded into the worktree so agents
    can read them via relative paths without absolute-path injection.
    """
    if manifest is None:
        manifest = load_manifest(spec.repo_root)

    role_path = resolve(spec.repo_root, "roles", spec.role_name, manifest)
    if role_path is None:
        raise FileNotFoundError(f"Role not found: {spec.role_name}")

    role_body = _strip_frontmatter(role_path.read_text())

    pieces = [role_body]

    # Add base + local conventions (full content; bundler usually trims, but
    # for the system prompt we include everything since conventions guide
    # the agent's overall behavior, not just per-task).
    base_root = _base_dir(spec.repo_root, manifest)
    base_conv = base_root / "conventions.md"
    local_conv = spec.repo_root / ".agents" / "local" / "conventions.md"

    if base_conv.exists():
        pieces.append("\n\n## Base conventions\n\n" + base_conv.read_text())
    if local_conv.exists():
        pieces.append("\n\n## Local conventions\n\n" + local_conv.read_text())

    untouchables = spec.repo_root / ".agents" / "local" / "untouchables.md"
    if untouchables.exists():
        pieces.append("\n\n## Untouchables\n\n" + untouchables.read_text())

    body = "\n".join(pieces)

    # Prepend the Journey inputs block when a worktree is specified.
    # The block lists relative paths to inputs seeded by seed_worktree_inputs().
    if spec.worktree is not None:
        seed_plan = journey_state.select_inputs(
            repo_root=spec.repo_root,
            task_id=spec.task_id,
            layout=manifest.tasks_layout,
            prior_attempt_dir=spec.prior_attempt_dir,
        )
        seeded = journey_state.seed_worktree(spec.worktree, spec.run_id, seed_plan)
        inputs_block = journey_state.format_inputs_block(seeded, spec.worktree)
        if inputs_block:
            body = inputs_block + "\n" + body

    return body


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from a markdown file's content."""
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    return parts[2].lstrip()


def resolve_model_id(runner_name: str, tier: str) -> str:
    """Map a tier name to a runner-specific model ID."""
    if runner_name == "claude-code":
        if tier not in CLAUDE_CODE_TIERS:
            raise ValueError(f"Unknown tier for claude-code: {tier}")
        return CLAUDE_CODE_TIERS[tier]
    raise NotImplementedError(f"Runner not yet implemented: {runner_name}")


def make_run_dir(spec: RunSpec) -> Path:
    """Create the runs/<run-id>/ directory with subdirs."""
    run_dir = spec.repo_root / ".agents" / "runs" / spec.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "evidence").mkdir(exist_ok=True)
    return run_dir


def seed_worktree_inputs(spec: RunSpec, manifest: "Manifest") -> list[Path]:
    """Copy journey inputs into the target worktree's inputs directory.

    Wraps journey_state.select_inputs() + journey_state.seed_worktree().
    Returns the list of seeded destination paths (relative to the worktree).

    When spec.worktree is None, the worktree is treated as spec.repo_root
    (preserving single-worktree behaviour). Callers should log the returned
    paths for manual inspection during journey 3.

    Args:
        spec: RunSpec with task_id, run_id, worktree, and optional
            prior_attempt_dir set.
        manifest: Already-loaded Manifest (determines tasks_layout).

    Returns:
        List of relative Path objects for the seeded files.
    """
    worktree_root = spec.worktree or spec.repo_root
    seed_plan = journey_state.select_inputs(
        repo_root=spec.repo_root,
        task_id=spec.task_id,
        layout=manifest.tasks_layout,
        prior_attempt_dir=spec.prior_attempt_dir,
    )
    return journey_state.seed_worktree(worktree_root, spec.run_id, seed_plan)


def read_workflow_from_task(
    repo_root: Path,
    task_id: str,
    manifest: "Manifest",
) -> str | None:
    """Read the workflow: field from a task's frontmatter.

    Uses task_schema.parse_frontmatter for consistency with the rest of the
    task-reading surface. Returns None if the task cannot be found or has no
    workflow: field.

    Args:
        repo_root: Absolute path to the repository root.
        task_id: Task ID string (e.g., "019").
        manifest: Already-loaded Manifest (determines tasks_layout).

    Returns:
        The workflow name string if present in the task frontmatter, else None.
    """
    from .task_schema import layout_folders

    tasks_root = repo_root / "tasks"
    for folder in layout_folders(manifest.tasks_layout):
        folder_path = tasks_root / folder
        if not folder_path.exists():
            continue
        for task_file in folder_path.glob("*.md"):
            if task_file.stem.startswith(task_id):
                try:
                    text = task_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                fm = parse_frontmatter(text)
                workflow_val = fm.get("workflow")
                if workflow_val:
                    return str(workflow_val)
                return None
    return None


def resolve_workflow_name(spec: "RunSpec", manifest: "Manifest") -> str:
    """Resolve the effective workflow name per ADR 0003 override semantics.

    Resolution order (first non-None wins):
    1. spec.workflow_name (--workflow CLI flag).
    2. task frontmatter workflow: field.
    3. Default: "ship-feature".

    Args:
        spec: RunSpec with repo_root, task_id, and optional workflow_name.
        manifest: Already-loaded Manifest.

    Returns:
        Resolved workflow name string.
    """
    if spec.workflow_name:
        return spec.workflow_name

    from_task = read_workflow_from_task(spec.repo_root, spec.task_id, manifest)
    if from_task:
        return from_task

    return "ship-feature"


def load_workflow(spec: "RunSpec", manifest: "Manifest") -> WorkflowSpec:
    """Load and validate the workflow file for the given spec.

    Resolves the workflow name via resolve_workflow_name, then resolves the
    file path via resolution.resolve(), parses it, and validates it.

    Raises:
        ValueError: If no matching workflow file is found or the spec is invalid.

    Args:
        spec: RunSpec with repo_root, task_id, and optional workflow_name.
        manifest: Already-loaded Manifest.

    Returns:
        Validated WorkflowSpec.
    """
    name = resolve_workflow_name(spec, manifest)
    workflow_path = resolve(spec.repo_root, "workflows", name, manifest)
    if workflow_path is None:
        available = list_available(spec.repo_root, "workflows", manifest)
        raise ValueError(
            f"Unknown workflow: {name!r}. "
            f"Available: {available}"
        )

    wf = parse_workflow_file(workflow_path)
    errors = validate_workflow_spec(wf)
    if errors:
        raise ValueError(
            f"Workflow file {workflow_path} is invalid:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    return wf


def dispatch_roles(
    spec: "RunSpec",
    workflow: WorkflowSpec,
    manifest: "Manifest",
) -> int:
    """Iterate workflow roles and dispatch each (Phase-0 stub).

    For each role declared in workflow.roles (in order):
    - Consults workflow.gate_rules[role] to determine gate mode.
    - Phase 0: prints "would dispatch <role> with gate <mode>" rather than
      spawning a real subprocess (real dispatch waits for task-009).
    - Calls flip_for_role after each role to apply or halt the transition
      per gate-rules (task-022). Phase 0 passes role_exit_code=0 (simulated
      success); when task-009 lands real dispatch, role_exit_code will be
      the real subprocess exit code — a one-line change at that point.

    Args:
        spec: RunSpec describing the task and runner.
        workflow: Validated WorkflowSpec with roles + gate_rules.
        manifest: Already-loaded Manifest (determines tasks_layout).

    Returns:
        Exit code (0 = success, 1 = role failed).
    """
    run_dir = make_run_dir(spec)

    for role in workflow.roles:
        gate_mode = workflow.gate_rules.get(role, "human")
        print(f"[runner] would dispatch {role} with gate {gate_mode}")

        decision = flip_for_role(
            spec=spec,
            workflow=workflow,
            role=role,
            role_exit_code=0,
            run_dir=run_dir,
            manifest=manifest,
        )

        if decision.decision == "role-failed":
            print(
                f"[runner] Role {role} failed; "
                f"check run artifacts at {run_dir}"
            )
            return 1
        elif decision.decision == "human-required":
            print(
                f"[runner] Halt at {role}; "
                f"review artifact at {run_dir}; "
                f"run: {decision.halted_reason}"
            )
            return 0
        else:
            # decision starts with "auto" — flipped successfully.
            prev = decision.prev_status
            new = decision.new_status
            print(
                f"[runner] Auto-flipped {spec.task_id}: "
                f"{prev} → {new} (gate {gate_mode})"
            )

    return 0


def close_journey(
    repo_root: Path,
    worktree_paths: list[Path],
) -> list[tuple[Path, str]]:
    """Remove worktrees at journey close while preserving inputs/ directories.

    Delegates to journey_state.teardown_worktrees. Lives here because
    journey close is an orchestration verb tied to the journey lifecycle,
    while teardown_worktrees() is a pure-function helper.

    Args:
        repo_root: Absolute path to the primary repository root.
        worktree_paths: List of worktree root paths to remove.

    Returns:
        List of (path, status) pairs from teardown_worktrees().
    """
    return journey_state.teardown_worktrees(repo_root, worktree_paths)


def dispatch_claude_code(spec: RunSpec, system_prompt_file: Path, input_text: str) -> int:
    """Invoke the claude CLI with the composed prompt.

    Returns the exit code. Captures stdout to runs/<run-id>/transcript.jsonl.
    Phase 0 implementation is a placeholder; real Claude Code integration
    arrives in Phase 1 once we have a working CLI runner pattern.

    Seeds the worktree with journey inputs before the dispatch placeholder
    runs, so the seeded paths appear in the placeholder output for manual
    inspection during journey 3.
    """
    run_dir = make_run_dir(spec)
    transcript_file = run_dir / "transcript.jsonl"
    cwd = spec.cwd or spec.repo_root

    # Seed worktree inputs before dispatch (task-021).
    # manifest is loaded here because dispatch_claude_code doesn't receive it;
    # it's a lightweight read and consistent with make_run_dir's lack of manifest.
    try:
        manifest = load_manifest(spec.repo_root)
        seeded = seed_worktree_inputs(spec, manifest)
        if seeded:
            print(f"[runner] Seeded {len(seeded)} input(s) into worktree:")
            for p in seeded:
                print(f"[runner]   {p}")
    except Exception as exc:  # noqa: BLE001
        print(f"[runner] Warning: input seeding failed ({exc}); continuing without inputs")

    cmd = [
        "claude",
        "--system-prompt-file", str(system_prompt_file),
        "--model", resolve_model_id(spec.runner_name, spec.tier),
        "--working-dir", str(cwd),
        "--output-format", "json",
    ]

    print(f"[runner] Phase 0 placeholder: would dispatch claude with: {' '.join(cmd)}")
    print(f"[runner] System prompt file: {system_prompt_file}")
    print(f"[runner] CWD: {cwd}")
    print(f"[runner] Run ID: {spec.run_id}")
    print(f"[runner] Transcript would land at: {transcript_file}")
    return 0
