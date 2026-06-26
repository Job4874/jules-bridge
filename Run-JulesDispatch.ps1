<#
.SYNOPSIS
    Build Jules worker packets from a pasted Jules task queue.

.DESCRIPTION
    Calls the local Jules Bridge /jules/dispatch route. By default this writes
    packet files and a launch-command script but does not start remote Jules
    sessions. Pass -Launch only after reviewing the generated commands. Launches
    are routed through /jules/launch for timeout protection and state tracking.

.EXAMPLE
    .\Run-JulesDispatch.ps1 -SourcePath C:\Users\abdul\.codex\attachments\...\pasted-text-1.txt
    .\Run-JulesDispatch.ps1 -SourcePath .\queue.txt -MaxInstances 6 -Launch
#>

param(
    [string]$SourcePath = "",
    [string]$Content = "",
    [int]$MaxInstances = 4,
    [string]$RepoPath = "C:\aotp\projects\OracleV5",
    [string]$BridgeUrl = "http://127.0.0.1:5000",
    [string]$OutputDir = "",
    [int]$LaunchTimeoutSeconds = 120,
    [switch]$Launch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $SourcePath -and -not $Content) {
    throw "Provide -SourcePath or -Content."
}

if (-not $OutputDir) {
    $OutputDir = Join-Path $PSScriptRoot "jules_inbox\jules_dispatch"
}

$body = @{
    max_instances = $MaxInstances
    write_packets = $true
    output_dir = $OutputDir
    repo_path = $RepoPath
}

if ($SourcePath) {
    $body.path = (Resolve-Path -LiteralPath $SourcePath).Path
}
if ($Content) {
    $body.content = $Content
}

$json = $body | ConvertTo-Json -Depth 8
$uri = "$BridgeUrl/jules/dispatch"

Write-Host "Dispatching Jules queue via $uri"
$result = Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json" -Body $json

Write-Host "Tasks parsed: $($result.task_count)"
Write-Host "Packets selected: $($result.selected_count)"
Write-Host "Output dir: $($result.output_dir)"

if ($result.launch_commands) {
    Write-Host ""
    Write-Host "Launch commands:"
    foreach ($command in $result.launch_commands) {
        Write-Host "  $command"
    }
}

$launchScript = Join-Path $OutputDir "jules_launch_commands.ps1"
$launchBody = @{
    packet_dir = $OutputDir
    repo_path = $RepoPath
    dry_run = (-not $Launch)
    timeout_s = $LaunchTimeoutSeconds
    write_state = $true
} | ConvertTo-Json -Depth 8

$launchUri = "$BridgeUrl/jules/launch"
$launchResult = Invoke-RestMethod -Uri $launchUri -Method Post -ContentType "application/json" -Body $launchBody

Write-Host ""
Write-Host "Launch preview/state:"
Write-Host "  dry_run: $($launchResult.dry_run)"
Write-Host "  selected: $($launchResult.selected_count)"
Write-Host "  launched: $($launchResult.launched_count)"
Write-Host "  state: $($launchResult.state_path)"

if ($Launch) {
    Write-Host "Live launch attempted through $launchUri"
}
else {
    Write-Host ""
    Write-Host "Dry run complete. Review before launching:"
    Write-Host "  $launchScript"
    Write-Host "Then rerun with -Launch."
}
