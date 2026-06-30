# Launch-Offload-Host.ps1 - Detached local offload (NOT Cursor terminal)
param(
    [int]$MaxConcurrent = 8,
    [int]$MaxInstances = 24,
    [int]$WatchSeconds = 3600,
    [string]$BridgeUrl = "http://127.0.0.1:5000",
    [string]$RepoPath = "C:\aotp\projects\OracleV5",
    [string]$PacketDir = "$PSScriptRoot\jules_inbox\jules_dispatch",
    [string]$LogDir = "$PSScriptRoot\jules_inbox\offload_logs"
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$log = Join-Path $LogDir ("offload_{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

function Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format o), $msg
    Add-Content -Path $log -Value $line
    Write-Output $line
}

Log "OFFLOAD START host PID=$PID"

$headers = @{
    Authorization = "Bearer JULES-SECURE-999"
    "Content-Type" = "application/json"
}

$queuePath = Join-Path $PSScriptRoot "jules_inbox\antigravity_offload_queue.txt"
$promptDir = "C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover\TIBIN_CODEX_MASTER_HANDOVER_V2\04_CODEX_PROMPTS"
if (-not (Test-Path $queuePath) -and (Test-Path $promptDir)) {
    $lines = @()
    Get-ChildItem -Path $promptDir -Filter "*.md" | ForEach-Object {
        $lines += "Needs review | Antigravity offload: $($_.Name) | repo=$RepoPath"
    }
    $lines | Set-Content -Path $queuePath -Encoding UTF8
    Log ("Built queue: {0} count={1}" -f $queuePath, $lines.Count)
}

try {
    $pressure = Invoke-RestMethod -Uri "$BridgeUrl/vm/resource_pressure" -Method POST -Headers $headers -Body "{}" -TimeoutSec 15
    Log ("VM pressure status={0} mem={1}" -f $pressure.status, $pressure.memory_percent)
    if ($pressure.status -eq "maxed_out") {
        Log "Host maxed out - booting secondary VM via bridge"
        $bootBody = @{ script_name = "Start-SecondaryVM.ps1"; dry_run = $false; allow_vm_boot = $true } | ConvertTo-Json
        try {
            $boot = Invoke-RestMethod -Uri "$BridgeUrl/vm/boot_secondary" -Method POST -Headers $headers -Body $bootBody -TimeoutSec 60
            Log ("Secondary VM boot status={0}" -f $boot.status)
        } catch {
            Log ("Secondary VM boot skipped: {0}" -f $_.Exception.Message)
        }
    }
} catch {
    Log ("VM pressure skipped: {0}" -f $_.Exception.Message)
}

# Google Cloud compute worker (tibin-terminal-2026) - detached host script, not Cursor
$gcpBoot = Join-Path $PSScriptRoot "vm_scripts\Boot-GCP-Worker.ps1"
if (Test-Path $gcpBoot) {
    Log "Spawning GCP worker boot in background host process"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$gcpBoot`""
    ) -WindowStyle Minimized | Out-Null
}

$body = @{
    path = $queuePath
    packet_dir = $PacketDir
    repo_path = $RepoPath
    max_instances = $MaxInstances
    max_concurrent = $MaxConcurrent
    launch_batch_size = 3
    dry_run = $false
    timeout_s = 180
    require_remote_ready = $true
    write_state = $true
    max_wait_s = $WatchSeconds
    poll_interval_s = 45
} | ConvertTo-Json -Depth 6

Log ("Starting jules/fleet-watch LIVE concurrent={0} watch_s={1}" -f $MaxConcurrent, $WatchSeconds)
try {
    $result = Invoke-RestMethod -Uri "$BridgeUrl/jules/fleet-watch" -Method POST -Headers $headers -Body $body -TimeoutSec ($WatchSeconds + 300)
    Log ("Fleet-watch status={0} stop={1}" -f $result.status, $result.stop_reason)
    if ($result.final_fleet.cot) {
        Log ("COT complete={0} pending={1}" -f $result.final_fleet.cot.completed_count, $result.final_fleet.cot.pending_count)
    }
} catch {
    Log ("Fleet-watch error: {0}" -f $_.Exception.Message)
}

try {
    $mail = @{
        subject = "[JULES-OFFLOAD] Host fleet-watch finished"
        body = "Log: $log"
    } | ConvertTo-Json
    Invoke-RestMethod -Uri "$BridgeUrl/notify/email" -Method POST -Headers $headers -Body $mail -TimeoutSec 30 | Out-Null
    Log "Email sent"
} catch {
    Log ("Email skipped: {0}" -f $_.Exception.Message)
}

Log "OFFLOAD END"
