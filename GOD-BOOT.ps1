# Jules God-Mode boot — run this file (guest / no admin)
# In Cursor: right-click this file in Explorer → "Reveal in File Explorer" → double-click GOD-BOOT.cmd
# Or paste in PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File "c:\jules-bridge-master\GOD-BOOT.ps1"

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  /god — Jules Bridge boot (no admin)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Repo: $RepoRoot"
Write-Host ""

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Setup-NoAdminGuest.ps1")

Write-Host ""
Write-Host "Press Enter to close..."
Read-Host
