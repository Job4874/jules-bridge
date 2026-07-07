function ConvertTo-MsysPath {
    param([string]$Path)
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    return ('/' + $resolved.Substring(0, 1).ToLower() + $resolved.Substring(2)).Replace('\', '/')
}

function Initialize-GpgHome {
    param([string]$GpgHomeWin)
    if (-not (Test-Path $GpgHomeWin)) {
        New-Item -ItemType Directory -Force -Path $GpgHomeWin | Out-Null
    }
    $commonConf = Join-Path $GpgHomeWin "common.conf"
    if (-not (Test-Path $commonConf)) {
        Set-Content -Path $commonConf -Value "# Jules bridge GPG home" -Encoding ASCII
    }
}

function Test-GpgHomeUsable {
    param(
        [string]$GpgExe,
        [string]$GpgHomeMsys
    )
    $previousHome = $env:GNUPGHOME
    $previousErrorAction = $ErrorActionPreference
    try {
        $env:GNUPGHOME = $GpgHomeMsys
        $ErrorActionPreference = 'Continue'
        & $GpgExe --list-secret-keys 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    } finally {
        $env:GNUPGHOME = $previousHome
        $ErrorActionPreference = $previousErrorAction
    }
}

function Resolve-GpgHomeMsys {
    param(
        [string]$GpgExe,
        [string]$RepoRoot
    )
    $user = $env:USERNAME
    if (-not $user) { $user = Split-Path -Leaf $env:USERPROFILE }
    $candidates = @(
        @{ Win = Join-Path $env:USERPROFILE ".gnupg"; Msys = "/c/Users/$user/.gnupg" },
        @{ Win = Join-Path $RepoRoot ".gnupg-local"; Msys = $null }
    )
    foreach ($candidate in $candidates) {
        if (-not $candidate.Msys) {
            Initialize-GpgHome -GpgHomeWin $candidate.Win
            $candidate.Msys = ConvertTo-MsysPath -Path $candidate.Win
        } else {
            Initialize-GpgHome -GpgHomeWin $candidate.Win
        }
        if (Test-GpgHomeUsable -GpgExe $GpgExe -GpgHomeMsys $candidate.Msys) {
            return $candidate.Msys
        }
    }
    throw "Could not initialize a usable GPG home directory."
}
