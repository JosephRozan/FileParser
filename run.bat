@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo Virtual env not found. Create it first:
    echo   cd %~dp0
    echo   python -m venv ..\.venv
    echo   ..\.venv\Scripts\activate
    echo   pip install -e ".[dev]"
    exit /b 1
)

echo Starting FileParser from source...
"%VENV_PYTHON%" -m fileparser.main

endlocal
