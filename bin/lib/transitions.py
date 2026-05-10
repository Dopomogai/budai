"""Frontmatter transition orchestration for the budai runner.

Owns the atomic write+move primitive for task status transitions, the
role-to-next-status mapping, the predicate-context assembly step, and
the per-role orchestration verb that dispatch_roles calls after each
role completes. Both manual (bin/task move) and automatic (runner) flips
go through apply_transition — they share exactly one code path.

Fail-closed throughout: every missing predicate-context source returns
False rather than raising, so unknown state always halts for human
approval rather than silently auto-approving.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .task_schema import (
    folder_for_status,
    layout_folders,
    load_all_tasks,
    parse_frontmatter,
    validate_dependencies,
    validate_frontmatter,
    validate_transition,
)
from .workflow_schema import WorkflowSpec, evaluate_predicate, parse_predicate


# ---------------------------------------------------------------------------
# Role-to-next-status mapping — ADR 0004 §2.
# Five entries; exact spelling. Every value must be reachable from its
# corresponding role's expected prev-status via STATUS_TRANSITIONS.
# ---------------------------------------------------------------------------

ROLE_EXIT_STATUS: dict[str, str] = {
    "librarian": "planning",
    "planner": "reviewing-plan",
    "implementer": "reviewing-result",
    "verifier": "reviewing-result",
    "judge": "done",
}


# ---------------------------------------------------------------------------
# TransitionDecision dataclass
# ---------------------------------------------------------------------------

@dataclass
class TransitionDecision:
    """The outcome of flip_for_role.

    Attributes:
        role: Role name that was dispatched.
        prev_status: Task status before the flip (or at halt time).
        new_status: Status written if decision is "auto*"; None otherwise.
        decision: One of "auto", "auto-with-condition: <predicate>",
            "human-required", or "role-failed".
        gate_mode: The gate-rules value that was consulted ("human", "auto",
            or "auto-when:<predicate>").
        predicate: The predicate string when gate_mode is "auto-when:*";
            None otherwise.
        halted_reason: For "human-required", the manual command the operator
            should run. None for auto decisions and role-failed.
    """

    role: str
    prev_status: str
    new_status: str | None
    decision: str
    gate_mode: str
    predicate: str | None
    halted_reason: str | None


# ---------------------------------------------------------------------------
# Module-level cache for no_new_adr git results.
# Keyed by (worktree_str, run_dir_str) — one git call per journey, not per role.
# ---------------------------------------------------------------------------

_no_new_adr_cache: dict[tuple[str, str], bool] = {}


# ---------------------------------------------------------------------------
# Pure helper: next status and extra frontmatter updates
# ---------------------------------------------------------------------------

def next_status_for_role(role: str) -> str:
    """Return the deterministic next status for a role's completion.

    Args:
        role: Role name (e.g., "planner", "implementer").

    Returns:
        The status string this role exits to.

    Raises:
        KeyError: If role is not in ROLE_EXIT_STATUS.
    """
    return ROLE_EXIT_STATUS[role]


def extra_fm_updates_for_transition(prev_status: str, new_status: str) -> dict:
    """Return extra frontmatter key/value pairs implied by a status transition.

    Encodes the boolean-flip rules from ADR 0004 §2:
    - reviewing-plan → implementing: set plan-approved: True
    - reviewing-result → done: set result-approved: True
    - all other pairs: empty dict

    Args:
        prev_status: Status before the transition.
        new_status: Status after the transition.

    Returns:
        Dict of extra frontmatter updates (may be empty).
    """
    if prev_status == "reviewing-plan" and new_status == "implementing":
        return {"plan-approved": True}
    if new_status == "done":
        return {"result-approved": True}
    return {}


# ---------------------------------------------------------------------------
# Predicate-context builder — ADR 0004 §3
# ---------------------------------------------------------------------------

def build_predicate_context(
    repo_root: Path,
    task_id: str,
    run_dir: Path,
    worktree: Path | None,
    layout: str,
) -> dict:
    """Assemble the six-atom evaluation context for workflow gate predicates.

    Every missing or unreadable source returns False (fail-closed) per
    ADR 0004 §3. No exception propagates out of this function.

    Sources:
    - fan_out: task frontmatter "fan-out" field (int).
    - trivial: task frontmatter "trivial" field (bool).
    - verifier_passed: evidence/ac-mapping.json in worktree (or run_dir).
      True iff every entry has verdict == "pass".
    - all_ac_pass: same source as verifier_passed (alias today).
    - no_new_adr: git diff --name-only origin/main..HEAD -- memory/decisions/
      in worktree returns empty stdout. Cached per (worktree, run_dir).
    - single_attempt: count of council/<task_id>/attempts/attempt-*.md
      in repo_root equals 1.

    Args:
        repo_root: Absolute path to the repository root.
        task_id: Task ID string (e.g., "022").
        run_dir: Path to the current run directory.
        worktree: Path to the role's worktree, or None in placeholder mode.
        layout: Task folder layout string.

    Returns:
        Dict with keys: fan_out, trivial, verifier_passed, all_ac_pass,
        no_new_adr, single_attempt.
    """
    context: dict[str, Any] = {
        "fan_out": 1,
        "trivial": False,
        "verifier_passed": False,
        "all_ac_pass": False,
        "no_new_adr": False,
        "single_attempt": False,
    }

    # --- fan_out and trivial from task frontmatter ---
    try:
        all_tasks = load_all_tasks(repo_root, layout)
        if task_id in all_tasks:
            task_text = all_tasks[task_id].read_text(encoding="utf-8")
            fm = parse_frontmatter(task_text)
            context["fan_out"] = int(fm.get("fan-out", 1))
            context["trivial"] = bool(fm.get("trivial", False))
    except Exception:  # noqa: BLE001
        pass  # fail-closed: keep defaults

    # --- verifier_passed and all_ac_pass from evidence/ac-mapping.json ---
    try:
        if worktree is not None:
            ac_map_path = worktree / "evidence" / "ac-mapping.json"
        else:
            ac_map_path = run_dir / "evidence" / "ac-mapping.json"

        if ac_map_path.exists():
            raw = json.loads(ac_map_path.read_text(encoding="utf-8"))
            if isinstance(raw, list) and raw:
                all_pass = all(
                    isinstance(entry, dict) and entry.get("verdict") == "pass"
                    for entry in raw
                )
                context["verifier_passed"] = all_pass
                context["all_ac_pass"] = all_pass
    except Exception:  # noqa: BLE001
        pass  # fail-closed: keep False

    # --- no_new_adr via git diff (cached) ---
    if worktree is not None:
        cache_key = (str(worktree), str(run_dir))
        if cache_key in _no_new_adr_cache:
            context["no_new_adr"] = _no_new_adr_cache[cache_key]
        else:
            result = False
            try:
                completed = subprocess.run(
                    ["git", "-C", str(worktree), "diff", "--name-only",
                     "origin/main..HEAD", "--", "memory/decisions/"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if completed.returncode == 0:
                    result = completed.stdout.strip() == ""
            except Exception:  # noqa: BLE001
                result = False  # fail-closed
            _no_new_adr_cache[cache_key] = result
            context["no_new_adr"] = result
    # else: worktree is None → no_new_adr stays False (fail-closed)

    # --- single_attempt: count attempt-*.md files in council/<task_id>/attempts/ ---
    try:
        attempts_dir = repo_root / ".agents" / "council" / task_id / "attempts"
        if attempts_dir.exists():
            attempt_files = list(attempts_dir.glob("attempt-*.md"))
            context["single_attempt"] = len(attempt_files) == 1
    except Exception:  # noqa: BLE001
        pass  # fail-closed: keep False

    return context


# ---------------------------------------------------------------------------
# Atomic transition: find file, mutate frontmatter, write, move
# ---------------------------------------------------------------------------

def _find_task_file(repo_root: Path, task_id: str, layout: str) -> Path | None:
    """Locate a task file by ID across all configured layout folders."""
    tasks_dir = repo_root / "tasks"
    for folder in layout_folders(layout):
        folder_path = tasks_dir / folder
        if not folder_path.exists():
            continue
        matches = list(folder_path.glob(f"{task_id}*.md"))
        if matches:
            return matches[0]
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit_frontmatter(data: dict[str, Any]) -> str:
    """Serialise frontmatter dict back to YAML-fenced text."""
    import yaml
    return "---\n" + yaml.safe_dump(data, default_flow_style=False, sort_keys=False) + "---"


def apply_transition(
    repo_root: Path,
    task_id: str,
    new_status: str,
    layout: str,
    extra_fm_updates: dict | None = None,
) -> Path:
    """Atomically update task frontmatter and move file to the correct folder.

    Validates the transition via task_schema.validate_transition, mutates
    status + updated + any keys in extra_fm_updates, re-validates frontmatter
    and dependencies, writes back, then moves the file to the folder
    folder_for_status(new_status, layout) returns.

    Idempotent when old_status == new_status: returns the current path
    without error and without writing.

    Args:
        repo_root: Absolute path to the repository root.
        task_id: Task ID string (e.g., "022").
        new_status: The target status to transition to.
        layout: Task folder layout string.
        extra_fm_updates: Optional dict of additional frontmatter keys to set
            (e.g., {"plan-approved": True}).

    Returns:
        Path to the task file after the operation (may be the same path if
        no folder move was needed).

    Raises:
        ValueError: If the task is not found, the transition is illegal,
            or post-mutation frontmatter validation fails.
    """
    task_file = _find_task_file(repo_root, task_id, layout)
    if task_file is None:
        raise ValueError(f"Task not found: {task_id!r}")

    content = task_file.read_text(encoding="utf-8")
    fm_data = parse_frontmatter(content)
    old_status = str(fm_data.get("status", ""))

    # Idempotent: no-op when already at target.
    if old_status == new_status:
        return task_file

    # Validate the transition.
    trans_errors = validate_transition(old_status, new_status)
    if trans_errors:
        raise ValueError(
            f"Illegal transition for task {task_id}: "
            + "; ".join(trans_errors)
        )

    # Mutate frontmatter.
    fm_data["status"] = new_status
    fm_data["updated"] = _now_iso()
    if extra_fm_updates:
        fm_data.update(extra_fm_updates)

    # Re-validate full frontmatter.
    fm_errors = validate_frontmatter(fm_data, layout)
    if fm_errors:
        raise ValueError(
            f"Post-transition frontmatter invalid for task {task_id}: "
            + "; ".join(fm_errors)
        )

    # Re-validate dependencies.
    depends_on = fm_data.get("depends-on", [])
    if not isinstance(depends_on, list):
        depends_on = []
    task_id_str = str(fm_data.get("id", task_id))
    dep_strs = [str(d) for d in depends_on]
    all_tasks = load_all_tasks(repo_root, layout)
    dep_errors = validate_dependencies(task_id_str, dep_strs, all_tasks)
    if dep_errors:
        raise ValueError(
            f"Dependency errors after transition for task {task_id}: "
            + "; ".join(dep_errors)
        )

    # Reconstruct file content: replace frontmatter, preserve body.
    parts = content.split("---", 2)
    body = ("---" + parts[2]) if len(parts) >= 3 else ""
    new_content = _emit_frontmatter(fm_data) + body

    # Write updated content (atomic write before move).
    task_file.write_text(new_content, encoding="utf-8")

    # Move to the target folder if needed.
    target_folder = folder_for_status(new_status, layout)
    tasks_dir = repo_root / "tasks"
    if task_file.parent.name != target_folder:
        target_dir = tasks_dir / target_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        new_path = target_dir / task_file.name
        os.replace(task_file, new_path)
        task_file = new_path

    return task_file


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

def append_transition_record(run_dir: Path, record: dict) -> None:
    """Append a record to the transitions.json audit array.

    Read-modify-write the JSON array at <run_dir>/transitions.json.
    Creates the file with a single-element array if missing.

    Args:
        run_dir: Path to the run directory.
        record: Dict to append (must be JSON-serialisable).
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    transitions_file = run_dir / "transitions.json"

    records: list[dict] = []
    if transitions_file.exists():
        try:
            records = json.loads(transitions_file.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                records = []
        except (json.JSONDecodeError, OSError):
            records = []

    records.append(record)
    transitions_file.write_text(
        json.dumps(records, indent=2, default=str),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Orchestration verb: flip_for_role
# ---------------------------------------------------------------------------

def flip_for_role(
    spec: Any,
    workflow: WorkflowSpec,
    role: str,
    role_exit_code: int,
    run_dir: Path,
    manifest: Any,
) -> TransitionDecision:
    """Decide and (optionally) apply the status transition after a role completes.

    Reads the workflow's gate-rules for the role, evaluates any predicate,
    and either calls apply_transition (auto gates) or returns without flipping
    (human or failed gates). Always appends a record to transitions.json.

    Args:
        spec: RunSpec with repo_root, task_id, worktree, run_id fields.
        workflow: Validated WorkflowSpec with gate_rules.
        role: The role that just completed.
        role_exit_code: Process exit code for the role (0 = success).
        run_dir: Path to the run directory (for transitions.json).
        manifest: Already-loaded Manifest (determines tasks_layout).

    Returns:
        TransitionDecision describing the outcome.
    """
    repo_root: Path = spec.repo_root
    task_id: str = spec.task_id
    worktree: Path | None = getattr(spec, "worktree", None)
    layout: str = manifest.tasks_layout

    gate_mode = workflow.gate_rules.get(role, "human")

    timestamp = _now_iso()

    # --- Role failed: write record and return without flipping ---
    if role_exit_code != 0:
        decision = TransitionDecision(
            role=role,
            prev_status=_safe_read_status(repo_root, task_id, layout),
            new_status=None,
            decision="role-failed",
            gate_mode=gate_mode,
            predicate=None,
            halted_reason=f"Role {role!r} exited with code {role_exit_code}",
        )
        append_transition_record(run_dir, _build_record(decision, timestamp))
        return decision

    # --- Read current status ---
    prev_status = _safe_read_status(repo_root, task_id, layout)

    # --- Resolve next status ---
    try:
        new_status = next_status_for_role(role)
    except KeyError:
        halted_reason = (
            f"role {role!r} has no exit-status mapping; "
            f"add to transitions.ROLE_EXIT_STATUS"
        )
        decision = TransitionDecision(
            role=role,
            prev_status=prev_status,
            new_status=None,
            decision="human-required",
            gate_mode=gate_mode,
            predicate=None,
            halted_reason=halted_reason,
        )
        append_transition_record(run_dir, _build_record(decision, timestamp))
        return decision

    extra = extra_fm_updates_for_transition(prev_status, new_status)

    # --- Branch on gate_mode ---
    if gate_mode == "auto":
        try:
            apply_transition(repo_root, task_id, new_status, layout, extra or None)
        except ValueError as exc:
            raise
        decision = TransitionDecision(
            role=role,
            prev_status=prev_status,
            new_status=new_status,
            decision="auto",
            gate_mode=gate_mode,
            predicate=None,
            halted_reason=None,
        )

    elif gate_mode == "human":
        halted_reason = f"python3 bin/task move {task_id} {new_status}"
        decision = TransitionDecision(
            role=role,
            prev_status=prev_status,
            new_status=None,
            decision="human-required",
            gate_mode=gate_mode,
            predicate=None,
            halted_reason=halted_reason,
        )

    elif gate_mode.startswith("auto-when:"):
        predicate_str = gate_mode[len("auto-when:"):]
        try:
            atoms = parse_predicate(predicate_str)
        except ValueError as exc:
            halted_reason = f"invalid predicate {predicate_str!r}: {exc}"
            decision = TransitionDecision(
                role=role,
                prev_status=prev_status,
                new_status=None,
                decision="human-required",
                gate_mode=gate_mode,
                predicate=predicate_str,
                halted_reason=halted_reason,
            )
            append_transition_record(run_dir, _build_record(decision, timestamp))
            return decision

        context = build_predicate_context(
            repo_root, task_id, run_dir, worktree, layout
        )
        predicate_result = evaluate_predicate(predicate_str, context)

        if predicate_result:
            try:
                apply_transition(repo_root, task_id, new_status, layout, extra or None)
            except ValueError:
                raise
            decision = TransitionDecision(
                role=role,
                prev_status=prev_status,
                new_status=new_status,
                decision=f"auto-with-condition: {predicate_str}",
                gate_mode=gate_mode,
                predicate=predicate_str,
                halted_reason=None,
            )
        else:
            halted_reason = f"python3 bin/task move {task_id} {new_status}"
            decision = TransitionDecision(
                role=role,
                prev_status=prev_status,
                new_status=None,
                decision="human-required",
                gate_mode=gate_mode,
                predicate=predicate_str,
                halted_reason=halted_reason,
            )

    else:
        # Unknown gate mode — treat as human-required.
        halted_reason = (
            f"unknown gate mode {gate_mode!r}; "
            f"run: python3 bin/task move {task_id} {new_status}"
        )
        decision = TransitionDecision(
            role=role,
            prev_status=prev_status,
            new_status=None,
            decision="human-required",
            gate_mode=gate_mode,
            predicate=None,
            halted_reason=halted_reason,
        )

    append_transition_record(run_dir, _build_record(decision, timestamp))
    return decision


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_read_status(repo_root: Path, task_id: str, layout: str) -> str:
    """Read current task status without raising."""
    try:
        task_file = _find_task_file(repo_root, task_id, layout)
        if task_file is None:
            return "unknown"
        text = task_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        return str(fm.get("status", "unknown"))
    except Exception:  # noqa: BLE001
        return "unknown"


def _build_record(decision: TransitionDecision, timestamp: str) -> dict:
    """Convert a TransitionDecision to the transitions.json record schema."""
    return {
        "role": decision.role,
        "exit_status": "failed" if decision.decision == "role-failed" else "success",
        "prev_task_status": decision.prev_status,
        "new_task_status": decision.new_status,
        "decision": decision.decision,
        "gate_mode": decision.gate_mode,
        "predicate": decision.predicate,
        "timestamp": timestamp,
    }
