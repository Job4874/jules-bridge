# Launch-Offload-Host.ps1 — Detached local offload (NOT Cursor terminal)
# Spawns Jules Google-remote fleet + Antigravity handover workers on the Windows host.

param(
    [int]$MaxConcurrent = 8,
    [int]$MaxInstances = 24,
    [int]$WatchSeconds = 3600,
    [string]$BridgeUrl = "http://127.0.0.1:5000",
    [string]$RepoPath = "C:\aotp\projects\OracleV5",
    [string]$PacketDir = "C:\Users\abdul\.jules\jules_inbox\jules_dispatch",
    [string]$LogDir = "C:\Users\abdul\.jules\jules_inbox\offload_logs"
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$log = Join-Path $LogDir ("offload_{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

function Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format o), $msg
    Add-Content -Path $log -Value $line
    Write-Output $line
}

Log "OFFLOAD START — host detached process PID=$PID"

$headers = @{
    Authorization = "Bearer JULES-SECURE-999"
    "Content-Type" = "application/json"
}

# 1) Build Antigravity offload queue from CODEX prompts if missing
$queuePath = "C:\Users\abdul\.jules\jules_inbox\antigravity_offload_queue.txt"
$promptDir = "C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover\TIBIN_CODEX_MASTER_HANDOVER_V2\04_CODEX_PROMPTS"
if (-not (Test-Path $queuePath) -and (Test-Path $promptDir)) {
    $lines = @()
    Get-ChildItem -Path $promptDir -Filter "*.md" | ForEach-Object {
        $lines += "Needs review | Antigravity offload: $($_.Name) | repo=$RepoPath | read=$($_.FullName)"
    }
    $lines | Set-Content -Path $queuePath -Encoding UTF8
    Log "Built queue: $queuePath ($($lines.Count) tasks)"
}

# 2) VM resource check — skip local VM if maxed
try {
    $pressure = Invoke-RestMethod -Uri "$BridgeUrl/vm/resource_pressure" -Method POST -Headers $headers -Body "{}" -TimeoutSec 15
    Log ("VM pressure: status={0} cpu={1} mem={2}" -f $pressure.status, $pressure.cpu_percent, $pressure.memory_percent)
} catch {
    Log "VM pressure check skipped: $($_.Exception.Message)"
}

# 3) Jules fleet-watch LIVE — Google remote workers (cloud offload)
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

Log "Starting jules/fleet-watch LIVE max_concurrent=$MaxConcurrent watch_s=$WatchSeconds"
try {
    $result = Invoke-RestMethod -Uri "$BridgeUrl/jules/fleet-watch" -Method POST -Headers $headers -Body $body -TimeoutSec ($WatchSeconds + 300)
    Log ("Fleet-watch status={0} stop={1} iterations={2}" -f $result.status, $result.stop_reason, $result.iterations.Count)
    if ($result.final_fleet.cot) {
        Log ("COT complete={0} pending={1}" -f $result.final_fleet.cot.completed_count, $result.final_fleet.cot.pending_count)
    }
} catch {
    Log "Fleet-watch error: $($_.Exception.Message)"
}

# 4) Email operator summary (one shot)
try {
    $mail = @{
        subject = "[JULES-OFFLOAD] Host fleet-watch finished"
        body = "Detached offload log: $log`nSee JULES_COT_LEDGER in $PacketDir"
    } | ConvertTo-Json
    Invoke-RestMethod -Uri "$BridgeUrl/notify/email" -Method POST -Headers $headers -Body $mail -TimeoutSec 30 | Out-Null
    Log "Operator email sent"
} catch {
    Log "Email skipped: $($_.Exception.Message)"
}

Log "OFFLOAD END"
