"""Background scan worker for non-blocking UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from fileparser.analyzer import analyze_scan
from fileparser.models import ScanResult
from fileparser.scanner import ScanConfig, Scanner


class ScanWorker(QObject):
    progress = Signal(str, int)
    phase = Signal(str)
    project_found = Signal(str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        root: Path,
        project_root_depth: int,
        allowed_extensions: list[str],
        ignore_patterns: list[str],
        max_depth: int | None = None,
        follow_symlinks: bool = False,
    ) -> None:
        super().__init__()
        self.root = root
        self.project_root_depth = project_root_depth
        self.allowed_extensions = allowed_extensions
        self.ignore_patterns = ignore_patterns
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            config = ScanConfig(
                root=self.root,
                project_root_depth=self.project_root_depth,
                ignore_patterns=self.ignore_patterns,
                max_depth=self.max_depth,
                follow_symlinks=self.follow_symlinks,
            )
            scanner = Scanner(
                config,
                on_progress=lambda path, count: self.progress.emit(path, count),
                on_project_found=lambda project_id: self.project_found.emit(project_id),
                should_cancel=lambda: self._cancelled,
            )
            files, directories, errors = scanner.scan()
            if self._cancelled:
                return
            result = analyze_scan(
                self.root,
                files,
                project_root_depth=self.project_root_depth,
                allowed_extensions=self.allowed_extensions,
                scan_errors=errors,
                scan_directories=directories,
                on_progress=self.phase.emit,
                should_cancel=lambda: self._cancelled,
            )
            if self._cancelled:
                return
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 — surface to UI
            self.error.emit(str(exc))
