@echo off
title Tibin Codex v11
color 0B
cd /d "%~dp0"
echo.
echo  TIBIN CODEX v11 - launching...
echo  (Keep this window open)
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Codex-Tibin-OmniChannel.ps1"
echo.
echo  Codex exited.
pause
