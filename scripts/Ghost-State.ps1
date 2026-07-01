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
