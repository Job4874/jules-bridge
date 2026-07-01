@echo off
REM Do NOT open this from Cursor chat links — use File Explorer double-click or GOD-BOOT.cmd
title Jules Setup (guest / no admin)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Setup-NoAdminGuest.ps1"
pause
