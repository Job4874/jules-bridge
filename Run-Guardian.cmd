@echo off
REM Run-Guardian.cmd — Starts the Jules Bridge Guardian
REM Prevents sleep/lock. Unlocks on PIN 4874.
REM Turns monitor off. Keeps bridge alive.

setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo ERROR: Virtual environment not found.
    echo Run setup-bridge.cmd first.
    pause
    exit /b 1
)

echo ========================================
echo   JULES BRIDGE GUARDIAN
echo   Monitor will turn off in 5 seconds
echo   Type 4874 + Enter to unlock and exit
echo ========================================
echo.

"%PYTHON%" "%~dp0guardian.py" --wait-4pm %*

pause
