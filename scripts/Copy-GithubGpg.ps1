#Requires -Version 5.1
<#
.SYNOPSIS
  Copy Jules GPG public key to clipboard and open GitHub add-key page.

.DESCRIPTION
  One-click flow:
    1. Ensures GPG key exists (runs Setup-GitHubGpg.ps1 if needed)
    2. Copies the full public key block to clipboard
    3. Opens https://github.com/settings/gpg/new
    4. Shows a popup: Title = jules, Key = Ctrl+V

.USAGE
  .\scripts\Copy-GithubGpg.ps1
  Double-click Copy-GithubGpg.cmd in repo root
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$KeyFile = Join-Path $RepoRoot "jules-gpg-public.asc"
$SetupScript = Join-Path $PSScriptRoot "Setup-GitHubGpg.ps1"
$KeyTitle = "jules"
$GitHubUrl = "https://github.com/settings/gpg/new"

function Write-Ok([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Err([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Get-GitRoot {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) { return $null }
    $root = (& git -C $RepoRoot rev-parse --show-toplevel 2>$null)
    if ($root) { return $root.Trim() }
    $probe = Split-Path -Parent $gitCmd.Source
    while ($probe -and -not (Test-Path (Join-Path $probe "usr\bin\gpg.exe"))) {
        $parent = Split-Path -Parent $probe
        if ($parent -eq $probe) { break }
        $probe = $parent
    }
    return $probe
}

function Get-KeyIdFromFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    $content = Get-Content -LiteralPath $Path -Raw
    if ($content -match "/([0-9A-Fa-f]{16})") {
        return $Matches[1].ToUpper()
    }
    return $null
}

function Refresh-PublicKeyFile {
    param([string]$Path)
    $gitRoot = Get-GitRoot
    if (-not $gitRoot) { return }
    $gpgExe = Join-Path $gitRoot "usr\bin\gpg.exe"
    if (-not (Test-Path $gpgExe)) { return }

    $user = $env:USERNAME
    if (-not $user) { $user = Split-Path -Leaf $env:USERPROFILE }
    $env:GNUPGHOME = "/c/Users/$user/.gnupg"

    $keyId = Get-KeyIdFromFile -Path $Path
    if (-not $keyId) {
        $list = & $gpgExe --list-secret-keys --keyid-format=long 2>$null
        foreach ($line in ($list -split "`n")) {
            if ($line -match "^sec\s+\S+/([0-9A-Fa-f]{16})\s") {
                $keyId = $Matches[1].ToUpper()
                break
            }
        }
    }
    if (-not $keyId) { return }

    $armor = (& $gpgExe --armor --export $keyId 2>$null | Out-String).TrimEnd()
    if ($armor) {
        Set-Content -Path $Path -Value $armor -Encoding ASCII -NoNewline
        if (-not $armor.EndsWith("`n")) {
            Add-Content -Path $Path -Value "" -Encoding ASCII
        }
    }
}

function Show-InstructionsPopup {
    param([string]$Title)
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show(
            @"
GitHub GPG page opened in your browser.

Title:  $Title   (type this in the Title box)

Key:    already copied — click the Key box and press Ctrl+V

Then click "Add GPG key".
"@,
            "Jules GPG — paste and done",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        )
    } catch {
        Write-Host ""
        Write-Host "  Title: $Title  (type in GitHub Title box)" -ForegroundColor Yellow
        Write-Host "  Key:   already in clipboard — press Ctrl+V in Key box" -ForegroundColor Yellow
        Write-Host ""
    }
}

try {
    if (-not (Test-Path $KeyFile)) {
        Write-Host "No key yet — running Setup-GitHubGpg.ps1 ..." -ForegroundColor Yellow
        if (-not (Test-Path $SetupScript)) {
            throw "Setup script not found: $SetupScript"
        }
        & $SetupScript
        if ($LASTEXITCODE -ne 0) {
            throw "Setup-GitHubGpg.ps1 failed with exit code $LASTEXITCODE"
        }
    }

    Refresh-PublicKeyFile -Path $KeyFile

    if (-not (Test-Path $KeyFile)) {
        throw "Public key file missing: $KeyFile"
    }

    $keyText = (Get-Content -LiteralPath $KeyFile -Raw).Trim()
    if ($keyText -notmatch "BEGIN PGP PUBLIC KEY BLOCK") {
        throw "Invalid public key file (missing BEGIN PGP PUBLIC KEY BLOCK): $KeyFile"
    }

    Set-Clipboard -Value $keyText
    Write-Ok "Public key copied to clipboard"

    Start-Process $GitHubUrl
    Write-Ok "Opened $GitHubUrl"

    Show-InstructionsPopup -Title $KeyTitle

    Write-Host ""
    Write-Host "Done. On GitHub:" -ForegroundColor Cyan
    Write-Host "  Title : $KeyTitle"
    Write-Host "  Key   : Ctrl+V (already copied)"
    Write-Host ""
    exit 0
} catch {
    Write-Err $_.Exception.Message
    Write-Host "`nPress Enter to close..." -ForegroundColor Gray
    Read-Host | Out-Null
    exit 1
}
