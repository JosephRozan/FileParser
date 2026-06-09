"""Scan configuration panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
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

from fileparser.scan_history import ScanHistoryEntry


class ScanPanel(QGroupBox):
    scan_requested = Signal(str)
    cancel_requested = Signal()
    output_path_changed = Signal(str)
    scan_root_changed = Signal(str)
    saved_scan_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Scan configuration", parent)
        self._scanning = False

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select project server root folder…")
        self.browse_btn = QPushButton("Browse…")

        self.history_combo = QComboBox()
        self.history_combo.setPlaceholderText("Load a saved scan…")
        self.history_combo.setToolTip(
            "Previously saved scans for this root path. Pick one to reload without scanning again."
        )

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Select output folder for stored files…")
        self.output_browse_btn = QPushButton("Browse…")

        self.start_btn = QPushButton("Start scan")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)

        scan_row = QHBoxLayout()
        scan_row.addWidget(QLabel("Scan root:"))
        scan_row.addWidget(self.path_edit, stretch=1)
        scan_row.addWidget(self.browse_btn)

        history_row = QHBoxLayout()
        history_row.addWidget(QLabel("Saved scans:"))
        history_row.addWidget(self.history_combo, stretch=1)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        output_row.addWidget(self.output_edit, stretch=1)
        output_row.addWidget(self.output_browse_btn)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.cancel_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        layout.addLayout(scan_row)
        layout.addLayout(history_row)
        layout.addLayout(output_row)
        layout.addLayout(btn_row)

        self.browse_btn.clicked.connect(self._browse_scan_root)
        self.output_browse_btn.clicked.connect(self._browse_output)
        self.output_edit.editingFinished.connect(self._emit_output_path)
        self.path_edit.editingFinished.connect(self._emit_scan_root_changed)
        self.history_combo.currentIndexChanged.connect(self._on_history_selected)
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)

    def set_scan_root(self, path: str) -> None:
        self.path_edit.setText(path)

    def set_output_path(self, path: str) -> None:
        self.output_edit.setText(path)

    def scan_root(self) -> str:
        return self.path_edit.text().strip()

    def output_path(self) -> str:
        return self.output_edit.text().strip()

    def set_history_entries(
        self,
        entries: list[ScanHistoryEntry],
        *,
        select_id: str | None = None,
    ) -> None:
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItem("— Load a saved scan —", "")
        for entry in entries:
            index = self.history_combo.count()
            self.history_combo.addItem(entry.label(), entry.id)
            self.history_combo.setItemData(
                index,
                entry.scan_root,
                Qt.ItemDataRole.ToolTipRole,
            )
        if select_id:
            index = self.history_combo.findData(select_id)
            if index >= 0:
                self.history_combo.setCurrentIndex(index)
        else:
            self.history_combo.setCurrentIndex(0)
        self.history_combo.blockSignals(False)

    def set_scanning(self, scanning: bool) -> None:
        self._scanning = scanning
        self.start_btn.setEnabled(not scanning)
        self.cancel_btn.setEnabled(scanning)
        self.browse_btn.setEnabled(not scanning)
        self.path_edit.setEnabled(not scanning)
        self.history_combo.setEnabled(not scanning)
        self.output_browse_btn.setEnabled(not scanning)
        self.output_edit.setEnabled(not scanning)

    def _emit_output_path(self) -> None:
        self.output_path_changed.emit(self.output_path())

    def _emit_scan_root_changed(self) -> None:
        self.scan_root_changed.emit(self.scan_root())

    def _browse_scan_root(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select scan root")
        if directory:
            self.path_edit.setText(directory)
            self.scan_root_changed.emit(directory)

    def _browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select output folder")
        if directory:
            self.output_edit.setText(directory)
            self.output_path_changed.emit(directory)

    def _on_history_selected(self, index: int) -> None:
        if index <= 0:
            return
        entry_id = self.history_combo.itemData(index)
        if entry_id:
            self.saved_scan_selected.emit(str(entry_id))

    def _start(self) -> None:
        root = self.scan_root()
        if not root:
            return
        if not Path(root).exists():
            return
        self.scan_requested.emit(root)
