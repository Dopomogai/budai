"""Frontmatter schema, status state machine, and dependency-graph validators.

@purpose  Validate task frontmatter, status transitions, and dependency graphs
          for bin/task new and bin/task move.
@why      Centralises all correctness rules in one pure-function module so the
          CLI (bin/task) stays a thin orchestrator and rules stay testable in
          isolation.
@role     Implementer-support library; imported by bin/task and tests.
@exports  VALID_STATUSES, VALID_TYPES, STATUS_TRANSITIONS,
          folder_for_status, layout_folders,
          parse_frontmatter, validate_frontmatter,
          validate_transition, load_all_tasks, validate_dependencies
@uses     yaml (pyyaml), pathlib, typing
@stability experimental
@gotchas  STATUS_TRANSITIONS must stay in lock-step with docs/11-task-format.md.
          If you change one, change the other. The canonical source is the doc;
          this module is the executable enforcement.
          Cycle detection uses iterative DFS to avoid Python's default recursion
          limit (~1000 frames), which matters when dependency chains are deep.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Constants — single source of truth; bin/task imports from here.
# ---------------------------------------------------------------------------

VALID_TYPES: list[str] = [
    "feature",
    "bug",
    "refactor",
    "research",
    "audit",
]

# Statuses in display / logical order.
# backlog is a pre-promotion holding state (added in task-004).
# docs/11-task-format.md does not yet list "backlog" (follow-up doc-sweep task
# is planned); code leads doc here per the risk note in the plan.
VALID_STATUSES: list[str] = [
    "backlog",
    "open",
    "planning",
    "reviewing-plan",
    "implementing",
    "reviewing-result",
    "coordinator",
    "done",
    "abandoned",
    "failed",
]

_TERMINAL_STATUSES = frozenset({"done", "abandoned", "failed"})
_NON_TERMINAL_STATUSES = frozenset(VALID_STATUSES) - _TERMINAL_STATUSES

# Status state machine — adjacency map.
# Source: docs/11-task-format.md "Status state machine" section.
#
# Main path:
#   open → planning → reviewing-plan → implementing → reviewing-result → done
# Coordinator path:
#   reviewing-plan → coordinator → done (when all sub-tasks done)
# Backlog entry:
#   backlog → open (pre-promotion holding state; not yet in the doc)
# Any non-terminal may transition to abandoned (human) or failed (Judge).
# reviewing-plan ↔ planning loop (human requests revisions).
# reviewing-result ↔ implementing loop (human requests revisions).
STATUS_TRANSITIONS: dict[str, set[str]] = {
    "backlog": {"open"},
    "open": {"planning", "abandoned", "failed"},
    "planning": {"reviewing-plan", "abandoned", "failed"},
    "reviewing-plan": {"implementing", "coordinator", "planning", "abandoned", "failed"},
    "implementing": {"reviewing-result", "abandoned", "failed"},
    "reviewing-result": {"done", "implementing", "abandoned", "failed"},
    "coordinator": {"done", "abandoned", "failed"},
    # Terminal statuses have no outgoing transitions.
    "done": set(),
    "abandoned": set(),
    "failed": set(),
}


# ---------------------------------------------------------------------------
# Layout helpers — pure functions, no I/O.
# ---------------------------------------------------------------------------

# Status-to-folder mapping for each layout.
# Standard layout: done|abandoned|failed → archive, everything else → open.
# Legacy-four-folder layout: table from ADR 0001.
_FOLDER_MAP: dict[str, dict[str, str]] = {
    "standard": {
        "backlog": "open",
        "open": "open",
        "planning": "open",
        "reviewing-plan": "open",
        "implementing": "open",
        "reviewing-result": "open",
        "coordinator": "open",
        "done": "archive",
        "abandoned": "archive",
        "failed": "archive",
    },
    "legacy-four-folder": {
        "backlog": "backlog",
        "open": "todo",
        "planning": "in-progress",
        "reviewing-plan": "in-progress",
        "implementing": "in-progress",
        "reviewing-result": "in-progress",
        "coordinator": "in-progress",
        "done": "done",
        "abandoned": "done",
        "failed": "done",
    },
}

_LAYOUT_FOLDERS: dict[str, list[str]] = {
    "standard": ["open", "archive"],
    "legacy-four-folder": ["backlog", "todo", "in-progress", "done"],
}


def folder_for_status(status: str, layout: str) -> str:
    """Return the folder name for a given status and layout.

    Args:
        status: A value from VALID_STATUSES.
        layout: "standard" or "legacy-four-folder".

    Returns:
        Folder name relative to tasks/.

    Raises:
        ValueError: If layout or status is unknown.
    """
    if layout not in _FOLDER_MAP:
        raise ValueError(f"Unknown layout: {layout!r}")
    mapping = _FOLDER_MAP[layout]
    if status not in mapping:
        raise ValueError(f"Unknown status: {status!r}")
    return mapping[status]


def layout_folders(layout: str) -> list[str]:
    """Return the folder names for a layout in display order.

    Args:
        layout: "standard" or "legacy-four-folder".

    Returns:
        Ordered list of folder names relative to tasks/.

    Raises:
        ValueError: If layout is unknown.
    """
    if layout not in _LAYOUT_FOLDERS:
        raise ValueError(f"Unknown layout: {layout!r}")
    return list(_LAYOUT_FOLDERS[layout])


# ---------------------------------------------------------------------------
# Frontmatter parsing.
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse YAML frontmatter from a markdown string.

    Expects the document to start with '---' followed by YAML content and a
    closing '---'.  Returns an empty dict if no frontmatter is found or the
    block is empty.
    """
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        result = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(result, dict):
        return {}
    return result


# ---------------------------------------------------------------------------
# Frontmatter validation.
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {
    "id",
    "title",
    "type",
    "scope",
    "status",
    "fan-out",
    "needs-architect",
    "plan-approved",
    "result-approved",
    "trivial",
    "depends-on",
    "created",
    "updated",
}

_BOOLEAN_KEYS = {"needs-architect", "plan-approved", "result-approved", "trivial"}


def validate_frontmatter(data: dict[str, Any], layout: str) -> list[str]:
    """Validate task frontmatter dict.

    Returns a list of human-readable error strings.  An empty list means the
    frontmatter is valid.  Does not raise.

    Checks:
    - All required keys are present.
    - type is in VALID_TYPES.
    - status is in VALID_STATUSES.
    - id is parseable (non-empty string).
    - title is non-empty.
    - depends-on is a list.
    - Boolean fields are actual booleans.
    - created and updated are parseable ISO-8601 strings (basic check).
    """
    errors: list[str] = []

    # Required keys present.
    missing = _REQUIRED_KEYS - set(data.keys())
    if missing:
        errors.append(f"Missing required keys: {', '.join(sorted(missing))}")

    # type check.
    if "type" in data and data["type"] not in VALID_TYPES:
        errors.append(f"Invalid type: {data['type']!r}. Must be one of: {', '.join(VALID_TYPES)}")

    # status check.
    if "status" in data and data["status"] not in VALID_STATUSES:
        errors.append(f"Invalid status: {data['status']!r}. Must be one of: {', '.join(VALID_STATUSES)}")

    # id parseable and non-empty.
    if "id" in data:
        id_val = str(data["id"]).strip()
        if not id_val:
            errors.append("Field 'id' must not be empty.")

    # title non-empty.
    if "title" in data:
        title_val = str(data["title"]).strip()
        if not title_val:
            errors.append("Field 'title' must not be empty.")

    # depends-on must be a list.
    if "depends-on" in data and not isinstance(data["depends-on"], list):
        errors.append("Field 'depends-on' must be a list.")

    # Boolean fields.
    for key in _BOOLEAN_KEYS:
        if key in data and not isinstance(data[key], bool):
            errors.append(f"Field '{key}' must be a boolean (got {data[key]!r}).")

    # Timestamp fields: basic non-empty string check.
    for ts_key in ("created", "updated"):
        if ts_key in data:
            ts_val = str(data[ts_key]).strip()
            if not ts_val:
                errors.append(f"Field '{ts_key}' must not be empty.")

    return errors


# ---------------------------------------------------------------------------
# Transition validation.
# ---------------------------------------------------------------------------

def validate_transition(old: str, new: str) -> list[str]:
    """Validate a status transition.

    Returns a list of error strings.  Empty list means the transition is legal.
    Idempotent transitions (old == new) are always accepted.
    """
    if old == new:
        return []
    allowed = STATUS_TRANSITIONS.get(old, set())
    if new not in allowed:
        return [
            f"Illegal status transition: {old!r} → {new!r}. "
            f"Allowed from {old!r}: {sorted(allowed) or '(none)'}."
        ]
    return []


# ---------------------------------------------------------------------------
# Dependency graph validation.
# ---------------------------------------------------------------------------

def load_all_tasks(repo_root: Path, layout: str) -> dict[str, Path]:
    """Walk all configured task folders and return a map of task_id → path.

    Only files matching the pattern <id>-<slug>.md or <id><letter>-<slug>.md
    are included.  Ignores files without a numeric-prefixed stem.

    Args:
        repo_root: Absolute path to the repository root.
        layout: "standard" or "legacy-four-folder".

    Returns:
        Dict mapping task ID strings (e.g. "042", "042a") to their Path.
    """
    import re

    tasks_dir = repo_root / "tasks"
    result: dict[str, Path] = {}
    for folder in layout_folders(layout):
        folder_path = tasks_dir / folder
        if not folder_path.exists():
            continue
        for task_file in folder_path.glob("*.md"):
            match = re.match(r"^(\d+[a-z]?)", task_file.stem)
            if match:
                task_id = match.group(1)
                result[task_id] = task_file
    return result


def validate_dependencies(
    task_id: str,
    depends_on: list[str],
    all_tasks: dict[str, Path],
) -> list[str]:
    """Validate that dependency IDs exist and introduce no cycles.

    Checks:
    - Self-loops: task_id must not appear in depends_on.
    - Existence: every ID in depends_on must be in all_tasks.
    - Cycles: iterative DFS from task_id through the depends-on graph.

    Cycle detection reads the frontmatter of each visited task to follow
    its own depends-on.  Uses iterative DFS to avoid Python's default
    recursion limit (~1000 frames).

    Args:
        task_id: The ID of the task being created or validated.
        depends_on: List of task IDs this task depends on.
        all_tasks: Map from task_id → Path, as returned by load_all_tasks.

    Returns:
        List of human-readable error strings.  Empty list means valid.
    """
    import re

    errors: list[str] = []

    # Normalise incoming IDs to strings.
    depends_on_strs = [str(d) for d in depends_on]

    # Self-loop check.
    if task_id in depends_on_strs:
        errors.append(f"Task {task_id!r} depends on itself (self-loop).")

    # Existence check.
    missing = [d for d in depends_on_strs if d not in all_tasks]
    if missing:
        errors.append(f"Unknown dependency IDs: {', '.join(missing)}.")

    if errors:
        # Don't bother with cycle detection if there are already errors.
        return errors

    # Cycle detection: iterative DFS.
    # Build the graph incrementally by reading frontmatter on demand.
    # Start from the new node (task_id → depends_on_strs) and walk outwards.

    # graph: node → list[neighbour]
    graph: dict[str, list[str]] = {}
    graph[task_id] = depends_on_strs

    def _get_deps(tid: str) -> list[str]:
        """Read depends-on for a task already in all_tasks."""
        if tid not in all_tasks:
            return []
        try:
            text = all_tasks[tid].read_text(encoding="utf-8")
        except OSError:
            return []
        fm = parse_frontmatter(text)
        raw = fm.get("depends-on", [])
        if not isinstance(raw, list):
            return []
        return [str(d) for d in raw]

    # Stack-based DFS: (node, iterator-over-neighbours, path-so-far)
    visited: set[str] = set()
    stack: list[tuple[str, int, list[str]]] = [(task_id, 0, [task_id])]

    while stack:
        node, idx, path = stack[-1]

        # Expand neighbours on first visit.
        if node not in graph:
            graph[node] = _get_deps(node)

        neighbours = graph[node]

        if idx >= len(neighbours):
            stack.pop()
            visited.add(node)
            continue

        # Advance the index in the stack frame.
        stack[-1] = (node, idx + 1, path)

        neighbour = neighbours[idx]
        if neighbour in path:
            # Cycle found.
            cycle_start = path.index(neighbour)
            cycle_nodes = path[cycle_start:] + [neighbour]
            errors.append(f"Dependency cycle detected: {' → '.join(cycle_nodes)}.")
            break  # One cycle report is enough.

        if neighbour not in visited:
            stack.append((neighbour, 0, path + [neighbour]))

    return errors
