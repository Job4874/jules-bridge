#Requires -Version 5.1
<#
.SYNOPSIS
  Unlock ghost mode — stops always-on hook and bridge only with operator password.

.USAGE
  & scripts\Ghost-Unlock.ps1 -Password "YOUR_PASSWORD"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Password,
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

. (Join-Path $PSScriptRoot "Ghost-State.ps1")
. (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")

if (-not (Test-GhostUnlock -Password $Password)) {
    Write-Host "[DENIED] Ghost state remains locked." -ForegroundColor Red
    exit 1
}

Write-Host "Unlocking ghost state..." -ForegroundColor Yellow
Clear-GhostLock -Password $Password -RepoRoot $RepoRoot | Out-Null

$startup = [Environment]::GetFolderPath("Startup")
$shortcut = Join-Path $startup "JulesBridge-AlwaysOn.lnk"
if (Test-Path $shortcut) {
    Remove-Item $shortcut -Force
    Write-Host "[OK] Removed logon startup shortcut" -ForegroundColor Green
}

Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "[OK] Ghost mode unlocked — bridge stopped, always-on disabled" -ForegroundColor Green
