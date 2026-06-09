"""Persist and load past scan results."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fileparser.models import ScanResult
from fileparser.paths import user_data_dir

MAX_HISTORY_ENTRIES = 30


@dataclass(frozen=True)
class ScanHistoryEntry:
    id: str
    scan_root: str
    scanned_at: str
    total_files: int
    total_projects: int

    def label(self) -> str:
        when = _format_scanned_at(self.scanned_at)
        root_name = _root_display_name(self.scan_root)
        summary = f"{self.total_projects} projects, {self.total_files} files"
        return f"{root_name} — {when} — {summary}"


def _root_display_name(scan_root: str) -> str:
    if not scan_root:
        return "(unknown root)"
    name = Path(scan_root).name
    return name or scan_root


def _format_scanned_at(scanned_at: str) -> str:
    try:
        normalized = scanned_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return scanned_at


def _normalize_root(path: str) -> str:
    if not path:
        return ""
    cleaned = path.strip().rstrip("\\/")
    if not cleaned:
        return ""
    return os.path.normcase(os.path.normpath(cleaned))


def _history_dir() -> Path:
    path = user_data_dir() / "scan_history"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index_path() -> Path:
    return _history_dir() / "index.json"


def _scan_path(entry_id: str) -> Path:
    safe_id = re.sub(r"[^\w\-.]", "_", entry_id)
    return _history_dir() / f"{safe_id}.json"


def _write_json_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(path)


class ScanHistoryStore:
    def __init__(self) -> None:
        self._entries: list[ScanHistoryEntry] = []
        self.reload()

    def reload(self) -> None:
        self._load_index()
        self._sync_orphan_scan_files()

    @property
    def entries(self) -> list[ScanHistoryEntry]:
        return list(self._entries)

    def entries_for_root(self, scan_root: str, *, include_all: bool = False) -> list[ScanHistoryEntry]:
        if include_all or not scan_root.strip():
            return list(self._entries)
        normalized = _normalize_root(scan_root)
        return [
            entry
            for entry in self._entries
            if _normalize_root(entry.scan_root) == normalized
        ]

    def latest_for_root(self, scan_root: str) -> ScanHistoryEntry | None:
        matches = self.entries_for_root(scan_root)
        return matches[0] if matches else None

    def save(self, result: ScanResult) -> ScanHistoryEntry:
        entry_id = uuid.uuid4().hex
        entry = ScanHistoryEntry(
            id=entry_id,
            scan_root=result.scan_root,
            scanned_at=result.scanned_at,
            total_files=result.total_files,
            total_projects=len(result.projects),
        )
        scan_path = _scan_path(entry_id)
        _write_json_atomic(
            scan_path,
            json.dumps(result.to_dict(), ensure_ascii=False),
        )
        self._entries = [entry] + [e for e in self._entries if e.id != entry_id]
        self._entries.sort(key=lambda item: item.scanned_at, reverse=True)
        self._prune()
        self._save_index()
        return entry

    def load(self, entry_id: str) -> ScanResult | None:
        path = _scan_path(entry_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ScanResult.from_dict(data)

    def storage_dir(self) -> Path:
        return _history_dir()

    def _prune(self) -> None:
        while len(self._entries) > MAX_HISTORY_ENTRIES:
            removed = self._entries.pop()
            scan_file = _scan_path(removed.id)
            if scan_file.exists():
                scan_file.unlink()

    def _sync_orphan_scan_files(self) -> None:
        """Register scan JSON files that exist on disk but are missing from the index."""
        known_ids = {entry.id for entry in self._entries}
        for path in _history_dir().glob("*.json"):
            if path.name == "index.json":
                continue
            entry_id = path.stem
            if entry_id in known_ids:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result = ScanResult.from_dict(data)
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            self._entries.append(
                ScanHistoryEntry(
                    id=entry_id,
                    scan_root=result.scan_root,
                    scanned_at=result.scanned_at,
                    total_files=result.total_files,
                    total_projects=len(result.projects),
                )
            )
        self._entries.sort(key=lambda item: item.scanned_at, reverse=True)

    def _load_index(self) -> None:
        index_file = _index_path()
        if not index_file.exists():
            self._entries = []
            return
        try:
            raw = json.loads(index_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._entries = []
            return
        self._entries = [
            ScanHistoryEntry(
                id=str(item["id"]),
                scan_root=str(item["scan_root"]),
                scanned_at=str(item["scanned_at"]),
                total_files=int(item["total_files"]),
                total_projects=int(item["total_projects"]),
            )
            for item in raw.get("entries", [])
        ]
        self._entries.sort(key=lambda item: item.scanned_at, reverse=True)

    def _save_index(self) -> None:
        payload = {
            "entries": [
                {
                    "id": entry.id,
                    "scan_root": entry.scan_root,
                    "scanned_at": entry.scanned_at,
                    "total_files": entry.total_files,
                    "total_projects": entry.total_projects,
                }
                for entry in self._entries
            ]
        }
        _write_json_atomic(
            _index_path(),
            json.dumps(payload, indent=2, ensure_ascii=False),
        )
