@echo off
title Jules Always-On Remote
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Setup-NoAdminGuest.ps1" -SkipLogin
pause
