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
from lib.runner import (
    RunSpec,
    close_journey,
    compose_system_prompt,
    dispatch_roles,
    load_workflow,
    resolve_workflow_name,
    seed_worktree_inputs,
)


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


# ---------------------------------------------------------------------------
# Helpers for workflow tests
# ---------------------------------------------------------------------------

def _setup_workflow_file(repo: Path, wf_name: str, roles: list[str]) -> Path:
    """Write a minimal valid workflow file to base/workflows/<wf_name>.md."""
    roles_yaml = "[" + ", ".join(roles) + "]"
    gate_rules_yaml = "\n".join(f"  {r}: human" for r in roles)
    content = f"""---
workflow: {wf_name}
version: 1.0.0
roles: {roles_yaml}
gate-rules:
{gate_rules_yaml}
---

# {wf_name}

Stub body.
"""
    path = repo / "base" / "workflows" / f"{wf_name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_workflow — base path resolution
# ---------------------------------------------------------------------------

def test_load_workflow_resolves_base_path(tmp_path: Path):
    """load_workflow returns a WorkflowSpec with roles from base/workflows/medium-track.md."""
    repo = _setup_repo(tmp_path)
    _setup_workflow_file(repo, "medium-track", ["planner", "implementer", "verifier"])

    manifest = _make_manifest()
    spec = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="021",
        workflow_name="medium-track",  # explicit: resolves to base/workflows/medium-track.md
    )

    wf = load_workflow(spec, manifest)
    assert wf.name == "medium-track"
    assert wf.roles == ["planner", "implementer", "verifier"]


# ---------------------------------------------------------------------------
# load_workflow — local overlay takes precedence over base
# ---------------------------------------------------------------------------

def test_load_workflow_prefers_local_overlay(tmp_path: Path):
    """When both base and local workflow files exist, load_workflow uses local."""
    repo = _setup_repo(tmp_path)

    # Write base version with roles [implementer]
    _setup_workflow_file(repo, "fast-track", ["implementer"])

    # Write local overlay with different roles [planner, implementer]
    local_wf_content = """---
workflow: fast-track
version: 2.0.0
roles: [planner, implementer]
gate-rules:
  planner: human
  implementer: human
---

# fast-track (local override)

Local body.
"""
    local_path = repo / ".agents" / "local" / "workflows" / "fast-track.md"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(local_wf_content, encoding="utf-8")

    manifest = _make_manifest()
    spec = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="020",
        workflow_name="fast-track",  # explicit: resolution will prefer local overlay
    )

    wf = load_workflow(spec, manifest)
    # local overlay version is 2.0.0, base is 1.0.0
    assert wf.version == "2.0.0", "Expected local overlay to win over base"
    assert wf.roles == ["planner", "implementer"]


# ---------------------------------------------------------------------------
# load_workflow — rejects unknown workflow name
# ---------------------------------------------------------------------------

def test_load_workflow_rejects_unknown_name(tmp_path: Path):
    """load_workflow raises ValueError for a workflow name with no matching file."""
    repo = _setup_repo(tmp_path)
    # No workflow files written

    manifest = _make_manifest()
    spec = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="099",
        workflow_name="nonexistent-workflow",
    )

    with pytest.raises(ValueError, match="Unknown workflow"):
        load_workflow(spec, manifest)


# ---------------------------------------------------------------------------
# resolve_workflow_name — precedence: flag > task frontmatter > default
# ---------------------------------------------------------------------------

def test_resolve_workflow_name_precedence(tmp_path: Path):
    """--workflow flag wins over task frontmatter, which wins over default."""
    repo = _setup_repo(tmp_path)

    # Task frontmatter declares workflow: medium-track
    _write(
        repo / "tasks" / "in-progress" / "019-test.md",
        "---\nid: 019\nworkflow: medium-track\n---\n\n# Task\n",
    )

    manifest = _make_manifest()

    # Case 1: spec.workflow_name (flag) wins over task frontmatter
    spec_with_flag = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="019",
        workflow_name="fast-track",  # flag override
    )
    assert resolve_workflow_name(spec_with_flag, manifest) == "fast-track"

    # Case 2: no flag — task frontmatter wins
    spec_no_flag = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="019",
        workflow_name=None,
    )
    assert resolve_workflow_name(spec_no_flag, manifest) == "medium-track"

    # Case 3: no flag, no task frontmatter match — default ship-feature
    spec_no_task = RunSpec(
        repo_root=repo,
        role_name="implementer",
        task_id="999",  # task doesn't exist
        workflow_name=None,
    )
    assert resolve_workflow_name(spec_no_task, manifest) == "ship-feature"


# ---------------------------------------------------------------------------
# dispatch_roles — order matches workflow frontmatter
# ---------------------------------------------------------------------------

def test_workflow_dispatch_order_matches_frontmatter(tmp_path: Path, capsys):
    """dispatch_roles prints roles in the order declared in workflow.roles."""
    repo = _setup_repo(tmp_path)
    manifest = _make_manifest()

    from lib.workflow_schema import WorkflowSpec

    wf = WorkflowSpec(
        name="test-wf",
        version="1.0.0",
        roles=["alpha", "beta", "gamma"],
        gate_rules={"alpha": "auto", "beta": "human", "gamma": "auto"},
    )

    spec = RunSpec(
        repo_root=repo,
        role_name="alpha",
        task_id="001",
    )

    exit_code = dispatch_roles(spec, wf, manifest)

    assert exit_code == 0

    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if "would dispatch" in l]

    assert len(lines) == 3
    assert "alpha" in lines[0]
    assert "beta" in lines[1]
    assert "gamma" in lines[2]

    # Gate modes appear in output
    assert "auto" in lines[0]
    assert "human" in lines[1]
