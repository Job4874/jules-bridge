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

echo [1/4] Ensuring persistent secrets (tokens + ngrok auth)...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Ensure-JulesSecrets.ps1"
if errorlevel 1 (
    echo.
    echo Secrets setup failed. Remote tunnel requires NGROK_AUTHTOKEN.
    echo Run: scripts\Ensure-JulesSecrets.ps1 -PromptForNgrok
    pause
    exit /b 1
)

echo [2/4] Stopping stale bridge on port 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
taskkill /F /IM ngrok.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [3/4] Starting bridge + ngrok (logging to bridge.log)...
echo.
python start.py
if errorlevel 1 (
    echo.
    echo Bridge exited with error. See bridge.log
)
echo.
echo [4/4] Window stays open. Press any key to close bridge...
pause >nul
