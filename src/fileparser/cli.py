"""Optional CLI for development and headless scans."""

from __future__ import annotations

from pathlib import Path

import typer

from fileparser.analyzer import analyze_scan
from fileparser.reporter import export_reports, format_cli_summary
from fileparser.scanner import ScanConfig, Scanner
from fileparser.schema import get_template
from fileparser.settings import Settings

app = typer.Typer(help="FileParser CLI (dev/debug)")


@app.command()
def scan(
    root: Path = typer.Option(..., "--root", "-r", help="Scan root directory"),
    team: str = typer.Option("default", "--team", "-t", help="Folder template team name"),
    out: Path = typer.Option(Path("./reports"), "--out", "-o", help="Output directory"),
    list_projects_only: bool = typer.Option(
        False, "--list-projects-only", help="List project folders without full scan"
    ),
) -> None:
    """Run a headless scan and export JSON/CSV reports."""
    settings = Settings.load()
    template = get_template(team)

    if list_projects_only:
        from fileparser.scanner import discover_projects

        projects = discover_projects(root, template.project_root_depth)
        for project in projects:
            typer.echo(project)
        return

    config = ScanConfig(
        root=root,
        project_root_depth=template.project_root_depth,
        ignore_patterns=settings.ignore_patterns,
        max_depth=settings.max_depth,
        follow_symlinks=settings.follow_symlinks,
    )
    scanner = Scanner(
        config,
        on_progress=lambda path, count: typer.echo(f"[{count}] {path}", err=True),
    )
    files, _dirs, errors = scanner.scan()
    result = analyze_scan(root, files, template, errors)
    export_reports(result, out)
    typer.echo(format_cli_summary(result))
    typer.echo(f"Reports written to {out.resolve()}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
