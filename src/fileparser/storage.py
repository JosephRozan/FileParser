"""Copy selected project files to an output folder."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CopyResult:
    copied: int = 0
    skipped: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def _unique_filename(source: Path, used_names: set[str]) -> str:
    """Pick a flat filename; disambiguate duplicates within the same store batch."""
    name = source.name
    if name not in used_names:
        used_names.add(name)
        return name

    stem = source.stem
    suffix = source.suffix
    counter = 1
    while True:
        candidate = f"{stem} ({counter}){suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1


def copy_files_to_output(output_root: Path, files: list[Path]) -> CopyResult:
    """Copy files directly into output_root (no subfolders)."""
    result = CopyResult()
    output_root.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()

    for source in files:
        if not source.is_file():
            result.skipped += 1
            result.errors.append(f"Not found: {source}")
            continue
        dest_name = _unique_filename(source, used_names)
        destination = output_root / dest_name
        try:
            shutil.copy2(source, destination)
            result.copied += 1
        except OSError as exc:
            result.skipped += 1
            result.errors.append(f"{source} → {destination}: {exc}")

    return result
