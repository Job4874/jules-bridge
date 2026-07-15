#Requires -Version 5.1
<#
.SYNOPSIS
  Wire Gmail app password into all Jules .env mirrors (no admin).

.USAGE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Set-GmailAppPassword.ps1 -AppPassword "xxxx xxxx xxxx xxxx"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AppPassword
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$password = ($AppPassword -replace "\s", "").Trim()
if ($password.Length -lt 16) {
    throw "Gmail app password must be at least 16 characters."
}

$targets = @(
    (Join-Path $RepoRoot ".env"),
    (Join-Path $env:LOCALAPPDATA "JulesBridge\.env"),
    (Join-Path $RepoRoot "user-persist\.env")
)

foreach ($path in $targets) {
    if (-not (Test-Path $path)) { continue }
    $lines = Get-Content $path
    $updated = $false
    $out = foreach ($line in $lines) {
        if ($line -match '^GMAIL_APP_PASSWORD=') {
            $updated = $true
            "GMAIL_APP_PASSWORD=$password"
        } else {
            $line
        }
    }
    if (-not $updated) {
        $out += "GMAIL_APP_PASSWORD=$password"
    }
    $out | Set-Content $path -Encoding UTF8
    Write-Host "[OK] $path" -ForegroundColor Green
}

Write-Host "Gmail app password saved. Test with:" -ForegroundColor Cyan
Write-Host "  python notify_email.py `"Jules test`" `"Email wired on $(hostname)`""
