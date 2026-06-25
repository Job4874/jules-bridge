@echo off
title Jules Bridge - KEEP THIS WINDOW OPEN
color 0A
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo ========================================
echo   JULES BRIDGE - dedicated terminal
echo   Logs also written to bridge.log
echo ========================================
echo.

echo [1/3] Stopping stale bridge on port 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
taskkill /F /IM ngrok.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Starting bridge + ngrok (logging to bridge.log)...
echo.
python start.py
if errorlevel 1 (
    echo.
    echo Bridge exited with error. See bridge.log
)
echo.
echo [3/3] Window stays open. Press any key to close bridge...
pause >nul
