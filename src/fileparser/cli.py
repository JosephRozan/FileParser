"""Optional CLI for development and headless scans."""

from __future__ import annotations

from pathlib import Path

import typer

from fileparser.analyzer import analyze_scan
from fileparser.reporter import export_reports, format_cli_summary
from fileparser.scanner import ScanConfig, Scanner
from fileparser.settings import Settings

app = typer.Typer(help="FileParser CLI (dev/debug)")


@app.command()
def scan(
    root: Path = typer.Option(..., "--root", "-r", help="Scan root directory"),
    out: Path = typer.Option(Path("./reports"), "--out", "-o", help="Output directory"),
    list_projects_only: bool = typer.Option(
        False, "--list-projects-only", help="List project folders without full scan"
    ),
) -> None:
    """Run a headless scan and export JSON/CSV reports."""
    settings = Settings.load()

    if list_projects_only:
        from fileparser.scanner import discover_projects

        projects = discover_projects(root, settings.project_root_depth)
        for project in projects:
            typer.echo(project)
        return

    config = ScanConfig(
        root=root,
        project_root_depth=settings.project_root_depth,
        ignore_patterns=settings.ignore_patterns,
        max_depth=settings.max_depth,
        follow_symlinks=settings.follow_symlinks,
    )
    scanner = Scanner(
        config,
        on_progress=lambda path, count: typer.echo(f"[{count}] {path}", err=True),
    )
    files, directories, errors = scanner.scan()
    result = analyze_scan(
        root,
        files,
        project_root_depth=settings.project_root_depth,
        allowed_extensions=settings.allowed_extensions,
        scan_errors=errors,
        scan_directories=directories,
        on_progress=lambda msg: typer.echo(msg, err=True),
    )
    export_reports(result, out)
    typer.echo(format_cli_summary(result))
    typer.echo(f"Reports written to {out.resolve()}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
