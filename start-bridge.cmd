@echo off
setlocal

cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo ERROR: Virtual environment not found.
    echo Run setup-bridge.cmd first to create the venv and install dependencies.
    exit /b 1
)

echo Starting Jules Bridge...
echo Press Ctrl+C to stop.
echo.
"%PYTHON%" "%~dp0bridge.py"
