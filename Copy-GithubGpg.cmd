@echo off
title Copy Jules GPG key for GitHub
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Copy-GithubGpg.ps1"
pause
