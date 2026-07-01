#Requires -Version 5.1
<#
.SYNOPSIS
  Bootstrap the 64GB school PC as the remote ngrok bridge host.

.DESCRIPTION
  Run this ON THE SCHOOL PC (not your laptop):
    1. Ensure persistent secrets (BRIDGE_TOKEN, NGROK_AUTHTOKEN)
    2. Label host as [SCHOOL_COMPUTE]
    3. Launch Run-JulesBridge.cmd (bridge + ngrok)

.USAGE
  .\scripts\Bootstrap-SchoolBridge.ps1
  .\scripts\Bootstrap-SchoolBridge.ps1 -NgrokAuthtoken "YOUR_TOKEN"
#>
[CmdletBinding()]
param(
    [string]$NgrokAuthtoken = "",
    [switch]$PromptForNgrok
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)

if ($ramGb -lt 32) {
    Write-Host "[ERROR] This machine reports ${ramGb}GB RAM." -ForegroundColor Red
    Write-Host "Bootstrap-SchoolBridge.ps1 must run on the 64GB school PC, not a laptop." -ForegroundColor Yellow
    Write-Host "On a laptop use: .\scripts\Setup-LaptopIdentity.ps1" -ForegroundColor Yellow
    exit 1
}

$secretsScript = Join-Path $PSScriptRoot "Ensure-JulesSecrets.ps1"
$schoolScript = Join-Path $PSScriptRoot "Setup-SchoolIdentity.ps1"
$launcher = Join-Path $RepoRoot "Run-JulesBridge.cmd"

$secretArgs = @()
if ($NgrokAuthtoken) { $secretArgs += @("-NgrokAuthtoken", $NgrokAuthtoken) }
if ($PromptForNgrok) { $secretArgs += "-PromptForNgrok" }

& $secretsScript @secretArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $schoolScript
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Starting school bridge + ngrok..." -ForegroundColor Cyan
Start-Process -FilePath $launcher -WorkingDirectory $RepoRoot
Write-Host "Verify from anywhere: .\scripts\Reach-SchoolBridge.ps1" -ForegroundColor Green
