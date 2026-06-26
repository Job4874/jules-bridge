<#
.SYNOPSIS
    Build Jules worker packets from a pasted Jules task queue.

.DESCRIPTION
    Calls the local Jules Bridge /jules/cycle route. By default this writes
    packet files, refreshes launch state, and builds a COT ledger without
    starting remote Jules sessions. Pass -Launch only after reviewing the
    generated commands. Live launches are still gated by remote session
    readiness checks inside the bridge. Repeated live launches skip packets
    already marked launched and keep the COT ledger cumulative. Pass -Watch to
    poll launched sessions, pull completed results, and refresh COT until the
    bounded watch window ends or all COT reports are complete. Pass -Fleet to
    keep a larger worker queue warm while respecting a max-concurrent cap. Pass
    -FleetWatch to keep scaling, pulling, and refreshing COT in one bounded loop.

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
    [switch]$Launch,
    [switch]$Fleet,
    [switch]$FleetWatch,
    [int]$MaxConcurrent = 6,
    [int]$LaunchBatchSize = 2,
    [switch]$Watch,
    [int]$WatchSeconds = 900,
    [int]$PollSeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($FleetWatch -and $Watch) {
    throw "Use either -FleetWatch or -Watch, not both."
}

if (-not $SourcePath -and -not $Content -and -not $Watch -and -not $Fleet -and -not $FleetWatch) {
    throw "Provide -SourcePath, -Content, -Fleet, -FleetWatch, or -Watch for existing packets."
}

if (-not $OutputDir) {
    $OutputDir = Join-Path $PSScriptRoot "jules_inbox\jules_dispatch"
}

if ($Fleet -or $FleetWatch) {
    $body = @{
        max_instances = $MaxInstances
        packet_dir = $OutputDir
        repo_path = $RepoPath
        max_concurrent = $MaxConcurrent
        launch_batch_size = $LaunchBatchSize
        dry_run = (-not $Launch)
        timeout_s = $LaunchTimeoutSeconds
        require_remote_ready = $true
        write_state = $true
    }
    if ($FleetWatch) {
        $body.max_wait_s = $WatchSeconds
        $body.poll_interval_s = $PollSeconds
    }
}
else {
    $body = @{
        max_instances = $MaxInstances
        write_packets = $true
        packet_dir = $OutputDir
        repo_path = $RepoPath
        launch = [bool]$Launch
        dry_run = (-not $Launch)
        timeout_s = $LaunchTimeoutSeconds
        check_remote = $true
        require_remote_ready = $true
        write_state = $true
    }
}

if ($SourcePath) {
    $body.path = (Resolve-Path -LiteralPath $SourcePath).Path
}
if ($Content) {
    $body.content = $Content
}

$json = $body | ConvertTo-Json -Depth 10
$uri = if ($FleetWatch) { "$BridgeUrl/jules/fleet-watch" } elseif ($Fleet) { "$BridgeUrl/jules/fleet" } else { "$BridgeUrl/jules/cycle" }

Write-Host "Running Jules $(if ($FleetWatch) { 'fleet-watch' } elseif ($Fleet) { 'fleet' } else { 'cycle' }) via $uri"
$result = Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json" -Body $json
$fleetResult = if ($FleetWatch) { $result.final_fleet } else { $result }
$dispatchResult = $fleetResult.dispatch
$launchResult = $fleetResult.launch_result
$cotResult = $fleetResult.cot

Write-Host "$(if ($FleetWatch) { 'Fleet-watch' } elseif ($Fleet) { 'Fleet' } else { 'Cycle' }) status: $($result.status)"
if ($FleetWatch) {
    Write-Host "Stop reason: $($result.stop_reason)"
    Write-Host "Iterations: $($result.iterations.Count)"
}
Write-Host "Tasks parsed: $($dispatchResult.task_count)"
Write-Host "Packets selected: $($dispatchResult.selected_count)"
Write-Host "Output dir: $($dispatchResult.output_dir)"
if ($Fleet -or $FleetWatch) {
    if ($FleetWatch) {
        Write-Host "Fleet-watch state: $($result.fleet_watch_state_path)"
    }
    else {
        Write-Host "Fleet state: $($result.fleet_state_path)"
    }
    Write-Host "Active remote sessions: $($fleetResult.active_remote_count)"
    Write-Host "Available launch capacity: $($fleetResult.available_launch_capacity)"
    Write-Host "Requested launch limit: $($fleetResult.requested_launch_limit)"
}
else {
    Write-Host "Cycle state: $($result.cycle_state_path)"
}

if ($dispatchResult.launch_commands) {
    Write-Host ""
    Write-Host "Launch commands:"
    foreach ($command in $dispatchResult.launch_commands) {
        Write-Host "  $command"
    }
}

$launchScript = Join-Path $OutputDir "jules_launch_commands.ps1"

Write-Host ""
Write-Host "Launch preview/state:"
Write-Host "  dry_run: $($result.launch_dry_run)"
Write-Host "  selected: $($launchResult.selected_count)"
Write-Host "  attempted: $($launchResult.attempted_count)"
Write-Host "  skipped_launched: $($launchResult.skipped_launched_count)"
Write-Host "  launched: $($launchResult.launched_count)"
Write-Host "  state: $($launchResult.state_path)"

Write-Host ""
Write-Host "COT ledger:"
Write-Host "  all_complete: $($cotResult.all_complete)"
Write-Host "  completed: $($cotResult.completed_count)"
Write-Host "  pending: $($cotResult.pending_count)"
Write-Host "  ledger: $($cotResult.ledger_path)"

if ($result.blockers) {
    Write-Host ""
    Write-Host "Blockers:"
    foreach ($blocker in $result.blockers) {
        Write-Host "  $blocker"
    }
}

if ($Launch) {
    Write-Host "Live launch requested through $uri"
}
else {
    Write-Host ""
    if ($FleetWatch) {
        Write-Host "Fleet-watch dry run complete. Rerun with -FleetWatch -Launch after reviewing capacity and packets."
    }
    elseif ($Fleet) {
        Write-Host "Fleet dry run complete. Rerun with -Fleet -Launch after reviewing capacity and packets."
    }
    else {
        Write-Host "Dry run complete. Review before launching:"
        Write-Host "  $launchScript"
        Write-Host "Then rerun with -Launch."
    }
}

if ($Watch) {
    $watchBody = @{
        packet_dir = $OutputDir
        repo_path = $RepoPath
        max_wait_s = $WatchSeconds
        poll_interval_s = $PollSeconds
        timeout_s = $LaunchTimeoutSeconds
        dry_run = $false
        require_remote_ready = $true
        write_state = $true
    }
    $watchJson = $watchBody | ConvertTo-Json -Depth 10
    $watchUri = "$BridgeUrl/jules/watch"
    Write-Host ""
    Write-Host "Watching Jules COT via $watchUri"
    $watchResult = Invoke-RestMethod -Uri $watchUri -Method Post -ContentType "application/json" -Body $watchJson -TimeoutSec ($WatchSeconds + 120)
    Write-Host "Watch status: $($watchResult.status)"
    Write-Host "Stop reason: $($watchResult.stop_reason)"
    Write-Host "Iterations: $($watchResult.iterations.Count)"
    Write-Host "Watch state: $($watchResult.watch_state_path)"
    if ($watchResult.final_cycle -and $watchResult.final_cycle.cot) {
        Write-Host "COT completed: $($watchResult.final_cycle.cot.completed_count)"
        Write-Host "COT pending: $($watchResult.final_cycle.cot.pending_count)"
    }
}
