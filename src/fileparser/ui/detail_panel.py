"""Folder structure detail tree for a selected project."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from fileparser.models import FileEntry, ProjectReport

COLOR_NOT_EMPTY = QColor("#2e7d32")
COLOR_EMPTY = QColor("#f9a825")
COLOR_FILE = QColor("#37474f")
COLOR_FILE_OPENABLE = QColor("#1565c0")

_ROLE_ABSOLUTE_PATH = Qt.ItemDataRole.UserRole
_ROLE_RELATIVE_PATH = Qt.ItemDataRole.UserRole + 1
_ROLE_FOLDER_PATH = Qt.ItemDataRole.UserRole + 2
_ROLE_LAZY_PLACEHOLDER = Qt.ItemDataRole.UserRole + 3
_COL_SELECT = 3

LAZY_FILE_THRESHOLD = 250
LAZY_ROOT_FILE_THRESHOLD = 80

OPENABLE_EXTENSIONS = frozenset({
    ".pdf",
    ".msg",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".jpe",
    ".jfif",
    ".gif",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
    ".svg",
    ".ico",
    ".heic",
    ".heif",
    ".avif",
})


def _is_openable_ext(extension: str) -> bool:
    normalized = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    return normalized in OPENABLE_EXTENSIONS


def _ancestor_folders(rel_path: str) -> list[str]:
    parent = Path(rel_path).parent.as_posix()
    if parent in {"", "."}:
        return []
    parts = parent.split("/")
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def _openable_type_label(ext: str) -> str:
    normalized = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
    if normalized == ".pdf":
        return "PDF"
    if normalized == ".msg":
        return "MSG"
    if normalized == ".xlsx":
        return "XLSX"
    return normalized.lstrip(".").upper()


def _format_openable_types(extensions: set[str]) -> str:
    if not extensions:
        return ""
    return ", ".join(sorted({_openable_type_label(ext) for ext in extensions}, key=str.lower))


def _project_relative_path(file_entry: FileEntry, project_id: str) -> str:
    """Derive project-relative path from scan data (no disk access)."""
    rel = file_entry.relative_path.replace("\\", "/")
    prefix = f"{project_id}/"
    if rel.startswith(prefix):
        return rel[len(prefix) :]
    parts = rel.split("/")
    if project_id in parts:
        idx = parts.index(project_id)
        return "/".join(parts[idx + 1 :])
    return Path(rel).name


def _parent_folder(rel_path: str) -> str:
    parent = Path(rel_path).parent.as_posix()
    return "" if parent in {"", "."} else parent


def _branch_stats(
    files: list[FileEntry], project_id: str
) -> tuple[dict[str, bool], dict[str, set[str]]]:
    has_descendants: dict[str, bool] = defaultdict(bool)
    openable_by_folder: dict[str, set[str]] = defaultdict(set)

    for file_entry in files:
        rel_path = _project_relative_path(file_entry, project_id)
        for folder in _ancestor_folders(rel_path):
            has_descendants[folder] = True
            if _is_openable_ext(file_entry.extension):
                openable_by_folder[folder].add(file_entry.extension.lower())

    return has_descendants, openable_by_folder


def _group_files_by_folder(
    files: list[FileEntry], project_id: str
) -> dict[str, list[tuple[FileEntry, str]]]:
    grouped: dict[str, list[tuple[FileEntry, str]]] = defaultdict(list)
    for file_entry in files:
        rel_path = _project_relative_path(file_entry, project_id)
        grouped[_parent_folder(rel_path)].append((file_entry, rel_path))
    return grouped


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


class DetailPanel(QGroupBox):
    store_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Project detail", parent)
        self._current_project: ProjectReport | None = None
        self._cache_key: tuple[str, int] | None = None
        self._updating_checks = False
        self._lazy_mode = False
        self._files_by_folder: dict[str, list[tuple[FileEntry, str]]] = {}
        self._loaded_folders: set[str] = set()

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Status", "Openable files", "Select"])
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.setColumnWidth(1, 130)
        self.tree.setColumnWidth(2, 110)
        self.tree.setColumnWidth(3, 52)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemExpanded.connect(self._on_item_expanded)

        self.hide_empty_cb = QCheckBox("Hide empty folders")
        self.hide_empty_cb.setToolTip("Hide folders that contain no files in their branch")
        self.hide_empty_cb.toggled.connect(self._on_hide_empty_toggled)

        self.store_btn = QPushButton("Store selected files…")
        self.store_btn.setEnabled(False)
        self.store_btn.clicked.connect(self.store_requested.emit)

        options_row = QHBoxLayout()
        options_row.addWidget(self.hide_empty_cb)
        options_row.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.store_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(options_row)
        layout.addWidget(self.tree)
        layout.addLayout(btn_row)

    def clear(self) -> None:
        self._current_project = None
        self._cache_key = None
        self._files_by_folder = {}
        self._loaded_folders = set()
        self._lazy_mode = False
        self.tree.clear()
        self.store_btn.setEnabled(False)

    def current_project(self) -> ProjectReport | None:
        return self._current_project

    def selected_files(self) -> list[Path]:
        """Return absolute paths of checked files."""
        if not self._current_project:
            return []
        selected: list[Path] = []
        for index in range(self.tree.topLevelItemCount()):
            self._collect_checked(self.tree.topLevelItem(index), selected)
        return selected

    def _collect_checked(self, item: QTreeWidgetItem, selected: list[Path]) -> None:
        absolute = item.data(0, _ROLE_ABSOLUTE_PATH)
        if absolute and item.checkState(_COL_SELECT) == Qt.CheckState.Checked:
            selected.append(Path(str(absolute)))
        for child_index in range(item.childCount()):
            self._collect_checked(item.child(child_index), selected)

    def show_project(self, project: ProjectReport | None) -> None:
        if project is None:
            self.clear()
            return

        cache_key = (
            project.project_id,
            project.file_count,
            self.hide_empty_cb.isChecked(),
        )
        if cache_key == self._cache_key:
            return

        self._cache_key = cache_key
        self._current_project = project
        self._files_by_folder = _group_files_by_folder(project.files, project.project_id)
        self._loaded_folders = set()
        self._lazy_mode = len(project.files) >= LAZY_FILE_THRESHOLD

        self.setTitle(f"Project detail — {project.project_id}")
        self.store_btn.setEnabled(True)

        self._updating_checks = True
        self.tree.blockSignals(True)
        self.tree.setUpdatesEnabled(False)
        try:
            self.tree.clear()
            self._build_folder_tree(project)
        finally:
            self.tree.setUpdatesEnabled(True)
            self.tree.blockSignals(False)
            self._updating_checks = False

        self.tree.expandToDepth(1)

    def _build_folder_tree(self, project: ProjectReport) -> None:
        all_paths = sorted(project.present_folders, key=str.lower)
        branch_has_descendants, branch_openable_types = _branch_stats(
            project.files, project.project_id
        )
        nodes: dict[str, QTreeWidgetItem] = {}

        def folder_status(path: str) -> tuple[str, QColor]:
            if branch_has_descendants.get(path):
                return "Not empty", COLOR_NOT_EMPTY
            return "Empty", COLOR_EMPTY

        def apply_folder_labels(item: QTreeWidgetItem, path: str) -> None:
            status, color = folder_status(path)
            openable_summary = _format_openable_types(branch_openable_types.get(path, set()))
            item.setText(1, status)
            item.setText(2, openable_summary)
            item.setForeground(0, color)
            item.setForeground(1, color)
            item.setForeground(2, color)
            if openable_summary:
                item.setToolTip(2, f"Openable types in this folder: {openable_summary}")

        def ensure_node(path: str) -> QTreeWidgetItem:
            if path in nodes:
                return nodes[path]
            parent_path = "/".join(path.split("/")[:-1])
            if parent_path:
                parent_item = ensure_node(parent_path)
            else:
                parent_item = self.tree.invisibleRootItem()
            item = QTreeWidgetItem([path.split("/")[-1], "", "", ""])
            item.setData(0, _ROLE_FOLDER_PATH, path)
            parent_item.addChild(item)
            nodes[path] = item
            return item

        folder_paths = set(all_paths)
        for _folder, entries in self._files_by_folder.items():
            for _entry, rel_path in entries:
                folder_paths.update(_ancestor_folders(rel_path))

        hide_empty = self.hide_empty_cb.isChecked()
        for path in sorted(folder_paths, key=str.lower):
            if hide_empty and not branch_has_descendants.get(path):
                continue
            item = ensure_node(path)
            apply_folder_labels(item, path)
            self._attach_folder_files(item, path)

        root_files = self._files_by_folder.get("", [])
        if not root_files:
            return

        if self._lazy_mode and len(root_files) > LAZY_ROOT_FILE_THRESHOLD:
            root_item = QTreeWidgetItem([f"(root files)", f"{len(root_files)} files", "", ""])
            root_item.setData(0, _ROLE_FOLDER_PATH, "")
            self.tree.addTopLevelItem(root_item)
            self._add_lazy_placeholder(root_item, len(root_files))
        elif self._lazy_mode:
            for file_entry, rel_path in sorted(root_files, key=lambda pair: pair[1].lower()):
                self._append_file_item(self.tree.invisibleRootItem(), file_entry, rel_path)
            self._loaded_folders.add("")
        else:
            for file_entry, rel_path in sorted(root_files, key=lambda pair: pair[1].lower()):
                self._append_file_item(self.tree.invisibleRootItem(), file_entry, rel_path)

    def _attach_folder_files(self, folder_item: QTreeWidgetItem, folder_path: str) -> None:
        entries = self._files_by_folder.get(folder_path, [])
        if not entries:
            return
        if self._lazy_mode:
            self._add_lazy_placeholder(folder_item, len(entries))
            return
        for file_entry, rel_path in sorted(entries, key=lambda pair: pair[1].lower()):
            self._append_file_item(folder_item, file_entry, rel_path)
        self._loaded_folders.add(folder_path)

    def _add_lazy_placeholder(self, folder_item: QTreeWidgetItem, file_count: int) -> None:
        placeholder = QTreeWidgetItem([f"Expand to list {file_count} file(s)…", "", "", ""])
        placeholder.setData(0, _ROLE_LAZY_PLACEHOLDER, True)
        placeholder.setFlags(Qt.ItemFlag.ItemIsEnabled)
        folder_item.addChild(placeholder)

    def _load_folder_files(self, folder_item: QTreeWidgetItem, folder_path: str) -> None:
        if folder_path in self._loaded_folders:
            return

        self._updating_checks = True
        self.tree.blockSignals(True)
        try:
            to_remove: list[QTreeWidgetItem] = []
            for index in range(folder_item.childCount()):
                child = folder_item.child(index)
                if child.data(0, _ROLE_LAZY_PLACEHOLDER):
                    to_remove.append(child)
            for child in to_remove:
                folder_item.removeChild(child)

            for file_entry, rel_path in sorted(
                self._files_by_folder.get(folder_path, []),
                key=lambda pair: pair[1].lower(),
            ):
                self._append_file_item(folder_item, file_entry, rel_path)
            self._loaded_folders.add(folder_path)
        finally:
            self.tree.blockSignals(False)
            self._updating_checks = False

    def _append_file_item(
        self,
        parent_item: QTreeWidgetItem,
        file_entry: FileEntry,
        rel_path: str,
    ) -> None:
        name = Path(rel_path).name
        ext = file_entry.extension or "(no ext)"
        status = f"{ext} · {_format_size(file_entry.size)}"
        openable = _is_openable_ext(file_entry.extension)
        openable_label = _openable_type_label(ext) if openable else ""

        file_item = QTreeWidgetItem([name, status, openable_label, ""])
        file_item.setData(0, _ROLE_ABSOLUTE_PATH, file_entry.absolute_path)
        file_item.setData(0, _ROLE_RELATIVE_PATH, rel_path)
        file_item.setFlags(
            file_item.flags()
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        file_item.setCheckState(_COL_SELECT, Qt.CheckState.Unchecked)
        file_item.setToolTip(0, file_entry.absolute_path)
        file_item.setToolTip(_COL_SELECT, "Select to copy to output folder")
        if openable:
            file_item.setToolTip(1, "Double-click to open")
            file_color = COLOR_FILE_OPENABLE
        else:
            file_item.setToolTip(1, "Preview not available for this file type")
            file_color = COLOR_FILE
        file_item.setForeground(0, file_color)
        file_item.setForeground(1, file_color)
        file_item.setForeground(2, file_color)
        parent_item.addChild(file_item)

    def _on_hide_empty_toggled(self, _checked: bool) -> None:
        if not self._current_project:
            return
        self._cache_key = None
        self.show_project(self._current_project)

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.data(0, _ROLE_ABSOLUTE_PATH):
            return
        folder_path = item.data(0, _ROLE_FOLDER_PATH)
        if folder_path is None or not self._lazy_mode:
            return
        self._load_folder_files(item, str(folder_path))

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating_checks or column != _COL_SELECT:
            return
        if not item.data(0, _ROLE_ABSOLUTE_PATH):
            self._updating_checks = True
            item.setCheckState(_COL_SELECT, Qt.CheckState.Unchecked)
            self._updating_checks = False

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if column == _COL_SELECT:
            return

        absolute_path = item.data(0, _ROLE_ABSOLUTE_PATH)
        if not absolute_path:
            return

        path = Path(str(absolute_path))
        extension = path.suffix
        if not _is_openable_ext(extension):
            QMessageBox.information(
                self,
                "Cannot open file",
                "Only PDF, image files (PNG, JPEG, etc.), Outlook .msg, and Excel .xlsx "
                "files can be opened from here.",
            )
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        if not opened:
            QMessageBox.warning(
                self,
                "Cannot open file",
                f"No application is associated with:\n{path}",
            )
