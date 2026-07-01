#Requires -Version 5.1
<#
.SYNOPSIS
  Keep Jules Bridge reachable without Administrator rights.

  Uses Startup folder (not scheduled tasks) when non-admin.
  Power plan changes are skipped without admin; a user-level keep-awake hook runs instead.
#>
[CmdletBinding()]
param(
    [switch]$BlackScreenNow,
    [switch]$SkipScheduledTask,
    [switch]$SkipPowerTuning,
    [switch]$SkipStartupShortcut,
    [switch]$StartNow
)

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")

$BridgeLauncher = Join-Path $RepoRoot "Run-JulesBridge.cmd"
$CliLauncher = Join-Path $RepoRoot "Open-JulesCLI.cmd"
$TaskName = "JulesBridge-AlwaysOn"
$NgrokDomain = "parade-marrow-pulp.ngrok-free.dev"
$IsAdmin = Test-IsAdministrator

function Write-Step([string]$Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" -ForegroundColor Yellow }

function Turn-DisplayOff {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public class JulesDisplayPower {
    [DllImport("user32.dll")]
    public static extern int SendMessage(int hWnd, int hMsg, int wParam, int lParam);
    public static void MonitorOff() {
        SendMessage(-1, 0x0112, 0xF170, 2);
    }
}
"@ -ErrorAction SilentlyContinue
    [JulesDisplayPower]::MonitorOff()
    Write-Ok "Display powered off (PC still running)"
}

function Test-BridgeAlive {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5000/ping" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch { return $false }
}

function Test-TunnelAlive {
    try {
        $r = Invoke-WebRequest -Uri "https://$NgrokDomain/ping" -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop `
            -Headers @{ "ngrok-skip-browser-warning" = "true" }
        return $r.StatusCode -eq 200
    } catch { return $false }
}

function Stop-StaleBridge {
    Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

function Start-BridgeRemote {
    if (-not (Test-Path $BridgeLauncher)) { throw "Missing launcher: $BridgeLauncher" }
    Restore-JulesUserState $RepoRoot
    Write-UserEnvLauncher $RepoRoot | Out-Null
    Invoke-UserKeepAwake
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList @("/c", "`"$BridgeLauncher`"") `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Minimized
    Write-Ok "Bridge + ngrok starting minimized"
}

function Set-AlwaysAwakePower {
    if (-not $IsAdmin) {
        Write-Warn "No admin — skipping powercfg. Using user keep-awake instead."
        Invoke-UserKeepAwake
        return
    }
    Write-Step "Configuring power (admin): PC never sleeps, display may turn off"
    $active = (powercfg /getactivescheme) -replace '.*GUID: ([a-f0-9-]+).*', '$1'
    if ($active -match '^[a-f0-9-]{36}$') {
        powercfg /SETACVALUEINDEX $active 238C9FA8-0AAD-41ED-83F4-97BE242C8F20 29f6c1db-86da-48c5-9fdb-f2b67b1f44da 0 | Out-Null
        powercfg /SETACVALUEINDEX $active 238C9FA8-0AAD-41ED-83F4-97BE242C8F20 94ac6d29-73ce-41a6-809f-6363ba21b47e 0 | Out-Null
        powercfg /SETACVALUEINDEX $active 238C9FA8-0AAD-41ED-83F4-97BE242C8F20 7648efa3-dd9c-4e3e-b566-50f929386280 0 | Out-Null
        powercfg /SETACVALUEINDEX $active 238C9FA8-0AAD-41ED-83F4-97BE242C8F20 238c9fa8-0aad-41ed-83f4-97be242c8f20 60 | Out-Null
        powercfg /SETACTIVE $active | Out-Null
        Write-Ok "AC power: sleep/hibernate disabled"
    }
}

function Register-LogonTask {
    if (-not $IsAdmin) {
        Write-Warn "Scheduled task needs admin — using Startup folder instead."
        return
    }
    $scriptPath = Join-Path $RepoRoot "scripts\Start-AlwaysOnAtLogon.ps1"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Ok "Scheduled task '$TaskName' registered"
}

Write-Host "`n$('=' * 60)" -ForegroundColor Green
Write-Host "  JULES ALWAYS-ON (no-admin safe)" -ForegroundColor Green
Write-Host "$('=' * 60)" -ForegroundColor Green
Write-Host "  Admin:  $IsAdmin"
Write-Host "  Repo:   $RepoRoot"
Write-Host "  Store:  $(Get-JulesUserDataRoot)"
Write-Host "  Tunnel: https://$NgrokDomain"

Restore-JulesUserState $RepoRoot
Write-UserEnvLauncher $RepoRoot | Out-Null

if (-not $SkipPowerTuning) { Set-AlwaysAwakePower }

if (-not $SkipStartupShortcut) {
    Write-Step "Startup folder auto-start (works without admin)"
    try {
        $lnk = Register-StartupShortcut $RepoRoot
        Write-Ok "Startup shortcut: $lnk"
    } catch {
        Write-Warn $_.Exception.Message
    }
}

if (-not $SkipScheduledTask -and $IsAdmin) {
    Write-Step "Optional scheduled task (admin only)"
    try { Register-LogonTask } catch { Write-Warn $_.Exception.Message }
}

if ($StartNow -or $BlackScreenNow) {
    Write-Step "Starting bridge now"
    if (-not (Test-TunnelAlive)) {
        Stop-StaleBridge
        Start-BridgeRemote
        for ($i = 1; $i -le 30; $i++) {
            Start-Sleep -Seconds 2
            if ((Test-BridgeAlive) -and (Test-TunnelAlive)) { break }
            Write-Host "  [$i/30] waiting..." -ForegroundColor DarkGray
        }
    }
    if (Test-TunnelAlive) {
        Write-Ok "Remote: https://$NgrokDomain/ping"
    } elseif (Test-BridgeAlive) {
        Write-Warn "Local bridge up; ngrok still connecting — see bridge.log"
    } else {
        Write-Warn "Bridge not up. Run Setup-NoAdminGuest.cmd first."
    }
    Backup-JulesUserState $RepoRoot
}

if ($BlackScreenNow) {
    Write-Step "Black screen"
    Start-Sleep -Seconds 2
    Turn-DisplayOff
}

Write-Host "`n  Local:   http://127.0.0.1:5000/ping"
Write-Host "  Remote:  https://$NgrokDomain/ping"
Write-Host "  CLI:     $CliLauncher"
Write-Host "  Setup:   Setup-NoAdminGuest.cmd"
Write-Host ""
