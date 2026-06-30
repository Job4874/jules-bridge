#Requires -Version 5.1
<#
.SYNOPSIS
  End-to-end, user-level Jules CLI + jules-bridge setup (no Administrator required).

.DESCRIPTION
  - Installs portable Node.js LTS if node/npm are missing
  - Configures user-local npm global prefix and PATH
  - Installs @google/jules globally
  - Runs jules login (browser auth)
  - Verifies CLI, checks .env for REST API vars, offers to start bridge.py

.USAGE
  From repo root:
    .\scripts\setup-jules.ps1

  One-liner (paste in PowerShell):
    powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\jules-bridge\scripts\setup-jules.ps1"

  Or clone path:
    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\abdul\jules-bridge\scripts\setup-jules.ps1"

.PARAMETER SkipLogin
  Skip the interactive jules login step.

.PARAMETER SkipBridge
  Skip bridge health check and startup offer.

.PARAMETER SkipVerify
  Skip jules version / remote list verification.

.PARAMETER ForceNodeReinstall
  Re-download portable Node.js even when an install already exists.
#>
[CmdletBinding()]
param(
    [switch]$SkipLogin,
    [switch]$SkipBridge,
    [switch]$SkipVerify,
    [switch]$ForceNodeReinstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Older Windows PowerShell 5.1 may default to TLS 1.0 for nodejs.org downloads.
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {
    # Non-fatal; download may still succeed on newer OS builds.
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$NodeInstallRoot = Join-Path $env:LOCALAPPDATA "NodeJS"
$NodeInstallAlt = Join-Path $env:USERPROFILE ".local\nodejs"
$NpmPrefix = Join-Path $env:USERPROFILE ".npm-packages"
$NpmBin = Join-Path $NpmPrefix "bin"
$BridgePort = 5000
$BridgeUrl = "http://127.0.0.1:$BridgePort"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Err([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Info([string]$Message) {
    Write-Host "     $Message" -ForegroundColor Gray
}

function Test-CommandExists([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-Npm {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & npm @Arguments | Out-Host
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Get-ExistingNodeDirectory {
    $candidates = @(
        $NodeInstallRoot,
        $NodeInstallAlt
    )
    foreach ($root in $candidates) {
        if (-not (Test-Path $root)) { continue }
        $directNode = Join-Path $root "node.exe"
        if (Test-Path $directNode) { return $root }
        $nested = Get-ChildItem -Path $root -Directory -Filter "node-v*-win-x64" -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            Select-Object -First 1
        if ($nested -and (Test-Path (Join-Path $nested.FullName "node.exe"))) {
            return $nested.FullName
        }
    }
    return $null
}

function Get-NodeLtsDownload {
    Write-Info "Fetching latest Node.js LTS from nodejs.org..."
    $index = Invoke-RestMethod -Uri "https://nodejs.org/dist/index.json" -UseBasicParsing
    $lts = @($index | Where-Object { $_.lts -and ($_.lts -is [string]) -and $_.lts.Trim() -ne "" }) | Select-Object -First 1
    if (-not $lts) {
        throw "Could not determine Node.js LTS version from nodejs.org/dist/index.json"
    }
    $version = [string]$lts.version
    $folder = "node-$version-win-x64"
    return @{
        Version = $version
        Folder  = $folder
        Url     = "https://nodejs.org/dist/$version/$folder.zip"
    }
}

function Add-ToUserPath([string[]]$PathsToAdd) {
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
        $newPath = ($segments -join ";")
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Ok "Updated user PATH (persistent, no admin): $($PathsToAdd -join ', ')"
    } else {
        Write-Info "User PATH already contains required Node/npm entries."
    }
}

function Ensure-PortableNode {
    if (-not $ForceNodeReinstall -and (Test-CommandExists "node") -and (Test-CommandExists "npm")) {
        $nodeVersion = (& node --version 2>$null)
        Write-Ok "Node.js already available: $nodeVersion"
        return
    }

    $existingDir = Get-ExistingNodeDirectory
    if (-not $ForceNodeReinstall -and $existingDir -and (Test-Path (Join-Path $existingDir "node.exe"))) {
        Write-Ok "Using existing portable Node.js at $existingDir"
        Add-ToUserPath @($existingDir)
        if (-not (Test-CommandExists "node")) {
            throw "Portable Node.js found at $existingDir but is not on PATH. Open a new terminal and re-run this script."
        }
        return
    }

    Write-Step "Installing portable Node.js LTS (user-local, no admin)"
    $download = Get-NodeLtsDownload
    Write-Info "LTS version: $($download.Version)"
    Write-Info "Download URL: $($download.Url)"

    New-Item -ItemType Directory -Force -Path $NodeInstallRoot | Out-Null
    $zipPath = Join-Path $env:TEMP "$($download.Folder).zip"
    $extractRoot = Join-Path $NodeInstallRoot $download.Folder

    if (Test-Path $extractRoot) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }

    Invoke-WebRequest -Uri $download.Url -OutFile $zipPath -UseBasicParsing
    Expand-Archive -LiteralPath $zipPath -DestinationPath $NodeInstallRoot -Force
    Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue

    if (-not (Test-Path (Join-Path $extractRoot "node.exe"))) {
        throw "Portable Node install failed: node.exe not found in $extractRoot"
    }

    Add-ToUserPath @($extractRoot)
    if (-not (Test-CommandExists "node")) {
        throw "Node.js was installed but is not on PATH in this session. Open a new terminal and re-run this script."
    }
    Write-Ok "Portable Node.js installed: $(node --version)"
}

function Configure-NpmPrefix {
    Write-Step "Configuring user-local npm global prefix"
    New-Item -ItemType Directory -Force -Path $NpmPrefix | Out-Null
    New-Item -ItemType Directory -Force -Path $NpmBin | Out-Null

    $exitCode = Invoke-Npm config set prefix $NpmPrefix --location=user
    if ($exitCode -ne 0) {
        $exitCode = Invoke-Npm config set prefix $NpmPrefix
        if ($exitCode -ne 0) {
            throw "npm config set prefix failed with exit code $exitCode"
        }
    }
    Write-Ok "npm prefix set to $NpmPrefix"

    # Windows npm shims land in prefix root; Unix-style bin/ is included for compatibility.
    Add-ToUserPath @($NpmPrefix, $NpmBin)
}

function Install-JulesCli {
    Write-Step "Installing @google/jules globally (user prefix)"
    $exitCode = Invoke-Npm install -g @google/jules
    if ($exitCode -ne 0) {
        throw "npm install -g @google/jules failed with exit code $exitCode"
    }

    $julesCmd = Get-Command jules -ErrorAction SilentlyContinue
    if (-not $julesCmd) {
        $fallbacks = @(
            (Join-Path $NpmPrefix "jules.cmd"),
            (Join-Path $NpmBin "jules.cmd"),
            (Join-Path $NpmPrefix "jules.ps1"),
            (Join-Path $NpmBin "jules.ps1")
        )
        foreach ($candidate in $fallbacks) {
            if (Test-Path $candidate) {
                $julesDir = Split-Path -Parent $candidate
                Add-ToUserPath @($julesDir)
                Write-Ok "Jules CLI installed at $candidate"
                return
            }
        }
        throw "Jules CLI install finished but 'jules' is not on PATH. Check $NpmPrefix and $NpmBin."
    }
    Write-Ok "Jules CLI available: $($julesCmd.Source)"
}

function Invoke-JulesLogin {
    Write-Step "Jules login (browser authentication required)"
    Write-Host @"

  A browser window should open for Google/Jules authentication.
  Complete sign-in there, then return to this terminal.

  If no browser opens, copy any URL printed by the CLI into your browser.

"@ -ForegroundColor Yellow

    if (-not (Test-CommandExists "jules")) {
        throw "The 'jules' command is not available. Open a new terminal and re-run this script."
    }

    & jules login
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "jules login exited with code $LASTEXITCODE. Re-run this script after completing auth."
        return
    }
    Write-Ok "jules login completed"
}

function Test-JulesAuthenticated {
    $authPaths = @(
        (Join-Path $env:APPDATA "jules"),
        (Join-Path $env:LOCALAPPDATA "jules"),
        (Join-Path $env:USERPROFILE ".config\jules"),
        (Join-Path $env:USERPROFILE ".jules_auth")
    )
    foreach ($path in $authPaths) {
        if (Test-Path $path) { return $true }
    }
    return $false
}

function Verify-JulesCli {
    Write-Step "Verifying Jules CLI"
    if (-not (Test-CommandExists "jules")) {
        Write-Warn "The 'jules' command is not on PATH yet. Open a new terminal and run: jules version"
        return
    }

    & jules version
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "jules version failed. Auth may be incomplete."
        return
    }
    Write-Ok "jules version succeeded"

    Write-Info "Listing remote sessions (jules remote list --session)..."
    & jules remote list --session
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "jules remote list --session failed. Login may be required or network blocked."
    } else {
        Write-Ok "Remote session list succeeded"
    }
}

function Get-DotEnvValues([string]$Path) {
    $values = @{}
    if (-not (Test-Path $Path)) { return $values }
    Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $key = $line.Substring(0, $eq).Trim()
        $val = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
        $values[$key] = $val
    }
    return $values
}

function Check-RestApiEnv {
    Write-Step "Checking .env for Jules REST API settings"
    $envPath = Join-Path $RepoRoot ".env"
    $examplePath = Join-Path $RepoRoot ".env.example"

    if (-not (Test-Path $envPath)) {
        Write-Warn ".env not found at $envPath"
        if (Test-Path $examplePath) {
            Write-Info "Copy .env.example to .env and fill in values:"
            Write-Host "  Copy-Item -LiteralPath '$examplePath' -Destination '$envPath'" -ForegroundColor Yellow
        }
    }

    $vars = Get-DotEnvValues $envPath
    $checks = @(
        @{ Name = "JULES_API_KEY"; Hint = "REST API key from Jules / Google AI Studio" },
        @{ Name = "JULES_SOURCE"; Hint = "e.g. sources/github/owner/repo" },
        @{ Name = "JULES_USE_REST_API"; Hint = 'Set to 1 to enable REST routes under /jules/api/*' }
    )

    foreach ($check in $checks) {
        $name = $check.Name
        if (-not $vars.ContainsKey($name) -or [string]::IsNullOrWhiteSpace([string]$vars[$name])) {
            Write-Warn "$name is missing or empty in .env"
            Write-Info $check.Hint
            continue
        }
        if ($name -eq "JULES_USE_REST_API" -and [string]$vars[$name] -notin @("1", "true", "True", "yes")) {
            Write-Warn "$name is set but not enabled (use 1 for REST API bridge routes)"
            continue
        }
        if ($name -eq "JULES_API_KEY") {
            Write-Ok "$name is set (value hidden)"
        } else {
            Write-Ok "$name is set"
        }
    }

    Write-Info 'Bridge uses Jules CLI (jules new, jules remote ...) and optional REST API when JULES_USE_REST_API=1.'
    Write-Info 'This script never writes secrets - edit .env manually.'
}

function Test-BridgeAlive {
    try {
        $response = Invoke-WebRequest -Uri "$BridgeUrl/ping" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Ensure-Bridge {
    Write-Step "Checking jules-bridge on port $BridgePort"
    if (Test-BridgeAlive) {
        Write-Ok "Bridge already running at $BridgeUrl"
        return
    }

    Write-Warn "Bridge is not responding at $BridgeUrl/ping"
    if (-not (Test-CommandExists "python")) {
        Write-Warn "Python not found on PATH. Install Python 3 and run: python bridge.py"
        Write-Info "Dependencies: pip install -r requirements.txt (from repo root)"
        return
    }

    $start = Read-Host "Start bridge now in a new window? [Y/n]"
    if ($start -match "^(n|no)$") {
        Write-Info "Skipped bridge startup. Run manually from repo root: python bridge.py"
        return
    }

    $bridgePy = Join-Path $RepoRoot "bridge.py"
    if (-not (Test-Path $bridgePy)) {
        throw "bridge.py not found at $bridgePy"
    }

    Start-Process -FilePath "cmd.exe" `
        -ArgumentList @("/k", "python bridge.py") `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Normal

    Write-Info "Waiting for bridge to respond..."
    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep -Seconds 1
        if (Test-BridgeAlive) {
            Write-Ok "Bridge online at $BridgeUrl"
            return
        }
        Write-Host "  [$i/20] polling $BridgeUrl/ping..." -ForegroundColor DarkGray
    }
    Write-Warn "Bridge window opened but /ping did not respond yet. Check the bridge terminal for errors."
}

function Show-Summary {
    Write-Host "`n$("=" * 60)" -ForegroundColor Green
    Write-Host "  Jules setup complete" -ForegroundColor Green
    Write-Host "$("=" * 60)" -ForegroundColor Green
    Write-Host "  Repo:    $RepoRoot"
    Write-Host "  Node:    $(if (Test-CommandExists node) { node --version } else { 'not found' })"
    Write-Host "  Jules:   $(if (Test-CommandExists jules) { (Get-Command jules).Source } else { 'not found' })"
    Write-Host "  Bridge:  $BridgeUrl"
    Write-Host ""
    Write-Host '  Next: chat via bridge routes (/jules/*) or run:' -ForegroundColor Cyan
    Write-Host ('    cd "{0}"' -f $RepoRoot) -ForegroundColor Gray
    Write-Host "    python bridge.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Re-run anytime (idempotent):" -ForegroundColor Cyan
    Write-Host "    .\scripts\setup-jules.ps1" -ForegroundColor Gray
}

try {
    Write-Host "`n$("=" * 60)" -ForegroundColor Cyan
    Write-Host '  jules-bridge setup (user-level, no admin)' -ForegroundColor Cyan
    Write-Host "$("=" * 60)" -ForegroundColor Cyan
    Write-Host "  Repo: $RepoRoot" -ForegroundColor Gray

    Ensure-PortableNode
    Configure-NpmPrefix
    Install-JulesCli

    if (-not $SkipLogin) {
        if (Test-JulesAuthenticated) {
            Write-Ok "Existing Jules auth data found; skipping login."
            $forceLogin = Read-Host "Run jules login anyway? [y/N]"
            if ($forceLogin -match "^(y|yes)$") {
                Invoke-JulesLogin
            }
        } else {
            Invoke-JulesLogin
        }
    } else {
        Write-Info "Skipped jules login (-SkipLogin)"
    }

    if (-not $SkipVerify) {
        Verify-JulesCli
    } else {
        Write-Info "Skipped CLI verification (-SkipVerify)"
    }

    Check-RestApiEnv

    if (-not $SkipBridge) {
        Ensure-Bridge
    } else {
        Write-Info "Skipped bridge check (-SkipBridge)"
    }

    Show-Summary
    exit 0
} catch {
    Write-Err $_.Exception.Message
    if ($_.ScriptStackTrace) {
        Write-Info $_.ScriptStackTrace
    }
    Write-Host "`nSetup failed. Fix the issue above and re-run:" -ForegroundColor Yellow
    Write-Host "  .\scripts\setup-jules.ps1" -ForegroundColor Gray
    exit 1
}
