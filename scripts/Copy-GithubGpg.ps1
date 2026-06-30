#Requires -Version 5.1
<#
.SYNOPSIS
  Copy Jules GPG public key to clipboard and open GitHub add-key page.
#>

$RepoRoot = Split-Path -Parent $PSScriptRoot
$KeyFile = Join-Path $RepoRoot "jules-gpg-public.asc"

if (-not (Test-Path $KeyFile)) {
    Write-Host "No key yet - running Setup-GitHubGpg.ps1 ..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "Setup-GitHubGpg.ps1")
}

if (Test-Path $KeyFile) {
    $keyText = Get-Content -Path $KeyFile -Raw
    Set-Clipboard -Value $keyText
    Write-Host "Title (type this in GitHub):"
    Write-Host "jules" -ForegroundColor Cyan
    Write-Host "Key (select from -----BEGIN through -----END, or use Copy-GithubGpg.cmd — key auto-copies to clipboard):"
    Write-Host "Key auto-copied to clipboard!" -ForegroundColor Green
    Start-Process "https://github.com/settings/gpg/new"
} else {
    Write-Host "Failed to find or generate GPG key at $KeyFile" -ForegroundColor Red
}
