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


def compose_system_prompt(spec: RunSpec, manifest: "Manifest | None" = None) -> str:
    """Compose the system prompt from role body + relevant overlays.

    When manifest is provided its registry-source field determines which base
    directory is searched for roles and conventions.  When None, the manifest
    is loaded from disk.
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

    return "\n".join(pieces)


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


def dispatch_claude_code(spec: RunSpec, system_prompt_file: Path, input_text: str) -> int:
    """Invoke the claude CLI with the composed prompt.

    Returns the exit code. Captures stdout to runs/<run-id>/transcript.jsonl.
    Phase 0 implementation is a placeholder; real Claude Code integration
    arrives in Phase 1 once we have a working CLI runner pattern.
    """
    run_dir = make_run_dir(spec)
    transcript_file = run_dir / "transcript.jsonl"
    cwd = spec.cwd or spec.repo_root

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
