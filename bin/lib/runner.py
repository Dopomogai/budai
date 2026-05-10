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
from .resolution import _base_dir, resolve
from . import journey_state


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
