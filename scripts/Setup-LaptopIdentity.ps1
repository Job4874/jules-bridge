#Requires -Version 5.1
<#
.SYNOPSIS
  Label this machine as a local laptop node (not the school PC).

.DESCRIPTION
  Writes SYSTEM_ID.txt, sets JULES_IDENTITY and JULES_CONTEXT=[LOCAL] in .env,
  and mirrors to ~/.jules/.env. Use Setup-SchoolIdentity.ps1 only on the 64GB school PC.

.USAGE
  .\scripts\Setup-LaptopIdentity.ps1
#>
[CmdletBinding()]
param(
    [string]$Identity = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SystemIdPath = Join-Path $RepoRoot "SYSTEM_ID.txt"
$EnvPath = Join-Path $RepoRoot ".env"

function Get-RamGb {
    $bytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    return [math]::Round($bytes / 1GB)
}

function Set-EnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )
    $lines = @()
    if (Test-Path $Path) {
        $lines = @(Get-Content -LiteralPath $Path)
    }
    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
            $found = $true
            "$Key=$Value"
        } else {
            $line
        }
    }
    if (-not $found) {
        if ($updated.Count -gt 0 -and $updated[-1] -ne "") {
            $updated += ""
        }
        $updated += "$Key=$Value"
    }
    Set-Content -LiteralPath $Path -Value $updated -Encoding UTF8
}

try {
    $ramGb = Get-RamGb
    if (-not $Identity) {
        $Identity = "Laptop-PC-RAM-$ramGb-GB"
    }

    Set-Content -LiteralPath $SystemIdPath -Value $Identity -Encoding UTF8

    if (-not (Test-Path $EnvPath)) {
        $example = Join-Path $RepoRoot ".env.example"
        if (Test-Path $example) {
            Copy-Item -LiteralPath $example -Destination $EnvPath
        } else {
            New-Item -ItemType File -Path $EnvPath -Force | Out-Null
        }
    }

    Set-EnvValue -Path $EnvPath -Key "JULES_IDENTITY" -Value $Identity
    Set-EnvValue -Path $EnvPath -Key "JULES_CONTEXT" -Value "[LOCAL]"

    $mirrorScript = Join-Path $PSScriptRoot "ensure_jules_secrets.py"
    if (Test-Path $mirrorScript) {
        & python $mirrorScript | Out-Null
    }

    Write-Host ""
    Write-Host "Laptop identity configured" -ForegroundColor Green
    Write-Host "  RAM       : $ramGb GB"
    Write-Host "  Identity  : $Identity"
    Write-Host "  Context   : [LOCAL]"
    Write-Host ""
    Write-Host "Do NOT run Run-JulesBridge.cmd on this laptop if the school PC should own ngrok." -ForegroundColor Yellow
    Write-Host "On the 64GB school PC run: .\scripts\Bootstrap-SchoolBridge.ps1" -ForegroundColor Cyan
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
