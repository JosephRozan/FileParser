"""Tests for report exporters."""

from __future__ import annotations

import json
from pathlib import Path

from fileparser.analyzer import analyze_scan
from fileparser.reporter import export_csv, export_json, export_reports, format_cli_summary
from fileparser.scanner import ScanConfig, Scanner

FIXTURES = Path(__file__).parent / "fixtures" / "sample_project_tree" / "scan_root"


def _result():
    config = ScanConfig(root=FIXTURES, project_root_depth=1)
    files, _, errors = Scanner(config).scan()
    return analyze_scan(
        FIXTURES,
        files,
        project_root_depth=1,
        allowed_extensions=[".pdf"],
        scan_errors=errors,
    )


def test_export_json(tmp_path: Path):
    result = _result()
    path = export_json(result, tmp_path / "out.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["scan_root"]
    assert len(data["projects"]) >= 1


def test_export_csv(tmp_path: Path):
    result = _result()
    path = export_csv(result, tmp_path / "out.csv")
    text = path.read_text(encoding="utf-8")
    assert "project_id" in text
    assert "not_empty" in text or "empty" in text


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
