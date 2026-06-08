"""Scan progress dialog with live log."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class ProgressDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scanning…")
        self.setModal(False)
        self.resize(640, 360)

        self._start_time = time.monotonic()
        self._file_count = 0

        self.status_label = QLabel("Preparing scan…")
        self.count_label = QLabel("Files: 0")
        self.elapsed_label = QLabel("Elapsed: 0s")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.log = QListWidget()
        self.cancel_btn = QPushButton("Cancel")

        top = QHBoxLayout()
        top.addWidget(self.count_label)
        top.addStretch()
        top.addWidget(self.elapsed_label)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addLayout(top)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.cancel_btn.clicked.connect(self.reject)

    def update_progress(self, path: str, file_count: int) -> None:
        self._file_count = file_count
        self.status_label.setText(path)
        self.count_label.setText(f"Files: {file_count}")
        elapsed = int(time.monotonic() - self._start_time)
        self.elapsed_label.setText(f"Elapsed: {elapsed}s")
        self.log.insertItem(0, path)
        if self.log.count() > 200:
            self.log.takeItem(self.log.count() - 1)

    def add_project(self, project_id: str) -> None:
        self.log.insertItem(0, f"[project] {project_id}")

    def finish(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.cancel_btn.setText("Close")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)
