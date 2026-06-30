@echo off
setlocal
:: Jules Bridge cockpit quick boot.
:: Opens the real-time dashboard + bridge + VM worker check in one shot.
powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0Quick-Boot-Jules-Cockpit.ps1"
