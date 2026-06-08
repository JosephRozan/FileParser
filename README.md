# FileParser

Windows desktop tool for Wilmotte to inventory architecture projects on a local file server, detect empty folders, and check compliance against per-design-team folder templates. Exports JSON and CSV reports for RAG ingestion.

## Features

- PySide6 GUI with folder picker, live scan progress, and cancellable background scans
- Project summary table with compliance scores and status coloring
- Detail tree showing expected vs actual folders (missing, empty, unexpected)
- JSON manifest and CSV summary export
- Configurable folder templates per design team (YAML)
- Optional dev CLI for headless scans

## Development setup

Requires Python 3.10+.

```bash
cd /path/to/FileParser
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the GUI (requires a display):

```bash
fileparser
# or
python -m fileparser.main
```

Run headless scan:

```bash
fileparser-cli --root /path/to/projects --team default --out ./reports
```

Run tests:

```bash
pytest
```

## Configuration

Bundled defaults live in `config/`:

- `config/settings.example.yaml` — scan options (copied to user settings on first run)
- `config/templates/*.yaml` — folder structure templates per design team

User settings are stored at:

- Windows: `%APPDATA%\FileParser\settings.yaml`
- Linux/macOS (dev): `~/.config/fileparser/settings.yaml`

Custom templates can be added to `%APPDATA%\FileParser\templates\` without rebuilding the app.

### Folder template example

```yaml
team: default
project_root_depth: 1
expected_folders:
  - path: "01_Admin"
    required: true
  - path: "02_Drawings/PDF"
    required: true
  - path: "03_Photos"
    required: false
  - path: "04_Specs"
    required: true
allowed_extensions:
  - .pdf
  - .dwg
  - .docx
```

## Building FileParser.exe (Windows)

The `.exe` must be built on a Windows machine:

```powershell
cd C:\path\to\FileParser
.\build\build_exe.ps1
```

Output: `dist\FileParser\FileParser.exe`

Distribute the entire `dist\FileParser\` folder (or zip it) to staff machines. No Python install required on end-user PCs.

## Usage

1. Launch **FileParser.exe**
2. Click **Browse** and select the project server root (e.g. `Z:\Projects` or `\\server\share\projects`)
3. Choose the design team template
4. Click **Start scan** — progress appears in a live dialog
5. Review projects in the summary table; select a row to see folder detail
6. Use **File → Export reports** to save `project_inventory.json` and `compliance_summary.csv`

## Project layout

```
config/                 Bundled settings and templates
src/fileparser/         Core engine + PySide6 UI
build/                  PyInstaller spec and Windows build script
tests/                  Pytest suite with fixture project trees
```
# FileParser
