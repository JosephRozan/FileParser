# Launch FileParser from source (always picks up latest code changes)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path (Split-Path $Root -Parent) ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    $VenvPython = Join-Path $Root "..\.venv\Scripts\python.exe"
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual env not found. Create it first:"
    Write-Host "  cd $Root"
    Write-Host "  python -m venv ..\.venv"
    Write-Host "  ..\.venv\Scripts\activate"
    Write-Host "  pip install -e `".[dev]`""
    exit 1
}

Write-Host "Starting FileParser from source..."
& $VenvPython -m fileparser.main
