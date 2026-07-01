#Requires -Version 5.1
<#
.SYNOPSIS
  Label this machine as the Jules school PC (64GB RAM workstation).

.DESCRIPTION
  Writes SYSTEM_ID.txt, sets JULES_IDENTITY and JULES_CONTEXT in .env, and
  prints the identity string Jules will report on GET /host/identity.

.USAGE
  .\scripts\Setup-SchoolIdentity.ps1
  .\scripts\Setup-SchoolIdentity.ps1 -Identity "School-64GB-Workstation-ID-64"
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
        $Identity = "School-PC-RAM-$ramGb-GB"
    }

    $systemLabel = "School-PC-RAM-$ramGb-GB"
    Set-Content -LiteralPath $SystemIdPath -Value $systemLabel -Encoding UTF8

    if (-not (Test-Path $EnvPath)) {
        $example = Join-Path $RepoRoot ".env.example"
        if (Test-Path $example) {
            Copy-Item -LiteralPath $example -Destination $EnvPath
        } else {
            New-Item -ItemType File -Path $EnvPath -Force | Out-Null
        }
    }

    Set-EnvValue -Path $EnvPath -Key "JULES_IDENTITY" -Value $Identity
    Set-EnvValue -Path $EnvPath -Key "JULES_CONTEXT" -Value "[SCHOOL_COMPUTE]"

    Write-Host ""
    Write-Host "School identity configured" -ForegroundColor Green
    Write-Host "  RAM       : $ramGb GB"
    Write-Host "  Identity  : $Identity"
    Write-Host "  Context   : [SCHOOL_COMPUTE]"
    Write-Host "  SYSTEM_ID : $SystemIdPath"
    Write-Host ""
    Write-Host "Restart bridge.py so /host/identity picks this up." -ForegroundColor Cyan
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
