"""Compare scanned projects against expected folder templates."""

from __future__ import annotations

from pathlib import Path

from fileparser.models import (
    ComplianceStatus,
    FileEntry,
    FolderTemplate,
    ProjectReport,
    ScanResult,
)
from fileparser.scanner import discover_projects, group_files_by_project


def _normalize_folder(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _folder_has_files(folder: str, files: list[FileEntry]) -> bool:
    prefix = f"{folder}/"
    for file_entry in files:
        rel = file_entry.relative_path
        if rel == folder or rel.startswith(prefix):
            return True
    return False


def _collect_present_folders(project_path: Path, files: list[FileEntry]) -> set[str]:
    present: set[str] = set()
    if project_path.is_dir():
        import os

        for dirpath, dirnames, _ in os.walk(project_path):
            rel = Path(dirpath).relative_to(project_path).as_posix()
            if rel and rel != ".":
                present.add(rel)
            for name in dirnames:
                child = f"{rel}/{name}" if rel and rel != "." else name
                present.add(child)
    for file_entry in files:
        parent = Path(file_entry.relative_path).parent.as_posix()
        if parent and parent != ".":
            present.add(parent)
            parts = parent.split("/")
            for i in range(1, len(parts)):
                present.add("/".join(parts[:i]))
    return {_normalize_folder(p) for p in present if p and p != "."}


def _empty_folders(present_folders: set[str], files: list[FileEntry]) -> list[str]:
    empty: list[str] = []
    for folder in sorted(present_folders):
        if not _folder_has_files(folder, files):
            empty.append(folder)
    return empty


def analyze_project(
    project_id: str,
    project_path: Path,
    files: list[FileEntry],
    template: FolderTemplate,
) -> ProjectReport:
    errors: list[str] = []
    if not project_path.exists():
        errors.append(f"Project path not found: {project_path}")
        return ProjectReport(
            project_id=project_id,
            project_path=str(project_path),
            team=template.team,
            compliance_score=0.0,
            status=ComplianceStatus.ERROR,
            file_count=0,
            errors=errors,
        )

    present_folders = _collect_present_folders(project_path, files)
    expected_paths = [_normalize_folder(f.path) for f in template.expected_folders]
    required_paths = [_normalize_folder(f.path) for f in template.expected_folders if f.required]

    missing = [path for path in required_paths if path not in present_folders]
    unexpected = sorted(present_folders - set(expected_paths)) if expected_paths else []

    required_present = sum(1 for path in required_paths if path in present_folders)
    compliance_score = (
        required_present / len(required_paths) if required_paths else 1.0
    )

    empty = _empty_folders(present_folders, files)

    extensions: dict[str, int] = {}
    for file_entry in files:
        ext = file_entry.extension or "(no ext)"
        extensions[ext] = extensions.get(ext, 0) + 1

    allowed = {ext.lower() for ext in template.allowed_extensions}
    rag_candidates = (
        [f for f in files if f.extension.lower() in allowed]
        if allowed
        else list(files)
    )

    if not files:
        status = ComplianceStatus.EMPTY
    elif compliance_score >= 1.0 and not empty:
        status = ComplianceStatus.COMPLIANT
    else:
        status = ComplianceStatus.PARTIAL

    return ProjectReport(
        project_id=project_id,
        project_path=str(project_path),
        team=template.team,
        compliance_score=round(compliance_score, 4),
        status=status,
        file_count=len(files),
        empty_folders=empty,
        missing_folders=missing,
        unexpected_folders=unexpected,
        present_folders=sorted(present_folders),
        files_by_extension=extensions,
        rag_candidates=rag_candidates,
        errors=errors,
    )


def analyze_scan(
    scan_root: Path,
    files: list[FileEntry],
    template: FolderTemplate,
    scan_errors: list[str] | None = None,
) -> ScanResult:
    result = ScanResult.new(str(scan_root), template.team)
    result.total_files = len(files)
    result.scan_errors = list(scan_errors or [])

    grouped = group_files_by_project(files)
    discovered = discover_projects(scan_root, template.project_root_depth)
    project_ids = sorted(set(discovered) | set(grouped.keys()))

    for project_id in project_ids:
        project_path = scan_root / project_id
        project_files = grouped.get(project_id, [])
        report = analyze_project(project_id, project_path, project_files, template)
        result.projects.append(report)

    return result
