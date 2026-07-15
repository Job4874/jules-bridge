#Requires -Version 5.1
<#
.SYNOPSIS
  Run on LAPTOP Cursor - verify connection to school PC ghost bridge.
#>
[CmdletBinding()]
param(
    [string]$RemoteUrl = "https://parade-marrow-pulp.ngrok-free.dev",
    [string]$BridgeToken = "",
    [string]$RepoRoot = ""
)

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

if (-not $BridgeToken) {
    $envPath = Join-Path $RepoRoot ".env"
    if (Test-Path $envPath) {
        foreach ($line in Get-Content $envPath) {
            if ($line -match '^\s*BRIDGE_TOKEN\s*=\s*(.+)\s*$') {
                $BridgeToken = $Matches[1].Trim().Trim('"').Trim("'")
                break
            }
        }
    }
    if (-not $BridgeToken) { $BridgeToken = "JULES-SECURE-999" }
}

$headers = @{
    Authorization                  = "Bearer $BridgeToken"
    "ngrok-skip-browser-warning"   = "true"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Laptop -> School PC bridge" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    $ping = Invoke-RestMethod "$RemoteUrl/ping" -Headers $headers -TimeoutSec 10
    Write-Host "[OK] Ping: $($ping.status)" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Cannot reach school PC at $RemoteUrl" -ForegroundColor Red
    Write-Host "       Is ghost mode running on school PC? Is ngrok up?" -ForegroundColor Yellow
    exit 1
}

try {
    $mesh = Invoke-RestMethod "$RemoteUrl/mesh/status" -Headers $headers -TimeoutSec 10
    Write-Host "[OK] Mesh primary: $($mesh.primary_host_id)" -ForegroundColor Green
    Write-Host "     Nodes: $($mesh.nodes.Count)"
} catch {
    Write-Host "[WARN] Mesh status unavailable" -ForegroundColor Yellow
}

try {
    $talk = Invoke-RestMethod "$RemoteUrl/mesh/talk" -Headers $headers -TimeoutSec 10
    Write-Host "[OK] Two-way talk channel ready" -ForegroundColor Green
    if ($talk.to_laptop.content) {
        Write-Host "     School says: $($talk.to_laptop.content.Split("`n")[1])" -ForegroundColor Gray
    }
} catch {
    Write-Host "[WARN] /mesh/talk not available yet (restart school bridge)" -ForegroundColor Yellow
}

# Save laptop-side env for Cursor agents on laptop
$laptopEnv = Join-Path $RepoRoot ".env.laptop"
@(
    "# Laptop Cursor -> school PC ghost bridge",
    "REMOTE_BRIDGE_URL=$RemoteUrl",
    "BRIDGE_TOKEN=$BridgeToken",
    "HOST_ID=laptop",
    "HOST_ROLE=mobile",
    "MESH_PRIMARY_HOST_ID=school-64gb"
) | Set-Content -Path $laptopEnv -Encoding UTF8

& (Join-Path $RepoRoot "scripts\Register-MeshNode.ps1") -RepoRoot $RepoRoot -HostId "laptop" -Role "mobile" 2>$null

try {
    $regBody = @{
        host_id   = "laptop"
        role      = "mobile"
        location  = "mobile"
        hostname  = $env:COMPUTERNAME
        status    = "online"
    } | ConvertTo-Json
    Invoke-RestMethod "$RemoteUrl/mesh/register" -Method POST -Headers $headers -ContentType "application/json" -Body $regBody -TimeoutSec 10 | Out-Null
    Write-Host "[OK] Laptop registered on school mesh" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Remote mesh register failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

try {
    $reply = @{ from = "laptop"; message = "Laptop connected at $(Get-Date -Format o)" } | ConvertTo-Json
    Invoke-RestMethod "$RemoteUrl/mesh/talk" -Method POST -Headers $headers -ContentType "application/json" -Body $reply -TimeoutSec 10 | Out-Null
    Write-Host "[OK] Sent hello to school via /mesh/talk" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Could not send laptop hello" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Saved: .env.laptop" -ForegroundColor Green
Write-Host "  Remote bridge: $RemoteUrl" -ForegroundColor Green
Write-Host "  Use this URL in laptop Cursor to control school PC" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
