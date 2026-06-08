"""Tests for project structure analyzer."""

from __future__ import annotations

from pathlib import Path

from fileparser.analyzer import analyze_project, analyze_scan
from fileparser.models import ComplianceStatus, ExpectedFolder, FolderTemplate
from fileparser.scanner import ScanConfig, Scanner

FIXTURES = Path(__file__).parent / "fixtures" / "sample_project_tree"

DEFAULT_TEMPLATE = FolderTemplate(
    team="default",
    project_root_depth=1,
    expected_folders=[
        ExpectedFolder("01_Admin", required=True),
        ExpectedFolder("02_Drawings/PDF", required=True),
        ExpectedFolder("03_Photos", required=False),
        ExpectedFolder("04_Specs", required=True),
    ],
    allowed_extensions=[".pdf", ".docx"],
)


def _scan_project_root() -> tuple[Path, list]:
    root = FIXTURES / "scan_root"
    config = ScanConfig(root=root, project_root_depth=1)
    files, _, _ = Scanner(config).scan()
    return root, files


def test_compliant_project():
    root = FIXTURES / "compliant"
    config = ScanConfig(root=root.parent, project_root_depth=2)
    files, _, _ = Scanner(config).scan()
    project_files = [f for f in files if f.project_id == "compliant"]
    report = analyze_project("compliant", root, project_files, DEFAULT_TEMPLATE)
    assert report.compliance_score == 1.0
    assert report.status in {ComplianceStatus.COMPLIANT, ComplianceStatus.PARTIAL}
    assert report.file_count >= 3


def test_partial_project_missing_folders():
    root = FIXTURES / "partial"
    config = ScanConfig(root=root.parent, project_root_depth=2)
    files, _, _ = Scanner(config).scan()
    project_files = [f for f in files if f.project_id == "partial"]
    report = analyze_project("partial", root, project_files, DEFAULT_TEMPLATE)
    assert "02_Drawings/PDF" in report.missing_folders
    assert report.status == ComplianceStatus.PARTIAL


def test_empty_project():
    root = FIXTURES / "empty_project"
    report = analyze_project("empty_project", root, [], DEFAULT_TEMPLATE)
    assert report.status == ComplianceStatus.EMPTY
    assert report.file_count == 0


def test_analyze_scan_aggregate():
    root, files = _scan_project_root()
    result = analyze_scan(root, files, DEFAULT_TEMPLATE)
    assert len(result.projects) == 3
    ids = {p.project_id for p in result.projects}
    assert ids == {"compliant", "partial", "empty_project"}


def test_rag_candidates_filtered():
    root = FIXTURES / "compliant"
    config = ScanConfig(root=root.parent, project_root_depth=2)
    files, _, _ = Scanner(config).scan()
    project_files = [f for f in files if f.project_id == "compliant"]
    report = analyze_project("compliant", root, project_files, DEFAULT_TEMPLATE)
    assert all(f.extension in {".pdf", ".docx"} for f in report.rag_candidates)
