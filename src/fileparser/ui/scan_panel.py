"""Scan configuration panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fileparser.schema import FolderTemplate, list_templates


class ScanPanel(QGroupBox):
    scan_requested = Signal(str, str)
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Scan configuration", parent)
        self._scanning = False

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select project server root folder…")
        self.browse_btn = QPushButton("Browse…")
        self.team_combo = QComboBox()
        self.start_btn = QPushButton("Start scan")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, stretch=1)
        path_row.addWidget(self.browse_btn)

        team_row = QHBoxLayout()
        team_row.addWidget(QLabel("Design team template:"))
        team_row.addWidget(self.team_combo, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.cancel_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(path_row)
        layout.addLayout(team_row)
        layout.addLayout(btn_row)

        self.browse_btn.clicked.connect(self._browse)
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)

        self.reload_templates()

    def reload_templates(self) -> None:
        self.team_combo.clear()
        for template in list_templates():
            self.team_combo.addItem(template.team, template.team)

    def set_scan_root(self, path: str) -> None:
        self.path_edit.setText(path)

    def scan_root(self) -> str:
        return self.path_edit.text().strip()

    def selected_team(self) -> str:
        return str(self.team_combo.currentData() or self.team_combo.currentText())

    def set_scanning(self, scanning: bool) -> None:
        self._scanning = scanning
        self.start_btn.setEnabled(not scanning)
        self.cancel_btn.setEnabled(scanning)
        self.browse_btn.setEnabled(not scanning)
        self.path_edit.setEnabled(not scanning)
        self.team_combo.setEnabled(not scanning)

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select scan root")
        if directory:
            self.path_edit.setText(directory)

    def _start(self) -> None:
        root = self.scan_root()
        if not root:
            return
        if not Path(root).exists():
            return
        self.scan_requested.emit(root, self.selected_team())
