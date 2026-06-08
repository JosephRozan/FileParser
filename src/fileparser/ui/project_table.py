"""Sortable project summary table with filtering."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fileparser.models import ComplianceStatus, ProjectReport, ScanResult

STATUS_COLORS = {
    ComplianceStatus.COMPLIANT: QColor("#2e7d32"),
    ComplianceStatus.PARTIAL: QColor("#f9a825"),
    ComplianceStatus.EMPTY: QColor("#c62828"),
    ComplianceStatus.ERROR: QColor("#6d4c41"),
}


class ProjectTable(QWidget):
    project_selected = Signal(object)
    project_activated = Signal(object)

    COLUMNS = [
        "Project",
        "Team",
        "Status",
        "Compliance %",
        "Files",
        "Empty",
        "Missing",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._projects: list[ProjectReport] = []
        self._filtered: list[ProjectReport] = []

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by project name or status…")
        self.summary_label = QLabel("No scan results yet.")
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.filter_edit)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table)

        self.filter_edit.textChanged.connect(self._apply_filter)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.itemDoubleClicked.connect(self._on_double_click)

    def set_result(self, result: ScanResult | None) -> None:
        self._projects = list(result.projects) if result else []
        self._update_summary(result)
        self._apply_filter()

    def _update_summary(self, result: ScanResult | None) -> None:
        if not result:
            self.summary_label.setText("No scan results yet.")
            return
        s = result.summary
        self.summary_label.setText(
            f"Projects: {s['total_projects']} | "
            f"Compliant: {s.get('compliant', 0)} | "
            f"Partial: {s.get('partial', 0)} | "
            f"Empty: {s.get('empty', 0)} | "
            f"Errors: {s.get('error', 0)} | "
            f"Files: {result.total_files}"
        )

    def _apply_filter(self) -> None:
        query = self.filter_edit.text().strip().lower()
        if not query:
            self._filtered = list(self._projects)
        else:
            self._filtered = [
                p
                for p in self._projects
                if query in p.project_id.lower()
                or query in p.status.value.lower()
            ]
        self._populate_table()

    def _populate_table(self) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._filtered))
        for row, project in enumerate(self._filtered):
            compliance_pct = f"{project.compliance_score * 100:.0f}%"
            values = [
                project.project_id,
                project.team,
                project.status.value,
                compliance_pct,
                str(project.file_count),
                str(len(project.empty_folders)),
                str(len(project.missing_folders)),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (3, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 2:
                    color = STATUS_COLORS.get(project.status)
                    if color:
                        item.setForeground(color)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, project)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def _project_at_row(self, row: int) -> ProjectReport | None:
        item = self.table.item(row, 0)
        if item is None:
            return None
        project = item.data(Qt.ItemDataRole.UserRole)
        return project if isinstance(project, ProjectReport) else None

    def _on_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        project = self._project_at_row(rows[0].row())
        if project:
            self.project_selected.emit(project)

    def _on_double_click(self, _item: QTableWidgetItem) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        project = self._project_at_row(rows[0].row())
        if project:
            self.project_activated.emit(project)
