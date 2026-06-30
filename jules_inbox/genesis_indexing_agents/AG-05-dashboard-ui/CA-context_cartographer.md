# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 05: Dashboard UI build and status panel map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 5
- active_prompt_chars: 7749
- omitted_middle_chars: 27440
- compression_ratio: 0.2182

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

### App.jsx
- path_ref: path-ref:629c358eca63
- sha256: 1da0d27cd377dc4d3cdcfa0b47dcba646fb252d059daceac21b130efec71cda8
- chars: 19325
- omitted_middle_chars: 16925
- omitted_middle_sha256: 8e71dd86fc7082e52fbd8312200b3a6bfaf652c7e461482bd1392264b0debe10
- signals: smart_truncation

Head:
```text
import { useState, useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import './index.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
);

const BRIDGE = import.meta.env.VITE_BRIDGE_URL || 'http://127.0.0.1:5000';
const TOKEN = import.meta.env.VITE_BRIDGE_TOKEN || '';

const DEFAULT_PROVIDERS = {
  gemini: { status: 'no_key' },
  openrouter: { status: 'no_key' },
  vm_worker: { status: 'offline' },
};

const providerStatus = (providers, key) => providers?.[key]?.status || DEFAULT_PROVIDERS[key]?.status ||
...[truncated]
```

Tail:
```text
v>
            )}
          </div>

          <div className="chat-input-area">
            {pendingImage && (
              <div className="img-strip">
                <img src={pendingImage.src} alt="thumbnail" />
                <span className="img-label">Visual data attached</span>
                <button className="btn-clear" onClick={() => setPendingImage(null)} title="Remove attachment">✕</button>
              </div>
            )}
            <div className="chat-row">
              <textarea
                className="chat-input"
                placeholder="Enter command or paste image..."
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={onKey}
                rows={1}
                title="Message Inpu
...[truncated]
```

### index.css
- path_ref: path-ref:51a8fadf6a19
- sha256: 850cc06729d21feddba845a4f1deee2b42ba5ab70ebee7ef03dba08b8561829f
- chars: 9982
- omitted_middle_chars: 7582
- omitted_middle_sha256: ef13e37b06516f89bdaf2053e215a32b821e21aa7f15313aff649f5ab19150a3
- signals: smart_truncation

Head:
```text
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
  --bg-color: #0d1117;
  --panel-bg: rgba(22, 27, 34, 0.65);
  --panel-border: rgba(255, 255, 255, 0.1);

  --text-main: #e6edf3;
  --text-dim: #8b949e;

  --accent-blue: #58a6ff;
  --accent-green: #3fb950;
  --accent-red: #f85149;
  --accent-yellow: #d29922;

  --font-sans: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-sans);
  background-color: var(--bg-color);
  color: var(--text-main);
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

#root {
  height: 100%;
  width: 100%;
  display: flex;
  flex-d
...[truncated]
```

Tail:
```text
5, 255, 0.08);
}

.btn-send {
  width: 42px;
  height: 42px;
  border-radius: 6px;
  border: 1px solid var(--accent-blue);
  background: rgba(88, 166, 255, 0.15);
  color: var(--accent-blue);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-send:hover {
  background: rgba(88, 166, 255, 0.25);
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.img-preview {
  max-width: 100%;
  border-radius: 4px;
  margin-top: 8px;
  border: 1px solid rgba(255,255,255,0.1);
}

.img-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: rgba(88, 166, 255, 0.08);
  border: 1px solid rgba(88, 166, 255, 0.2);
  border-radius: 6px;
  margin-bottom: 12px;
}
.img-strip im
...[truncated]
```

### package.json
- path_ref: path-ref:bf4cf1ed72ab
- sha256: b582cd17a8790112817a421b1835f06989f74c82497d7e49e5dc1f509ae14ac5
- chars: 547
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
{
  "name": "dashboard-ui",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "oxlint",
    "preview": "vite preview"
  },
  "dependencies": {
    "chart.js": "^4.5.1",
    "react": "^19.2.7",
    "react-chartjs-2": "^5.3.1",
    "react-dom": "^19.2.7"
  },
  "devDependencies": {
    "@types/react": "^19.2.17",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.2",
    "oxlint": "^1.69.0",
    "vite": "^8.1.0"
  }
}

```

### Launch-Dashboard.ps1
- path_ref: path-ref:4223628f8457
- sha256: 4c1d4bb23b8802683ca371961a8c49f66e62efb46d0d985720cce1c236d19c57
- chars: 5333
- omitted_middle_chars: 2933
- omitted_middle_sha256: 0c12ae12a0e4088aeb964c464e8217c9ba060a22fbf5c6ce233d2f83a7b64337
- signals: (none)

Head:
```text
# Launch-Dashboard.ps1
# Opens PowerShell as Administrator, starts the bridge, boots cloud VMs,
# and opens the Jules Mission Control dashboard in the browser.
# Run this by right-clicking and "Run as Administrator", or via the .cmd wrapper.

param(
    [switch]$SkipVMBoot,
    [switch]$SkipBridge,
    [int]$BridgePort = 5000
)

$ErrorActionPreference = "Continue"
$Root = "path-redacted"
$BridgeUrl = "http://127.0.0.1:$BridgePort"
$Dashboard = Join-Path $Root "dashboard.html"

function Write-Banner($msg, $color = "Cyan") {
    Write-Host "`n$("=" * 60)" -ForegroundColor $color
    Write-Host "  $msg" -ForegroundColor $color
    Write-Host "$("=" * 60)" -ForegroundColor $color
}

function Test-BridgeAlive {
    try {
        $r = Invoke-WebRequest -Uri "$BridgeUrl/ping" -TimeoutSec 3 -UseBa
...[truncated]
```

Tail:
```text
 summary loop (optional companion output)
# ---------------------------------------------------------------
Write-Banner "LIVE STATUS (refreshes every 10s — Ctrl+C to stop)" "DarkCyan"
while ($true) {
    try {
        $json = Invoke-RestMethod -Uri "$BridgeUrl/dashboard/status" -TimeoutSec 5 -ErrorAction Stop
        $cpu  = if ($json.resource_pressure.cpu_percent) { "{0:N1}%" -f $json.resource_pressure.cpu_percent } else { "?" }
        $mem  = if ($json.resource_pressure.memory_percent) { "{0:N1}%" -f $json.resource_pressure.memory_percent } else { "?" }
        $online = $json.cloud.online
        $total  = $json.cloud.total
        $comp   = $json.jules_fleet.completed
        $launched = $json.jules_fleet.launched
        $uptime = $json.bridge.uptime_human

        $ts = Get-Date -F
...[truncated]
```

### Open-Dashboard.cmd
- path_ref: path-ref:4ac7f765cd3d
- sha256: 901be12e6bbf95682d9ba6f65dfc19f3dade99ec8a8bcd925136668e1c311b9e
- chars: 319
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
@echo off
:: Jules Mission Control — double-click to launch as Administrator
:: Opens the real-time dashboard + bridge + cloud VMs in one shot.
powershell.exe -Command "Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""path-redacted""' -Verb RunAs"

```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.
