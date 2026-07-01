#Requires -Version 5.1
# Logon hook: restore auth, repair tools if needed, start bridge, optional black screen.
$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")

$BridgeLauncher = Join-Path $RepoRoot "Run-JulesBridge.cmd"
$LogPath = Join-Path (Get-JulesUserDataRoot) "always_on.log"

function Write-Log([string]$Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    New-Item -ItemType Directory -Force -Path (Get-JulesUserDataRoot) | Out-Null
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

function Test-BridgeAlive {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5000/ping" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch { return $false }
}

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
"@
    [JulesDisplayPower]::MonitorOff()
}

Write-Log "Logon hook started (user=$env:USERNAME admin=$(Test-IsAdministrator))"

. (Join-Path $PSScriptRoot "Ghost-State.ps1")
$ghostLocked = Test-GhostLocked
if ($ghostLocked) {
    Write-Log "Ghost mode LOCKED — enforcing always-on bridge + black screen"
}

Restore-JulesUserState $RepoRoot
Write-UserEnvLauncher $RepoRoot | Out-Null
Invoke-UserKeepAwake

$python = Find-PythonExecutable
$jules = Find-JulesExecutable
if (-not $python -or -not $jules) {
    Write-Log "Missing tools (python=$([bool]$python) jules=$([bool]$jules)) — running Setup-NoAdminGuest.ps1"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Setup-NoAdminGuest.ps1") -SkipLogin -SkipBridgeStart
}

if (-not (Test-BridgeAlive)) {
    if (Test-Path $BridgeLauncher) {
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList @("/c", "`"$BridgeLauncher`"") `
            -WorkingDirectory $RepoRoot `
            -WindowStyle Minimized
        Write-Log "Launched bridge minimized"
        $waitMax = if ($ghostLocked) { 45 } else { 15 }
        Start-Sleep -Seconds $waitMax
    } else {
        Write-Log "Missing bridge launcher"
    }
} else {
    Write-Log "Bridge already running"
}

if ($ghostLocked -and -not (Test-BridgeAlive)) {
    Write-Log "Ghost locked but bridge still down — retrying God-Paste"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\God-Paste.ps1") -RepoRoot $RepoRoot
}

Backup-JulesUserState $RepoRoot
Start-Sleep -Seconds 5
Turn-DisplayOff
Write-Log "Display off; PC online"
