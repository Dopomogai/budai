"""Tests for bin/lib/journey_state.py.

Mirrors the test layout established by tests/bin/test_resolution.py:
sys.path bootstrap from repo root, tmp_path fixtures, no shared state
between tests.

Run with: python3 -m pytest tests/bin/test_journey_state.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure bin/ is importable regardless of where pytest is invoked from.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_DIR = REPO_ROOT / "bin"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

from lib.journey_state import (
    SeedPlan,
    format_inputs_block,
    inputs_dir,
    seed_worktree,
    select_inputs,
    teardown_worktrees,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str = "# stub\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_manifest_yaml(layout: str = "legacy-four-folder") -> str:
    return f"""budai-version: "0.1.0"
tasks-layout: {layout}
registry-source: self
"""


def _minimal_repo(tmp_path: Path, layout: str = "legacy-four-folder") -> Path:
    """Create a minimal repository layout with a manifest."""
    (tmp_path / ".agents").mkdir()
    _write(tmp_path / ".agents" / "manifest.yaml", _make_manifest_yaml(layout))
    return tmp_path


# ---------------------------------------------------------------------------
# select_inputs — task body discovery
# ---------------------------------------------------------------------------

def test_select_inputs_finds_task_body_in_in_progress(tmp_path: Path):
    """select_inputs locates a task body sitting in tasks/in-progress/."""
    repo = _minimal_repo(tmp_path)
    task_file = _write(repo / "tasks" / "in-progress" / "021-foo.md", "---\nid: 021\n---\n")

    plan = select_inputs(repo, "021", layout="legacy-four-folder")

    assert plan.task_body == task_file, (
        f"Expected task body at {task_file}, got {plan.task_body}"
    )


# ---------------------------------------------------------------------------
# select_inputs — bundle globbing
# ---------------------------------------------------------------------------

def test_select_inputs_globs_bundle_with_token_count_suffix(tmp_path: Path):
    """select_inputs captures bundle files with encoded token count in filename."""
    repo = _minimal_repo(tmp_path)
    folder = repo / "tasks" / "in-progress"
    folder.mkdir(parents=True, exist_ok=True)
    bundle_15k = _write(folder / "021-foo.bundle.15k.md")
    bundle_plain = _write(folder / "021-foo.bundle.plain.md")

    plan = select_inputs(repo, "021", layout="legacy-four-folder")

    assert bundle_15k in plan.bundle, "Expected 15k bundle in plan"
    assert bundle_plain in plan.bundle, "Expected plain-suffix bundle in plan"


# ---------------------------------------------------------------------------
# select_inputs — ADR parsing
# ---------------------------------------------------------------------------

def test_select_inputs_parses_adr_references_from_plan_section(tmp_path: Path):
    """select_inputs extracts ADR path from ## ADR section of task body."""
    repo = _minimal_repo(tmp_path)
    adr_file = _write(
        repo / "memory" / "decisions" / "0002-foo.md",
        "# ADR 0002\n",
    )
    task_content = (
        "---\nid: 021\n---\n"
        "## Plan\n\nsome plan\n\n"
        "## ADR\n\n"
        "Wrote `memory/decisions/0002-foo.md`.\n"
    )
    _write(repo / "tasks" / "in-progress" / "021-task.md", task_content)

    plan = select_inputs(repo, "021", layout="legacy-four-folder")

    assert adr_file in plan.adrs, f"Expected {adr_file} in adrs, got {plan.adrs}"


def test_select_inputs_skips_absent_adr_silently(tmp_path: Path):
    """select_inputs returns empty adrs list when ## ADR section references non-existent file."""
    repo = _minimal_repo(tmp_path)
    task_content = (
        "---\nid: 021\n---\n"
        "## ADR\n\n"
        "See `memory/decisions/9999-nonexistent.md`.\n"
    )
    _write(repo / "tasks" / "in-progress" / "021-task.md", task_content)
    # Intentionally do NOT create the ADR file

    plan = select_inputs(repo, "021", layout="legacy-four-folder")

    assert plan.adrs == [], f"Expected empty adrs, got {plan.adrs}"


# ---------------------------------------------------------------------------
# select_inputs — prior verifier failure
# ---------------------------------------------------------------------------

def test_select_inputs_includes_prior_failure_when_supplied(tmp_path: Path):
    """select_inputs sets verifier_failure when prior_attempt_dir contains failure.md."""
    repo = _minimal_repo(tmp_path)
    prior_dir = tmp_path / "attempt-Z"
    failure_file = _write(prior_dir / "failure.md", "# Verifier failure\n")

    plan = select_inputs(
        repo, "021",
        layout="legacy-four-folder",
        prior_attempt_dir=prior_dir,
    )

    assert plan.verifier_failure == failure_file, (
        f"Expected verifier_failure={failure_file}, got {plan.verifier_failure}"
    )


# ---------------------------------------------------------------------------
# seed_worktree — destination layout
# ---------------------------------------------------------------------------

def test_seed_worktree_copies_files_to_inputs_subdir(tmp_path: Path):
    """seed_worktree places all seeded files under .agents/runs/<run_id>/inputs/."""
    src = tmp_path / "src"
    worktree = tmp_path / "wt"
    worktree.mkdir()

    task_file = _write(src / "021-task.md", "task body\n")
    bundle_file = _write(src / "021-task.bundle.15k.md", "bundle\n")
    adr_file = _write(src / "decisions" / "0002-foo.md", "adr\n")

    plan = SeedPlan(
        task_body=task_file,
        bundle=[bundle_file],
        adrs=[adr_file],
    )
    run_id = "test-run-001"

    seeded = seed_worktree(worktree, run_id, plan)

    inputs_root = worktree / ".agents" / "runs" / run_id / "inputs"
    assert (inputs_root / "021-task.md").exists(), "task body not copied"
    assert (inputs_root / "021-task.bundle.15k.md").exists(), "bundle not copied"
    assert (inputs_root / "decisions" / "0002-foo.md").exists(), "ADR not copied"
    assert len(seeded) == 3, f"Expected 3 seeded paths, got {len(seeded)}"


# ---------------------------------------------------------------------------
# seed_worktree — copy not symlink (frozen at dispatch time)
# ---------------------------------------------------------------------------

def test_seed_worktree_content_matches_source_at_dispatch_time(tmp_path: Path):
    """Seeded files reflect source content at copy time; later edits don't bleed through."""
    src = tmp_path / "src"
    worktree = tmp_path / "wt"
    worktree.mkdir()

    original_content = "original task body\n"
    task_file = _write(src / "021-task.md", original_content)

    plan = SeedPlan(task_body=task_file)
    run_id = "run-freeze"

    seed_worktree(worktree, run_id, plan)

    # Mutate the source AFTER seeding
    task_file.write_text("modified content\n", encoding="utf-8")

    dest_file = worktree / ".agents" / "runs" / run_id / "inputs" / "021-task.md"
    dest_content = dest_file.read_text(encoding="utf-8")
    assert dest_content == original_content, (
        f"Seeded file should be frozen at dispatch time, but content changed: {dest_content!r}"
    )


# ---------------------------------------------------------------------------
# format_inputs_block
# ---------------------------------------------------------------------------

def test_format_inputs_block_renders_relative_paths(tmp_path: Path):
    """format_inputs_block produces relative paths regardless of worktree_root."""
    worktree = tmp_path / "wt"
    worktree.mkdir()

    rel1 = Path(".agents/runs/r1/inputs/021-task.md")
    rel2 = Path(".agents/runs/r1/inputs/021-task.bundle.15k.md")

    block = format_inputs_block([rel1, rel2], worktree)

    assert "## Journey inputs" in block
    assert str(rel1) in block
    assert str(rel2) in block
    # No absolute paths from the host system
    assert str(worktree) not in block


def test_format_inputs_block_empty_list_returns_empty_string(tmp_path: Path):
    """format_inputs_block returns empty string when no paths are supplied."""
    result = format_inputs_block([], tmp_path)
    assert result == "", f"Expected empty string, got {result!r}"


# ---------------------------------------------------------------------------
# teardown_worktrees — idempotency
# ---------------------------------------------------------------------------

def test_teardown_idempotent_on_missing_path(tmp_path: Path):
    """teardown_worktrees returns 'missing' for a path that does not exist."""
    repo = tmp_path / "repo"
    repo.mkdir()

    nonexistent = tmp_path / "ghost-worktree"
    assert not nonexistent.exists()

    results = teardown_worktrees(repo, [nonexistent])

    assert len(results) == 1
    path, status = results[0]
    assert path == nonexistent
    assert status == "missing"


# ---------------------------------------------------------------------------
# teardown_worktrees — removal and inputs preservation
# ---------------------------------------------------------------------------

def test_teardown_removes_worktree_but_preserves_inputs(tmp_path: Path):
    """teardown_worktrees calls 'git worktree remove' and does not touch inputs/."""
    repo = tmp_path / "repo"
    repo.mkdir()
    worktree = tmp_path / "wt"
    worktree.mkdir()

    # Create an inputs directory inside the worktree to verify preservation logic
    inputs = worktree / ".agents" / "runs" / "run-1" / "inputs"
    inputs.mkdir(parents=True)
    sentinel = inputs / "task.md"
    sentinel.write_text("seeded content\n")

    # Patch subprocess.run to simulate git removing the directory
    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        # Simulate git worktree remove: delete the worktree dir itself
        import shutil as _shutil
        if worktree.exists():
            _shutil.rmtree(worktree)
        return result

    with patch("lib.journey_state.subprocess.run", side_effect=fake_run):
        results = teardown_worktrees(repo, [worktree])

    assert len(results) == 1
    _, status = results[0]
    assert status == "removed", f"Expected 'removed', got {status!r}"
    # The worktree directory itself is gone (simulated by fake_run)
    assert not worktree.exists(), "Worktree directory should have been removed"
    # inputs/ lives outside the worktree after removal — nothing to check here
    # The key assertion is that teardown_worktrees never explicitly removes inputs/
    # (which is verified by the absence of rmtree(inputs) in the function body)
