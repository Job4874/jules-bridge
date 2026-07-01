#Requires -Version 5.1
<#
.SYNOPSIS
  Ping the school bridge from anywhere and show machine identity.

.PARAMETER BaseUrl
  Ngrok bridge URL. Default: parade-marrow-pulp.ngrok-free.dev

.PARAMETER Token
  BRIDGE_TOKEN value. Default: from .env or JULES-SECURE-999
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = "https://parade-marrow-pulp.ngrok-free.dev",
    [string]$Token = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvPath = Join-Path $RepoRoot ".env"

function Get-EnvToken {
    if (-not (Test-Path $EnvPath)) { return "" }
    foreach ($line in Get-Content -LiteralPath $EnvPath) {
        if ($line -match '^\s*BRIDGE_TOKEN\s*=\s*(.+)\s*$') {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

function Invoke-BridgeGet {
    param([string]$Path, [switch]$Auth)
    $headers = @{
        "ngrok-skip-browser-warning" = "true"
    }
    if ($Auth) {
        $headers["Authorization"] = "Bearer $Token"
    }
    return Invoke-RestMethod -Uri "$BaseUrl$Path" -Headers $headers -TimeoutSec 20
}

if (-not $Token) {
    $Token = Get-EnvToken
    if (-not $Token) {
        Write-Host "[ERROR] BRIDGE_TOKEN missing from $EnvPath" -ForegroundColor Red
        Write-Host "Run: .\scripts\Ensure-JulesSecrets.ps1" -ForegroundColor Yellow
        exit 1
    }
}

try {
    Write-Host ""
    Write-Host "Pinging $BaseUrl ..." -ForegroundColor Cyan

    $ping = Invoke-BridgeGet -Path "/ping"
    Write-Host "[OK] Bridge online" -ForegroundColor Green
    Write-Host "  Status   : $($ping.status)"
    Write-Host "  Identity : $($ping.identity)"
    Write-Host "  Hostname : $($ping.hostname)"
    Write-Host "  RAM (GB) : $($ping.ram_gb)"
    Write-Host "  GPG      : $($ping.gpg_configured)"

    $identity = Invoke-BridgeGet -Path "/host/identity"
    Write-Host ""
    Write-Host "Full identity:" -ForegroundColor Cyan
    $identity | ConvertTo-Json -Depth 4

    if (-not $ping.gpg_configured) {
        Write-Host ""
        Write-Host "GPG not registered yet. On the school PC run Copy-GithubGpg.cmd" -ForegroundColor Yellow
        Write-Host "Or fetch key remotely:" -ForegroundColor Yellow
        Write-Host "  GET $BaseUrl/host/gpg/public  (Authorization: Bearer <token>)" -ForegroundColor Gray
    } else {
        try {
            $gpg = Invoke-BridgeGet -Path "/host/gpg/public" -Auth
            Write-Host ""
            Write-Host "GPG key ready for GitHub (title: $($gpg.title))" -ForegroundColor Green
            Write-Host "  Add at: $($gpg.github_add_url)" -ForegroundColor Gray
        } catch {
            Write-Host ""
            Write-Host "[WARN] Could not fetch /host/gpg/public: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Tunnel may be down. On school PC run Run-JulesBridge.cmd" -ForegroundColor Yellow
    exit 1
}
