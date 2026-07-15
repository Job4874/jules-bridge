#Requires -Version 5.1
# Ghost lock helpers — password hash stored under %LOCALAPPDATA%\JulesBridge only.

function Get-GhostStatePath {
    Join-Path $env:LOCALAPPDATA "JulesBridge\ghost_state.json"
}

function Get-GhostState {
    $path = Get-GhostStatePath
    if (-not (Test-Path $path)) {
        return @{ locked = $false }
    }
    try {
        return (Get-Content $path -Raw | ConvertFrom-Json)
    } catch {
        return @{ locked = $false }
    }
}

function Test-GhostLocked {
    $state = Get-GhostState
    return [bool]$state.locked
}

function Test-GhostUnlock {
    param([Parameter(Mandatory = $true)][string]$Password)
    . (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")
    $py = Find-PythonExecutable
    if (-not $py) { return $false }
    $repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $env:PYTHONPATH = $repo
    if (-not (Test-GhostLocked)) { return $true }
    $check = & $py -c "import sys; sys.path.insert(0, r'$repo'); import modules.ghost_state as g; print('ok' if g.verify_unlock(sys.argv[1]) else 'no')" $Password 2>$null
    return ($check -eq "ok")
}

function Set-GhostLocked {
    param(
        [Parameter(Mandatory = $true)][string]$Password,
        [string]$RepoRoot = ""
    )
    if (-not $RepoRoot) {
        $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    }
    . (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")
    $py = Find-PythonExecutable
    if (-not $py) {
        throw "Python not found - cannot lock ghost state"
    }
    $env:PYTHONPATH = $RepoRoot
    & $py (Join-Path $PSScriptRoot "ghost_state_cli.py") lock --password $Password --repo-root $RepoRoot
    if ($LASTEXITCODE -ne 0) { throw "ghost lock failed" }
}

function Clear-GhostLock {
    param(
        [Parameter(Mandatory = $true)][string]$Password,
        [string]$RepoRoot = ""
    )
    if (-not $RepoRoot) {
        $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    }
    . (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")
    $py = Find-PythonExecutable
    if (-not $py) { throw "Python not found" }
    $env:PYTHONPATH = $RepoRoot
    & $py (Join-Path $PSScriptRoot "ghost_state_cli.py") unlock --password $Password --repo-root $RepoRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[DENIED] Invalid unlock password." -ForegroundColor Red
        exit 1
    }
}

function Start-LocalInputBlock {
    param([string]$RepoRoot = "")
    if (-not $RepoRoot) {
        $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    }
    $pidFile = Join-Path $env:LOCALAPPDATA "JulesBridge\input_block.pid"
    if (Test-Path $pidFile) {
        $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
            return $true
        }
    }
    $holder = Join-Path $RepoRoot "scripts\Hold-InputBlock.ps1"
    if (-not (Test-Path $holder)) { return $false }
    Start-Process powershell.exe -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", "`"$holder`""
    ) -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 1
    return Test-Path $pidFile
}

function Stop-LocalInputBlock {
    $pidFile = Join-Path $env:LOCALAPPDATA "JulesBridge\input_block.pid"
    if (-not (Test-Path $pidFile)) { return }
    $blockPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($blockPid) {
        Stop-Process -Id $blockPid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    try {
        Add-Type @"
using System.Runtime.InteropServices;
public class JulesInputUnblock {
    [DllImport("user32.dll")] public static extern bool BlockInput(bool fBlockIt);
}
"@ -ErrorAction SilentlyContinue
        [JulesInputUnblock]::BlockInput($false) | Out-Null
    } catch { }
}
