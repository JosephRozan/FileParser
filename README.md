# FileParser

Windows desktop tool for Wilmotte to inventory architecture projects on a local file server, detect empty folders, and browse project files. Exports JSON and CSV reports for RAG ingestion.

## Features

- PySide6 GUI with folder picker, live scan progress, and cancellable background scans
- **Saved scans** — completed scans are stored locally and can be reloaded from a dropdown without rescanning
- Project summary table with Empty / Not empty status
- Detail tree showing folders and files (Empty / Not empty per folder), with **Hide empty folders** toggle
- **Openable files** column (PDF, images, `.msg`, `.xlsx`) — double-click to open
- **Select** checkboxes on files and **Store selected files** to copy them flat into an output folder
- JSON manifest and CSV summary export
- Optional dev CLI for headless scans

## Development setup

Requires Python 3.10+.

From the project folder (where `pyproject.toml` lives):

```powershell
cd C:\path\to\FileParser\FileParser\FileParser
python -m venv ..\.venv
..\.venv\Scripts\activate
pip install -e ".[dev]"
```

Run the GUI:

```powershell
# Recommended — always loads latest source code
.\run.bat
# or
.\run.ps1
# or
..\.venv\Scripts\python.exe -m fileparser.main
```

The window title shows `(dev)` when running from source.

Run headless scan:

```bash
fileparser-cli --root /path/to/projects --out ./reports
```

Run tests:

```bash
pytest
```

## Configuration

Bundled defaults live in `config/settings.example.yaml` (scan options; copied to user settings on first run).

User data is stored at:

- Windows: `%APPDATA%\FileParser\`
  - `settings.yaml` — app preferences
  - `scan_history\` — saved scan results (JSON + index)
- Linux/macOS (dev): `~/.config/fileparser/`

Key options in `settings.yaml`:

```yaml
project_root_depth: 1
last_scan_root: ""
last_output_path: ""
allowed_extensions:
  - .pdf
  - .dwg
  - .docx
  - .xlsx
  - .jpg
  - .png
```

`allowed_extensions` controls which files are tagged as RAG candidates in exports.

## Building FileParser.exe (Windows)

The `.exe` must be built on a Windows machine:

```powershell
cd C:\path\to\FileParser\FileParser\FileParser
.\build\build_exe.ps1
```

Output: `dist\FileParser\FileParser.exe`

Distribute the entire `dist\FileParser\` folder (or zip it) to staff machines. No Python install required on end-user PCs.

## Usage

1. Launch **FileParser** (`run.bat`, `FileParser.exe`, or `fileparser`)
2. Set **Scan root** — browse to the project server root (e.g. `L:\` or `\\server\share\projects`)
3. Optionally pick a **Saved scan** from the dropdown to reload a previous result without scanning
4. Click **Start scan** for a fresh scan — progress appears in a live dialog
5. Review projects in the summary table; select a row to see folders and files in the detail panel
6. Use **Hide empty folders** to collapse folders with no files in their branch
7. Tick **Select** on files and click **Store selected files** to copy them into the **Output folder** (files are copied flat, no subfolders)
8. Use **File → Export reports** to save `project_inventory.json` and `project_summary.csv`

## Project layout

```
config/                 Bundled settings
src/fileparser/         Core engine + PySide6 UI
build/                  PyInstaller spec and Windows build script
tests/                  Pytest suite with fixture project trees
run.bat / run.ps1       Launch from source (dev)
```
