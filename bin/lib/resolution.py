"""Base/local overlay resolution.

Per docs/02-structure.md: when looking up a skill/role/workflow named X,
check `local/<dir>/X.md` first; fall back to `base/<dir>/X.md`.
Local wins.

When the manifest declares `registry-source: self`, the authoritative base
tree lives at `<repo_root>/base/` (the registry ships inside the repo itself).
For all other values of `registry-source`, the base tree lives at
`<repo_root>/.agents/base/` (the synced consumer path, existing behavior).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manifest import Manifest


AGENTS_DIR = ".agents"


def _base_dir(repo_root: Path, manifest: "Manifest") -> Path:
    """Return the base directory for registry content.

    When registry-source is "self", the repo ships its own base/ at the
    repo root.  All other values (registry URL, local path, etc.) use the
    synced .agents/base/ path, which is the existing consumer-repo behavior.
    """
    if manifest.registry_source == "self":
        return repo_root / "base"
    return repo_root / AGENTS_DIR / "base"


def resolve(
    repo_root: Path,
    category: str,
    name: str,
    manifest: "Manifest | None" = None,
    extension: str = ".md",
) -> Path | None:
    """Resolve a name in the given category (roles, skills, workflows, runners).

    Returns the local file if it exists, otherwise the base file.
    Returns None if neither exists.

    When manifest is provided its registry-source field determines which base
    directory is searched.  When manifest is None the legacy .agents/base/
    path is used (backward-compatible).
    """
    agents = repo_root / AGENTS_DIR

    local_path = agents / "local" / category / f"{name}{extension}"
    if local_path.exists():
        return local_path

    if manifest is not None:
        base_root = _base_dir(repo_root, manifest)
    else:
        base_root = agents / "base"

    base_path = base_root / category / f"{name}{extension}"
    if base_path.exists():
        return base_path

    return None


def list_available(
    repo_root: Path,
    category: str,
    manifest: "Manifest | None" = None,
) -> list[str]:
    """List all names available in a category (union of local + base)."""
    agents = repo_root / AGENTS_DIR

    if manifest is not None:
        base_root = _base_dir(repo_root, manifest)
    else:
        base_root = agents / "base"

    names: set[str] = set()

    for source in [base_root / category, agents / "local" / category]:
        if source.exists():
            for path in source.glob("*.md"):
                names.add(path.stem)

    return sorted(names)


def is_local(
    repo_root: Path,
    category: str,
    name: str,
) -> bool:
    """Check if a given name has a local override."""
    agents = repo_root / AGENTS_DIR
    return (agents / "local" / category / f"{name}.md").exists()


def is_base_only(
    repo_root: Path,
    category: str,
    name: str,
    manifest: "Manifest | None" = None,
) -> bool:
    """Check if a name comes only from base (no local override)."""
    return not is_local(repo_root, category, name) and resolve(repo_root, category, name, manifest) is not None
