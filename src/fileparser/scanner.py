"""Recursive filesystem scanner with progress callbacks."""

from __future__ import annotations

import fnmatch
import os
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from fileparser.models import FileEntry


ProgressCallback = Callable[[str, int], None]
ProjectFoundCallback = Callable[[str], None]
CancelCallback = Callable[[], bool]


@dataclass
class ScanConfig:
    root: Path
    project_root_depth: int = 1
    ignore_patterns: list[str] = field(default_factory=list)
    max_depth: int | None = None
    follow_symlinks: bool = False


def _should_ignore(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _infer_project_id(relative: Path, depth: int) -> str:
    parts = relative.parts
    if not parts:
        return ""
    index = min(depth - 1, len(parts) - 1)
    return parts[index]


class Scanner:
    def __init__(
        self,
        config: ScanConfig,
        on_progress: ProgressCallback | None = None,
        on_project_found: ProjectFoundCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> None:
        self.config = config
        self.on_progress = on_progress
        self.on_project_found = on_project_found
        self.should_cancel = should_cancel
        self.files: list[FileEntry] = []
        self.directories: set[str] = set()
        self.errors: list[str] = []
        self._seen_projects: set[str] = set()
        self._file_count = 0

    def scan(self) -> tuple[list[FileEntry], set[str], list[str]]:
        root = self.config.root.resolve()
        if not root.exists():
            raise FileNotFoundError(f"Scan root does not exist: {root}")

        self._walk(root, root, depth=0)
        return self.files, self.directories, self.errors

    def _walk(self, root: Path, current: Path, depth: int) -> None:
        if self.should_cancel and self.should_cancel():
            return

        rel = current.relative_to(root)
        rel_posix = rel.as_posix()
        if rel_posix:
            self.directories.add(rel_posix)

        if self.config.max_depth is not None and depth > self.config.max_depth:
            return

        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except PermissionError as exc:
            self.errors.append(f"Permission denied: {current} ({exc})")
            return
        except OSError as exc:
            self.errors.append(f"Cannot read directory: {current} ({exc})")
            return

        for entry in entries:
            if self.should_cancel and self.should_cancel():
                return

            if _should_ignore(entry.name, self.config.ignore_patterns):
                continue

            if entry.is_symlink() and not self.config.follow_symlinks:
                continue

            try:
                is_dir = entry.is_dir()
            except OSError as exc:
                self.errors.append(f"Cannot stat: {entry} ({exc})")
                continue

            if is_dir:
                self._walk(root, entry, depth + 1)
            else:
                self._record_file(root, entry)

    def _record_file(self, root: Path, path: Path) -> None:
        relative = path.relative_to(root)
        project_id = _infer_project_id(relative, self.config.project_root_depth)
        if project_id and project_id not in self._seen_projects:
            self._seen_projects.add(project_id)
            if self.on_project_found:
                self.on_project_found(project_id)

        try:
            stat = path.stat()
        except OSError as exc:
            self.errors.append(f"Cannot stat file: {path} ({exc})")
            return

        entry = FileEntry(
            relative_path=relative.as_posix(),
            absolute_path=str(path.resolve()),
            size=stat.st_size,
            extension=path.suffix.lower(),
            mtime=stat.st_mtime,
            project_id=project_id,
        )
        self.files.append(entry)
        self._file_count += 1

        parent = relative.parent
        parts: list[str] = []
        for part in parent.parts:
            parts.append(part)
            self.directories.add("/".join(parts))

        if self.on_progress:
            self.on_progress(entry.relative_path, self._file_count)


def group_files_by_project(files: list[FileEntry]) -> dict[str, list[FileEntry]]:
    grouped: dict[str, list[FileEntry]] = defaultdict(list)
    for file_entry in files:
        if file_entry.project_id:
            grouped[file_entry.project_id].append(file_entry)
    return dict(grouped)


def discover_projects(root: Path, project_root_depth: int = 1) -> list[str]:
    """List top-level project folders without a full recursive scan."""
    if not root.exists():
        return []
    projects: list[str] = []
    if project_root_depth == 1:
        try:
            for entry in sorted(root.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    projects.append(entry.name)
        except OSError:
            pass
    return projects


def list_all_directories(root: Path, ignore_patterns: list[str] | None = None) -> set[str]:
    """Collect all directory paths under root (relative posix paths)."""
    ignore_patterns = ignore_patterns or []
    directories: set[str] = set()

    for dirpath, dirnames, _filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if not name.startswith(".") and not _should_ignore(name, ignore_patterns)
        ]
        rel = current.relative_to(root)
        rel_posix = rel.as_posix()
        if rel_posix:
            directories.add(rel_posix)
        for name in dirnames:
            child = (rel / name).as_posix() if rel_posix else name
            directories.add(child)

    return directories
