@echo off
title Finish GitHub GPG setup (copy + paste)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Copy-GithubGpg.ps1"
if errorlevel 1 pause
