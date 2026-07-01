#Requires -Version 5.1
<#
.SYNOPSIS
  Run on LAPTOP Cursor - verify connection to school PC ghost bridge.
#>
[CmdletBinding()]
param(
    [string]$RemoteUrl = "https://parade-marrow-pulp.ngrok-free.dev",
    [string]$BridgeToken = "JULES-SECURE-999",
    [string]$RepoRoot = ""
)

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
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
    $id = Invoke-RestMethod "$RemoteUrl/host/identity" -Headers $headers -TimeoutSec 10
    Write-Host "[OK] Host: $($id.host_id) ($($id.location), $($id.ram_gb)GB RAM)" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Host identity unavailable" -ForegroundColor Yellow
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

Write-Host ""
Write-Host "  Saved: .env.laptop" -ForegroundColor Green
Write-Host "  Remote bridge: $RemoteUrl" -ForegroundColor Green
Write-Host "  Use this URL in laptop Cursor to control school PC" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
