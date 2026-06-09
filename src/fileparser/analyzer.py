"""Analyze scanned projects for folder occupancy and file inventory."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fileparser.models import FileEntry, ProjectReport, ProjectStatus, ScanResult
from fileparser.scanner import discover_projects, group_files_by_project

AnalyzeProgressCallback = Callable[[str], None]


def _normalize_folder(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _file_project_relative_path(file_entry: FileEntry, project_path: Path) -> str:
    file_path = Path(file_entry.absolute_path).resolve()
    base = project_path.resolve()
    try:
        return file_path.relative_to(base).as_posix()
    except ValueError:
        rel = file_entry.relative_path.replace("\\", "/")
        parts = rel.split("/")
        project_name = base.name
        if project_name in parts:
            idx = parts.index(project_name)
            return "/".join(parts[idx + 1 :])
        return Path(rel).name


def _folders_with_files(files: list[FileEntry], project_path: Path) -> set[str]:
    """Folders that contain at least one file in their subtree."""
    folders: set[str] = set()
    for file_entry in files:
        rel = _file_project_relative_path(file_entry, project_path)
        parent = Path(rel).parent.as_posix()
        if not parent or parent == ".":
            continue
        parts = parent.split("/")
        for i in range(1, len(parts) + 1):
            folders.add("/".join(parts[:i]))
    return folders


def _collect_present_folders(
    project_id: str,
    files: list[FileEntry],
    project_path: Path,
    scan_directories: set[str] | None = None,
) -> set[str]:
    """Build folder list from scan data — no second disk walk."""
    present: set[str] = set()
    prefix = f"{project_id}/"
    for path in scan_directories or ():
        norm = _normalize_folder(path)
        if norm.startswith(prefix):
            rel = norm[len(prefix) :]
            if rel:
                present.add(rel)
    for file_entry in files:
        rel = _file_project_relative_path(file_entry, project_path)
        parent = Path(rel).parent.as_posix()
        if parent and parent != ".":
            present.add(parent)
            parts = parent.split("/")
            for i in range(1, len(parts)):
                present.add("/".join(parts[:i]))
    return {_normalize_folder(p) for p in present if p and p != "."}


def _empty_folders(
    present_folders: set[str], files: list[FileEntry], project_path: Path
) -> list[str]:
    with_files = _folders_with_files(files, project_path)
    return sorted(folder for folder in present_folders if folder not in with_files)


def analyze_project(
    project_id: str,
    project_path: Path,
    files: list[FileEntry],
    allowed_extensions: list[str] | None = None,
    scan_directories: set[str] | None = None,
) -> ProjectReport:
    errors: list[str] = []
    if not project_path.exists():
        errors.append(f"Project path not found: {project_path}")
        return ProjectReport(
            project_id=project_id,
            project_path=str(project_path),
            status=ProjectStatus.ERROR,
            file_count=0,
            errors=errors,
        )

    present_folders = _collect_present_folders(
        project_id, files, project_path, scan_directories
    )
    empty = _empty_folders(present_folders, files, project_path)

    extensions: dict[str, int] = {}
    for file_entry in files:
        ext = file_entry.extension or "(no ext)"
        extensions[ext] = extensions.get(ext, 0) + 1

    allowed = {ext.lower() for ext in (allowed_extensions or [])}
    rag_candidates = (
        [f for f in files if f.extension.lower() in allowed]
        if allowed
        else list(files)
    )

    status = ProjectStatus.EMPTY if not files else ProjectStatus.NOT_EMPTY

    return ProjectReport(
        project_id=project_id,
        project_path=str(project_path),
        status=status,
        file_count=len(files),
        empty_folders=empty,
        present_folders=sorted(present_folders),
        files_by_extension=extensions,
        files=list(files),
        rag_candidates=rag_candidates,
        errors=errors,
    )


def analyze_scan(
    scan_root: Path,
    files: list[FileEntry],
    project_root_depth: int = 1,
    allowed_extensions: list[str] | None = None,
    scan_errors: list[str] | None = None,
    scan_directories: set[str] | None = None,
    on_progress: AnalyzeProgressCallback | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> ScanResult:
    result = ScanResult.new(str(scan_root))
    result.total_files = len(files)
    result.scan_errors = list(scan_errors or [])

    grouped = group_files_by_project(files)
    discovered = discover_projects(scan_root, project_root_depth)
    project_ids = sorted(set(discovered) | set(grouped.keys()))
    total = len(project_ids)

    if on_progress:
        on_progress("Analyzing projects…")

    for index, project_id in enumerate(project_ids, start=1):
        if should_cancel and should_cancel():
            break
        if on_progress:
            on_progress(f"Analyzing {project_id} ({index}/{total})")
        project_path = scan_root / project_id
        project_files = grouped.get(project_id, [])
        report = analyze_project(
            project_id,
            project_path,
            project_files,
            allowed_extensions=allowed_extensions,
            scan_directories=scan_directories,
        )
        result.projects.append(report)

    return result
