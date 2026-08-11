from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .sanitize import sanitize_text


DEFAULT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".jsonl", ".yaml", ".yml",
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".kts",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".go", ".rs", ".swift", ".html", ".css", ".xml",
}

SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__"}


@dataclass(frozen=True)
class BatchItem:
    path: str
    changed: bool
    finding_count_before: int
    finding_count_after: int
    change_count: int
    output_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "changed": self.changed,
            "finding_count_before": self.finding_count_before,
            "finding_count_after": self.finding_count_after,
            "change_count": self.change_count,
            "output_path": self.output_path,
            "error": self.error,
        }


def iter_text_files(root: Path, extensions: set[str] | None = None) -> Iterable[Path]:
    allowed = {ext.lower() for ext in (extensions or DEFAULT_EXTENSIONS)}
    if root.is_file():
        if root.suffix.lower() in allowed or not root.suffix:
            yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in allowed:
            yield path


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def process_path(
    root: Path,
    *,
    output_dir: Path | None = None,
    in_place: bool = False,
    dry_run: bool = False,
    profile: str = "conservative",
    normalization: str = "NFC",
    extensions: set[str] | None = None,
) -> dict[str, Any]:
    if in_place and output_dir is not None:
        raise ValueError("in_place and output_dir are mutually exclusive")
    if not root.exists():
        raise FileNotFoundError(root)

    items: list[BatchItem] = []
    base = root.parent if root.is_file() else root

    # Snapshot inputs before any writes so an output directory nested beneath the
    # input root can never feed generated files back into the same batch run.
    paths = list(iter_text_files(root, extensions))
    if output_dir is not None and root.is_dir() and _is_within(output_dir, root):
        paths = [path for path in paths if not _is_within(path, output_dir)]

    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
            result = sanitize_text(source, profile=profile, normalization=normalization)
            destination: Path | None = None
            if result.changed and not dry_run:
                if in_place:
                    destination = path
                elif output_dir is not None:
                    destination = output_dir / path.relative_to(base)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                if destination is not None:
                    destination.write_text(result.text, encoding="utf-8")

            items.append(
                BatchItem(
                    path=str(path),
                    changed=result.changed,
                    finding_count_before=int(result.before["finding_count"]),
                    finding_count_after=int(result.after["finding_count"]),
                    change_count=result.change_count,
                    output_path=str(destination) if destination else None,
                )
            )
        except (UnicodeDecodeError, OSError) as exc:
            items.append(BatchItem(str(path), False, 0, 0, 0, error=str(exc)))

    return {
        "root": str(root),
        "profile": profile,
        "normalization": normalization,
        "dry_run": dry_run,
        "in_place": in_place,
        "file_count": len(items),
        "changed_count": sum(item.changed for item in items),
        "error_count": sum(item.error is not None for item in items),
        "finding_count_before": sum(item.finding_count_before for item in items),
        "finding_count_after": sum(item.finding_count_after for item in items),
        "items": [item.to_dict() for item in items],
    }
