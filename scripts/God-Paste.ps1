#Requires -Version 5.1
<#
.SYNOPSIS
  /god end-to-end boot - fully non-interactive (no prompts, no jules login browser).

.USAGE
  Paste into PowerShell:
    Set-ExecutionPolicy Bypass -Scope Process -Force; & "c:\jules-bridge-master\scripts\God-Paste.ps1"
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [switch]$BlackScreenNow
)

$ErrorActionPreference = "Continue"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
if (-not (Test-Path (Join-Path $RepoRoot "bridge.py"))) {
    foreach ($guess in @("c:\jules-bridge-master", "$env:USERPROFILE\jules-bridge-master")) {
        if (Test-Path (Join-Path $guess "bridge.py")) { $RepoRoot = $guess; break }
    }
}
if (-not (Test-Path (Join-Path $RepoRoot "bridge.py"))) {
    Write-Host "[FAIL] jules-bridge repo not found. Set -RepoRoot or clone to c:\jules-bridge-master" -ForegroundColor Red
    exit 1
}

. (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")

$NgrokDomain = "parade-marrow-pulp.ngrok-free.dev"
$NodeInstallRoot = Join-Path $env:LOCALAPPDATA "NodeJS"
$NpmPrefix = Join-Path $env:USERPROFILE ".npm-packages"
$NpmBin = Join-Path $NpmPrefix "bin"

function Step([string]$m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok([string]$m) { Write-Host "[OK] $m" -ForegroundColor Green }
function Warn([string]$m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }

function Test-BridgeAlive {
    try {
        return ((Invoke-WebRequest "http://127.0.0.1:5000/ping" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200)
    } catch { return $false }
}

function Test-TunnelAlive {
    try {
        return ((Invoke-WebRequest "https://$NgrokDomain/ping" -TimeoutSec 8 -UseBasicParsing `
            -Headers @{ "ngrok-skip-browser-warning" = "true" }).StatusCode -eq 200)
    } catch { return $false }
}

function Stop-StaleBridge {
    Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

function Ensure-PortableNode {
    if (Get-Command node -ErrorAction SilentlyContinue) { return }
    $existing = Get-ChildItem $NodeInstallRoot -Directory -Filter "node-v*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if ($existing -and (Test-Path (Join-Path $existing.FullName "node.exe"))) {
        Add-ToUserPath @($existing.FullName)
        return
    }
    Step "Installing portable Node.js LTS (user-local)"
    $index = Invoke-RestMethod "https://nodejs.org/dist/index.json" -UseBasicParsing
    $lts = @($index | Where-Object { $_.lts -and ($_.lts -is [string]) -and $_.lts.Trim() }) | Select-Object -First 1
    if (-not $lts) { throw "Could not resolve Node.js LTS version" }
    $folder = "node-$($lts.version)-win-x64"
    $url = "https://nodejs.org/dist/$($lts.version)/$folder.zip"
    New-Item -ItemType Directory -Force -Path $NodeInstallRoot | Out-Null
    $zip = Join-Path $env:TEMP "$folder.zip"
    $extract = Join-Path $NodeInstallRoot $folder
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
    Expand-Archive -LiteralPath $zip -DestinationPath $NodeInstallRoot -Force
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    Add-ToUserPath @($extract)
    Ok "Node $(node --version)"
}

function Ensure-NpmJules {
    New-Item -ItemType Directory -Force -Path $NpmPrefix, $NpmBin | Out-Null
    npm config set prefix $NpmPrefix --location=user 2>$null
    if ($LASTEXITCODE -ne 0) { npm config set prefix $NpmPrefix 2>$null }
    Add-ToUserPath @($NpmPrefix, $NpmBin)
    $julesExe = Join-Path $NpmBin "jules.exe"
    if (Test-Path $julesExe) { return $julesExe }
    Step "Installing @google/jules (user prefix)"
    npm install -g @google/jules 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "npm install -g @google/jules failed" }
    if (Test-Path $julesExe) { return $julesExe }
    $cmd = Join-Path $NpmPrefix "jules.cmd"
    if (Test-Path $cmd) { return $cmd }
    throw "Jules CLI install finished but binary not found"
}

function Turn-DisplayOff {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public class JulesDisplayPower {
    [DllImport("user32.dll")]
    public static extern int SendMessage(int hWnd, int hMsg, int wParam, int lParam);
    public static void MonitorOff() { SendMessage(-1, 0x0112, 0xF170, 2); }
}
"@ -ErrorAction SilentlyContinue
    [JulesDisplayPower]::MonitorOff()
}

Write-Host "`n$('=' * 60)" -ForegroundColor Green
Write-Host "  /god PASTE BOOT - zero prompts" -ForegroundColor Green
Write-Host "$('=' * 60)" -ForegroundColor Green
Write-Host "  User:  $env:USERNAME  Admin: $(Test-IsAdministrator)"
Write-Host "  Repo:  $RepoRoot"

Step "Restore auth + .env"
Restore-JulesUserState $RepoRoot

Step "Node + Jules CLI"
Ensure-PortableNode
$julesPath = Ensure-NpmJules
Ok "Jules: $julesPath"
if (Test-JulesAuthenticated) { Ok "Jules auth restored" } else { Warn "No Jules auth yet - run 'jules login' once when you can use a browser" }

Step "Python deps (pip --user)"
$pip = Install-PythonDependencies $RepoRoot
if ($pip.Ok) { Ok "Python: $($pip.Python)" } else { Warn $pip.Error }

Step "User env launchers"
$envInfo = Write-UserEnvLauncher $RepoRoot
if ($envInfo.Python) { Ok "Python path OK" } else { Warn "Python missing - install Python 3.12 for me only from python.org" }

Step "Logon startup shortcut"
try {
    Ok (Register-StartupShortcut $RepoRoot)
} catch {
    Warn $_.Exception.Message
}

Invoke-UserKeepAwake

Step "Start bridge + ngrok"
if (-not (Test-TunnelAlive)) {
    Stop-StaleBridge
    $python = Find-PythonExecutable
    if (-not $python) {
        Warn "Cannot start bridge - Python not found"
    } else {
        $env:PYTHONIOENCODING = "utf-8"
        Start-Process -FilePath $python -ArgumentList "start.py" -WorkingDirectory $RepoRoot -WindowStyle Minimized
        Ok "Bridge process started minimized"
        for ($i = 1; $i -le 30; $i++) {
            Start-Sleep -Seconds 2
            if ((Test-BridgeAlive) -and (Test-TunnelAlive)) { break }
            Write-Host "  [$i/30] local=$(Test-BridgeAlive) tunnel=$(Test-TunnelAlive)" -ForegroundColor DarkGray
        }
    }
}

Step "Save state for next reboot"
Backup-JulesUserState $RepoRoot

Step "Register mesh node"
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Register-MeshNode.ps1") -RepoRoot $RepoRoot | Out-Null
    Ok "Mesh registry updated"
} catch {
    Warn $_.Exception.Message
}

Write-Host "`n$('=' * 60)" -ForegroundColor Green
Write-Host "  RESULT" -ForegroundColor Green
Write-Host "$('=' * 60)" -ForegroundColor Green
Write-Host "  Local:  http://127.0.0.1:5000/ping  -> $(if (Test-BridgeAlive) { 'UP' } else { 'DOWN' })"
Write-Host "  Remote: https://$NgrokDomain/ping -> $(if (Test-TunnelAlive) { 'UP' } else { 'DOWN' })"
Write-Host "  Jules:  $julesPath"
Write-Host "  Store:  $(Get-JulesUserDataRoot)"
Write-Host "  Log:    $(Join-Path $RepoRoot 'bridge.log')"

if ($BlackScreenNow) {
    Step "Black screen (monitor off, PC online)"
    Start-Sleep -Seconds 3
    Turn-DisplayOff
    Ok "Display off"
}

Write-Host ""
