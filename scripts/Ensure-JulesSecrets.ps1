#Requires -Version 5.1
<#
.SYNOPSIS
  Ensure Jules secrets persist across reboots and configure ngrok auth.

.DESCRIPTION
  - Restores missing repo .env keys from ~/.jules/.env mirror
  - Never rotates an existing BRIDGE_TOKEN
  - Mirrors BRIDGE_TOKEN, LOCAL_BRIDGE_TOKEN, NGROK_AUTHTOKEN, and API keys
  - Writes ~/.jules/ngrok_authtoken and runs ngrok config add-authtoken

.USAGE
  .\scripts\Ensure-JulesSecrets.ps1
  .\scripts\Ensure-JulesSecrets.ps1 -NgrokAuthtoken "YOUR_TOKEN"
  .\scripts\Ensure-JulesSecrets.ps1 -PromptForNgrok
#>
[CmdletBinding()]
param(
    [string]$NgrokAuthtoken = "",
    [switch]$PromptForNgrok,
    [switch]$ForceNgrok
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PyScript = Join-Path $PSScriptRoot "ensure_jules_secrets.py"

function Write-Ok([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Err([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

try {
    if ($PromptForNgrok -and -not $NgrokAuthtoken) {
        Write-Host ""
        Write-Host "Paste your ngrok authtoken (from https://dashboard.ngrok.com/get-started/your-authtoken)" -ForegroundColor Cyan
        $NgrokAuthtoken = Read-Host "NGROK_AUTHTOKEN"
    }

    $args = @($PyScript)
    if ($NgrokAuthtoken) {
        $args += @("--ngrok-authtoken", $NgrokAuthtoken)
    }
    if ($ForceNgrok) {
        $args += "--force-ngrok"
    }

    Push-Location $RepoRoot
    $output = & python @args 2>&1 | Out-String
    $exitCode = $LASTEXITCODE
    Pop-Location

    if ($exitCode -ne 0) {
        Write-Host $output
        Write-Err "Ngrok authtoken is missing or invalid."
        Write-Host ""
        Write-Host "One-time fix:" -ForegroundColor Cyan
        Write-Host "  .\scripts\Ensure-JulesSecrets.ps1 -PromptForNgrok" -ForegroundColor Gray
        Write-Host "  or" -ForegroundColor Gray
        Write-Host "  .\scripts\Ensure-JulesSecrets.ps1 -NgrokAuthtoken `"YOUR_TOKEN`"" -ForegroundColor Gray
        exit $exitCode
    }

    $result = $output | ConvertFrom-Json
    Write-Ok "Repo env: $($result.repo_env_path)"
    Write-Ok "Mirror env: $($result.mirror_path)"
    if ($result.restored_from_mirror.PSObject.Properties.Count -gt 0) {
        Write-Ok "Restored missing keys from mirror"
    }
    if ($result.mirrored_to_jules_home.PSObject.Properties.Count -gt 0) {
        Write-Ok "Mirrored persistent keys to ~/.jules/.env"
    }
    Write-Ok $result.ngrok_detail
    exit 0
} catch {
    Write-Err $_.Exception.Message
    exit 1
}
