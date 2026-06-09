"""Main application window."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QWidget,
)

from fileparser.models import ScanResult
from fileparser.reporter import export_reports
from fileparser.scan_history import ScanHistoryStore
from fileparser.settings import Settings
from fileparser.storage import copy_files_to_output
from fileparser.ui.detail_panel import DetailPanel
from fileparser.ui.progress_dialog import ProgressDialog
from fileparser.ui.project_table import ProjectTable
from fileparser.ui.scan_panel import ScanPanel
from fileparser.ui.workers import ScanWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FileParser — Wilmotte")
        self.resize(1100, 700)

        self.settings = Settings.load()
        self._history = ScanHistoryStore()
        self._result: ScanResult | None = None
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._progress: ProgressDialog | None = None
        self._scan_active = False

        self.scan_panel = ScanPanel()
        self.project_table = ProjectTable()
        self.detail_panel = DetailPanel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.project_table)
        splitter.addWidget(self.detail_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([320, 680])

        self.scan_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum,
        )

        central = QWidget()
        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(central)
        layout.setSpacing(6)
        layout.addWidget(self.scan_panel, 0)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self._build_menu()
        self.setStatusBar(QStatusBar())

        if self.settings.last_scan_root:
            self.scan_panel.set_scan_root(self.settings.last_scan_root)
        if self.settings.last_output_path:
            self.scan_panel.set_output_path(self.settings.last_output_path)

        self.scan_panel.scan_requested.connect(self._start_scan)
        self.scan_panel.cancel_requested.connect(self._cancel_scan)
        self.scan_panel.output_path_changed.connect(self._save_output_path)
        self.scan_panel.scan_root_changed.connect(self._refresh_scan_history)
        self.scan_panel.saved_scan_selected.connect(self._load_saved_scan)
        self.project_table.project_selected.connect(self.detail_panel.show_project)
        self.project_table.project_activated.connect(self.detail_panel.show_project)
        self.detail_panel.store_requested.connect(self._store_selected_files)

        self._refresh_scan_history()
        self._try_load_latest_saved_scan()

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("File")
        export_action = menu.addAction("Export reports…")
        export_action.triggered.connect(self._export)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

    def _start_scan(self, root: str) -> None:
        if not Path(root).exists():
            QMessageBox.warning(self, "Invalid path", f"Path does not exist:\n{root}")
            return
        if self._thread and self._thread.isRunning():
            QMessageBox.warning(
                self,
                "Scan in progress",
                "A scan is already running. Wait for it to finish or cancel it first.",
            )
            return

        self.settings.last_scan_root = root
        self.settings.save()

        self._scan_active = True
        self.scan_panel.set_scanning(True)
        self.statusBar().showMessage(f"Scanning {root}…")

        self._progress = ProgressDialog(self)
        self._progress.finished.connect(self._on_progress_dialog_finished)
        self._progress.show()

        self._thread = QThread(self)
        self._worker = ScanWorker(
            root=Path(root),
            project_root_depth=self.settings.project_root_depth,
            allowed_extensions=self.settings.allowed_extensions,
            ignore_patterns=self.settings.ignore_patterns,
            max_depth=self.settings.max_depth,
            follow_symlinks=self.settings.follow_symlinks,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        queued = Qt.ConnectionType.QueuedConnection
        self._worker.progress.connect(self._on_progress, queued)
        self._worker.phase.connect(self._on_phase, queued)
        self._worker.project_found.connect(self._on_project_found, queued)
        self._worker.finished.connect(self._on_finished, queued)
        self._worker.error.connect(self._on_error, queued)
        self._worker.finished.connect(self._thread.quit, queued)
        self._worker.error.connect(self._thread.quit, queued)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_progress(self, path: str, count: int) -> None:
        if self._progress:
            self._progress.update_progress(path, count)

    def _on_phase(self, message: str) -> None:
        if self._progress:
            self._progress.set_phase(message)

    def _on_project_found(self, project_id: str) -> None:
        if self._progress:
            self._progress.add_project(project_id)

    def _on_finished(self, result: object) -> None:
        if not isinstance(result, ScanResult):
            return
        self._scan_active = False
        self.scan_panel.set_scanning(False)
        self._dismiss_progress(completed=True)

        try:
            entry = self._history.save(result)
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Could not save scan",
                f"The scan finished but could not be saved to history.\n\n{exc}",
            )
            self._apply_scan_result(result, status_prefix="Scan complete (not saved)")
        else:
            self._apply_scan_result(
                result,
                entry_id=entry.id,
                status_prefix="Scan complete",
                saved_to_history=True,
            )

        self.raise_()
        self.activateWindow()

    def _on_error(self, message: str) -> None:
        self._scan_active = False
        self.scan_panel.set_scanning(False)
        self._dismiss_progress(completed=True)
        QMessageBox.critical(self, "Scan failed", message)
        self.statusBar().showMessage("Scan failed")

    def _on_progress_dialog_finished(self, result: int) -> None:
        cancelled = result == QDialog.DialogCode.Rejected
        self._progress = None
        if not self._scan_active:
            return
        if cancelled:
            self._cancel_scan()
            self._scan_active = False
            self.scan_panel.set_scanning(False)
            self.statusBar().showMessage("Scan cancelled")

    def _cancel_scan(self) -> None:
        if self._worker:
            self._worker.cancel()

    def _dismiss_progress(self, *, completed: bool) -> None:
        if not self._progress:
            return
        dialog = self._progress
        self._progress = None
        dialog.blockSignals(True)
        if completed:
            dialog.finish()
        dialog.setVisible(False)
        dialog.deleteLater()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread and self._thread.isRunning():
            self._cancel_scan()
            self._thread.quit()
            self._thread.wait(10_000)
        self._dismiss_progress(completed=False)
        super().closeEvent(event)

    def _cleanup_thread(self) -> None:
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None

    def _apply_scan_result(
        self,
        result: ScanResult,
        *,
        entry_id: str | None = None,
        status_prefix: str = "Loaded saved scan",
        saved_to_history: bool = False,
    ) -> None:
        self._result = result
        self.project_table.set_result(result)
        self.detail_panel.clear()
        summary = result.summary
        message = (
            f"{status_prefix} — {summary['total_projects']} projects, "
            f"{result.total_files} files"
        )
        if saved_to_history:
            message += f" — saved to {self._history.storage_dir()}"
        self.statusBar().showMessage(message)
        self._refresh_scan_history(select_id=entry_id)

    def _refresh_scan_history(self, *, select_id: str | None = None) -> None:
        self._history.reload()
        self.scan_panel.set_history_entries(self._history.entries, select_id=select_id)

    def _try_load_latest_saved_scan(self) -> None:
        root = self.scan_panel.scan_root()
        if not root:
            return
        entry = self._history.latest_for_root(root)
        if not entry:
            return
        result = self._history.load(entry.id)
        if result:
            self._apply_scan_result(result, entry_id=entry.id)

    def _load_saved_scan(self, entry_id: str) -> None:
        if self._thread and self._thread.isRunning():
            QMessageBox.warning(
                self,
                "Scan in progress",
                "Wait for the current scan to finish before loading a saved scan.",
            )
            self._refresh_scan_history()
            return

        result = self._history.load(entry_id)
        if not result:
            QMessageBox.warning(
                self,
                "Saved scan not found",
                "That saved scan could not be loaded. It may have been removed.",
            )
            self._refresh_scan_history()
            return

        self.scan_panel.set_scan_root(result.scan_root)
        self.settings.last_scan_root = result.scan_root
        self.settings.save()
        self._apply_scan_result(result, entry_id=entry_id)

    def _save_output_path(self, path: str) -> None:
        self.settings.last_output_path = path
        self.settings.save()

    def _store_selected_files(self) -> None:
        project = self.detail_panel.current_project()
        if not project:
            QMessageBox.information(self, "Store files", "Select a project first.")
            return

        output = self.scan_panel.output_path()
        if not output:
            QMessageBox.warning(
                self,
                "Output folder required",
                "Choose an output folder under Scan configuration before storing files.",
            )
            return

        output_dir = Path(output)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Cannot create output folder",
                f"Could not create:\n{output_dir}\n\n{exc}",
            )
            return

        selected = self.detail_panel.selected_files()
        if not selected:
            QMessageBox.information(
                self,
                "No files selected",
                "Tick the Select checkboxes on files you want to copy.",
            )
            return

        self.settings.last_output_path = output
        self.settings.save()

        result = copy_files_to_output(output_dir, selected)
        message = f"Copied {result.copied} file(s) to:\n{output_dir}"
        if result.skipped:
            message += f"\n\nSkipped {result.skipped} file(s)."
        if result.errors:
            preview = "\n".join(result.errors[:5])
            if len(result.errors) > 5:
                preview += f"\n… and {len(result.errors) - 5} more"
            message += f"\n\nIssues:\n{preview}"

        QMessageBox.information(self, "Store complete", message)
        self.statusBar().showMessage(
            f"Stored {result.copied} file(s) in {output_dir}"
        )

    def _export(self) -> None:
        if not self._result:
            QMessageBox.information(self, "Export", "Run a scan before exporting.")
            return
        directory = QFileDialog.getExistingDirectory(self, "Select export folder")
        if not directory:
            return
        out_dir = Path(directory)
        json_path, csv_path = export_reports(self._result, out_dir)
        reply = QMessageBox.question(
            self,
            "Export complete",
            f"Saved:\n{json_path}\n{csv_path}\n\nOpen folder in file explorer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._open_in_explorer(out_dir)

    @staticmethod
    def _open_in_explorer(path: Path) -> None:
        if sys.platform == "win32":
            subprocess.run(["explorer", str(path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
