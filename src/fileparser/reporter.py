"""Export scan results to JSON and CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from fileparser.models import ScanResult


def export_json(result: ScanResult, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def export_csv(result: ScanResult, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "project_id",
        "status",
        "file_count",
        "empty_folder_count",
        "rag_candidate_count",
        "project_path",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for project in result.projects:
            writer.writerow(
                {
                    "project_id": project.project_id,
                    "status": project.status.value,
                    "file_count": project.file_count,
                    "empty_folder_count": len(project.empty_folders),
                    "rag_candidate_count": len(project.rag_candidates),
                    "project_path": project.project_path,
                }
            )
    return output_path


def export_reports(result: ScanResult, output_dir: Path) -> tuple[Path, Path]:
    json_path = output_dir / "project_inventory.json"
    csv_path = output_dir / "project_summary.csv"
    export_json(result, json_path)
    export_csv(result, csv_path)
    return json_path, csv_path


def format_cli_summary(result: ScanResult) -> str:
    summary = result.summary
    lines = [
        f"Scan root: {result.scan_root}",
        f"Scanned at: {result.scanned_at}",
        f"Total files: {result.total_files}",
        f"Projects: {summary['total_projects']}",
        f"  Not empty: {summary.get('not_empty', 0)}",
        f"  Empty: {summary.get('empty', 0)}",
        f"  Errors: {summary.get('error', 0)}",
    ]
    if result.scan_errors:
        lines.append(f"Scan warnings: {len(result.scan_errors)}")
    return "\n".join(lines)
