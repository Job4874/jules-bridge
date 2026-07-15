# Launch-AutoPilot.ps1 — F1 Driver One-Button Start
# ====================================================
# Starts the bridge, reads the mission queue, picks the next task,
# routes it to the right executor, and runs the post-task learning loop.
#
# Usage:
#   .\Launch-AutoPilot.ps1              # full auto (starts bridge if needed)
#   .\Launch-AutoPilot.ps1 -NoBridge   # skip bridge start (already running)
#   .\Launch-AutoPilot.ps1 -DryRun     # show plan without executing

param(
    [switch]$NoBridge,
    [switch]$DryRun,
    [string]$BridgeUrl = "http://127.0.0.1:5000"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PyExe = "C:\Users\shpctac1002c\AppData\Local\Programs\Python\Python312\python.exe"
$env:PYTHONPATH = "C:\Users\shpctac1002c\AppData\Roaming\Python\Python312\site-packages"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ANTIGRAVITY AUTOPILOT -- F1 DRIVER    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Load .env
$EnvFile = Join-Path $ScriptDir ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and (-not $line.StartsWith("#")) -and $line.Contains("=")) {
            $idx = $line.IndexOf("=")
            $key = $line.Substring(0, $idx).Trim()
            $val = $line.Substring($idx + 1).Trim()
            if ($key) { [System.Environment]::SetEnvironmentVariable($key, $val, "Process") }
        }
    }
    Write-Host "[ENV] Loaded .env" -ForegroundColor Green
} else {
    Write-Host "[WARN] No .env found" -ForegroundColor Yellow
}

$Token = $env:BRIDGE_TOKEN
if (-not $Token) {
    Write-Host "[ERROR] BRIDGE_TOKEN not set in .env" -ForegroundColor Red
    exit 1
}

# Step 2: Check/start bridge
if (-not $NoBridge) {
    $BridgeRunning = $false
    try {
        $resp = Invoke-RestMethod -Uri "$BridgeUrl/health" -TimeoutSec 3 -ErrorAction Stop
        if ($resp.status -eq "ok") { $BridgeRunning = $true }
    } catch {}

    if ($BridgeRunning) {
        Write-Host "[BRIDGE] Already running at $BridgeUrl" -ForegroundColor Green
    } else {
        Write-Host "[BRIDGE] Starting bridge..." -ForegroundColor Yellow
        if (-not $DryRun) {
            $BridgePy = Join-Path $ScriptDir "bridge.py"
            Start-Process -FilePath $PyExe -ArgumentList $BridgePy `
                -WorkingDirectory $ScriptDir -WindowStyle Minimized
            Start-Sleep -Seconds 5

            $ok = $false
            for ($i = 0; $i -lt 12; $i++) {
                try {
                    $resp = Invoke-RestMethod -Uri "$BridgeUrl/health" -TimeoutSec 2 -ErrorAction Stop
                    if ($resp.status -eq "ok") { $ok = $true; break }
                } catch {}
                Start-Sleep -Seconds 1
            }
            if ($ok) {
                Write-Host "[BRIDGE] Online at $BridgeUrl" -ForegroundColor Green
            } else {
                Write-Host "[ERROR] Bridge failed to start. Check bridge.log" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "[DRY-RUN] Would start: $PyExe bridge.py" -ForegroundColor Gray
        }
    }
}

# Step 3: Check Playwright
Write-Host "[PLAYWRIGHT] Checking browser install..." -ForegroundColor Yellow
$playwrightCheck = & $PyExe -c "from playwright.sync_api import sync_playwright; print('ok')" 2>&1
if ($playwrightCheck -notmatch "ok") {
    Write-Host "[PLAYWRIGHT] Installing..." -ForegroundColor Yellow
    if (-not $DryRun) {
        & $PyExe -m pip install playwright --user --quiet
        & $PyExe -m playwright install chromium
        Write-Host "[PLAYWRIGHT] Installed" -ForegroundColor Green
    }
} else {
    Write-Host "[PLAYWRIGHT] Ready" -ForegroundColor Green
}

# Step 4: Run mission cycle
Write-Host ""
Write-Host "[MISSION] Loading queue..." -ForegroundColor Cyan

if (-not $DryRun) {
    $Headers = @{
        "Authorization" = "Bearer $Token"
        "Content-Type"  = "application/json"
    }

    try {
        $Queue = Invoke-RestMethod -Uri "$BridgeUrl/mission/queue" -Headers $Headers -TimeoutSec 10
        Write-Host "[QUEUE] Pending: $($Queue.pending) | Active: $($Queue.active) | Done: $($Queue.done)" -ForegroundColor White

        if ($Queue.pending -eq 0 -and $Queue.active -eq 0) {
            Write-Host "[MISSION] Queue clear. Add tasks to jules_inbox/MISSION_QUEUE.md" -ForegroundColor Yellow
        } else {
            $Cycle = Invoke-RestMethod -Uri "$BridgeUrl/mission/cycle" `
                -Method POST -Headers $Headers -Body "{}" -ContentType "application/json" -TimeoutSec 15

            if ($Cycle.ok -and $Cycle.active_task) {
                $Task = $Cycle.active_task
                Write-Host ""
                Write-Host "========================================" -ForegroundColor Green
                Write-Host "  ACTIVE: $($Task.task_id) -- $($Task.type)" -ForegroundColor Green
                Write-Host "  Title: $($Task.title)" -ForegroundColor Green
                Write-Host "  URL:   $($Task.url)" -ForegroundColor Green
                Write-Host "  Agent: $($Task.assigned_to)" -ForegroundColor Green
                Write-Host "========================================" -ForegroundColor Green
                Write-Host ""

                $TaskResult = @{ ok = $false; note = "not executed" }

                switch ($Task.assigned_to) {
                    "playwright_agent" {
                        Write-Host "[EXECUTOR] Browser automation..." -ForegroundColor Cyan
                        if ($Task.type -eq "quiz") {
                            Write-Host "[BROWSER] Solving quiz: $($Task.url)" -ForegroundColor Yellow
                            $Body = @{ url = $Task.url; model = "fast" } | ConvertTo-Json
                            $Result = Invoke-RestMethod -Uri "$BridgeUrl/browser/quiz" `
                                -Method POST -Headers $Headers -Body $Body -TimeoutSec 120
                            Write-Host "[RESULT] Answered: $($Result.questions_answered)/$($Result.questions_found) | Submitted: $($Result.submitted)" -ForegroundColor White
                            if ($Result.screenshot_path) {
                                Write-Host "[PROOF]  Screenshot: $($Result.screenshot_path)" -ForegroundColor White
                            }
                            $TaskResult = $Result
                        } elseif ($Task.type -eq "research") {
                            Write-Host "[BROWSER] Navigating for research: $($Task.url)" -ForegroundColor Yellow
                            $Body = @{ url = $Task.url } | ConvertTo-Json
                            $Result = Invoke-RestMethod -Uri "$BridgeUrl/browser/navigate" `
                                -Method POST -Headers $Headers -Body $Body -TimeoutSec 60
                            Write-Host "[RESULT] Page text: $($Result.page_text.Length) chars" -ForegroundColor White
                            $TaskResult = $Result
                        }

                        # Mark done
                        $DoneBody = @{ task_id = $Task.task_id; result = $TaskResult } | ConvertTo-Json -Depth 5
                        Invoke-RestMethod -Uri "$BridgeUrl/mission/done" `
                            -Method POST -Headers $Headers -Body $DoneBody -TimeoutSec 10 | Out-Null
                        Write-Host "[MISSION] $($Task.task_id) marked DONE" -ForegroundColor Green
                    }
                    "jules_fleet" {
                        Write-Host "[EXECUTOR] Jules fleet..." -ForegroundColor Cyan
                        $Body = @{ dry_run = $false; max_concurrent = 4 } | ConvertTo-Json
                        $Result = Invoke-RestMethod -Uri "$BridgeUrl/jules/fleet" `
                            -Method POST -Headers $Headers -Body $Body -TimeoutSec 60
                        Write-Host "[FLEET] $($Result | ConvertTo-Json -Compress)" -ForegroundColor White
                        $TaskResult = $Result
                    }
                    default {
                        Write-Host "[EXECUTOR] Agent '$($Task.assigned_to)' -- self-handled" -ForegroundColor Yellow
                    }
                }

                # Post-task learning
                Write-Host "[LEARNING] Running retrospective..." -ForegroundColor Cyan
                $ReflectBody = @{ task = $Task; result = $TaskResult } | ConvertTo-Json -Depth 5
                Invoke-RestMethod -Uri "$BridgeUrl/learning/reflect" `
                    -Method POST -Headers $Headers -Body $ReflectBody -TimeoutSec 10 | Out-Null
                Write-Host "[LEARNING] Memory updated" -ForegroundColor Green

            } else {
                Write-Host "[MISSION] No task picked (all may be active/done)" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "[ERROR] Autopilot cycle failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "[DRY-RUN] Would call POST $BridgeUrl/mission/cycle and execute returned task" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AUTOPILOT CYCLE COMPLETE              " -ForegroundColor Cyan
Write-Host "  Bridge: $BridgeUrl" -ForegroundColor Cyan
Write-Host "  Queue:  jules_inbox/MISSION_QUEUE.md" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
