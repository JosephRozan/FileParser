"""Data models for scan results and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ProjectStatus(str, Enum):
    EMPTY = "empty"
    NOT_EMPTY = "not_empty"
    ERROR = "error"


# Backwards-compatible alias for existing imports during transition
ComplianceStatus = ProjectStatus


@dataclass
class FileEntry:
    relative_path: str
    absolute_path: str
    size: int
    extension: str
    mtime: float
    project_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileEntry:
        return cls(
            relative_path=str(data["relative_path"]),
            absolute_path=str(data["absolute_path"]),
            size=int(data["size"]),
            extension=str(data["extension"]),
            mtime=float(data["mtime"]),
            project_id=str(data["project_id"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "size": self.size,
            "extension": self.extension,
            "mtime": self.mtime,
            "project_id": self.project_id,
        }


@dataclass
class ProjectReport:
    project_id: str
    project_path: str
    status: ProjectStatus
    file_count: int
    empty_folders: list[str] = field(default_factory=list)
    present_folders: list[str] = field(default_factory=list)
    files_by_extension: dict[str, int] = field(default_factory=dict)
    files: list[FileEntry] = field(default_factory=list)
    rag_candidates: list[FileEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectReport:
        return cls(
            project_id=str(data["project_id"]),
            project_path=str(data["project_path"]),
            status=ProjectStatus(str(data["status"])),
            file_count=int(data["file_count"]),
            empty_folders=list(data.get("empty_folders", [])),
            present_folders=list(data.get("present_folders", [])),
            files_by_extension=dict(data.get("files_by_extension", {})),
            files=[FileEntry.from_dict(f) for f in data.get("files", [])],
            rag_candidates=[
                FileEntry.from_dict(f) for f in data.get("rag_candidates", [])
            ],
            errors=list(data.get("errors", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_path": self.project_path,
            "status": self.status.value,
            "file_count": self.file_count,
            "empty_folders": self.empty_folders,
            "present_folders": self.present_folders,
            "files_by_extension": self.files_by_extension,
            "files": [f.to_dict() for f in self.files],
            "rag_candidates": [f.to_dict() for f in self.rag_candidates],
            "errors": self.errors,
        }


@dataclass
class ScanResult:
    scan_root: str
    scanned_at: str
    projects: list[ProjectReport] = field(default_factory=list)
    total_files: int = 0
    scan_errors: list[str] = field(default_factory=list)

    @classmethod
    def new(cls, scan_root: str) -> ScanResult:
        return cls(
            scan_root=scan_root,
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScanResult:
        return cls(
            scan_root=str(data["scan_root"]),
            scanned_at=str(data["scanned_at"]),
            total_files=int(data.get("total_files", 0)),
            scan_errors=list(data.get("scan_errors", [])),
            projects=[ProjectReport.from_dict(p) for p in data.get("projects", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_root": self.scan_root,
            "scanned_at": self.scanned_at,
            "total_files": self.total_files,
            "scan_errors": self.scan_errors,
            "projects": [p.to_dict() for p in self.projects],
        }

    @property
    def summary(self) -> dict[str, int]:
        counts = {s.value: 0 for s in ProjectStatus}
        for project in self.projects:
            counts[project.status.value] += 1
        return {
            "total_projects": len(self.projects),
            **counts,
        }
