"""Base/local overlay resolution.

Per docs/02-structure.md: when looking up a skill/role/workflow named X,
check `local/<dir>/X.md` first; fall back to `base/<dir>/X.md`.
Local wins.
"""

from __future__ import annotations

from pathlib import Path


AGENTS_DIR = ".agents"


def resolve(
    repo_root: Path,
    category: str,
    name: str,
    extension: str = ".md",
) -> Path | None:
    """Resolve a name in the given category (roles, skills, workflows, runners).

    Returns the local file if it exists, otherwise the base file.
    Returns None if neither exists.
    """
    agents = repo_root / AGENTS_DIR

    local_path = agents / "local" / category / f"{name}{extension}"
    if local_path.exists():
        return local_path

    base_path = agents / "base" / category / f"{name}{extension}"
    if base_path.exists():
        return base_path

    return None


def list_available(repo_root: Path, category: str) -> list[str]:
    """List all names available in a category (union of local + base)."""
    agents = repo_root / AGENTS_DIR

    names: set[str] = set()

    for source in [agents / "base" / category, agents / "local" / category]:
        if source.exists():
            for path in source.glob("*.md"):
                names.add(path.stem)

    return sorted(names)


def is_local(repo_root: Path, category: str, name: str) -> bool:
    """Check if a given name has a local override."""
    agents = repo_root / AGENTS_DIR
    return (agents / "local" / category / f"{name}.md").exists()


def is_base_only(repo_root: Path, category: str, name: str) -> bool:
    """Check if a name comes only from base (no local override)."""
    return not is_local(repo_root, category, name) and resolve(repo_root, category, name) is not None
