# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 07: VM relay cloud worker offload and tunnel runtime map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 5
- active_prompt_chars: 11711
- omitted_middle_chars: 31421
- compression_ratio: 0.2697

## No Slop Workflow
- mode: spec_first
- compaction_required: False
- phases: research -> plan -> implement
- gates: review research before plan; review plan before code; record evidence before done

## Context Handling Policy
- active_context: source head/tail excerpts only
- memory_store: head_tail_active_context_middle_memory_refs (5 refs)
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

### vm_relay.py
- path_ref: path-ref:2d9bedede7a0
- sha256: bfd018edf6527040de53e35c6dc06776d6570a8ce6b147c9aebfd4527dd69af3
- chars: 14005
- omitted_middle_chars: 11605
- omitted_middle_sha256: 61b923f86ae4852823d5574ce22dcf3d5cff0829c7d4c03668725eb2e5020683
- signals: smart_truncation

Head:
```text
#!/usr/bin/env python3
"""
Jules Two-Way Bridge Relay — vm_relay.py

This runs INSIDE the local bridge (already started as part of bridge.py modules).
It also runs as a standalone bootstrap tool to:
  1. SSH into the GCP VM
  2. Install Python + deps on the VM
  3. Push the jules-worker bootstrap script
  4. Start jules-worker-agent.py on the VM
  5. Maintain a persistent HTTP relay so local bridge <-> VM bridge can exchange tasks

The VM runs its own lightweight agent (jules-worker-agent.py) that:
  - Accepts POST /task packets
  - Executes them (code, research, browser, file ops)
  - Returns results to local bridge relay
  - Has its own Gemini key and can make autonomous decisions

Architecture:
  [User/Dashboard] -> [Local Bridge :5000] -> [VM Relay] -> [VM Agent :6000]
...[truncated]
```

Tail:
```text
ates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            pass

    # OpenRouter fallback
    for model in _FREE_MODELS:
        for key in OR_KEYS:
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "system", "content": system},
                                     {"role": "user", "content": full_prompt}],
                        "max_tokens": 4096,
                    },
                    headers={"Authorization": f"Bearer {key}"}, timeout=90
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
...[truncated]
```

### vm_manager.py
- path_ref: path-ref:57b7a4564b92
- sha256: 2940c6c80f07714a412562f11e0d40ac629c0ce40be910a2988c8301d0f23d4b
- chars: 10711
- omitted_middle_chars: 8311
- omitted_middle_sha256: d6877c7b2188b7d21a25f6e79f938865a536b3a90d89d50c4770cd0651c8a9b6
- signals: smart_truncation

Head:
```text
"""VM manager deep module -- resource pressure and guarded VM boot.

This module hides host metric collection, allowlisted script resolution, and
dry-run-first VM boot execution behind small typed contracts.

Public interface:
    detect_resource_pressure(...) -> ResourcePressureResult
    boot_secondary_vm(...) -> VMBootResult
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_CPU_THRESHOLD = 90.0
_DEFAULT_MEMORY_THRESHOLD = 90.0
_VM_SCRIPT_DIR_ENV = "JULES_VM_SCRIPT_DIR"
_ALLOWED_SCRIPT_EXTENSIONS = {".ps1", ".cmd", ".bat"}


# -------------------------
...[truncated]
```

Tail:
```text
  started=False,
                dry_run=False,
                error="allow_vm_boot must be true for real VM boot",
            )

        process = subprocess.Popen(
            _build_script_args(script_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return VMBootResult(
            status="started",
            selected_script=selected_script,
            started=True,
            dry_run=False,
            pid=process.pid,
            error=None,
        )
    except Exception as exc:
        return VMBootResult(
            status="error",
            selected_script="",
            started=False,
            dry_run=dry_run,
            error=str(exc),
        )


def check_and_scale_compute(
    dry_run: bool = True,
    allow_
...[truncated]
```

### dashboard_module.py
- path_ref: path-ref:22b604c0cd5e
- sha256: 94e707092e756f626f43e0af6a7e6917a91ef99d1cc9a2a9d4079f0ff8214763
- chars: 10191
- omitted_middle_chars: 7791
- omitted_middle_sha256: 785db922c65e02c7f09a12d6ad50f47f85669719c8bcb06c63da8e56097248cb
- signals: smart_truncation

Head:
```text
"""Dashboard module — real-time multi-cloud status aggregator.

Collects GCP VM, Azure VM, bridge health, resource pressure, Jules fleet
state, and recent log lines into a single snapshot dict.

Public interface:
    get_dashboard_status() -> dict
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from functools import lru_cache

from modules.chat_service import test_chat_providers
from modules.vm_manager import detect_resource_pressure

_ROOT = Path(__file__).parent.parent
_LOG_PATH = _ROOT / "bridge.log"
_LT_LOG_PATH = _ROOT / "jules_inbox" / "LOCAL_TUNNEL_CURRENT.log"
_LAUNCH_STATE = _ROOT / "JULES_LAUNCH_STATE.json"
_COT_LEDGER = _ROOT / "JULES_COT_LED
...[truncated]
```

Tail:
```text
url,
                "local_url": "http://127.0.0.1:5000",
            },
            "resource_pressure": {
                "status": pressure.get("status", "unknown"),
                "cpu_percent": pressure.get("cpu_percent"),
                "memory_percent": pressure.get("memory_percent"),
                "maxed_out": pressure.get("maxed_out", False),
                "reasons": pressure.get("reasons", []),
            },
            "cloud": cloud,
            "jules_fleet": fleet,
            "recent_logs": logs,
            "providers": providers,
            "env_keys_present": [
                k for k in ["GEMINI_API_KEY", "GCE_WORKER_IP", "OPENROUTER_API_KEY", "GMAIL_USER"]
                if env.get(k)
            ],
        }
        _dashboard_status_cache['last'] = (now_ts,
...[truncated]
```

### Bootstrap-Jules-VM.ps1
- path_ref: path-ref:3aace94ce984
- sha256: 7e78b3bf0511606ac85aea79849f1b5e9460f4c3a55255dd222ab0ef0d87b539
- chars: 4991
- omitted_middle_chars: 2591
- omitted_middle_sha256: 78dcb101c437d7b1893328d7d63ec647eb6ea377b842aeb15f6a041777ff9941
- signals: smart_truncation

Head:
```text
param(
    [string]$LocalBridgeToken = ""
)

# Generate SSH key and push to GCP VM via gcloud OS Login / metadata
# Then install jules-worker-agent

$VM_NAME = "jules-offload-worker"
$VM_ZONE = "us-central1-a"
$VM_PROJECT = "tibin-terminal-2026"
$VM_USER = "atibin7_gmail_com"  # gcloud uses email-derived username for OS Login
$VM_IP = "34.132.193.73"
$VM_PORT = 22

Write-Host "=== Jules VM Bootstrap ===" -ForegroundColor Cyan

# 1. Generate SSH key if needed
$sshDir = "$env:USERPROFILE\.ssh"
if (-not (Test-Path "$sshDir\jules_vm_rsa")) {
    Write-Host "[KEY] Generating SSH key..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
    & ssh-keygen -t rsa -b 4096 -f "$sshDir\jules_vm_rsa" -N "" -C "jules-worker" -q
    Write-Host "[KEY] Generated: $ssh
...[truncated]
```

Tail:
```text
5000
LOCAL_BRIDGE_TOKEN=$bridgeToken
"@
$envContent | Out-File -FilePath "$env:TEMP\vm_jules.env" -Encoding UTF8 -NoNewline

& gcloud compute scp "$env:TEMP\vm_jules.env" "julesadmin@${VM_NAME}:/home/julesadmin/.jules_worker.env" `
    --zone=$VM_ZONE --project=$VM_PROJECT 2>&1

Write-Host "[DEPS] Installing Python dependencies on VM..." -ForegroundColor Yellow
& gcloud compute ssh "julesadmin@$VM_NAME" `
    --zone=$VM_ZONE --project=$VM_PROJECT `
    --command="sudo apt-get install -y -qq python3-pip && pip3 install flask requests google-generativeai --quiet 2>&1 | tail -3" 2>&1

Write-Host "[START] Starting jules-worker-agent on VM..." -ForegroundColor Yellow
& gcloud compute ssh "julesadmin@$VM_NAME" `
    --zone=$VM_ZONE --project=$VM_PROJECT `
    --command="pkill -f jules-worker-age
...[truncated]
```

### Boot-GCP-Worker.ps1
- path_ref: path-ref:4427a5575f49
- sha256: 63778266dc046ea04cecd0e9dc4c74a4b0c6aa1eb74855cce5d17abf3a33215c
- chars: 3523
- omitted_middle_chars: 1123
- omitted_middle_sha256: 99e30c2c1422bccaa45fbb28fd577939ce2906a3170e35fb041c93bdb2694296
- signals: (none)

Head:
```text
# Boot-GCP-Worker.ps1 — enable Compute API and ensure a Jules offload worker VM exists
#
# PREREQUISITE (one-time, manual):
#   Service Usage API must be enabled on tibin-terminal-2026 via the Cloud Console:
#   https://console.developers.google.com/apis/api/serviceusage.googleapis.com/overview?project=tibin-terminal-2026
#
$ErrorActionPreference = "Continue"
$Project   = "tibin-terminal-2026"
$Zone      = "us-central1-a"
$VmName    = "jules-offload-worker"
$MachineType = "e2-standard-4"
$logDir = Join-Path $env:USERPROFILE ".jules\jules_inbox\gcp_boot"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("gcp_{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

function Write-Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format o), $msg
    Add-Content -Path $log -
...[truncated]
```

Tail:
```text
ompute instances describe $VmName `
    --zone=$Zone --project=$Project --format="value(status)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "VM not found — creating $VmName ($MachineType) in $Zone"
    & $gcloud compute instances create $VmName `
        --project=$Project `
        --zone=$Zone `
        --machine-type=$MachineType `
        --boot-disk-size=100GB `
        --boot-disk-type=pd-balanced `
        --image-family=ubuntu-2204-lts `
        --image-project=ubuntu-os-cloud `
        --scopes=cloud-platform `
        --metadata=startup-script="#`!/bin/bash`napt-get update -y`napt-get install -y git python3 python3-pip`n" `
        --quiet 2>&1 | ForEach-Object { Write-Log $_ }
} else {
    $vmStatus = ($describe | Where-Object { $_ -notmatch "^WARNING" }) -join ""
    Write-L
...[truncated]
```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.
