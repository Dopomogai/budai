"""Parse, validate, and evaluate workflow frontmatter and gate-rule predicates.

Mirrors bin/lib/task_schema.py for workflow files. Pure-function module: no I/O
side effects beyond the parse_workflow_file() entry point that reads one file.

The predicate language is a closed set defined in ADR 0003 § 2. VALID_PREDICATE_ATOMS
must stay in lock-step with ADR 0003. If you add an atom here, update the ADR first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Closed-set predicate atoms — ADR 0003 § 2.
# ---------------------------------------------------------------------------

VALID_PREDICATE_ATOMS: frozenset[str] = frozenset({
    "fan-out-1",
    "verifier-passed",
    "trivial",
    "all-ac-pass",
    "no-new-adr",
    "single-attempt",
})

VALID_GATE_MODES: frozenset[str] = frozenset({"human", "auto"})

# Prefix for conditional gate modes: "auto-when:<predicate>"
_AUTO_WHEN_PREFIX = "auto-when:"

# Workflow name must be kebab-case.
_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


# ---------------------------------------------------------------------------
# WorkflowSpec dataclass — the parsed in-memory representation of a workflow file.
# ---------------------------------------------------------------------------

@dataclass
class WorkflowSpec:
    name: str
    version: str
    roles: list[str]
    applicable_task_types: list[str] = field(default_factory=list)
    default_fan_out: int = 1
    human_gates: list[str] = field(default_factory=list)
    default_retry_budget: int = 2
    peer_reviewers: int = 0
    stability: str = "experimental"
    auto_spawn_follow_ups: list[dict] = field(default_factory=list)
    entry_criteria: list[str] = field(default_factory=list)
    exit_criteria: list[str] = field(default_factory=list)
    skipped_artifacts: list[str] = field(default_factory=list)
    auto_approve_when: str = "never"
    gate_rules: dict[str, str] = field(default_factory=dict)
    body: str = ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _strip_frontmatter(content: str) -> tuple[str, str]:
    """Split a markdown file into (frontmatter_yaml, body).

    Returns ('', content) when no frontmatter block is found.
    """
    if not content.startswith("---"):
        return "", content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", content
    return parts[1].strip(), parts[2].lstrip()


def parse_workflow_file(path: Path) -> WorkflowSpec:
    """Read a workflow markdown file and return a WorkflowSpec.

    Raises:
        FileNotFoundError: if path does not exist.
        ValueError: if the frontmatter is invalid YAML or missing the required
            'workflow' and 'roles' keys.
    """
    content = path.read_text(encoding="utf-8")
    fm_yaml, body = _strip_frontmatter(content)

    if not fm_yaml:
        raise ValueError(f"Workflow file {path} has no YAML frontmatter block.")

    try:
        fm: dict[str, Any] = yaml.safe_load(fm_yaml) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(fm, dict):
        raise ValueError(f"Frontmatter in {path} is not a YAML mapping.")

    name = str(fm.get("workflow", "")).strip()
    if not name:
        raise ValueError(f"Workflow file {path} missing required field 'workflow'.")

    raw_roles = fm.get("roles", [])
    if not isinstance(raw_roles, list):
        raise ValueError(f"Workflow file {path}: 'roles' must be a list.")
    roles = [str(r) for r in raw_roles]

    # Gate rules: coerce nested mapping from YAML.
    raw_gate_rules = fm.get("gate-rules", {}) or {}
    gate_rules: dict[str, str] = {str(k): str(v) for k, v in raw_gate_rules.items()}

    # auto-spawn-follow-ups: list of dicts.
    raw_follow_ups = fm.get("auto-spawn-follow-ups", []) or []
    follow_ups: list[dict] = []
    for item in raw_follow_ups:
        if isinstance(item, dict):
            follow_ups.append(item)
        else:
            follow_ups.append({"raw": str(item)})

    # entry/exit-criteria: accept list or str.
    def _to_str_list(val: Any) -> list[str]:
        if not val:
            return []
        if isinstance(val, list):
            return [str(x) for x in val]
        return [str(val)]

    return WorkflowSpec(
        name=name,
        version=str(fm.get("version", "0.0.0")),
        roles=roles,
        applicable_task_types=_to_str_list(fm.get("applicable-task-types", [])),
        default_fan_out=int(fm.get("default-fan-out", 1)),
        human_gates=_to_str_list(fm.get("human-gates", [])),
        default_retry_budget=int(fm.get("default-retry-budget", 2)),
        peer_reviewers=int(fm.get("peer-reviewers", 0)),
        stability=str(fm.get("stability", "experimental")),
        auto_spawn_follow_ups=follow_ups,
        entry_criteria=_to_str_list(fm.get("entry-criteria", [])),
        exit_criteria=_to_str_list(fm.get("exit-criteria", [])),
        skipped_artifacts=_to_str_list(fm.get("skipped-artifacts", [])),
        auto_approve_when=str(fm.get("auto-approve-when", "never")),
        gate_rules=gate_rules,
        body=body,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_gate_rules(rules: dict[str, str], roles: list[str]) -> list[str]:
    """Validate gate-rules keys and values.

    Returns list of error strings. Empty list means valid.

    Checks:
    - Every key in rules is in roles.
    - Every value is a valid gate mode (human, auto, or auto-when:<predicate>).
    """
    errors: list[str] = []
    role_set = set(roles)

    for role_key, mode_val in rules.items():
        if role_key not in role_set:
            errors.append(
                f"gate-rules key '{role_key}' is not in roles list {roles}."
            )
        # Validate mode value.
        if mode_val in VALID_GATE_MODES:
            continue
        if mode_val.startswith(_AUTO_WHEN_PREFIX):
            predicate_str = mode_val[len(_AUTO_WHEN_PREFIX):]
            try:
                parse_predicate(predicate_str)
            except ValueError as exc:
                errors.append(
                    f"gate-rules['{role_key}']: invalid predicate in '{mode_val}': {exc}"
                )
        else:
            errors.append(
                f"gate-rules['{role_key}']: unknown gate mode '{mode_val}'. "
                f"Must be one of {sorted(VALID_GATE_MODES)} or '{_AUTO_WHEN_PREFIX}<predicate>'."
            )

    return errors


def validate_workflow_spec(spec: WorkflowSpec) -> list[str]:
    """Validate a WorkflowSpec.

    Returns list of human-readable error strings. Empty list means valid.

    Checks:
    - name matches regex ^[a-z][a-z0-9-]*$
    - every entry in roles is non-empty
    - gate_rules keys are a subset of roles
    - every gate_rules value is a valid gate mode
    - auto_approve_when parses as 'never' or a valid predicate
    - default_fan_out >= 1
    """
    errors: list[str] = []

    # name format.
    if not _NAME_PATTERN.match(spec.name):
        errors.append(
            f"Workflow name '{spec.name}' does not match pattern ^[a-z][a-z0-9-]*$."
        )

    # roles non-empty entries.
    for i, role in enumerate(spec.roles):
        if not role.strip():
            errors.append(f"roles[{i}] is empty.")

    # gate_rules validation.
    errors.extend(validate_gate_rules(spec.gate_rules, spec.roles))

    # auto_approve_when.
    if spec.auto_approve_when != "never":
        try:
            parse_predicate(spec.auto_approve_when)
        except ValueError as exc:
            errors.append(f"auto-approve-when: {exc}")

    # default_fan_out.
    if spec.default_fan_out < 1:
        errors.append(
            f"default-fan-out must be >= 1, got {spec.default_fan_out}."
        )

    return errors


# ---------------------------------------------------------------------------
# Predicate parsing and evaluation
# ---------------------------------------------------------------------------

def parse_predicate(s: str) -> list[str]:
    """Parse a predicate string into a list of atoms.

    Splits on ' AND '. Raises ValueError if any atom is not in VALID_PREDICATE_ATOMS.

    Args:
        s: A predicate string like 'fan-out-1 AND verifier-passed' or a single atom.

    Returns:
        List of atom strings.

    Raises:
        ValueError: If any atom is not in VALID_PREDICATE_ATOMS.
    """
    atoms = [atom.strip() for atom in s.split(" AND ")]
    unknown = [a for a in atoms if a not in VALID_PREDICATE_ATOMS]
    if unknown:
        raise ValueError(
            f"Unknown predicate atom(s): {unknown}. "
            f"Valid atoms: {sorted(VALID_PREDICATE_ATOMS)}."
        )
    return atoms


def evaluate_predicate(predicate: str, context: dict) -> bool:
    """Evaluate a predicate string against a context dict.

    Splits on ' AND '; all atoms must be true (AND semantics).

    Context keys (all optional; absent keys are treated as False):
    - fan_out (int): effective fan-out for the task.
    - verifier_passed (bool): whether the Verifier report says all ACs pass.
    - trivial (bool): task frontmatter has trivial: true.
    - all_ac_pass (bool): every AC confirmed passing.
    - no_new_adr (bool): no new file under memory/decisions/ in this run.
    - single_attempt (bool): only one Implementer attempt exists.

    Args:
        predicate: A predicate string (e.g., 'fan-out-1 AND verifier-passed').
        context: Dict with evaluation context.

    Returns:
        True if all atoms in the predicate hold in context.

    Raises:
        ValueError: If predicate contains unknown atoms.
    """
    atoms = parse_predicate(predicate)

    _ATOM_EVALUATORS: dict[str, Any] = {
        "fan-out-1": lambda ctx: int(ctx.get("fan_out", 0)) == 1,
        "verifier-passed": lambda ctx: bool(ctx.get("verifier_passed", False)),
        "trivial": lambda ctx: bool(ctx.get("trivial", False)),
        "all-ac-pass": lambda ctx: bool(ctx.get("all_ac_pass", False)),
        "no-new-adr": lambda ctx: bool(ctx.get("no_new_adr", False)),
        "single-attempt": lambda ctx: bool(ctx.get("single_attempt", False)),
    }

    return all(_ATOM_EVALUATORS[atom](context) for atom in atoms)
