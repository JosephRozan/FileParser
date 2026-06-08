"""Main application window."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QWidget,
)

from fileparser.models import ScanResult
from fileparser.reporter import export_reports
from fileparser.schema import get_template
from fileparser.settings import Settings
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
        self._result: ScanResult | None = None
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._progress: ProgressDialog | None = None

        self.scan_panel = ScanPanel()
        self.project_table = ProjectTable()
        self.detail_panel = DetailPanel()

        splitter = QSplitter()
        splitter.addWidget(self.project_table)
        splitter.addWidget(self.detail_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        central = QWidget()
        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(central)
        layout.addWidget(self.scan_panel)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self._build_menu()
        self.setStatusBar(QStatusBar())

        if self.settings.last_scan_root:
            self.scan_panel.set_scan_root(self.settings.last_scan_root)
        team_index = self.scan_panel.team_combo.findData(self.settings.default_team)
        if team_index >= 0:
            self.scan_panel.team_combo.setCurrentIndex(team_index)

        self.scan_panel.scan_requested.connect(self._start_scan)
        self.scan_panel.cancel_requested.connect(self._cancel_scan)
        self.project_table.project_selected.connect(self.detail_panel.show_project)
        self.project_table.project_activated.connect(self.detail_panel.show_project)

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("File")
        export_action = menu.addAction("Export reports…")
        export_action.triggered.connect(self._export)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

    def _start_scan(self, root: str, team: str) -> None:
        if not Path(root).exists():
            QMessageBox.warning(self, "Invalid path", f"Path does not exist:\n{root}")
            return

        template = get_template(team)
        self.settings.last_scan_root = root
        self.settings.default_team = team
        self.settings.save()

        self.scan_panel.set_scanning(True)
        self.statusBar().showMessage(f"Scanning {root}…")

        self._progress = ProgressDialog(self)
        self._progress.show()

        self._thread = QThread()
        self._worker = ScanWorker(
            root=Path(root),
            template=template,
            ignore_patterns=self.settings.ignore_patterns,
            max_depth=self.settings.max_depth,
            follow_symlinks=self.settings.follow_symlinks,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.project_found.connect(self._on_project_found)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._progress.rejected.connect(self._cancel_scan)
        self._thread.start()

    def _on_progress(self, path: str, count: int) -> None:
        if self._progress:
            self._progress.update_progress(path, count)

    def _on_project_found(self, project_id: str) -> None:
        if self._progress:
            self._progress.add_project(project_id)

    def _on_finished(self, result: object) -> None:
        if not isinstance(result, ScanResult):
            return
        self._result = result
        self.project_table.set_result(result)
        self.detail_panel.clear()
        self.scan_panel.set_scanning(False)
        if self._progress:
            self._progress.finish()
        summary = result.summary
        self.statusBar().showMessage(
            f"Scan complete — {summary['total_projects']} projects, "
            f"{result.total_files} files"
        )

    def _on_error(self, message: str) -> None:
        self.scan_panel.set_scanning(False)
        if self._progress:
            self._progress.finish()
        QMessageBox.critical(self, "Scan failed", message)
        self.statusBar().showMessage("Scan failed")

    def _cancel_scan(self) -> None:
        if self._worker:
            self._worker.cancel()

    def _cleanup_thread(self) -> None:
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None

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
