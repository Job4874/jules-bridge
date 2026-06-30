# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 01: Bridge API and tentacle route map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 5
- active_prompt_chars: 9743
- omitted_middle_chars: 117031
- compression_ratio: 0.0767

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

### bridge.py
- path_ref: path-ref:f14cb63d89be
- sha256: 7104251c2cecccb3489509cf9bb9594c7417bf0a1c7f7a08c404b74f911702ba
- chars: 83477
- omitted_middle_chars: 81077
- omitted_middle_sha256: e01a04ec2b926c4df785f6db26f040cc4b7404cf05f5d62599c22dabb24707e5
- signals: smart_truncation, subagents, evidence, hrm

Head:
```text
﻿"""Jules God-Mode Bridge â€” thin HTTP routing layer.

This file contains ONLY:
  - Flask app setup and middleware
  - HTTP request validation (parsing JSON, field extraction)
  - Route handlers (validate â†’ call module â†’ return JSON)

All business logic lives in modules/:
  fs_service, shell_executor, ui_automation, inbox_service, oracle_session
"""

import errno
import json
import logging
import os
import re
import subprocess
import sys
from typing import Any
from collections import deque
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler

from flask import Flask, g, jsonify, request
from flask_cors import CORS

import notify_email as email_service
from notify_email import load_env
import modules

# -------------------
...[truncated]
```

Tail:
```text
ebug("[CHAT] Processing payload with keys: %s", list(data.keys()))
    message = string_field(data, "message", allow_empty=False)
    model_alias = string_field(data, "model", default="fast", allow_empty=False)
    system_prompt = string_field(data, "system", default="", allow_empty=True)
    image_b64 = string_field(data, "image_base64", default="", allow_empty=True)
    history = data.get("history", [])

    result = modules.chat(
        message=message,
        model_alias=model_alias,
        system_prompt=system_prompt,
        image_base64=image_b64,
        history=history,
    )
    return jsonify(dict(result)), 200



# ---------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
...[truncated]
```

### http_utils.py
- path_ref: path-ref:ae8739281a5f
- sha256: 52b6aba7d1e84c85057506f7f476c5c093bfeeed2276199d53c2d27c57e0ff61
- chars: 8337
- omitted_middle_chars: 5937
- omitted_middle_sha256: 59165f373eb38eb80cf63014b34d8e64902a9258373e3e4f58c1a821175514b0
- signals: smart_truncation

Head:
```text
"""HTTP validation and routing helpers for Jules Bridge.

These helpers are used by bridge.py and route modules to validate
incoming JSON payloads and handle errors consistently.
"""
from __future__ import annotations

import errno
import logging
import os
import re
import subprocess
from functools import wraps
from flask import jsonify, request

LOGGER = logging.getLogger("jules_bridge")

CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MISSING = object()

__all__ = [
    "CONTROL_CHAR_RE",
    "EMAIL_RE",
    "MISSING",
    "BridgeHTTPError",
    "route_errors",
    "json_payload",
    "string_field",
    "int_field",
    "bool_field",
    "string_list_field",
    "path_field",
    "content_field",
    "inbox_name_field",
]

class Brid
...[truncated]
```

Tail:
```text
st of strings")
    items = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be a list of non-empty strings")
        if control_safe and CONTROL_CHAR_RE.search(item):
            raise BridgeHTTPError(400, "Invalid input", details=f"{key} contains illegal control characters")
        items.append(item)
    return items

def path_field(data, key="path", default=MISSING):
    return string_field(data, key, default=default, control_safe=True)

def content_field(data):
    if "content" in data:
        return string_field(data, "content", allow_empty=True)
    if "data" in data:
        return string_field(data, "data", allow_empty=True)
    raise BridgeHTTPError(400, "Invalid input
...[truncated]
```

### router.py
- path_ref: path-ref:2cf5a00e44e4
- sha256: 2978e22f8da7f8fbdee2bd6cb3fe089e940d757c744b108269ad553674fea73a
- chars: 392
- omitted_middle_chars: 0
- omitted_middle_sha256:
- signals: (none)

Head:
```text
def dispatch(task_packet: dict) -> str:
    """Intelligent Task Router to classify and route a task packet."""
    task_type = task_packet.get("type")

    if task_type == "Code/Dev":
        return "Cursor/Jules"
    elif task_type == "Compute/Scale":
        return "Azure/Local VM"
    elif task_type == "Routine/UI":
        return "human_mimic_driver"

    return "UNROUTED"

```

### 02_architecture.md
- path_ref: path-ref:f83a0dbc7fa0
- sha256: 2257e98b11b16dcb6feaec1cf142b05133266632ceb57e754ced4cd864d9b94c
- chars: 14879
- omitted_middle_chars: 12479
- omitted_middle_sha256: 9239aa8a591e2bd32c82f320366f020e2c8013423589f854febc191d96346ec4
- signals: smart_truncation, subagents, long_session_evals, evidence, hrm

Head:
```text
# Jules Bridge — Architecture

> Context file 2 of 7. Defines module map, invariants, and boundaries.

## Module Map

```text
bridge.py                   ← Thin HTTP routing only. NO business logic.
├── modules/
│   ├── __init__.py         ← Package exports (single public API surface)
│   ├── fs_service.py       ← File read/write/grep/tail/list_dir
│   ├── shell_executor.py   ← PowerShell/cmd execution with timeout
│   ├── ui_automation.py    ← Screenshot/click/type, guarded secrets, UI state detection
│   ├── human_mimic_driver.py ← H/L/ACT UI driver loops built from ui_automation primitives
│   ├── vm_manager.py      ← CPU/memory pressure and dry-run-first VM boot gating
│   ├── chat_service.py    ← Gemini/OpenRouter chat provider routing and diagnostics
│   ├── inbox_service.py    ← Mes
...[truncated]
```

Tail:
```text
refreshes the COT ledger, and writes
  `JULES_WATCH_STATE.json`. It reports `Awaiting Plan`/`Awaiting User` rows as
  attention-required because the current Jules CLI does not expose plan approval.
- `POST /jules/fleet` maintains a larger Jules worker queue, pulls completed
  launched sessions, counts active remote sessions, and launches only the next
  unlaunched packets that fit inside `max_concurrent` and `launch_batch_size`.
  It is dry-run by default and writes `JULES_FLEET_STATE.json`. Failed rows,
  stale blank/unknown rows, and `Awaiting Plan` rows are retried by replacing
  the tracked packet session id when capacity is available.
- `POST /jules/fleet-watch` repeatedly runs the fleet cycle in a bounded loop,
  so completed sessions are pulled, COT is refreshed, and newly freed cap
...[truncated]
```

### 05_gotchas.md
- path_ref: path-ref:e290e27a0f0a
- sha256: 699789996c128bbfa1ab1ef36ddd4b5bec91858e5ea987e0be8ccffc1e52d6d4
- chars: 19938
- omitted_middle_chars: 17538
- omitted_middle_sha256: 2980c5ecf96b1e64e2b9307e9eecd2138f47399abf03a50cf6c3b441828612b1
- signals: smart_truncation, memory_store, subagents, long_session_evals, evidence, hrm

Head:
```text
# Jules Bridge — Gotchas



> Context file 5 of 7. What goes wrong. Not comprehensive docs — just the landmines.

> Nick Ni: "I have 553 lines of gotchas. Instead of 10,000 lines of docs."



## bridge.py



- **`string_field(data, key, default=...)`** — use `default=""` not `default=None` for optional strings

- **`json_payload()`** — raises BridgeHTTPError(400) if body is not valid JSON; always wrap with `@route_errors`

- **`@route_errors`** — MUST be the first decorator after `@app.route` (innermost position)

- **`jsonify(dict(some_dataclass))`** — dataclasses are NOT auto-serializable; convert to dict first

- **Adding a new route** — must also add to the TENTACLES list and to `context/02_architecture.md` route table

- **`POST /notify/email` attachments** - validate every local atta
...[truncated]
```

Tail:
```text

- **CRITICAL**: `/jules/watch`, `/jules/fleet`, `/jules/fleet-watch`, `/jules/cycle`, `/jules/dispatch`, `/jules/launch`, `/jules/pull`, `/jules/cot` are ALL **POST** routes, not GET. Using GET returns 405. Check `GET /tentacles` for the method column.



## doom_loop_prevention



- `GET /dashboard/status` was called 814x consecutively in one session — the worst doom loop in bridge history. Ticket 007 (circuit breaker) must be completed before any dashboard polling.

- `POST /jules/fleet-watch` averaged 441 seconds per call over 34 consecutive calls — 4.1 hours of compute burned. Always set bounded `max_wait_s`.

- `POST /shell` averaged 58 seconds per call. Never call it in a tight loop without caching.

- If you detect yourself calling any route > 5x consecutively, STOP and run the `re
...[truncated]
```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.
