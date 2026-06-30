# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 09: Install bundles launch scripts and boot path map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 6
- active_prompt_chars: 6999
- omitted_middle_chars: 6661
- compression_ratio: 0.4933

## No Slop Workflow
- mode: spec_first
- compaction_required: False
- phases: research -> plan -> implement
- gates: review research before plan; review plan before code; record evidence before done

## Context Handling Policy
- active_context: source head/tail excerpts only
- memory_store: head_tail_active_context_middle_memory_refs (6 refs)
- retrieve omitted middles before assuming missing details are irrelevant
- subagent_boundary: keep heavy source analysis inside role packets
- long_session_eval: preload 10 turns; probe turn 11
## Operating Rules
- Keep the main conversation light; do heavy source analysis inside this packet.
- Use source fingerprints and path refs for retrieval; do not assume omitted middle content is irrelevant.
- Preserve head/tail evidence and ask for retrieval only when the missing middle is necessary.
- Do not reveal private chain-of-thought. Return concise rationale, decisions, and evidence.

## Deliverables
- source inventory
- operating rules
- missing or risky source notes

## Source Capsules

### requirements.txt
- path_ref: path-ref:fafb365d99be
- sha256: e1cc6a2a9c594c43cdd6f0d924d2fb9fbc40c46ca506f0c0d37a10134331645a
- chars: 74
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
flask
flask-cors
pyautogui
pyngrok
requests
google-cloud-aiplatform

```

### Launch-Bridge-WithVM.cmd
- path_ref: path-ref:157afc3148b4
- sha256: feea498aea2406e8b2500d6ebc0fccc5ef7552df2b916e22c3614950dc6b9505
- chars: 578
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
@echo off
:: Launch-Bridge-WithVM.cmd
:: Opens the bridge + GCP boot in SEPARATE windows, NOT in Cursor terminal.
:: Double-click this from Explorer, or run it from any cmd prompt.

:: 1. Boot GCP offload worker in a minimized background window
start "GCP-Worker-Boot" /MIN powershell.exe -NoProfile -ExecutionPolicy Bypass -File "path-redacted"

:: 2. Launch the bridge in its own visible window
set JULES_VM_SCRIPT_DIR=path-redacted
start "Jules-Bridge" /D "path-redacted" cmd /k "python bridge.py"

```

### Run-JulesBridge.cmd
- path_ref: path-ref:7f5db56d288d
- sha256: f09d52e4e931f0124928853fb46c08f5d6722ad2e1f208716a1eb7f235f9de7c
- chars: 795
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
@echo off
title Jules Bridge - KEEP THIS WINDOW OPEN
color 0A
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo ========================================
echo   JULES BRIDGE - dedicated terminal
echo   Logs also written to bridge.log
echo ========================================
echo.

echo [1/3] Stopping stale bridge on port 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
taskkill /F /IM ngrok.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Starting bridge + ngrok (logging to bridge.log)...
echo.
python start.py
if errorlevel 1 (
    echo.
    echo Bridge exited with error. See bridge.log
)
echo.
echo [3/3] Window stays open. Press any key to close bridge...
pause >nul

```

### start.py
- path_ref: path-ref:086a37116d48
- sha256: b711e6ca2a3e28ee67497dd520d7706ef5d5fd34c509cd832eedb1d4201dc016
- chars: 7346
- omitted_middle_chars: 4946
- omitted_middle_sha256: 9e636c052f2698cb8f25097ce3ef40c63f952e908fac76590e634f1148f5b049
- signals: (none)

Head:
```text
"""Launch Jules Bridge locally and expose it through the reserved ngrok domain."""
import json
import logging
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pyngrok import ngrok
from pyngrok.exception import PyngrokError

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "bridge.log"
NGROK_DOMAIN = "parade-marrow-pulp.ngrok-free.dev"


class _BridgeState:
    """Mutable launcher state shared by startup and shutdown hooks."""

    flask_process: subprocess.Popen | None = None


STATE = _BridgeState()


def configure_logging() -> logging.Logger:
    """Configure rotating file and stdout logging for the launcher."""
    logger = loggin
...[truncated]
```

Tail:
```text
  with response_file.open("a", encoding="utf-8") as f:
            f.write("\n[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.\n")

        try:
            subprocess.run(["git", "add", str(blocker_file), str(response_file), str(self.inbox_dir / "TUNNEL_HEALTH.json")], cwd=str(ROOT), check=True)
            subprocess.run(["git", "commit", "-m", "[TUNNEL_DEAD] Ngrok tunnel cannot self-heal"], cwd=str(ROOT), check=True)
            subprocess.run(["git", "push"], cwd=str(ROOT), check=True)
        except subprocess.CalledProcessError as e:
            log(f"Failed to push offline escalation: {e}")

if __name__ == "__main__":
    main()

    watchdog = TunnelWatchdog()
    threading.Thread(target=watchdog.run_loop, daemon=True).start()

    log("Keeping process alive. Do not close this window."
...[truncated]
```

### Launch-Offload-Host.ps1
- path_ref: path-ref:21cd9eb123a5
- sha256: 7d4619a29823dbde1f3e3a6ab0d8b5cbba4e99a5c8ac20a6da0123854e261c67
- chars: 4115
- omitted_middle_chars: 1715
- omitted_middle_sha256: de3dc58cfef73589c03ddf0d43ab4628b872dd6f406d93764ba515c374f2734b
- signals: smart_truncation

Head:
```text
# Launch-Offload-Host.ps1 - Detached local offload (NOT Cursor terminal)
param(
    [int]$MaxConcurrent = 8,
    [int]$MaxInstances = 24,
    [int]$WatchSeconds = 3600,
    [string]$BridgeUrl = "http://127.0.0.1:5000",
    [string]$RepoPath = "path-redacted",
    [string]$PacketDir = "path-redacted",
    [string]$LogDir = "path-redacted"
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

$queueP
...[truncated]
```

Tail:
```text
rent = $MaxConcurrent
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
    Log ("Fleet-watch error: {0}" -f $_.Exception.Message
...[truncated]
```

### package.json
- path_ref: path-ref:de73a5803117
- sha256: 1981f04ab62070e0f9155bc526b4e6f7616658b2904f2cfe766e3dd36a9f8e0d
- chars: 1280
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
{
  "name": "vscode-vrl",
  "displayName": "VRL Language Support",
  "description": "Syntax highlighting, snippets, IntelliSense, hovers, and lightweight diagnostics for Vector Remap Language files.",
  "version": "0.1.0",
  "publisher": "local",
  "license": "UNLICENSED",
  "private": true,
  "engines": {
    "vscode": "^1.85.0"
  },
  "categories": [
    "Programming Languages"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "languages": [
      {
        "id": "vrl",
        "aliases": [
          "Vector Remap Language",
          "VRL",
          "vrl"
        ],
        "extensions": [
          ".vrl"
        ],
        "configuration": "./language-configuration.json"
      }
    ],
    "grammars": [
      {
        "language": "vrl",
        "scopeName": "source.vrl",
...[truncated]
```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.
