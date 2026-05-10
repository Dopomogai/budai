"""Tests for bin/lib/workflow_schema.py — parse, validate, and evaluate workflow specs.

Run with: python3 -m pytest tests/bin/test_workflow_schema.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure bin/ is importable regardless of where pytest is invoked from.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_DIR = REPO_ROOT / "bin"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

from lib.workflow_schema import (
    VALID_PREDICATE_ATOMS,
    WorkflowSpec,
    evaluate_predicate,
    parse_predicate,
    parse_workflow_file,
    validate_gate_rules,
    validate_workflow_spec,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _minimal_workflow_md(
    name: str = "test-workflow",
    roles: str = "[planner, implementer]",
    extra: str = "",
) -> str:
    return f"""---
workflow: {name}
version: 1.0.0
roles: {roles}
{extra}---

# {name}

Body text.
"""


# ---------------------------------------------------------------------------
# parse_workflow_file — roundtrip
# ---------------------------------------------------------------------------

def test_parse_workflow_file_roundtrip_returns_correct_name(tmp_path: Path):
    """parse_workflow_file correctly reads the 'workflow' field."""
    p = _write(
        tmp_path / "fast-track.md",
        _minimal_workflow_md(name="fast-track", roles="[implementer]"),
    )
    spec = parse_workflow_file(p)
    assert spec.name == "fast-track"


def test_parse_workflow_file_roundtrip_returns_correct_roles(tmp_path: Path):
    """parse_workflow_file returns roles in declared order."""
    p = _write(
        tmp_path / "medium-track.md",
        _minimal_workflow_md(
            name="medium-track",
            roles="[planner, implementer, verifier]",
        ),
    )
    spec = parse_workflow_file(p)
    assert spec.roles == ["planner", "implementer", "verifier"]


def test_parse_workflow_file_roundtrip_preserves_body(tmp_path: Path):
    """parse_workflow_file preserves the body text."""
    content = "---\nworkflow: stub\nversion: 0.1.0\nroles: [planner]\n---\n\n# stub\n\nBody here.\n"
    p = _write(tmp_path / "stub.md", content)
    spec = parse_workflow_file(p)
    assert "Body here." in spec.body


def test_parse_workflow_file_reads_gate_rules(tmp_path: Path):
    """parse_workflow_file reads gate-rules mapping."""
    extra = "gate-rules:\n  planner: human\n  implementer: auto\n"
    p = _write(
        tmp_path / "wf.md",
        _minimal_workflow_md(
            name="wf",
            roles="[planner, implementer]",
            extra=extra,
        ),
    )
    spec = parse_workflow_file(p)
    assert spec.gate_rules == {"planner": "human", "implementer": "auto"}


def test_parse_workflow_file_reads_auto_approve_when(tmp_path: Path):
    """parse_workflow_file reads auto-approve-when field."""
    extra = "auto-approve-when: fan-out-1 AND verifier-passed\n"
    p = _write(
        tmp_path / "wf.md",
        _minimal_workflow_md(name="wf", extra=extra),
    )
    spec = parse_workflow_file(p)
    assert spec.auto_approve_when == "fan-out-1 AND verifier-passed"


def test_parse_workflow_file_raises_on_missing_workflow_field(tmp_path: Path):
    """parse_workflow_file raises ValueError when 'workflow' key is absent."""
    p = _write(tmp_path / "bad.md", "---\nversion: 1.0.0\nroles: [implementer]\n---\n\nBody.\n")
    with pytest.raises(ValueError, match="missing required field"):
        parse_workflow_file(p)


# ---------------------------------------------------------------------------
# validate_workflow_spec — catches missing / invalid fields
# ---------------------------------------------------------------------------

def test_validate_workflow_spec_valid_spec_returns_no_errors():
    """validate_workflow_spec returns empty list for a valid spec."""
    spec = WorkflowSpec(
        name="fast-track",
        version="1.0.0",
        roles=["implementer"],
        gate_rules={"implementer": "human"},
        default_fan_out=1,
        auto_approve_when="never",
    )
    errors = validate_workflow_spec(spec)
    assert errors == []


def test_validate_workflow_spec_rejects_invalid_name():
    """validate_workflow_spec catches name that doesn't match ^[a-z][a-z0-9-]*$."""
    spec = WorkflowSpec(
        name="BadName",
        version="1.0.0",
        roles=["implementer"],
    )
    errors = validate_workflow_spec(spec)
    assert any("name" in e.lower() or "pattern" in e.lower() for e in errors)


def test_validate_workflow_spec_rejects_fan_out_less_than_1():
    """validate_workflow_spec catches default_fan_out < 1."""
    spec = WorkflowSpec(
        name="wf",
        version="1.0.0",
        roles=["implementer"],
        default_fan_out=0,
    )
    errors = validate_workflow_spec(spec)
    assert any("fan-out" in e for e in errors)


def test_validate_workflow_spec_rejects_gate_rules_key_not_in_roles():
    """validate_workflow_spec catches gate-rules key that is not in roles list."""
    spec = WorkflowSpec(
        name="wf",
        version="1.0.0",
        roles=["implementer"],
        gate_rules={"judge": "human"},  # judge not in roles
    )
    errors = validate_workflow_spec(spec)
    assert any("judge" in e for e in errors)


def test_validate_workflow_spec_rejects_invalid_auto_approve_when():
    """validate_workflow_spec catches unknown atom in auto-approve-when."""
    spec = WorkflowSpec(
        name="wf",
        version="1.0.0",
        roles=["implementer"],
        auto_approve_when="unknown-atom",
    )
    errors = validate_workflow_spec(spec)
    assert any("auto-approve-when" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_gate_rules — keys-subset-of-roles validation
# ---------------------------------------------------------------------------

def test_validate_gate_rules_rejects_key_not_in_roles():
    """validate_gate_rules flags gate-rules keys not present in roles."""
    errors = validate_gate_rules({"librarian": "auto"}, roles=["implementer"])
    assert len(errors) == 1
    assert "librarian" in errors[0]


def test_validate_gate_rules_accepts_valid_auto_when():
    """validate_gate_rules accepts auto-when:<valid-predicate> gate mode."""
    errors = validate_gate_rules(
        {"planner": "auto-when:trivial"},
        roles=["planner", "implementer"],
    )
    assert errors == []


def test_validate_gate_rules_rejects_auto_when_unknown_atom():
    """validate_gate_rules rejects auto-when:<unknown-atom> gate mode."""
    errors = validate_gate_rules(
        {"planner": "auto-when:nonexistent-atom"},
        roles=["planner"],
    )
    assert len(errors) == 1
    assert "nonexistent-atom" in errors[0] or "unknown" in errors[0].lower()


# ---------------------------------------------------------------------------
# parse_predicate — rejects unknown atoms
# ---------------------------------------------------------------------------

def test_parse_predicate_single_valid_atom():
    """parse_predicate returns single-element list for a valid single atom."""
    atoms = parse_predicate("fan-out-1")
    assert atoms == ["fan-out-1"]


def test_parse_predicate_valid_and_composition():
    """parse_predicate splits on ' AND ' and returns multiple atoms."""
    atoms = parse_predicate("fan-out-1 AND verifier-passed")
    assert atoms == ["fan-out-1", "verifier-passed"]


def test_parse_predicate_rejects_unknown_atom():
    """parse_predicate raises ValueError on an atom not in VALID_PREDICATE_ATOMS."""
    with pytest.raises(ValueError, match="Unknown predicate atom"):
        parse_predicate("fan-out-1 AND not-a-real-atom")


def test_parse_predicate_rejects_all_unknown_atoms():
    """parse_predicate raises ValueError even when no atom is valid."""
    with pytest.raises(ValueError, match="Unknown predicate atom"):
        parse_predicate("mystery-atom")


def test_valid_predicate_atoms_contains_exactly_six():
    """VALID_PREDICATE_ATOMS contains exactly 6 atoms per ADR 0003 § 2."""
    assert len(VALID_PREDICATE_ATOMS) == 6


# ---------------------------------------------------------------------------
# evaluate_predicate — AND composition
# ---------------------------------------------------------------------------

def test_evaluate_predicate_single_atom_true():
    """evaluate_predicate returns True when single atom evaluates true."""
    assert evaluate_predicate("fan-out-1", {"fan_out": 1}) is True


def test_evaluate_predicate_single_atom_false():
    """evaluate_predicate returns False when single atom evaluates false."""
    assert evaluate_predicate("fan-out-1", {"fan_out": 2}) is False


def test_evaluate_predicate_and_both_true():
    """evaluate_predicate returns True when all atoms in AND hold."""
    ctx = {"fan_out": 1, "verifier_passed": True}
    assert evaluate_predicate("fan-out-1 AND verifier-passed", ctx) is True


def test_evaluate_predicate_and_one_false():
    """evaluate_predicate returns False when any atom in AND is false."""
    ctx = {"fan_out": 1, "verifier_passed": False}
    assert evaluate_predicate("fan-out-1 AND verifier-passed", ctx) is False


def test_evaluate_predicate_missing_context_key_defaults_false():
    """evaluate_predicate treats absent context keys as False."""
    assert evaluate_predicate("trivial", {}) is False


def test_evaluate_predicate_all_atoms_individually():
    """evaluate_predicate correctly handles each of the 6 valid atoms."""
    cases = [
        ("fan-out-1", {"fan_out": 1}, True),
        ("fan-out-1", {"fan_out": 3}, False),
        ("verifier-passed", {"verifier_passed": True}, True),
        ("verifier-passed", {"verifier_passed": False}, False),
        ("trivial", {"trivial": True}, True),
        ("trivial", {}, False),
        ("all-ac-pass", {"all_ac_pass": True}, True),
        ("all-ac-pass", {}, False),
        ("no-new-adr", {"no_new_adr": True}, True),
        ("no-new-adr", {}, False),
        ("single-attempt", {"single_attempt": True}, True),
        ("single-attempt", {}, False),
    ]
    for predicate, ctx, expected in cases:
        result = evaluate_predicate(predicate, ctx)
        assert result is expected, f"predicate={predicate!r} ctx={ctx} expected={expected} got={result}"
