@echo off
title GHOST READY 48741721
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Ghost-Ready.ps1" -Code 48741721
pause
