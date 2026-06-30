# Quick-Boot-Jules-Cockpit.ps1
# Boots the local bridge, dashboard UI, optional VM worker check, and browser.

[CmdletBinding()]
param(
    [switch]$SkipVMBoot,
    [switch]$SkipBridge,
    [switch]$NoDashboard,
    [switch]$NoBrowser,
    [int]$BridgePort = 5000,
    [int]$DashboardPort = 5173
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSCommandPath
$BridgeUrl = "http://127.0.0.1:$BridgePort"
$DashboardUrl = "http://127.0.0.1:$DashboardPort/"
$DashboardDir = Join-Path $Root "dashboard-ui"
$RuntimeRoot = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
$BundledNodeBin = Join-Path $RuntimeRoot "node\bin"
$BundledBin = Join-Path $RuntimeRoot "bin"
$Pnpm = Join-Path $BundledBin "pnpm.cmd"

function Write-Step($Message, $Color = "Cyan") {
    Write-Host "[quick-boot] $Message" -ForegroundColor $Color
}

function Test-HttpOk($Url, $TimeoutSec = 3) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
    } catch {
        return $false
    }
}

function Wait-ForHttp($Url, $Seconds = 25) {
    for ($i = 0; $i -lt $Seconds; $i++) {
        if (Test-HttpOk $Url 2) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Resolve-Pnpm {
    if (Test-Path -LiteralPath $Pnpm) {
        return $Pnpm
    }
    $cmd = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "pnpm.cmd was not found. Expected bundled runtime at $Pnpm or pnpm on PATH."
}

function Get-DashboardPath {
    $paths = @($BundledNodeBin, $BundledBin) | Where-Object { Test-Path -LiteralPath $_ }
    if ($paths.Count -eq 0) {
        return $env:PATH
    }
    return (($paths -join ";") + ";" + $env:PATH)
}

Write-Host ""
Write-Host "Jules Bridge Quick Boot" -ForegroundColor Green
Write-Host "Repo:      $Root" -ForegroundColor DarkGray
Write-Host "Bridge:    $BridgeUrl" -ForegroundColor DarkGray
Write-Host "Dashboard: $DashboardUrl" -ForegroundColor DarkGray
Write-Host ""

if (-not $SkipVMBoot) {
    $vmBoot = Join-Path $Root "vm_scripts\Boot-GCP-Worker.ps1"
    if (Test-Path -LiteralPath $vmBoot) {
        Write-Step "starting VM worker check"
        Start-Process -FilePath "powershell.exe" `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $vmBoot) `
            -WorkingDirectory $Root `
            -WindowStyle Minimized
    } else {
        Write-Step "VM worker script missing; skipping" "DarkYellow"
    }
} else {
    Write-Step "VM worker check skipped"
}

if (-not $SkipBridge) {
    if (Test-HttpOk "$BridgeUrl/ping" 2) {
        Write-Step "bridge already online at $BridgeUrl" "Green"
    } else {
        $bridgeLauncher = Join-Path $Root "Run-JulesBridge.cmd"
        if (-not (Test-Path -LiteralPath $bridgeLauncher)) {
            throw "Bridge launcher missing: $bridgeLauncher"
        }
        Write-Step "starting bridge/ngrok window"
        Start-Process -FilePath $bridgeLauncher -WorkingDirectory $Root -WindowStyle Normal
        if (Wait-ForHttp "$BridgeUrl/ping" 30) {
            Write-Step "bridge is online" "Green"
        } else {
            Write-Step "bridge did not answer /ping yet; continuing with dashboard boot" "Yellow"
        }
    }
} else {
    Write-Step "bridge boot skipped"
}

if (-not $NoDashboard) {
    if (-not (Test-Path -LiteralPath $DashboardDir)) {
        throw "Dashboard directory missing: $DashboardDir"
    }

    if (Test-HttpOk $DashboardUrl 2) {
        Write-Step "dashboard already online at $DashboardUrl" "Green"
    } else {
        $resolvedPnpm = Resolve-Pnpm
        $dashboardPath = Get-DashboardPath
        $dashboardCommand = "set ""PATH=$dashboardPath"" && cd /d ""$DashboardDir"" && ""$resolvedPnpm"" run dev -- --host 127.0.0.1 --port $DashboardPort"
        Write-Step "starting dashboard UI server"
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList @("/k", $dashboardCommand) `
            -WorkingDirectory $DashboardDir `
            -WindowStyle Normal

        if (Wait-ForHttp $DashboardUrl 30) {
            Write-Step "dashboard is online" "Green"
        } else {
            Write-Step "dashboard did not answer yet; browser may need a manual refresh" "Yellow"
        }
    }
} else {
    Write-Step "dashboard boot skipped"
}

if (-not $NoBrowser) {
    Write-Step "opening cockpit in the default browser"
    Start-Process $DashboardUrl
} else {
    Write-Step "browser launch skipped"
}

Write-Host ""
Write-Host "Quick boot complete." -ForegroundColor Green
