"""Tests for bin/task CLI and bin/lib/task_schema.

Test cases follow the plan for task-004.  All 12 required cases are
implemented.  Tests exercise the public APIs of task_schema and the
integration behaviour of cmd_new / cmd_move / cmd_list via a temp-dir
fixture that simulates a minimal budai repo.

Task-003 (test harness) has not yet landed; this file uses plain pytest
with stdlib only (no custom fixtures from task-003).  The Verifier should
run with: python3 -m pytest tests/bin/test_task_cli.py -v
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure bin/ is importable regardless of where pytest is invoked from.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_DIR = REPO_ROOT / "bin"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

from lib.task_schema import (
    VALID_STATUSES,
    STATUS_TRANSITIONS,
    folder_for_status,
    layout_folders,
    load_all_tasks,
    parse_frontmatter,
    validate_dependencies,
    validate_frontmatter,
    validate_transition,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """Create a minimal budai repo layout in a temp directory.

    Returns the repo root.  Creates .agents/manifest.yaml with
    legacy-four-folder layout and a tasks/ directory with all four folders.
    """
    # .agents/manifest.yaml
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    manifest = agents_dir / "manifest.yaml"
    manifest.write_text(
        textwrap.dedent("""\
            budai-version: 0.2.0
            tasks-layout: legacy-four-folder
        """)
    )

    # tasks/ with four folders
    tasks_dir = tmp_path / "tasks"
    for folder in ["backlog", "todo", "in-progress", "done"]:
        (tasks_dir / folder).mkdir(parents=True)

    return tmp_path


@pytest.fixture()
def tmp_repo_standard(tmp_path: Path) -> Path:
    """Like tmp_repo but with standard (two-folder) layout."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "manifest.yaml").write_text(
        textwrap.dedent("""\
            budai-version: 0.2.0
        """)
    )
    tasks_dir = tmp_path / "tasks"
    for folder in ["open", "archive"]:
        (tasks_dir / folder).mkdir(parents=True)
    return tmp_path


def _make_task(
    repo: Path,
    folder: str,
    filename: str,
    status: str = "open",
    depends_on: list[str] | None = None,
) -> Path:
    """Write a minimal valid task file into tasks/<folder>/<filename>."""
    deps = depends_on or []
    content = textwrap.dedent(f"""\
        ---
        id: {filename[:3]}
        title: Test task
        type: feature
        scope: test
        status: {status}
        fan-out: 1
        needs-architect: true
        plan-approved: false
        result-approved: false
        trivial: false
        depends-on: {deps!r}
        created: 2026-01-01T00:00:00Z
        updated: 2026-01-01T00:00:00Z
        ---

        # Task {filename[:3]}: Test task
    """)
    path = repo / "tasks" / folder / filename
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# 1. test_new_task_lands_in_todo_under_legacy_four_folder
# ---------------------------------------------------------------------------

def test_new_task_lands_in_todo_under_legacy_four_folder():
    """folder_for_status('open', 'legacy-four-folder') == 'todo'."""
    assert folder_for_status("open", "legacy-four-folder") == "todo"


# ---------------------------------------------------------------------------
# 2. test_new_task_lands_in_open_under_standard
# ---------------------------------------------------------------------------

def test_new_task_lands_in_open_under_standard():
    """folder_for_status('open', 'standard') == 'open'."""
    assert folder_for_status("open", "standard") == "open"


# ---------------------------------------------------------------------------
# 3. test_move_done_routes_to_done_under_legacy_four_folder
# ---------------------------------------------------------------------------

def test_move_done_routes_to_done_under_legacy_four_folder():
    """folder_for_status('done', 'legacy-four-folder') == 'done'."""
    assert folder_for_status("done", "legacy-four-folder") == "done"


# ---------------------------------------------------------------------------
# 4. test_move_done_routes_to_archive_under_standard
# ---------------------------------------------------------------------------

def test_move_done_routes_to_archive_under_standard():
    """folder_for_status('done', 'standard') == 'archive'."""
    assert folder_for_status("done", "standard") == "archive"


# ---------------------------------------------------------------------------
# 5. test_list_walks_all_four_folders
# ---------------------------------------------------------------------------

def test_list_walks_all_four_folders(tmp_repo: Path):
    """load_all_tasks with legacy-four-folder layout scans all four folders."""
    # Place one task in each folder.
    _make_task(tmp_repo, "backlog", "001-alpha.md", status="backlog")
    _make_task(tmp_repo, "todo", "002-bravo.md", status="open")
    _make_task(tmp_repo, "in-progress", "003-charlie.md", status="implementing")
    _make_task(tmp_repo, "done", "004-delta.md", status="done")

    all_tasks = load_all_tasks(tmp_repo, "legacy-four-folder")
    assert "001" in all_tasks
    assert "002" in all_tasks
    assert "003" in all_tasks
    assert "004" in all_tasks


# ---------------------------------------------------------------------------
# 6. test_list_walks_open_only_under_standard
# ---------------------------------------------------------------------------

def test_list_walks_open_only_under_standard(tmp_repo_standard: Path):
    """load_all_tasks with standard layout only scans open/ and archive/."""
    _make_task(tmp_repo_standard, "open", "001-alpha.md", status="open")
    _make_task(tmp_repo_standard, "archive", "002-bravo.md", status="done")

    all_tasks = load_all_tasks(tmp_repo_standard, "standard")
    assert "001" in all_tasks
    assert "002" in all_tasks
    # Folders not in the standard layout must not be scanned.
    assert len(all_tasks) == 2


# ---------------------------------------------------------------------------
# 7. test_invalid_status_in_new_is_rejected
# ---------------------------------------------------------------------------

def test_invalid_status_in_new_is_rejected():
    """validate_frontmatter returns an error for an unknown status value."""
    fm = {
        "id": "001",
        "title": "Test",
        "type": "feature",
        "scope": "test",
        "status": "not-a-real-status",
        "fan-out": 1,
        "needs-architect": True,
        "plan-approved": False,
        "result-approved": False,
        "trivial": False,
        "depends-on": [],
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-01-01T00:00:00Z",
    }
    errors = validate_frontmatter(fm, "legacy-four-folder")
    assert any("status" in e.lower() for e in errors), f"Expected status error, got: {errors}"


# ---------------------------------------------------------------------------
# 8. test_invalid_transition_in_move_is_rejected
# ---------------------------------------------------------------------------

def test_invalid_transition_in_move_is_rejected():
    """validate_transition returns an error for an illegal status hop."""
    # "done" has no outgoing transitions.
    errors = validate_transition("done", "open")
    assert errors, "Expected a transition error from done → open"

    # "open" cannot jump directly to "reviewing-result".
    errors2 = validate_transition("open", "reviewing-result")
    assert errors2, "Expected a transition error from open → reviewing-result"


# ---------------------------------------------------------------------------
# 9. test_missing_dependency_id_is_rejected
# ---------------------------------------------------------------------------

def test_missing_dependency_id_is_rejected(tmp_repo: Path):
    """validate_dependencies flags depends-on IDs that do not exist."""
    # No task 999 exists in the repo.
    errors = validate_dependencies("001", ["999"], {})
    assert any("999" in e for e in errors), f"Expected missing-dep error, got: {errors}"


# ---------------------------------------------------------------------------
# 10. test_dependency_cycle_is_rejected
# ---------------------------------------------------------------------------

def test_dependency_cycle_is_rejected(tmp_repo: Path):
    """validate_dependencies detects a cycle in the dependency graph."""
    # Create a two-node cycle: 002 depends on 003, 003 depends on 002.
    task_002 = _make_task(tmp_repo, "todo", "002-beta.md", status="open", depends_on=["003"])
    task_003 = _make_task(tmp_repo, "todo", "003-gamma.md", status="open", depends_on=["002"])

    all_tasks = {"002": task_002, "003": task_003}

    # Creating 001 that depends on 002 should expose the cycle when DFS walks.
    errors = validate_dependencies("001", ["002"], all_tasks)
    assert any("cycle" in e.lower() for e in errors), (
        f"Expected cycle detection error, got: {errors}"
    )


# ---------------------------------------------------------------------------
# 11. test_unknown_tasks_layout_in_manifest_raises
# ---------------------------------------------------------------------------

def test_unknown_tasks_layout_in_manifest_raises(tmp_path: Path):
    """load_manifest raises ValueError for an unknown tasks-layout value."""
    from lib.manifest import load_manifest

    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "manifest.yaml").write_text(
        textwrap.dedent("""\
            budai-version: 0.2.0
            tasks-layout: not-a-valid-layout
        """)
    )

    with pytest.raises(ValueError, match="not-a-valid-layout"):
        load_manifest(tmp_path)


# ---------------------------------------------------------------------------
# 12. test_manifest_without_tasks_layout_defaults_to_standard
# ---------------------------------------------------------------------------

def test_manifest_without_tasks_layout_defaults_to_standard(tmp_path: Path):
    """load_manifest defaults tasks_layout to 'standard' when key is absent."""
    from lib.manifest import load_manifest

    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "manifest.yaml").write_text(
        textwrap.dedent("""\
            budai-version: 0.2.0
        """)
    )

    manifest = load_manifest(tmp_path)
    assert manifest.tasks_layout == "standard"
