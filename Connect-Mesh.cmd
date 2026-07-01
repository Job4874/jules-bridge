@echo off
title Jules Mesh Connect
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Connect-Mesh.ps1"
echo.
pause
