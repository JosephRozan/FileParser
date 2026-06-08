"""Folder structure detail tree for a selected project."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGroupBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout

from fileparser.models import ProjectReport
from fileparser.schema import get_template

COLOR_OK = QColor("#2e7d32")
COLOR_MISSING = QColor("#c62828")
COLOR_EMPTY = QColor("#f9a825")
COLOR_UNEXPECTED = QColor("#1565c0")


class DetailPanel(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__("Project detail", parent)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Folder", "Status"])
        self.tree.setAlternatingRowColors(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)

    def clear(self) -> None:
        self.tree.clear()

    def show_project(self, project: ProjectReport | None) -> None:
        self.tree.clear()
        if project is None:
            return

        self.setTitle(f"Project detail — {project.project_id}")

        try:
            template = get_template(project.team)
            expected_paths = {f.path.replace("\\", "/") for f in template.expected_folders}
            required_paths = {
                f.path.replace("\\", "/")
                for f in template.expected_folders
                if f.required
            }
        except FileNotFoundError:
            expected_paths = set()
            required_paths = set()

        empty_set = set(project.empty_folders)
        missing_set = set(project.missing_folders)
        present_set = set(project.present_folders)
        unexpected_set = set(project.unexpected_folders)

        all_paths = sorted(
            expected_paths | present_set | missing_set,
            key=lambda p: p.lower(),
        )

        nodes: dict[str, QTreeWidgetItem] = {}

        def ensure_node(path: str) -> QTreeWidgetItem:
            if path in nodes:
                return nodes[path]
            parent_path = "/".join(path.split("/")[:-1])
            if parent_path:
                parent_item = ensure_node(parent_path)
            else:
                parent_item = self.tree.invisibleRootItem()
            item = QTreeWidgetItem([path.split("/")[-1], ""])
            parent_item.addChild(item)
            nodes[path] = item
            return item

        for path in all_paths:
            item = ensure_node(path)
            if path in missing_set:
                status = "Missing (required)"
                color = COLOR_MISSING
            elif path in empty_set:
                status = "Empty"
                color = COLOR_EMPTY
            elif path in unexpected_set:
                status = "Unexpected"
                color = COLOR_UNEXPECTED
            elif path in present_set:
                status = "Present"
                color = COLOR_OK
            elif path in expected_paths:
                status = "Expected"
                color = COLOR_OK
            else:
                status = "Optional missing"
                color = COLOR_EMPTY if path not in required_paths else COLOR_MISSING

            item.setText(1, status)
            item.setForeground(0, color)
            item.setForeground(1, color)

        self.tree.expandToDepth(1)
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
