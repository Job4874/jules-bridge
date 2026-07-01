# Launch-Dashboard.ps1
# Opens PowerShell as Administrator, starts the bridge, boots cloud VMs,
# and opens the Jules Mission Control dashboard in the browser.
# Run this by right-clicking and "Run as Administrator", or via the .cmd wrapper.

param(
    [switch]$SkipVMBoot,
    [switch]$SkipBridge,
    [int]$BridgePort = 5000
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$BridgeUrl = "http://127.0.0.1:$BridgePort"
$Dashboard = Join-Path $Root "dashboard-ui\dist\index.html"

function Write-Banner($msg, $color = "Cyan") {
    Write-Host "`n$("=" * 60)" -ForegroundColor $color
    Write-Host "  $msg" -ForegroundColor $color
    Write-Host "$("=" * 60)" -ForegroundColor $color
}

function Test-BridgeAlive {
    try {
        $r = Invoke-WebRequest -Uri "$BridgeUrl/ping" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch { return $false }
}

# ---------------------------------------------------------------
Write-Banner "JULES MISSION CONTROL LAUNCHER" "Cyan"
Write-Host "  Root:      $Root" -ForegroundColor Gray
Write-Host "  Dashboard: $Dashboard" -ForegroundColor Gray
Write-Host "  Bridge:    $BridgeUrl" -ForegroundColor Gray

# ---------------------------------------------------------------
# 1. Check / start bridge
# ---------------------------------------------------------------
if (-not $SkipBridge) {
    if (Test-BridgeAlive) {
        Write-Host "`n[BRIDGE] Already running at $BridgeUrl" -ForegroundColor Green
    } else {
        Write-Host "`n[BRIDGE] Not detected — launching with ngrok..." -ForegroundColor Yellow
        $env:JULES_VM_SCRIPT_DIR = Join-Path $Root "vm_scripts"
        $launcher = Join-Path $Root "Run-JulesBridge.cmd"
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/k `"$launcher`"" `
            -WindowStyle Normal `
            -Verb RunAs 2>$null

        Write-Host "[BRIDGE] Waiting for bridge to come online..." -ForegroundColor Yellow
        $attempts = 0
        while (-not (Test-BridgeAlive) -and $attempts -lt 20) {
            Start-Sleep -Seconds 1
            $attempts++
            Write-Host "  [$attempts/20] Polling bridge..." -ForegroundColor DarkGray
        }
        if (Test-BridgeAlive) {
            Write-Host "[BRIDGE] Online! ✓" -ForegroundColor Green
        } else {
            Write-Host "[BRIDGE] WARNING: Bridge may not be responding yet." -ForegroundColor Red
        }
    }
}

# ---------------------------------------------------------------
# 2. Boot GCP worker (non-blocking background process)
# ---------------------------------------------------------------
if (-not $SkipVMBoot) {
    $gcpScript = Join-Path $Root "vm_scripts\Boot-GCP-Worker.ps1"
    if (Test-Path $gcpScript) {
        Write-Host "`n[GCP] Spawning GCP worker check in background..." -ForegroundColor Cyan
        Start-Process -FilePath "powershell.exe" `
            -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$gcpScript`"" `
            -WindowStyle Minimized
    }

    # Azure provisioning if script exists
    $azureScript = Join-Path $Root "vm_scripts\Provision-Azure-Offload.ps1"
    if (Test-Path $azureScript) {
        $azStatus = az account show --output json 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[AZURE] Logged in — spawning Azure VM provisioner..." -ForegroundColor Magenta
            Start-Process -FilePath "powershell.exe" `
                -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$azureScript`"" `
                -WindowStyle Minimized
        } else {
            Write-Host "[AZURE] Not logged in — skipping Azure provisioner (run 'az login' first)" -ForegroundColor DarkGray
        }
    }
}

# ---------------------------------------------------------------
# 3. Open dashboard in default browser
# ---------------------------------------------------------------
Write-Host "`n[DASHBOARD] Opening mission control..." -ForegroundColor Green
Start-Process $Dashboard

# ---------------------------------------------------------------
# 4. Live terminal summary loop (optional companion output)
# ---------------------------------------------------------------
Write-Banner "LIVE STATUS (refreshes every 10s — Ctrl+C to stop)" "DarkCyan"
while ($true) {
    try {
        $json = Invoke-RestMethod -Uri "$BridgeUrl/dashboard/status" -TimeoutSec 5 -ErrorAction Stop
        $cpu  = if ($json.resource_pressure.cpu_percent) { "{0:N1}%" -f $json.resource_pressure.cpu_percent } else { "?" }
        $mem  = if ($json.resource_pressure.memory_percent) { "{0:N1}%" -f $json.resource_pressure.memory_percent } else { "?" }
        $online = $json.cloud.online
        $total  = $json.cloud.total
        $comp   = $json.jules_fleet.completed
        $launched = $json.jules_fleet.launched
        $uptime = $json.bridge.uptime_human

        $ts = Get-Date -Format "HH:mm:ss"
        Write-Host "`r[$ts] Bridge: UP ($uptime) | CPU: $cpu | Mem: $mem | VMs: $online/$total online | Fleet: $comp/$launched complete   " -NoNewline -ForegroundColor Cyan
    } catch {
        Write-Host "`r[$(Get-Date -Format 'HH:mm:ss')] Bridge: OFFLINE or not responding...              " -NoNewline -ForegroundColor Red
    }
    Start-Sleep -Seconds 10
}
