# Build FileParser.exe on Windows
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python -m pip install -e ".[build]"
pyinstaller build/fileparser.spec

Write-Host ""
Write-Host "Build complete: dist/FileParser/FileParser.exe"
