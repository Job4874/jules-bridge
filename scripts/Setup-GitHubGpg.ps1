#Requires -Version 5.1
<#
.SYNOPSIS
  Configure Git + GPG signing for GitHub (Job4874 / Jules school PC).

.DESCRIPTION
  Uses Git for Windows bundled gpg.exe, generates a key if missing, enables
  signed commits, and exports the public key to jules-gpg-public.asc.

.USAGE
  .\scripts\Setup-GitHubGpg.ps1
  .\scripts\Setup-GitHubGpg.ps1 -Email "you@example.com"

.PARAMETER Email
  Must match a verified email on your GitHub account.
  Default: Job4874@users.noreply.github.com (GitHub private email).

.PARAMETER Name
  Real name on the GPG key. Default: Abdulwahab Tibin

.PARAMETER Comment
  Key comment. Default: Jules school PC
#>
[CmdletBinding()]
param(
    [string]$Email = "Job4874@users.noreply.github.com",
    [string]$Name = "Abdulwahab Tibin",
    [string]$Comment = "Jules school PC"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ExportPath = Join-Path $RepoRoot "jules-gpg-public.asc"
$KeyTitle = "jules"

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

function Get-GitInstallRoot {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) {
        throw "git is not on PATH. Install Git for Windows first."
    }
    $root = Split-Path -Parent $gitCmd.Source
    while ($root -and -not (Test-Path (Join-Path $root "usr\bin\gpg.exe"))) {
        $parent = Split-Path -Parent $root
        if ($parent -eq $root) { break }
        $root = $parent
    }
    if (-not $root -or -not (Test-Path (Join-Path $root "usr\bin\gpg.exe"))) {
        throw "Could not locate Git for Windows installation (need usr\bin\gpg.exe)."
    }
    return $root.Trim()
}

function Get-GpgExe {
    param([string]$GitRoot)
    $gpgExe = Join-Path $GitRoot "usr\bin\gpg.exe"
    if (-not (Test-Path $gpgExe)) {
        throw "gpg.exe not found at $gpgExe"
    }
    return $gpgExe
}

function Get-GpgHomeMsys {
    $user = $env:USERNAME
    if (-not $user) { $user = Split-Path -Leaf $env:USERPROFILE }
    return "/c/Users/$user/.gnupg"
}

function Invoke-Gpg {
    param(
        [string]$GpgExe,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )
    $output = & $GpgExe @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        $text = ($output | Out-String).Trim()
        throw "gpg $($Arguments -join ' ') failed (exit $LASTEXITCODE): $text"
    }
    return ($output | Out-String).TrimEnd()
}

function Get-SecretKeyId {
    param([string]$GpgExe)
    $list = Invoke-Gpg $GpgExe --list-secret-keys --keyid-format=long $Email
    foreach ($line in ($list -split "`n")) {
        if ($line -match "^sec\s+\S+/([0-9A-Fa-f]{16})\s") {
            return $Matches[1].ToUpper()
        }
    }
    return $null
}

function New-GpgKey {
    param(
        [string]$GpgExe,
        [string]$BatchPath
    )
    $batch = @"
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: $Name
Name-Comment: $Comment
Name-Email: $Email
Expire-Date: 0
%no-protection
%commit
"@
    Set-Content -Path $BatchPath -Value $batch -Encoding ASCII
    Invoke-Gpg $GpgExe --batch --generate-key $BatchPath | Out-Null
}

function Export-PublicKey {
    param(
        [string]$GpgExe,
        [string]$KeyId,
        [string]$Path
    )
    $armor = Invoke-Gpg $GpgExe --armor --export $KeyId
    $header = "# Jules-Key-ID: $KeyId"
    Set-Content -Path $Path -Value ($header + "`n" + $armor) -Encoding ASCII -NoNewline
    if (-not $armor.EndsWith("`n")) {
        Add-Content -Path $Path -Value "" -Encoding ASCII
    }
    return $armor
}

try {
    $divider = "=" * 60
    Write-Host "`n$divider" -ForegroundColor Cyan
    Write-Host "  GitHub GPG setup (Jules / Job4874)" -ForegroundColor Cyan
    Write-Host $divider -ForegroundColor Cyan

    $GitRoot = Get-GitInstallRoot
    $GpgExe = Get-GpgExe -GitRoot $GitRoot
    $gpgHomeWin = Join-Path $env:USERPROFILE ".gnupg"
    $gpgHomeMsys = Get-GpgHomeMsys
    $env:GNUPGHOME = $gpgHomeMsys

    if (-not (Test-Path $gpgHomeWin)) {
        New-Item -ItemType Directory -Force -Path $gpgHomeWin | Out-Null
    }

    Write-Ok "GPG: $GpgExe"
    Write-Ok "GNUPGHOME: $gpgHomeMsys"

    Write-Step "Checking for existing secret key"
    $keyId = Get-SecretKeyId -GpgExe $GpgExe
    if (-not $keyId) {
        Write-Warn "No key found for $Email - generating one..."
        $batchPath = Join-Path $env:TEMP "jules-gpg-batch.txt"
        New-GpgKey -GpgExe $GpgExe -BatchPath $batchPath
        Remove-Item -LiteralPath $batchPath -Force -ErrorAction SilentlyContinue
        $keyId = Get-SecretKeyId -GpgExe $GpgExe
        if (-not $keyId) {
            throw "Key generation finished but no secret key was found for $Email"
        }
        Write-Ok "Generated key: $keyId"
    } else {
        Write-Ok "Existing key: $keyId"
    }

    Write-Step "Configuring git for signed commits"
    & git config --global user.name $Name
    & git config --global user.email $Email
    & git config --global user.signingkey $keyId
    & git config --global commit.gpgsign true
    & git config --global gpg.program $GpgExe
    Write-Ok "commit.gpgsign=true, signingkey=$keyId"

    Write-Step "Exporting public key"
    $armor = Export-PublicKey -GpgExe $GpgExe -KeyId $keyId -Path $ExportPath
    Write-Ok "Exported to $ExportPath"

    Write-Host "`n$divider" -ForegroundColor Green
    Write-Host "  GPG ready" -ForegroundColor Green
    Write-Host $divider -ForegroundColor Green
    Write-Host "  Key ID : $keyId"
    Write-Host "  Email  : $Email"
    Write-Host "  Title  : $KeyTitle (for GitHub)"
    Write-Host ""
    Write-Host "  Next: double-click Copy-GithubGpg.cmd" -ForegroundColor Cyan
    Write-Host "        (copies key + opens GitHub - just paste)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Email must be verified on GitHub:" -ForegroundColor Yellow
    Write-Host "  https://github.com/settings/emails" -ForegroundColor Gray
    exit 0
} catch {
    Write-Err $_.Exception.Message
    if ($_.ScriptStackTrace) {
        Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    }
    exit 1
}
