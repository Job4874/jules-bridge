@echo off
:: Jules Mission Control — no admin required
:: Opens the real-time dashboard + bridge + cloud VMs in one shot.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-Dashboard.ps1"
