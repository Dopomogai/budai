"""Tests for bin/lib/resolution.py — registry-source branching (AC6 of task-020).

Run with: python3 -m pytest tests/bin/test_resolution.py -v
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

from lib.manifest import Manifest
from lib.resolution import _base_dir, is_base_only, is_local, list_available, resolve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manifest(registry_source: str = "self") -> Manifest:
    """Return a minimal Manifest with the given registry-source value."""
    return Manifest(budai_version="0.2.0", registry_source=registry_source)


def _write_file(path: Path, content: str = "# stub\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# AC6(a): registry-source: self resolves role at <repo_root>/base/roles/
# ---------------------------------------------------------------------------

def test_self_resolves_role_at_repo_root_base(tmp_path: Path):
    """When registry-source is 'self', resolve() finds files in <repo_root>/base/."""
    role_file = _write_file(tmp_path / "base" / "roles" / "librarian.md")
    # .agents/local/ and .agents/base/ intentionally absent

    manifest = _make_manifest("self")
    result = resolve(tmp_path, "roles", "librarian", manifest)

    assert result == role_file, f"Expected {role_file}, got {result}"


# ---------------------------------------------------------------------------
# AC6(b): registry-source: self with missing base/ category returns None
# ---------------------------------------------------------------------------

def test_self_missing_category_returns_none(tmp_path: Path):
    """When registry-source is 'self' and base/<category>/ doesn't exist, resolve returns None."""
    # No base/roles/ directory created
    manifest = _make_manifest("self")
    result = resolve(tmp_path, "roles", "librarian", manifest)

    assert result is None


# ---------------------------------------------------------------------------
# AC6(c): non-self path uses .agents/base/
# ---------------------------------------------------------------------------

def test_non_self_uses_agents_base(tmp_path: Path):
    """When registry-source is not 'self', resolve() looks in .agents/base/."""
    # Place file in .agents/base/roles/
    agents_role = _write_file(tmp_path / ".agents" / "base" / "roles" / "librarian.md")
    # Also create a base/roles/ file to confirm it is NOT used
    _write_file(tmp_path / "base" / "roles" / "librarian.md", "# wrong\n")

    manifest = _make_manifest("https://registry.example.com/budai")
    result = resolve(tmp_path, "roles", "librarian", manifest)

    assert result == agents_role, (
        f"Expected .agents/base/ path {agents_role}, got {result}"
    )


# ---------------------------------------------------------------------------
# AC6(d): local/ overlay wins over base/ regardless of registry-source
# ---------------------------------------------------------------------------

def test_local_overlay_wins_over_base_regardless_of_registry_source(tmp_path: Path):
    """Local override takes precedence whether registry-source is 'self' or not."""
    local_role = _write_file(tmp_path / ".agents" / "local" / "roles" / "librarian.md")
    # Also put a base file in place (self path)
    _write_file(tmp_path / "base" / "roles" / "librarian.md")

    for registry_source in ("self", "https://registry.example.com/budai"):
        manifest = _make_manifest(registry_source)
        result = resolve(tmp_path, "roles", "librarian", manifest)
        assert result == local_role, (
            f"registry_source={registry_source!r}: expected local {local_role}, got {result}"
        )


# ---------------------------------------------------------------------------
# AC6(e): _base_dir helper returns the right path for both modes
# ---------------------------------------------------------------------------

def test_base_dir_returns_repo_root_base_for_self(tmp_path: Path):
    """_base_dir returns <repo_root>/base when registry-source is 'self'."""
    manifest = _make_manifest("self")
    assert _base_dir(tmp_path, manifest) == tmp_path / "base"


def test_base_dir_returns_agents_base_for_non_self(tmp_path: Path):
    """_base_dir returns <repo_root>/.agents/base when registry-source is not 'self'."""
    manifest = _make_manifest("https://registry.example.com/budai")
    assert _base_dir(tmp_path, manifest) == tmp_path / ".agents" / "base"


# ---------------------------------------------------------------------------
# list_available respects registry-source
# ---------------------------------------------------------------------------

def test_list_available_self_walks_repo_root_base(tmp_path: Path):
    """list_available() with registry-source: self walks <repo_root>/base/<category>/."""
    _write_file(tmp_path / "base" / "roles" / "librarian.md")
    _write_file(tmp_path / "base" / "roles" / "planner.md")

    manifest = _make_manifest("self")
    result = list_available(tmp_path, "roles", manifest)

    assert "librarian" in result
    assert "planner" in result


def test_list_available_union_includes_local_and_base(tmp_path: Path):
    """list_available() merges local/ and base/ names (no duplicates)."""
    _write_file(tmp_path / "base" / "roles" / "librarian.md")
    _write_file(tmp_path / ".agents" / "local" / "roles" / "librarian.md")  # override
    _write_file(tmp_path / ".agents" / "local" / "roles" / "custom.md")

    manifest = _make_manifest("self")
    result = list_available(tmp_path, "roles", manifest)

    assert result == sorted({"librarian", "custom"})


# ---------------------------------------------------------------------------
# is_base_only passes manifest through correctly
# ---------------------------------------------------------------------------

def test_is_base_only_self(tmp_path: Path):
    """is_base_only() returns True when file only exists in base/ (self mode)."""
    _write_file(tmp_path / "base" / "roles" / "planner.md")

    manifest = _make_manifest("self")
    assert is_base_only(tmp_path, "roles", "planner", manifest) is True
    assert is_base_only(tmp_path, "roles", "nonexistent", manifest) is False
