@echo off
:: Launch-Bridge-WithVM.cmd
:: Opens the bridge + GCP boot in SEPARATE windows, NOT in Cursor terminal.
:: Double-click this from Explorer, or run it from any cmd prompt.

:: 1. Boot GCP offload worker in a minimized background window
start "GCP-Worker-Boot" /MIN powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0vm_scripts\Boot-GCP-Worker.ps1"

:: 2. Launch the bridge in its own visible window
set JULES_VM_SCRIPT_DIR=%~dp0vm_scripts
start "Jules-Bridge" /D "%~dp0" cmd /k "python bridge.py"
