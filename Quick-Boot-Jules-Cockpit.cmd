@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0Quick-Boot-Jules-Cockpit.ps1" %*
