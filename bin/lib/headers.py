"""File header parsing and index generation.

Reads source files looking for the six-field header comment block:

    @purpose <one line>
    @why <one line>
    @role <agent role>
    @exports <names>
    @uses <internal modules>
    @stability stable | experimental | deprecated
    @gotchas <only when non-obvious>

Generates `index/tree.md`, `index/tree.json`, `index/detailed.md`,
`index/detailed.json` from the parsed headers.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


SOURCE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".kt"}

HEADER_FIELD_PATTERN = re.compile(r"@(\w+)\s+(.+?)(?=\n\s*\*\s*@|\n\s*\*/|\n\s*\"\"\"|$)", re.DOTALL)


@dataclass
class FileHeader:
    path: str
    purpose: str = ""
    why: str = ""
    role: str = ""
    exports: list[str] = field(default_factory=list)
    uses: list[str] = field(default_factory=list)
    stability: str = ""
    gotchas: str = ""
    has_header: bool = False


def parse_header(source: str) -> dict[str, str]:
    """Extract the six fields from the start of a source file.

    Returns a dict with field names as keys and string values.
    Empty dict if no header found.
    """
    # Look for header in the first 50 lines or first 4096 chars (whichever first)
    head = source[: min(len(source), 4096)]

    fields: dict[str, str] = {}
    for match in HEADER_FIELD_PATTERN.finditer(head):
        name = match.group(1).lower()
        value = match.group(2).strip()
        # Clean up multi-line values: remove leading "* " or " * "
        value = re.sub(r"\n\s*\*\s?", "\n", value).strip()
        fields[name] = value

    return fields


def header_from_file(path: Path) -> FileHeader:
    """Read a file and extract its header."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return FileHeader(path=str(path))

    fields = parse_header(source)
    if not fields or "purpose" not in fields:
        return FileHeader(path=str(path), has_header=False)

    return FileHeader(
        path=str(path),
        purpose=fields.get("purpose", ""),
        why=fields.get("why", ""),
        role=fields.get("role", ""),
        exports=_split_list(fields.get("exports", "")),
        uses=_split_list(fields.get("uses", "")),
        stability=fields.get("stability", ""),
        gotchas=fields.get("gotchas", ""),
        has_header=True,
    )


def _split_list(value: str) -> list[str]:
    """Split a comma-separated or space-separated list field."""
    if not value:
        return []
    # Try comma first; fall back to whitespace
    parts = [p.strip() for p in value.split(",")]
    if len(parts) == 1:
        parts = value.split()
    return [p for p in parts if p]


def walk_source(roots: list[Path]) -> list[FileHeader]:
    """Walk source roots and return headers for every recognized source file."""
    results: list[FileHeader] = []

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in SOURCE_EXTENSIONS:
                continue
            if any(part.startswith(".") for part in path.parts):
                continue
            if "node_modules" in path.parts or "__pycache__" in path.parts:
                continue
            results.append(header_from_file(path))

    return results


def write_tree_md(headers: list[FileHeader], output: Path) -> None:
    """Write a hierarchical tree.md (paths only)."""
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Source tree", ""]
    last_dir: str | None = None

    for header in headers:
        directory = str(Path(header.path).parent)
        if directory != last_dir:
            lines.append(f"## {directory}/")
            last_dir = directory
        lines.append(f"- {header.path}")

    output.write_text("\n".join(lines) + "\n")


def write_tree_json(headers: list[FileHeader], output: Path) -> None:
    """Write a machine-readable tree.json."""
    output.parent.mkdir(parents=True, exist_ok=True)

    data = {h.path: {} for h in headers}
    output.write_text(json.dumps(data, indent=2))


def write_detailed_md(headers: list[FileHeader], output: Path) -> None:
    """Write detailed.md with full header info per file."""
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Source tree (detailed)", ""]
    for header in headers:
        lines.append(f"## {header.path}")
        if not header.has_header:
            lines.append("- *(missing header)*")
        else:
            if header.purpose:
                lines.append(f"- @purpose: {header.purpose}")
            if header.why:
                lines.append(f"- @why: {header.why}")
            if header.role:
                lines.append(f"- @role: {header.role}")
            if header.exports:
                lines.append(f"- @exports: {', '.join(header.exports)}")
            if header.uses:
                lines.append(f"- @uses: {', '.join(header.uses)}")
            if header.stability:
                lines.append(f"- @stability: {header.stability}")
            if header.gotchas:
                lines.append(f"- @gotchas: {header.gotchas}")
        lines.append("")

    output.write_text("\n".join(lines))


def write_detailed_json(headers: list[FileHeader], output: Path) -> None:
    """Write detailed.json (machine version of detailed.md)."""
    output.parent.mkdir(parents=True, exist_ok=True)

    data = {h.path: asdict(h) for h in headers}
    # Drop the path field from the inner dicts (it's the key)
    for inner in data.values():
        inner.pop("path", None)

    output.write_text(json.dumps(data, indent=2))


def count_missing_headers(headers: list[FileHeader]) -> int:
    return sum(1 for h in headers if not h.has_header)
