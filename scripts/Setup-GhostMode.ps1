#Requires -Version 5.1
<#
.SYNOPSIS
  Keep the school PC awake for ghost-mode (bridge runs, monitor can stay off).

.DESCRIPTION
  Sets AC power plan to never sleep and never hibernate. Does NOT turn off
  the display via software - use the monitor's physical power button so
  the PC keeps running while the screen stays dark.

.USAGE
  Run once before leaving (e.g. before 4:00 PM):
    .\scripts\Setup-GhostMode.ps1
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-PowerCfg {
    param([string[]]$Arguments)
    & powercfg @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "powercfg $($Arguments -join ' ') failed with exit $LASTEXITCODE"
    }
}

try {
    Write-Host ""
    Write-Host "Configuring ghost-mode power settings (plugged in)..." -ForegroundColor Cyan

    Invoke-PowerCfg @("/change", "standby-timeout-ac", "0")
    Invoke-PowerCfg @("/change", "hibernate-timeout-ac", "0")
    Invoke-PowerCfg @("/change", "monitor-timeout-ac", "0")

    Write-Host ""
    Write-Host "[OK] AC sleep/hibernate disabled" -ForegroundColor Green
    Write-Host "[OK] Display timeout set to Never (monitor off = use physical button)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Before you leave:" -ForegroundColor Yellow
    Write-Host "  1. Ensure bridge is running (Run-JulesBridge.cmd)"
    Write-Host "  2. Press the monitor power button (PC stays on, screen dark)"
    Write-Host "  3. Reach Jules remotely via ngrok /host/identity"
    Write-Host ""
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Try running PowerShell as Administrator if powercfg fails." -ForegroundColor Yellow
    exit 1
}
