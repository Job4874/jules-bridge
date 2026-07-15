#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot: register mesh + show how to reach all nodes (no admin).
#>
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& (Join-Path $PSScriptRoot "Register-MeshNode.ps1") -RepoRoot $RepoRoot

$GitExe = Join-Path $env:LOCALAPPDATA "Programs\Git\cmd\git.exe"
if (Test-Path $GitExe) {
    Set-Location $RepoRoot
    $remotes = & $GitExe remote 2>$null
    if ($remotes -notcontains "origin") {
        & $GitExe remote add origin "https://github.com/Job4874/jules-bridge.git"
        Write-Host "[OK] Git remote origin -> Job4874/jules-bridge" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JULES MESH - how to connect" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Primary bridge (school 64GB PC):"
Write-Host "    Local:  http://127.0.0.1:5000"
Write-Host "    Remote: https://parade-marrow-pulp.ngrok-free.dev"
Write-Host "    Auth:   Authorization: Bearer JULES-SECURE-999"
Write-Host ""
Write-Host "  Discovery:"
Write-Host "    GET /mesh/status"
Write-Host "    GET /host/identity"
Write-Host "    jules_inbox/MESH_REGISTRY.json"
Write-Host ""
Write-Host "  Jules cloud workers:"
Write-Host "    POST /jules/fleet  (on primary bridge)"
Write-Host ""
Write-Host "  GCP offload worker:"
Write-Host "    http://34.132.193.73:6000  (via POST /vm/task on primary)"
Write-Host ""
Write-Host "  Laptop (when you boot it):"
Write-Host "    HOST_ID=laptop + own NGROK_DOMAIN in .env"
Write-Host "    Run Register-MeshNode.ps1 on laptop"
Write-Host ""
Write-Host "  GitHub: https://github.com/Job4874/jules-bridge"
Write-Host "========================================" -ForegroundColor Cyan
