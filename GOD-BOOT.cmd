@echo off
REM /god boot launcher — double-click in File Explorer (NOT from Cursor chat links)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0GOD-BOOT.ps1"
