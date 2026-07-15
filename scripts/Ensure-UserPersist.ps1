#Requires -Version 5.1
# User-level persistence helpers (no Administrator required).
# Stores tools, auth, and .env under the user profile and mirrors to repo\user-persist.

function Get-JulesUserDataRoot {
    return Join-Path $env:LOCALAPPDATA "JulesBridge"
}

function Get-JulesPersistMirror {
    param([string]$RepoRoot)
    return Join-Path $RepoRoot "user-persist"
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-JulesUserLog {
    param([string]$Message, [string]$RepoRoot)
    $root = Get-JulesUserDataRoot
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path (Join-Path $root "setup.log") -Value $line -Encoding UTF8
    if ($RepoRoot) {
        $mirrorLog = Join-Path (Get-JulesPersistMirror $RepoRoot) "setup.log"
        New-Item -ItemType Directory -Force -Path (Split-Path $mirrorLog) | Out-Null
        Add-Content -Path $mirrorLog -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    }
}

function Add-ToUserPath {
    param([string[]]$PathsToAdd)
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { $userPath = "" }
    $segments = @($userPath -split ";" | Where-Object { $_ -and $_.Trim() })
    $changed = $false
    foreach ($segment in $PathsToAdd) {
        if (-not $segment) { continue }
        $normalized = $segment.TrimEnd("\")
        if (-not (Test-Path $normalized)) { continue }
        if ($segments -notcontains $normalized) {
            $segments += $normalized
            $changed = $true
        }
        if ($env:Path -notlike "*$normalized*") {
            $env:Path += ";$normalized"
        }
    }
    if ($changed) {
        [Environment]::SetEnvironmentVariable("Path", ($segments -join ";"), "User")
    }
}

function Find-PythonExecutable {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
        (Join-Path (Get-JulesUserDataRoot) "python\python.exe")
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike "*WindowsApps*") { return $cmd.Source }
    return ""
}

function Find-JulesExecutable {
    $candidates = @(
        (Join-Path $env:USERPROFILE ".npm-packages\bin\jules.exe"),
        (Join-Path $env:USERPROFILE ".npm-packages\jules.cmd")
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    $cmd = Get-Command jules -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return ""
}

function Get-JulesAuthPaths {
    return @(
        (Join-Path $env:APPDATA "jules"),
        (Join-Path $env:LOCALAPPDATA "jules"),
        (Join-Path $env:USERPROFILE ".config\jules"),
        (Join-Path $env:USERPROFILE ".jules_auth"),
        (Join-Path $env:USERPROFILE ".ngrok2"),
        (Join-Path $env:LOCALAPPDATA "ngrok"),
        (Join-Path $env:USERPROFILE ".config\gh"),
        (Join-Path $env:APPDATA "GitHub CLI"),
        (Join-Path $env:USERPROFILE ".ssh"),
        (Join-Path $env:USERPROFILE ".gnupg")
    ) | Where-Object { $_ }
}

function Sync-DirectoryTree {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (-not (Test-Path $Source)) { return $false }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Copy-Item -Path (Join-Path $Source "*") -Destination $Destination -Recurse -Force -ErrorAction SilentlyContinue
    return $true
}

function Backup-JulesUserState {
    param([string]$RepoRoot)
    $dataRoot = Get-JulesUserDataRoot
    $mirror = Get-JulesPersistMirror $RepoRoot
    New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $mirror | Out-Null

    $manifest = @{ auth = @(); saved_at = (Get-Date).ToString("o") }
    $index = 0
    foreach ($authPath in (Get-JulesAuthPaths)) {
        if (-not (Test-Path $authPath)) { continue }
        $label = "auth_$index"
        $index++
        Sync-DirectoryTree $authPath (Join-Path $dataRoot "auth\$label") | Out-Null
        Sync-DirectoryTree $authPath (Join-Path $mirror "auth\$label") | Out-Null
        $manifest.auth += @{
            label  = $label
            target = $authPath
        }
    }

    $repoEnv = Join-Path $RepoRoot ".env"
    $userEnv = Join-Path $dataRoot ".env"
    $mirrorEnv = Join-Path $mirror ".env"
    if (Test-Path $userEnv) {
        Copy-Item $userEnv $mirrorEnv -Force -ErrorAction SilentlyContinue
        if ((Test-Path $RepoRoot) -and -not (Test-Path $repoEnv)) {
            Copy-Item $userEnv $repoEnv -Force -ErrorAction SilentlyContinue
        }
    } elseif (Test-Path $repoEnv) {
        Copy-Item $repoEnv $userEnv -Force -ErrorAction SilentlyContinue
        Copy-Item $repoEnv $mirrorEnv -Force -ErrorAction SilentlyContinue
    } elseif (Test-Path $mirrorEnv) {
        Copy-Item $mirrorEnv $userEnv -Force -ErrorAction SilentlyContinue
        Copy-Item $mirrorEnv $repoEnv -Force -ErrorAction SilentlyContinue
    } else {
        $example = Join-Path $RepoRoot ".env.example"
        if (Test-Path $example) {
            Copy-Item $example $userEnv -Force
            Copy-Item $example $mirrorEnv -Force -ErrorAction SilentlyContinue
            Copy-Item $example $repoEnv -Force -ErrorAction SilentlyContinue
        }
    }

    $manifestJson = $manifest | ConvertTo-Json -Depth 4
    Set-Content -Path (Join-Path $dataRoot "manifest.json") -Value $manifestJson -Encoding UTF8
    Set-Content -Path (Join-Path $mirror "manifest.json") -Value $manifestJson -Encoding UTF8
    Write-JulesUserLog "Backed up user state" $RepoRoot
}

function Restore-JulesUserState {
    param([string]$RepoRoot)
    $dataRoot = Get-JulesUserDataRoot
    $mirror = Get-JulesPersistMirror $RepoRoot

    foreach ($base in @($mirror, $dataRoot)) {
        $manifestPath = Join-Path $base "manifest.json"
        if (-not (Test-Path $manifestPath)) { continue }
        $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
        foreach ($entry in $manifest.auth) {
            $src = Join-Path $base ("auth\" + $entry.label)
            if (-not (Test-Path $src)) { continue }
            $target = [string]$entry.target
            if ($target -match '^[A-Za-z]:\\Users\\[^\\]+\\(.+)$') {
                $target = Join-Path $env:USERPROFILE $Matches[1]
            }
            Sync-DirectoryTree $src $target | Out-Null
        }
    }

    foreach ($base in @($dataRoot, $mirror)) {
        $envFile = Join-Path $base ".env"
        if (Test-Path $envFile) {
            Copy-Item $envFile (Join-Path $dataRoot ".env") -Force -ErrorAction SilentlyContinue
            Copy-Item $envFile (Join-Path $RepoRoot ".env") -Force -ErrorAction SilentlyContinue
            break
        }
    }

    Write-JulesUserLog "Restored user state from persist store" $RepoRoot
}

function Write-UserEnvLauncher {
    param([string]$RepoRoot)
    $dataRoot = Get-JulesUserDataRoot
    New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
    $python = Find-PythonExecutable
    $jules = Find-JulesExecutable
    $nodeDir = Get-ChildItem (Join-Path $env:LOCALAPPDATA "NodeJS") -Directory -Filter "node-v*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    $npmBin = Join-Path $env:USERPROFILE ".npm-packages\bin"
    $paths = @()
    if ($python) { $paths += (Split-Path $python) }
    if ($nodeDir) { $paths += $nodeDir.FullName }
    if (Test-Path $npmBin) { $paths += $npmBin }
    Add-ToUserPath $paths

    $cmdPath = Join-Path $dataRoot "user-env.cmd"
    $psPath = Join-Path $dataRoot "user-env.ps1"
    $pythonLine = if ($python) { "`"$python`"" } else { "python" }
    $julesLine = if ($jules) { "`"$jules`"" } else { "jules" }
    @(
        "@echo off",
        "set `"JULES_USER_DATA=$dataRoot`"",
        "set `"JULES_REPO=$RepoRoot`"",
        "set `"PYTHONIOENCODING=utf-8`"",
        "set `"PYTHON_EXE=$pythonLine`"",
        "set `"JULES_EXE=$julesLine`""
    ) | Set-Content -Path $cmdPath -Encoding ASCII

    $psLines = @(
        "`$JulesUserData = '$dataRoot'",
        "`$JulesRepo = '$RepoRoot'",
        "`$env:PYTHONIOENCODING = 'utf-8'"
    )
    if ($python) { $psLines += "`$env:JULES_PYTHON = '$python'" } else { $psLines += "# python not found yet" }
    if ($jules) { $psLines += "`$env:JULES_CLI = '$jules'" } else { $psLines += "# jules not found yet" }
    $psLines | Set-Content -Path $psPath -Encoding UTF8

    Copy-Item $cmdPath (Join-Path $RepoRoot "user-env.cmd") -Force -ErrorAction SilentlyContinue
    return @{
        Python = $python
        Jules  = $jules
        CmdPath = $cmdPath
    }
}

function Register-StartupShortcut {
    param(
        [string]$RepoRoot,
        [string]$Name = "JulesBridge-AlwaysOn"
    )
    $startup = [Environment]::GetFolderPath("Startup")
    if (-not $startup) { throw "Could not resolve user Startup folder" }
    $target = Join-Path $RepoRoot "Boot-AlwaysOn-Silent.cmd"
    $shortcut = Join-Path $startup "$Name.lnk"
    $wsh = New-Object -ComObject WScript.Shell
    $link = $wsh.CreateShortcut($shortcut)
    $link.TargetPath = $target
    $link.WorkingDirectory = $RepoRoot
    $link.WindowStyle = 7
    $link.Description = "Start Jules Bridge at logon (no admin)"
    $link.Save()
    return $shortcut
}

function Install-PythonDependencies {
    param([string]$RepoRoot)
    $python = Find-PythonExecutable
    if (-not $python) {
        return @{ Ok = $false; Error = "Python not found. Install from python.org using 'Install for me only'." }
    }
    $req = Join-Path $RepoRoot "requirements.txt"
    if (-not (Test-Path $req)) {
        return @{ Ok = $false; Error = "requirements.txt missing" }
    }
    & $python -m pip install --user -r $req 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        return @{ Ok = $false; Error = "pip install failed (exit $LASTEXITCODE)" }
    }
    return @{ Ok = $true; Python = $python }
}

function Test-JulesAuthenticated {
    foreach ($path in (Get-JulesAuthPaths)) {
        if ((Split-Path $path -Leaf) -match 'ngrok') {
            if (Test-Path $path) { return $true }
            continue
        }
        if (Test-Path $path) { return $true }
    }
    return $false
}

function Invoke-UserKeepAwake {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public class JulesKeepAwake {
    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
    public const uint ES_CONTINUOUS = 0x80000000;
    public const uint ES_SYSTEM_REQUIRED = 0x00000001;
    public const uint ES_DISPLAY_REQUIRED = 0x00000002;
    public static void PreventSleep() {
        SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED);
    }
}
"@ -ErrorAction SilentlyContinue
    [JulesKeepAwake]::PreventSleep()
}
