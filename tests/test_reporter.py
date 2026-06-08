"""Tests for report exporters."""

from __future__ import annotations

import json
from pathlib import Path

from fileparser.analyzer import analyze_scan
from fileparser.models import ExpectedFolder, FolderTemplate
from fileparser.reporter import export_csv, export_json, export_reports, format_cli_summary
from fileparser.scanner import ScanConfig, Scanner

FIXTURES = Path(__file__).parent / "fixtures" / "sample_project_tree" / "scan_root"

TEMPLATE = FolderTemplate(
    team="default",
    expected_folders=[
        ExpectedFolder("01_Admin"),
        ExpectedFolder("02_Drawings/PDF"),
        ExpectedFolder("04_Specs"),
    ],
    allowed_extensions=[".pdf"],
)


def _result():
    config = ScanConfig(root=FIXTURES, project_root_depth=1)
    files, _, errors = Scanner(config).scan()
    return analyze_scan(FIXTURES, files, TEMPLATE, errors)


def test_export_json(tmp_path: Path):
    result = _result()
    path = export_json(result, tmp_path / "out.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["team"] == "default"
    assert len(data["projects"]) >= 1


def test_export_csv(tmp_path: Path):
    result = _result()
    path = export_csv(result, tmp_path / "out.csv")
    text = path.read_text(encoding="utf-8")
    assert "project_id" in text
    assert "compliant" in text or "partial" in text


def test_export_reports(tmp_path: Path):
    result = _result()
    json_path, csv_path = export_reports(result, tmp_path)
    assert json_path.exists()
    assert csv_path.exists()


def test_cli_summary():
    result = _result()
    summary = format_cli_summary(result)
    assert "Scan root:" in summary
    assert "Projects:" in summary
