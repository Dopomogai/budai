"""Tests for bin/lib/runner.py — glue layer: seed_worktree_inputs, close_journey,
and compose_system_prompt's journey-inputs prepend behaviour.

Run with: python3 -m pytest tests/bin/test_runner.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure bin/ is importable regardless of where pytest is invoked from.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_DIR = REPO_ROOT / "bin"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

from lib.manifest import Manifest
from lib.runner import RunSpec, close_journey, compose_system_prompt, seed_worktree_inputs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str = "# stub\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_manifest(tasks_layout: str = "legacy-four-folder", registry_source: str = "self") -> Manifest:
    return Manifest(
        budai_version="0.1.0",
        tasks_layout=tasks_layout,
        registry_source=registry_source,
    )


def _setup_repo(tmp_path: Path) -> Path:
    """Create a minimal repo with manifest and role for compose_system_prompt tests."""
    manifest_yaml = """budai-version: "0.1.0"
tasks-layout: legacy-four-folder
registry-source: self
"""
    (tmp_path / ".agents").mkdir()
    _write(tmp_path / ".agents" / "manifest.yaml", manifest_yaml)
    return tmp_path


def _setup_role(repo: Path, role_name: str = "implementer") -> Path:
    role_content = "# Implementer\n\nImplement the plan.\n"
    return _write(repo / "base" / "roles" / f"{role_name}.md", role_content)


# ---------------------------------------------------------------------------
# compose_system_prompt — journey inputs block prepended when inputs exist
# ---------------------------------------------------------------------------

def test_compose_system_prompt_prepends_journey_inputs_block_when_inputs_exist(tmp_path: Path):
    """When spec.worktree is set and inputs exist, ## Journey inputs appears at the top."""
    repo = _setup_repo(tmp_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    _setup_role(repo)

    # Create a task body and bundle so select_inputs finds them
    task_file = _write(
        repo / "tasks" / "in-progress" / "021-test.md",
        "---\nid: 021\n---\n## Plan\n\nSome plan.\n",
    )

    manifest = _make_manifest()

    spec = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="021",
        worktree=worktree,
        run_id="run-test-prepend",
    )

    result = compose_system_prompt(spec, manifest)

    assert result.startswith("## Journey inputs"), (
        f"Expected '## Journey inputs' at top of prompt, got:\n{result[:200]}"
    )


def test_compose_system_prompt_omits_journey_inputs_block_when_no_inputs(tmp_path: Path):
    """When no inputs exist (no task file, no bundle), ## Journey inputs is absent."""
    repo = _setup_repo(tmp_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    _setup_role(repo)

    manifest = _make_manifest()

    # No task body, no bundle files in the repo
    spec = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="999",  # task that doesn't exist
        worktree=worktree,
        run_id="run-test-no-inputs",
    )

    result = compose_system_prompt(spec, manifest)

    assert "## Journey inputs" not in result, (
        "Expected no '## Journey inputs' block when no inputs exist"
    )


# ---------------------------------------------------------------------------
# seed_worktree_inputs — creates inputs directory in worktree
# ---------------------------------------------------------------------------

def test_seed_worktree_inputs_creates_inputs_directory_in_worktree(tmp_path: Path):
    """seed_worktree_inputs creates .agents/runs/<run_id>/inputs/ in the worktree."""
    repo = _setup_repo(tmp_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()

    _write(
        repo / "tasks" / "in-progress" / "021-test.md",
        "---\nid: 021\n---\n## Plan\n",
    )

    manifest = _make_manifest()
    run_id = "run-seed-test"

    spec = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="021",
        worktree=worktree,
        run_id=run_id,
    )

    seeded = seed_worktree_inputs(spec, manifest)

    inputs_dir = worktree / ".agents" / "runs" / run_id / "inputs"
    assert inputs_dir.exists(), f"Inputs directory not created at {inputs_dir}"
    assert len(seeded) >= 1, "Expected at least the task body to be seeded"


# ---------------------------------------------------------------------------
# close_journey — delegates teardown to each worktree
# ---------------------------------------------------------------------------

def test_close_journey_calls_teardown_for_each_worktree(tmp_path: Path):
    """close_journey invokes 'git worktree remove' once per supplied path."""
    repo = tmp_path / "repo"
    repo.mkdir()

    wt1 = tmp_path / "wt1"
    wt2 = tmp_path / "wt2"
    wt1.mkdir()
    wt2.mkdir()

    call_log: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        call_log.append(list(cmd))
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        import shutil
        target = Path(cmd[-1])
        if target.exists():
            shutil.rmtree(target)
        return result

    with patch("lib.journey_state.subprocess.run", side_effect=fake_run):
        results = close_journey(repo, [wt1, wt2])

    # Both worktrees should have been processed
    assert len(results) == 2

    # git worktree remove should have been called for each
    remove_calls = [c for c in call_log if "worktree" in c and "remove" in c]
    assert len(remove_calls) == 2, (
        f"Expected 2 'git worktree remove' calls, got {len(remove_calls)}: {call_log}"
    )

    # Both should be reported as removed
    statuses = [status for _, status in results]
    assert all(s == "removed" for s in statuses), f"Unexpected statuses: {statuses}"
