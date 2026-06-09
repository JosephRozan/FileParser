"""Resolve bundled and user-specific config paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def bundle_root() -> Path:
    """Root directory for bundled config shipped with the app or repo."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # src/fileparser/paths.py -> repo root
    return Path(__file__).resolve().parents[2]


def default_config_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "config"
    repo_config = bundle_root() / "config"
    if repo_config.is_dir():
        return repo_config
    return Path(__file__).resolve().parent / "bundled_config"


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        path = Path(base) / "FileParser"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
        path = base / "fileparser"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_settings_path() -> Path:
    return user_data_dir() / "settings.yaml"

