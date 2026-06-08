"""Load folder structure templates from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from fileparser.models import ExpectedFolder, FolderTemplate
from fileparser.paths import default_config_dir, templates_dir


def load_template(path: Path) -> FolderTemplate:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    expected = [
        ExpectedFolder(
            path=str(item["path"]),
            required=bool(item.get("required", True)),
        )
        for item in data.get("expected_folders", [])
    ]
    extensions = [str(ext).lower() for ext in data.get("allowed_extensions", [])]
    if extensions and not all(ext.startswith(".") for ext in extensions):
        extensions = [f".{ext}" if not ext.startswith(".") else ext for ext in extensions]
    return FolderTemplate(
        team=str(data.get("team", path.stem)),
        project_root_depth=int(data.get("project_root_depth", 1)),
        expected_folders=expected,
        allowed_extensions=extensions,
    )


def list_templates() -> list[FolderTemplate]:
    templates: list[FolderTemplate] = []
    for path in sorted(templates_dir().glob("*.yaml")):
        templates.append(load_template(path))
    if not templates:
        fallback = default_config_dir() / "templates" / "default.yaml"
        if fallback.exists():
            templates.append(load_template(fallback))
    return templates


def get_template(team: str) -> FolderTemplate:
    for template in list_templates():
        if template.team == team:
            return template
    templates = list_templates()
    if templates:
        return templates[0]
    raise FileNotFoundError("No folder templates found. Add YAML files to config/templates/.")
