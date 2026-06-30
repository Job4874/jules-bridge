# Launch-Dashboard.ps1
# Compatibility wrapper for the repo-owned Jules cockpit quick boot.

[CmdletBinding()]
param(
    [switch]$SkipVMBoot,
    [switch]$SkipBridge,
    [switch]$NoDashboard,
    [switch]$NoBrowser,
    [int]$BridgePort = 5000,
    [int]$DashboardPort = 5173
)

$launcher = Join-Path $PSScriptRoot "Quick-Boot-Jules-Cockpit.ps1"
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Quick boot launcher missing: $launcher"
}

& $launcher @PSBoundParameters
