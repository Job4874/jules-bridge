@echo off
REM Detached host offload — double-click or bridge spawn. NOT Cursor terminal.
cd /d C:\Users\abdul\.jules
start "Jules Offload" /MIN powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\abdul\.jules\Launch-Offload-Host.ps1"
echo Offload spawned in minimized host window. Log: jules_inbox\offload_logs\
