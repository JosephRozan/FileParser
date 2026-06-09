"""Tests for project structure analyzer."""

from __future__ import annotations

from pathlib import Path

from fileparser.analyzer import analyze_project, analyze_scan
from fileparser.models import ProjectStatus
from fileparser.scanner import ScanConfig, Scanner

FIXTURES = Path(__file__).parent / "fixtures" / "sample_project_tree"

ALLOWED_EXTENSIONS = [".pdf", ".docx"]


def _scan_project_root() -> tuple[Path, list]:
    root = FIXTURES / "scan_root"
    config = ScanConfig(root=root, project_root_depth=1)
    files, _, _ = Scanner(config).scan()
    return root, files


def test_not_empty_project():
    root = FIXTURES / "compliant"
    config = ScanConfig(root=root.parent, project_root_depth=2)
    files, _, _ = Scanner(config).scan()
    project_files = [f for f in files if f.project_id == "compliant"]
    report = analyze_project(
        "compliant", root, project_files, allowed_extensions=ALLOWED_EXTENSIONS
    )
    assert report.status == ProjectStatus.NOT_EMPTY
    assert report.file_count >= 3
    assert len(report.files) == report.file_count


def test_partial_project_still_not_empty():
    root = FIXTURES / "partial"
    config = ScanConfig(root=root.parent, project_root_depth=2)
    files, _, _ = Scanner(config).scan()
    project_files = [f for f in files if f.project_id == "partial"]
    report = analyze_project(
        "partial", root, project_files, allowed_extensions=ALLOWED_EXTENSIONS
    )
    assert report.status == ProjectStatus.NOT_EMPTY
    assert report.file_count > 0


def test_empty_project():
    root = FIXTURES / "empty_project"
    report = analyze_project("empty_project", root, [], allowed_extensions=ALLOWED_EXTENSIONS)
    assert report.status == ProjectStatus.EMPTY
    assert report.file_count == 0


def test_analyze_scan_aggregate():
    root, files = _scan_project_root()
    result = analyze_scan(
        root,
        files,
        project_root_depth=1,
        allowed_extensions=ALLOWED_EXTENSIONS,
    )
    assert len(result.projects) == 3
    ids = {p.project_id for p in result.projects}
    assert ids == {"compliant", "partial", "empty_project"}


def test_rag_candidates_filtered():
    root = FIXTURES / "compliant"
    config = ScanConfig(root=root.parent, project_root_depth=2)
    files, _, _ = Scanner(config).scan()
    project_files = [f for f in files if f.project_id == "compliant"]
    report = analyze_project(
        "compliant", root, project_files, allowed_extensions=ALLOWED_EXTENSIONS
    )
    assert all(f.extension in {".pdf", ".docx"} for f in report.rag_candidates)
