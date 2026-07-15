#Requires -Version 5.1
<#
.SYNOPSIS
  Full ghost boot: bridge + ngrok + black screen + ghost lock + mesh (no admin).

.USAGE
  powershell -ExecutionPolicy Bypass -File scripts\Ghost-Ready.ps1 -Code 48741721 -UnlockPassword "YOUR_PASSWORD"
#>
[CmdletBinding()]
param(
    [string]$Code = "48741721",
    [string]$UnlockPassword = "",
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Continue"
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$NgrokDomain = "parade-marrow-pulp.ngrok-free.dev"
$BridgeToken = "JULES-SECURE-999"
$RemoteUrl = "https://$NgrokDomain"

function Test-BridgeUp {
    try {
        return ((Invoke-WebRequest "http://127.0.0.1:5000/ping" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200)
    } catch { return $false }
}

function Test-TunnelUp {
    try {
        return ((Invoke-WebRequest "$RemoteUrl/ping" -TimeoutSec 8 -UseBasicParsing `
            -Headers @{ "ngrok-skip-browser-warning" = "true" }).StatusCode -eq 200)
    } catch { return $false }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  GHOST READY - school 64GB PC" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

# Step 1: Ghost mode boot (bridge + black screen + optional lock)
$ghostArgs = @{
    RepoRoot = $RepoRoot
    Code     = $Code
}
if ($UnlockPassword) { $ghostArgs.UnlockPassword = $UnlockPassword }
& (Join-Path $RepoRoot "scripts\Ghost-Mode.ps1") @ghostArgs

# Step 2: Ensure ngrok tunnel (laptop Cursor needs remote URL)
if (-not (Test-TunnelUp)) {
    Write-Host ""
    Write-Host "==> Starting ngrok tunnel (needed for laptop Cursor)..." -ForegroundColor Cyan
    . (Join-Path $RepoRoot "scripts\Ensure-UserPersist.ps1")
    $py = Find-PythonExecutable
    if ($py) {
        Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        if (-not (Test-BridgeUp)) {
            $env:BRIDGE_TOKEN = $BridgeToken
            $env:PYTHONIOENCODING = "utf-8"
            Start-Process -FilePath $py -ArgumentList "start.py" -WorkingDirectory $RepoRoot -WindowStyle Minimized
            for ($i = 1; $i -le 45; $i++) {
                Start-Sleep -Seconds 2
                if ((Test-BridgeUp) -and (Test-TunnelUp)) { break }
            }
        } else {
            Start-Process -FilePath $py -ArgumentList "start.py" -WorkingDirectory $RepoRoot -WindowStyle Minimized
            Start-Sleep -Seconds 20
        }
    }
}

# Step 3: Mesh registry
& (Join-Path $RepoRoot "scripts\Register-MeshNode.ps1") -RepoRoot $RepoRoot | Out-Null

# Step 3b: Sync ghost state through bridge API when local bridge is up
if (Test-BridgeUp) {
    try {
        $headers = @{ Authorization = "Bearer $BridgeToken" }
        $ghost = Invoke-RestMethod "http://127.0.0.1:5000/ghost/status" -TimeoutSec 5 -UseBasicParsing
        Write-Host "[OK] Bridge ghost status: locked=$($ghost.ghost_locked) host=$($ghost.host_id)" -ForegroundColor Green
        if ($UnlockPassword -and -not $ghost.ghost_locked) {
            $body = @{ password = $UnlockPassword } | ConvertTo-Json
            Invoke-RestMethod "http://127.0.0.1:5000/ghost/lock" -Method POST -Body $body -ContentType "application/json" -Headers $headers -TimeoutSec 10 | Out-Null
            Write-Host "[OK] Ghost lock confirmed via bridge API" -ForegroundColor Green
        }
    } catch {
        Write-Host "[WARN] Bridge ghost API sync skipped: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Step 4: Write laptop connect card
$cardPath = Join-Path $RepoRoot "jules_inbox\LAPTOP_CURSOR_CONNECT.json"
$card = @{
    primary_host_id = "school-64gb"
    remote_bridge     = $RemoteUrl
    bridge_token     = $BridgeToken
    ngrok_header     = "ngrok-skip-browser-warning: true"
    auth_header      = "Authorization: Bearer $BridgeToken"
    ping             = "$RemoteUrl/ping"
    mesh_status      = "$RemoteUrl/mesh/status"
    host_identity    = "$RemoteUrl/host/identity"
    ghost_status     = "$RemoteUrl/ghost/status"
    mesh_talk        = "$RemoteUrl/mesh/talk"
    cursor_on_laptop = @{
        step1 = "Clone or sync jules-bridge-master to laptop"
        step2 = "In laptop Cursor terminal run scripts/Laptop-ConnectSchoolBridge.ps1"
        step3 = "Or paste LAPTOP-CONNECT.txt one-liner on laptop"
        step4 = "Cursor agent uses remote bridge for shell/ui on school PC"
    }
    updated_utc = (Get-Date).ToUniversalTime().ToString("o")
}
$card | ConvertTo-Json -Depth 5 | Set-Content -Path $cardPath -Encoding UTF8

# Step 5: Report
$localOk = Test-BridgeUp
$tunnelOk = Test-TunnelUp
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  GHOST READY RESULT" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Local bridge:  $(if ($localOk) { 'UP' } else { 'DOWN' })  http://127.0.0.1:5000"
Write-Host "  Remote tunnel: $(if ($tunnelOk) { 'UP' } else { 'DOWN - add ngrok authtoken' })  $RemoteUrl"
Write-Host "  Ghost lock:    $(if (Test-Path "$env:LOCALAPPDATA\JulesBridge\ghost_state.json") { 'configured' } else { 'not set - pass -UnlockPassword' })"
Write-Host "  Mesh:          jules_inbox/MESH_REGISTRY.json"
Write-Host "  Laptop card:   jules_inbox/LAPTOP_CURSOR_CONNECT.json"
Write-Host ""
if (-not $tunnelOk) {
    Write-Host "  LAPTOP BLOCKER: ngrok tunnel down." -ForegroundColor Yellow
    Write-Host "  Run once: ngrok config add-authtoken YOUR_TOKEN" -ForegroundColor Yellow
    Write-Host "  Get token: https://dashboard.ngrok.com/get-started/your-authtoken" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  ON LAPTOP (Cursor) - paste LAPTOP-CONNECT.txt" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
