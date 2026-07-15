@echo off
REM Runs silently at Windows logon via Startup folder (no admin).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0scripts\Start-AlwaysOnAtLogon.ps1"
