"""Tests for filesystem scanner."""

from __future__ import annotations

from pathlib import Path

from fileparser.scanner import ScanConfig, Scanner, discover_projects, group_files_by_project

FIXTURES = Path(__file__).parent / "fixtures" / "sample_project_tree"
SCAN_ROOT = FIXTURES / "scan_root"


def test_discover_projects():
    projects = discover_projects(SCAN_ROOT, project_root_depth=1)
    assert set(projects) == {"compliant", "partial", "empty_project"}


def test_scanner_collects_files():
    config = ScanConfig(root=SCAN_ROOT, project_root_depth=1, ignore_patterns=[".DS_Store"])
    scanner = Scanner(config)
    files, directories, errors = scanner.scan()
    assert len(files) >= 4
    assert errors == []
    grouped = group_files_by_project(files)
    assert "compliant" in grouped
    assert len(grouped["compliant"]) >= 3


def test_scanner_progress_callback():
    seen: list[str] = []

    def on_progress(path: str, count: int) -> None:
        seen.append(path)

    config = ScanConfig(root=SCAN_ROOT, project_root_depth=1)
    scanner = Scanner(config, on_progress=on_progress)
    scanner.scan()
    assert seen


def test_scanner_cancel():
    config = ScanConfig(root=SCAN_ROOT, project_root_depth=1)
    cancelled = {"value": False}

    def should_cancel() -> bool:
        return cancelled["value"]

    scanner = Scanner(config, should_cancel=should_cancel)
    cancelled["value"] = True
    files, _, _ = scanner.scan()
    assert isinstance(files, list)


def test_scanner_missing_root(tmp_path: Path):
    config = ScanConfig(root=tmp_path / "missing", project_root_depth=1)
    scanner = Scanner(config)
    try:
        scanner.scan()
        raised = False
    except FileNotFoundError:
        raised = True
    assert raised
