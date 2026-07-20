@echo off
setlocal

cd /d "%~dp0"

echo [1/3] Creating virtual environment...
python -m venv ".venv"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    exit /b 1
)

echo [2/3] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    exit /b 1
)

echo [3/3] Installing dependencies...
if exist "requirements.txt" (
    ".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
) else (
    ".venv\Scripts\python.exe" -m pip install flask flask-cors pyautogui pyngrok requests
)
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)

echo.
echo Jules Bridge setup completed successfully.
echo Run start-bridge.cmd to start the server.
