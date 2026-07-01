@echo off
:: Ensure-JulesSecrets.cmd — one-click persistent token + ngrok setup
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Ensure-JulesSecrets.ps1" -PromptForNgrok
pause
