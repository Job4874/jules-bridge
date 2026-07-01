#Requires -Version 5.1
<#
.SYNOPSIS
  Full Jules Bridge setup for guest / non-admin Windows accounts.

.DESCRIPTION
  No Administrator required. Everything lives under:
    %LOCALAPPDATA%\JulesBridge\
    <repo>\user-persist\          (mirror survives some guest profile wipes)

  Installs Jules CLI, restores auth, pip deps, logon startup, and bridge.

.USAGE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Setup-NoAdminGuest.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Setup-NoAdminGuest.ps1 -SkipLogin
#>
[CmdletBinding()]
param(
    [switch]$SkipLogin,
    [switch]$SkipBridgeStart,
    [switch]$BlackScreenNow
)

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")

function Write-Step([string]$Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" -ForegroundColor Yellow }

$isAdmin = Test-IsAdministrator
Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
Write-Host "  JULES SETUP - guest / no-admin" -ForegroundColor Cyan
Write-Host "$('=' * 60)" -ForegroundColor Cyan
Write-Host "  User:   $env:USERNAME"
Write-Host "  Admin:  $isAdmin"
Write-Host "  Repo:   $RepoRoot"
Write-Host "  Store:  $(Get-JulesUserDataRoot)"
Write-Host "  Mirror: $(Get-JulesPersistMirror $RepoRoot)"

Write-Step "Restoring saved auth and .env"
Restore-JulesUserState $RepoRoot

Write-Step "Installing Jules CLI + Node (user-local)"
$setupArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $RepoRoot "scripts\setup-jules.ps1"),
    "-SkipBridge", "-SkipVerify", "-SkipLogin"
)
$setupProc = Start-Process -FilePath "powershell.exe" -ArgumentList $setupArgs -Wait -PassThru -NoNewWindow
if ($setupProc.ExitCode -ne 0) {
    Write-Warn "setup-jules.ps1 exited $($setupProc.ExitCode). Continuing with repair steps."
}

if (-not $SkipLogin) {
    if (Test-JulesAuthenticated) {
        Write-Ok "Jules auth data present"
    } else {
        Write-Step "Jules login required (browser opens - no admin needed)"
        $jules = Find-JulesExecutable
        if ($jules) {
            & $jules login
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "jules login completed"
            } else {
                Write-Warn "jules login failed or was cancelled. Re-run this script after signing in."
            }
        } else {
            Write-Warn "Jules CLI not found yet. Re-run after opening a new terminal."
        }
    }
}

Write-Step "Installing Python packages (pip --user)"
$pipResult = Install-PythonDependencies $RepoRoot
if ($pipResult.Ok) {
    Write-Ok "Python deps installed with $($pipResult.Python)"
} else {
    Write-Warn $pipResult.Error
}

Write-Step "Writing user PATH launchers"
$launchers = Write-UserEnvLauncher $RepoRoot
if ($launchers.Python) { Write-Ok "Python: $($launchers.Python)" } else { Write-Warn "Python not found" }
if ($launchers.Jules) { Write-Ok "Jules:  $($launchers.Jules)" } else { Write-Warn "Jules CLI not found" }

Write-Step "Saving auth + secrets for next reboot"
Backup-JulesUserState $RepoRoot

Write-Step "Registering logon auto-start (Startup folder - no admin)"
try {
    $lnk = Register-StartupShortcut $RepoRoot
    Write-Ok "Startup shortcut: $lnk"
} catch {
    Write-Warn "Startup shortcut failed: $($_.Exception.Message)"
}

Write-Step "Registering always-on bridge settings"
$alwaysArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $RepoRoot "scripts\Install-AlwaysOnBackdoor.ps1"),
    "-SkipScheduledTask"
)
if (-not $SkipBridgeStart) { $alwaysArgs += "-StartNow" }
if ($BlackScreenNow) { $alwaysArgs += "-BlackScreenNow" }
& powershell.exe @alwaysArgs

Write-Host "`n$('=' * 60)" -ForegroundColor Green
Write-Host "  SETUP COMPLETE (no admin)" -ForegroundColor Green
Write-Host "$('=' * 60)" -ForegroundColor Green
Write-Host "  After reboot / guest reset, run this again OR rely on Startup shortcut."
Write-Host "  Bridge:  Run-JulesBridge.cmd"
Write-Host "  CLI:     Open-JulesCLI.cmd"
Write-Host "  Re-setup: Setup-NoAdminGuest.cmd"
Write-Host ""
