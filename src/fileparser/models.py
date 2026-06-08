"""Data models for scan results and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    EMPTY = "empty"
    ERROR = "error"


@dataclass
class FileEntry:
    relative_path: str
    absolute_path: str
    size: int
    extension: str
    mtime: float
    project_id: str

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
class ExpectedFolder:
    path: str
    required: bool = True


@dataclass
class FolderTemplate:
    team: str
    project_root_depth: int = 1
    expected_folders: list[ExpectedFolder] = field(default_factory=list)
    allowed_extensions: list[str] = field(default_factory=list)


@dataclass
class ProjectReport:
    project_id: str
    project_path: str
    team: str
    compliance_score: float
    status: ComplianceStatus
    file_count: int
    empty_folders: list[str] = field(default_factory=list)
    missing_folders: list[str] = field(default_factory=list)
    unexpected_folders: list[str] = field(default_factory=list)
    present_folders: list[str] = field(default_factory=list)
    files_by_extension: dict[str, int] = field(default_factory=dict)
    rag_candidates: list[FileEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_path": self.project_path,
            "team": self.team,
            "compliance_score": self.compliance_score,
            "status": self.status.value,
            "file_count": self.file_count,
            "empty_folders": self.empty_folders,
            "missing_folders": self.missing_folders,
            "unexpected_folders": self.unexpected_folders,
            "present_folders": self.present_folders,
            "files_by_extension": self.files_by_extension,
            "rag_candidates": [f.to_dict() for f in self.rag_candidates],
            "errors": self.errors,
        }


@dataclass
class ScanResult:
    scan_root: str
    scanned_at: str
    team: str
    projects: list[ProjectReport] = field(default_factory=list)
    total_files: int = 0
    scan_errors: list[str] = field(default_factory=list)

    @classmethod
    def new(cls, scan_root: str, team: str) -> ScanResult:
        return cls(
            scan_root=scan_root,
            scanned_at=datetime.now(timezone.utc).isoformat(),
            team=team,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_root": self.scan_root,
            "scanned_at": self.scanned_at,
            "team": self.team,
            "total_files": self.total_files,
            "scan_errors": self.scan_errors,
            "projects": [p.to_dict() for p in self.projects],
        }

    @property
    def summary(self) -> dict[str, int]:
        counts = {s.value: 0 for s in ComplianceStatus}
        for project in self.projects:
            counts[project.status.value] += 1
        return {
            "total_projects": len(self.projects),
            **counts,
        }
