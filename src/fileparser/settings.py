"""Load and persist application settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from fileparser.paths import default_config_dir, user_settings_path


@dataclass
class Settings:
    scan_roots: list[str] = field(default_factory=list)
    project_root_depth: int = 1
    ignore_patterns: list[str] = field(
        default_factory=lambda: [
            ".DS_Store",
            "Thumbs.db",
            "desktop.ini",
        ]
    )
    allowed_extensions: list[str] = field(
        default_factory=lambda: [
            ".pdf",
            ".dwg",
            ".docx",
            ".doc",
            ".xlsx",
            ".jpg",
            ".jpeg",
            ".png",
        ]
    )
    max_depth: int | None = None
    follow_symlinks: bool = False
    parallel_workers: int = 1
    last_scan_root: str = ""
    last_output_path: str = ""

    @classmethod
    def load(cls) -> Settings:
        path = user_settings_path()
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return cls.from_dict(data)
        example = default_config_dir() / "settings.example.yaml"
        if example.exists():
            data = yaml.safe_load(example.read_text(encoding="utf-8")) or {}
            return cls.from_dict(data)
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        return cls(
            scan_roots=list(data.get("scan_roots", [])),
            project_root_depth=int(data.get("project_root_depth", 1)),
            ignore_patterns=list(data.get("ignore_patterns", cls().ignore_patterns)),
            allowed_extensions=list(
                data.get("allowed_extensions", cls().allowed_extensions)
            ),
            max_depth=data.get("max_depth"),
            follow_symlinks=bool(data.get("follow_symlinks", False)),
            parallel_workers=int(data.get("parallel_workers", 1)),
            last_scan_root=str(data.get("last_scan_root", "")),
            last_output_path=str(data.get("last_output_path", "")),
        )

    def save(self) -> None:
        path = user_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_roots": self.scan_roots,
            "project_root_depth": self.project_root_depth,
            "ignore_patterns": self.ignore_patterns,
            "allowed_extensions": self.allowed_extensions,
            "max_depth": self.max_depth,
            "follow_symlinks": self.follow_symlinks,
            "parallel_workers": self.parallel_workers,
            "last_scan_root": self.last_scan_root,
            "last_output_path": self.last_output_path,
        }
