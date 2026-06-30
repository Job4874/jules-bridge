# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 08: Test suite and evidence recording map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 5
- active_prompt_chars: 11595
- omitted_middle_chars: 105766
- compression_ratio: 0.0985

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

### test_bridge_routes.py
- path_ref: path-ref:8f019eade3fe
- sha256: eeb456d587bcec8071f501fa495dd1b3553409ef422ba7ccaaacabc0ae84a272
- chars: 44878
- omitted_middle_chars: 42478
- omitted_middle_sha256: 49f7bd52dc3a4f8be558b1e73506446e6a7fb302b615615b849ecfb2ff0237ab
- signals: context_engineering, smart_truncation, subagents, tdd, evidence

Head:
```text
import os
os.environ["BRIDGE_TOKEN"] = "JULES-SECURE-999"
"""Integration tests for bridge.py HTTP routes.

These test the HTTP surface — validate → call module → JSON response.
Module internals are mocked. For module-level unit tests see test_*_service.py.
"""

import os
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import bridge


BRIDGE_AUTH_HEADER = {"Authorization": "Bearer JULES-SECURE-999"}


def authed_client(test_client):
    """Wrap Flask test client so protected routes receive the bridge token."""

    class _AuthedClient:
        def get(self, path, **kwargs):
            headers = {**BRIDGE_AUTH_HEADER, **(kwargs.pop("headers", None) or {})}
            return test_cli
...[truncated]
```

Tail:
```text
alse, "providers": {"gemini": {"status": "no_key"}}}

        response = self.client.get("/chat/test")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["healthy"])
        mock_test.assert_called_once_with()

    @patch("modules.chat")
    def test_chat_route_is_thin(self, mock_chat):
        mock_chat.return_value = {"response": "ok", "model_used": "stub", "elapsed_ms": 1, "errors": []}

        response = self.client.post(
            "/chat",
            json={
                "message": "hello",
                "model": "smart",
                "system": "system",
                "image_base64": "abc",
                "history": [{"role": "user", "content": "prior"}],
            },
        )

        self.assertEqual(response.status_cod
...[truncated]
```

### test_context_orchestrator.py
- path_ref: path-ref:bd38b89c1b62
- sha256: b2bcadf8488eebac0dc2f145f8971009d82e19b4b6e4e291cc1961b239ca2510
- chars: 6236
- omitted_middle_chars: 3836
- omitted_middle_sha256: fe46fc5247fbcf12f76bf3ee3ae316e522be5cc8ecaeaffa052c539258ebfcd0
- signals: context_engineering, smart_truncation, memory_store, subagents, long_session_evals, tdd, evidence, hrm

Head:
```text
"""Tests for modules/context_orchestrator.py."""

import json
import os
import tempfile

from modules.context_orchestrator import build_context_subagents


def test_builds_budgeted_capsules_without_middle_bloat():
    content = (
        "BEGIN context engineering needs memory stores and subagents.\n"
        + ("middle filler\n" * 100)
        + "MIDDLE_SHOULD_NOT_BE_IN_PACKET\n"
        + ("more middle filler\n" * 100)
        + "END long session evals need evidence gates.\n"
    )

    result = build_context_subagents(
        content=content,
        task="Optimize context handling",
        roles=["implementation_planner"],
        head_chars=80,
        tail_chars=80,
        max_packet_chars=3000,
    )

    assert result["status"] == "ready"
    assert result["context_strategy"] ==
...[truncated]
```

Tail:
```text
locked"
        assert result["error"] == "no readable source content"
        assert result["sources"][0]["readable"] is False
        assert result["sources"][0]["path_ref"].startswith("path-ref:")
        assert missing not in result["sources"][0]["error"]


def test_role_filter_selects_requested_role_only():
    result = build_context_subagents(
        content="Context management should delegate heavy search to subagents.",
        roles=["memory_curator"],
    )

    assert [agent["role_id"] for agent in result["subagents"]] == ["memory_curator"]


def test_capsule_excerpts_redact_local_paths_inside_source_text():
    result = build_context_subagents(
        content=(
            "Read path-redacted \r\n"
            "before continuing with context engineering.   \r\n"
        ),
...[truncated]
```

### test_jules_orchestrator.py
- path_ref: path-ref:081ab555bcdb
- sha256: 2d449e203b471d4b98c534dfd2c91f0505e71ead88ffa92ce20e955547b0e4f6
- chars: 50084
- omitted_middle_chars: 47684
- omitted_middle_sha256: ede927911074d05b8aa5e0bb11c76d0c43b77d6ffbe52b255fb3266a74cf4e21
- signals: smart_truncation, evidence

Head:
```text
"""Tests for Jules task dispatch orchestration.

The dispatcher is intentionally offline by default: it parses Jules cards and
builds worker packets/launch commands without starting remote sessions.
"""

import os
import json
import sys
import tempfile
import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def disable_session_cache(monkeypatch):
    monkeypatch.setenv("JULES_SESSION_CACHE_TTL_S", "0")

from modules.jules_orchestrator import (
    _run_cli_command,
    build_cot_ledger,
    build_dispatch,
    jules_preflight,
    launch_packets,
    list_remote_sessions,
    parse_antigravity_queue,
    parse_task_dump,
    pull_remote_session,
    run_jules_cycle,
    run_jules_fleet,
    run_jules_fleet_watch,
    run_jules_watch,
)


SAMPLE_DUMP = """Needs review
T
...[truncated]
```

Tail:
```text
["iterations"][0]["launched_sessions"] == ["222222"]
    assert result["iterations"][1]["pulled_sessions"] == ["222222"]
    assert mock_fleet.call_args_list[0].kwargs["source_path"] == r"path-redacted"
    assert mock_fleet.call_args_list[1].kwargs["source_path"] == ""


@patch("modules.jules_orchestrator.run_jules_fleet")
def test_run_jules_fleet_watch_dry_run_stops_after_one_iteration(mock_fleet):
    mock_fleet.return_value = {
        "status": "pending",
        "blockers": [],
        "pull_results": [],
        "launch_result": {"attempt_results": []},
        "active_remote_count": 0,
        "available_launch_capacity": 2,
        "requested_launch_limit": 2,
        "remote_status_counts": {},
        "remote_statuses": [],
        "cot": {
            "all_complete": False,
...[truncated]
```

### test_evidence.json
- path_ref: path-ref:13f18ffac4ad
- sha256: fe5fbf8613f44c0ee0edf64e48d5b24a8c25a4d758cac096c273d27b24f7fddb
- chars: 6705
- omitted_middle_chars: 4305
- omitted_middle_sha256: ababd5c076dbaebf6e6b94e778feef487018f9a75945d719ab3679f461298d4e
- signals: smart_truncation, evidence

Head:
```text
[
  {
    "output_hash": "8de1babe4bdad5b8fbc168813686c348a5073fdf758f71cd4b4dd788fddf7007",
    "timestamp_utc": "2026-06-26T20:38:37.116440+00:00",
    "passed": true,
    "test_count": 244,
    "raw_output_tail": "  /workspace/jules-bridge/modules/retrospective_module.py:58: PytestCollectionWarning: cannot collect test class 'TestEvidence' because it has a __init__ constructor (from: tests/test_retrospective_module.py)\n    @dataclass\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n244 passed, 1 warning in 1.68s"
  },
  {
    "output_hash": "665ca5504aaad019c608b6186db9fb6e62ab8865aa30f01c05433173abec703d",
    "timestamp_utc": "2026-06-26T20:50:26.142820+00:00",
    "passed": true,
    "test_count": 248,
    "raw_output_tail": "  /workspace/jules-bridge/modu
...[truncated]
```

Tail:
```text
13:33.825254+00:00",
    "passed": true,
    "test_count": 307,
    "raw_output_tail": "307 passed in 14.08s"
  },
  {
    "output_hash": "40e1389e0c36e3f2471acae69bd158c0022dc0f9257a47ffa0c8a6b0cc65b86a",
    "timestamp_utc": "2026-06-29T17:21:29.387869+00:00",
    "passed": true,
    "test_count": 307,
    "raw_output_tail": "307 passed in 14.31s"
  },
  {
    "output_hash": "fd5a5a13015e3f4bf8f36720d7acb9aafa4e7b2eee3d0caa1d2714b22fb65022",
    "timestamp_utc": "2026-06-29T18:25:05.263907+00:00",
    "passed": true,
    "test_count": 314,
    "raw_output_tail": "python -m pytest tests/ -q\n314 passed in 13.89s"
  },
  {
    "output_hash": "e1e7b4bce3b265a14326d66a18eb33d1a99af42a348d85cb1d45c9a614065408",
    "timestamp_utc": "2026-06-29T18:27:32.710356+00:00",
    "passed": true,
    "
...[truncated]
```

### 07_library_docs.md
- path_ref: path-ref:61fe8cce1da5
- sha256: c93ecb8fd6e43de98a76d205d326a1e1370d97e2c12e079d29f89274a23fa0a2
- chars: 9863
- omitted_middle_chars: 7463
- omitted_middle_sha256: b5f6b936ef2ce91fb8bdddd8bd2594ec4dc071960f3aece67fec7660da39ef3c
- signals: evidence

Head:
```text
# Jules Bridge — Library Docs

> Context file 7 of 7. How each dependency is used *in this specific project*.
> Not generic docs — project-specific patterns, configurations, and rules.

## Flask (flask + flask-cors)

### Configuration

- App created in `bridge.py` line 66: `app = Flask(__name__)`

- CORS enabled globally: `CORS(app)` — no origin restrictions (runs locally)

- No authentication middleware — local-only, firewall-protected

- Runs on port **5000** by default

### Error Handling Chain

All route handlers MUST use the `@route_errors` decorator (bridge.py lines 92–134). The decorator maps exceptions to HTTP status codes in this priority:

1. `BridgeHTTPError` → custom status code

2. `subprocess.TimeoutExpired` → 504

3. `ShellNotAvailableError` / `UnsupportedShellError` → 400
...[truncated]
```

Tail:
```text
 SMTP connection

---

## logging (stdlib)

### Configuration

- `RotatingFileHandler` writing to `bridge.log` at project root

- Max size: 10 MB, 3 backup files, UTF-8 encoding

- Format: `2025-06-25T14:30:00+0000 INFO jules_bridge: message`

- Both file and stdout handlers are tagged with `_jules_bridge_handler = True` to prevent duplicate registration

### Rules

- Always use `LOGGER = logging.getLogger("jules_bridge")` — never use `print()` for operational output

- The retrospective module reads `bridge.log` for pattern analysis — if you break the log format, you break retrospective analysis

- `start.py` has its own logger: `jules_bridge_start` — separate from the main bridge logger

---

## MCP Servers

If an MCP server is configured for any library used in this project:

1. Read it
...[truncated]
```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.
