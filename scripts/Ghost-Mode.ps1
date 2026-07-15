#Requires -Version 5.1
<#
.SYNOPSIS
  Ghost mode - full /god boot + black screen. Requires unlock code 48741721.

.USAGE
  & scripts\Ghost-Mode.ps1 -Code 48741721
  Double-click 48741721.cmd
#>
[CmdletBinding()]
param(
    [string]$Code = "",
    [string]$RepoRoot = "",
    [string]$UnlockPassword = ""
)

$GhostCode = "48741721"
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Deny {
    Write-Host "[DENIED] Invalid ghost code." -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Code)) {
    $Code = Read-Host "Ghost code"
}

if ($Code.Trim() -ne $GhostCode) { Deny }

Write-Host ""
Write-Host "  GHOST MODE $GhostCode - launching" -ForegroundColor Magenta
Write-Host "  Bridge + Jules CLI + ngrok + black screen" -ForegroundColor Magenta
Write-Host ""

Set-ExecutionPolicy Bypass -Scope Process -Force
& (Join-Path $RepoRoot "scripts\God-Paste.ps1") -RepoRoot $RepoRoot -BlackScreenNow

. (Join-Path $RepoRoot "scripts\Ghost-State.ps1")
$inputBlocked = Start-LocalInputBlock -RepoRoot $RepoRoot
if ($inputBlocked) {
    Write-Host "[OK] Local keyboard/mouse blocked (remote bridge still works)" -ForegroundColor Green
} else {
    Write-Host "[WARN] Could not block keyboard/mouse (may need admin). Monitor is off only." -ForegroundColor Yellow
}

try {
    & (Join-Path $RepoRoot "scripts\Register-MeshNode.ps1") -RepoRoot $RepoRoot | Out-Null
} catch { }

if ($UnlockPassword) {
    Set-GhostLocked -Password $UnlockPassword -RepoRoot $RepoRoot
    Write-Host "[OK] Ghost state LOCKED (password required to stop or interfere)" -ForegroundColor Green
}
