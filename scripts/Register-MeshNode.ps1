#Requires -Version 5.1
<#
.SYNOPSIS
  Register this machine in jules_inbox/MESH_REGISTRY.json (no admin).
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$HostId = "",
    [string]$Role = ""
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

. (Join-Path $PSScriptRoot "Ensure-UserPersist.ps1")
$py = Find-PythonExecutable
if (-not $py) { throw "Python not found" }

$env:PYTHONPATH = $RepoRoot
if ($HostId) { $env:HOST_ID = $HostId }
if ($Role) { $env:HOST_ROLE = $Role }

if (Test-Path (Join-Path $RepoRoot ".env")) {
    Get-Content (Join-Path $RepoRoot ".env") | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $name = $Matches[1]
            $val = $Matches[2].Trim().Trim('"').Trim("'")
            if ($val) { Set-Item -Path "Env:$name" -Value $val }
        }
    }
}

$code = @"
import os
import modules.mesh_registry as m
host_id = os.environ.get('HOST_ID') or None
role = os.environ.get('HOST_ROLE') or None
kwargs = {}
if host_id: kwargs['host_id'] = host_id
if role: kwargs['role'] = role
r = m.register_local_node(repo_root=r'$($RepoRoot.Replace("'","''"))', **kwargs)
print(r.get('primary_host_id'), len(r.get('nodes', [])))
"@

& $py -c $code
Write-Host "[OK] Mesh registry updated: $(Join-Path $RepoRoot 'jules_inbox\MESH_REGISTRY.json')" -ForegroundColor Green
