#Requires -Version 5.1
<#
.SYNOPSIS
  School PC: register mesh, publish laptop connect card, send two-way hello (no admin).
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$RemoteUrl = "https://parade-marrow-pulp.ngrok-free.dev",
    [switch]$SkipEmail
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-DotEnvValue([string]$Name) {
    $path = Join-Path $RepoRoot ".env"
    if (-not (Test-Path $path)) { return "" }
    foreach ($line in Get-Content $path) {
        if ($line -match "^\s*$Name\s*=\s*(.+)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

$token = Get-DotEnvValue "BRIDGE_TOKEN"
if (-not $token) { throw "BRIDGE_TOKEN missing in .env" }

Write-Host "`n==> Register school PC in mesh" -ForegroundColor Cyan
& (Join-Path $RepoRoot "scripts\Register-MeshNode.ps1") -RepoRoot $RepoRoot -HostId "school-64gb" -Role "primary"

$headers = @{
    Authorization                = "Bearer $token"
    "ngrok-skip-browser-warning" = "true"
}

Write-Host "`n==> Publish laptop connect card" -ForegroundColor Cyan
$card = @{
    primary_host_id  = "school-64gb"
    remote_bridge    = $RemoteUrl
    bridge_token     = $token
    ngrok_header     = "ngrok-skip-browser-warning: true"
    auth_header      = "Authorization: Bearer $token"
    ping             = "$RemoteUrl/ping"
    mesh_status      = "$RemoteUrl/mesh/status"
    mesh_talk        = "$RemoteUrl/mesh/talk"
    host_identity    = "$RemoteUrl/host/identity"
    updated_utc      = (Get-Date).ToUniversalTime().ToString("o")
    cursor_on_laptop = @{
        step1 = "Clone jules-bridge-master on laptop"
        step2 = "Run: scripts\Laptop-ConnectSchoolBridge.ps1"
        step3 = "Two-way chat: GET/POST $RemoteUrl/mesh/talk"
        step4 = "Laptop writes: POST /mesh/talk { `"from`": `"laptop`", `"message`": `"hello`" }"
    }
}
$cardPath = Join-Path $RepoRoot "jules_inbox\LAPTOP_CURSOR_CONNECT.json"
$card | ConvertTo-Json -Depth 6 | Set-Content $cardPath -Encoding UTF8
Write-Host "[OK] $cardPath" -ForegroundColor Green

Write-Host "`n==> Send hello on school -> laptop channel" -ForegroundColor Cyan
$hello = @{
    from    = "school"
    message = "School PC bridge is online and two-way mesh is ready. Reply with POST /mesh/talk from your laptop."
}
Invoke-RestMethod -Uri "$RemoteUrl/mesh/talk" -Method POST -Headers $headers -ContentType "application/json" -Body ($hello | ConvertTo-Json) | Out-Null
Write-Host "[OK] LAPTOP_MESSAGE.md updated" -ForegroundColor Green

if (-not $SkipEmail) {
    Write-Host "`n==> Email laptop connect instructions" -ForegroundColor Cyan
    $py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    $body = @"
Laptop -> School PC bridge is ready.

Remote URL: $RemoteUrl
Run on laptop (PowerShell in jules-bridge repo):
  scripts\Laptop-ConnectSchoolBridge.ps1

Two-way talk:
  GET  $RemoteUrl/mesh/talk
  POST $RemoteUrl/mesh/talk with from=laptop and your message

Full card: jules_inbox/LAPTOP_CURSOR_CONNECT.json (BRIDGE_TOKEN inside).
"@
    $body | & $py (Join-Path $RepoRoot "notify_email.py") "Jules laptop connect - two-way ready"
    Write-Host "[OK] Email sent to EMAIL_TO" -ForegroundColor Green
}

Write-Host "`n==> Verify mesh" -ForegroundColor Cyan
$mesh = Invoke-RestMethod "$RemoteUrl/mesh/status" -Headers $headers -TimeoutSec 15
Write-Host "[OK] Primary: $($mesh.primary_host_id) nodes=$($mesh.nodes.Count) remote_up=$($mesh.primary_bridge.remote_up)" -ForegroundColor Green
