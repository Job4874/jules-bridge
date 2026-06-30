# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Genesis codebase index subagent 06: Chat provider and deep health readiness map. Read-only. Do not edit source. Return files/routes indexed, boot implications, verification needed, and blockers.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 5
- active_prompt_chars: 11868
- omitted_middle_chars: 57880
- compression_ratio: 0.1698

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

### chat_service.py
- path_ref: path-ref:90fa313dd881
- sha256: 26a3be9e19fd962e77f7c6d42be731fa5f204e2c1fdfac907398571f81809fe2
- chars: 25550
- omitted_middle_chars: 23150
- omitted_middle_sha256: ef3c5ffb7bcfd9d1cc5ef97346ae5a9ad84f6492cc7d5aa61d72049219d43f51
- signals: smart_truncation

Head:
```text
"""Chat provider routing for the Jules Bridge chat endpoints.

This module hides provider selection, request payload construction, fallback
handling, and secret redaction behind two small public functions.

Public interface:
    test_chat_providers() -> ChatHealthResult
    chat(message, model_alias, system_prompt, image_base64, history) -> ChatResult
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Mapping, Sequence

_GEMINI_FAST = "gemini-2.0-flash"
_GEMINI_SMART = "gemini-2.5-pro"
_OPENROUTER_FAST = "google/gemma-3-27b-it:free"
_OPENROUTER_FAST_FALLBACKS = [
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "openchat/openchat-7b:free",
]
_OPENROUTER_SMART = "deepseek/deepseek-r1:free"
_OPENROUTER_SMART_FALLBA
...[truncated]
```

Tail:
```text
task, vm_get_status):
        try:
            response_text, vm_error = _vm_chat_fallback(
                message=message,
                system_prompt=system,
                vm_send_task=vm_send_task,
                vm_get_status=vm_get_status,
                sleep_func=sleep_func,
                task_attempts=vm_task_attempts,
                poll_attempts=vm_poll_attempts,
                poll_interval_s=vm_poll_interval_s,
            )
            if response_text:
                model_used = _VM_CHAT_MODEL
            elif vm_error:
                errors.append(vm_error)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(f"VM fallback exception: {str(exc)[:120]}")

    elapsed_ms = _elapsed_ms(start, clock)
    if response_te
...[truncated]
```

### health_service.py
- path_ref: path-ref:bac7bc7a4a04
- sha256: 5141dbcb9fc821883b9ab554c1bba63fcb2d6fd167c5c36bfded817044f696f9
- chars: 4357
- omitted_middle_chars: 1957
- omitted_middle_sha256: 232031e6c6fa441734a9aa5c357829ca690b195d1170b4d692e8aa6b76a3e264
- signals: smart_truncation

Head:
```text
"""Health service deep module — multi-provider connectivity and host status.

Tests API keys (or acknowledges keyless state), cloud reachability, and
resource pressure to provide a proof of system readiness.
"""

from __future__ import annotations

import os
import time
import socket
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from modules.chat_service import test_chat_providers
from modules.vm_manager import detect_resource_pressure


def _map_chat_provider_result(result: Dict[str, Any]) -> Dict[str, Any]:
    status = result.get("status")
    mapped = {
        "ok": "pass",
        "error": "fail",
        "exception": "error",
        "no_key": "keyless",
        "offline": "fail",
    }.get(status, "unknown")
...[truncated]
```

Tail:
```text
il not installed"}
    except Exception as exc:
        return {"error": str(exc)}

def get_deep_health() -> Dict[str, Any]:
    """Execute all health checks in parallel and return aggregated status."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_chat = executor.submit(_check_chat_providers)
        f_gcp = executor.submit(_check_gcp)
        f_azure = executor.submit(_check_azure)

        chat_results = f_chat.result()
        results = {
            **chat_results,
            "gcp": f_gcp.result(),
            "azure": f_azure.result(),
        }

    pressure = detect_resource_pressure()
    disk = get_disk_usage()

    return {
        "status": "ok",
        "keyless_mode": not (os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")),
...[truncated]
```

### test_chat_service.py
- path_ref: path-ref:c785b0d0ba64
- sha256: 583d744963956333c74d8c8bb3e6bc2089565d51a70ca8cf9474064bb6a06e53
- chars: 24379
- omitted_middle_chars: 21979
- omitted_middle_sha256: 6f22143e2cd3d15f407415971bfe2f927945fd1161690e076d6f9dd8fb24fc9d
- signals: smart_truncation

Head:
```text
"""Tests for chat provider routing."""

import unittest
from unittest.mock import patch

from modules import chat_service


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeRequests:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def clock_from(values):
    iterator = iter(values)
    return lambda: next(iterator)


class TestChatProviderHealth(unittest.TestCase):
    def setUp(self):
        chat_service._LAST_VM_CHAT_FAIL
...[truncated]
```

Tail:
```text
 "status": "done",
                            "result": "OK",
                        }
                    ],
                },
            ]
        )

        with patch("modules.chat_service.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "fixedmarker123"
            result = chat_service.test_chat_providers(
                env={},
                requests_client=FakeRequests([]),
                clock=clock_from([1.0, 1.2]),
                vm_send_task=lambda *args, **kwargs: {"ok": True, "status": "queued"},
                vm_get_status=lambda: next(statuses),
                sleep_func=lambda _: None,
            )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "ok")

    def test_sanitize_det
...[truncated]
```

### test_health_deep.py
- path_ref: path-ref:b6f438403620
- sha256: 0407d1215a56da0f34ee28f04551baf0172f31789d0781008a4e9a41c356747c
- chars: 4207
- omitted_middle_chars: 1807
- omitted_middle_sha256: 2e0463942992d822b03188a14252ea450539a10c366901e0d5c8b8c45a5d7537
- signals: smart_truncation

Head:
```text
import unittest
from unittest.mock import patch, MagicMock
from bridge import app

class TestHealthDeep(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.token = "JULES-SECURE-999"

    @patch("modules.health_service.test_chat_providers")
    @patch("modules.health_service.detect_resource_pressure")
    @patch("modules.health_service.get_disk_usage")
    @patch("modules.reasoning_module._gcloud_access_token")
    @patch("socket.create_connection")
    def test_health_deep_success(self, mock_socket, mock_gcloud, mock_disk, mock_pressure, mock_chat):
        mock_chat.return_value = {
            "healthy": True,
            "providers": {
                "gemini": {"status": "ok", "ms": 10},
                "openrouter
...[truncated]
```

Tail:
```text
r_type": "invalid_key",
                    "detail": "HTTP 401: user not found",
                },
            },
        }
        mock_pressure.return_value = {"cpu_percent": 10.0, "memory_percent": 20.0, "maxed_out": False}
        mock_disk.return_value = {"percent": 50.0, "free_gb": 100}

        response = self.app.get('/health/deep', headers={"Authorization": f"Bearer {self.token}"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["providers"]["gemini"]["status"], "fail")
        self.assertEqual(data["providers"]["gemini"]["code"], 400)
        self.assertEqual(data["providers"]["gemini"]["error_type"], "invalid_key")
        self.assertEqual(data["providers"]["openrouter"]["status"], "fail")
        self.asser
...[truncated]
```

### test_dashboard_module.py
- path_ref: path-ref:575c45fcfcb1
- sha256: a4a51c9ac0791fcb18606fbd8ed7c97c2289259e8b9d6bfb2712edfcd9345726
- chars: 11387
- omitted_middle_chars: 8987
- omitted_middle_sha256: 762b87d9e3c208047d618e02fc565b2eeb4b11b8f112dcedf5dc1da929876741
- signals: smart_truncation

Head:
```text
import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timezone
import json
import socket
import time
import modules.dashboard_module
from pathlib import Path

from modules.dashboard_module import (
    get_dashboard_status,
    _dashboard_status_cache,
    _env_vars,
    _tcp_reachable,
    _tail_log,
    _read_json,
    _fleet_status,
    _vm_info
)

@pytest.fixture(autouse=True)
def clear_cache():
    _dashboard_status_cache.clear()
    _env_vars.cache_clear()
    yield
    _dashboard_status_cache.clear()
    _env_vars.cache_clear()

def test_get_dashboard_status_happy_path():
    # Mocking dependencies
    with patch('modules.dashboard_module._env_vars') as mock_env_vars, \
         patch('modules.dashboard_module.detect_resource_pressure') a
...[truncated]
```

Tail:
```text
value={"launched": 0}), \
         patch('modules.dashboard_module._vm_info', return_value={"vms": [], "total": 0, "online": 0}), \
         patch('modules.dashboard_module._tail_log', return_value=[]), \
         patch('modules.dashboard_module._LT_LOG_PATH', tunnel_log):

        result = get_dashboard_status()
        assert result["ok"] is True
        assert result["bridge"]["tunnel_url"] == "https://calm-harbor-test.loca.lt"


def test_get_dashboard_status_env_fallback():
    with patch('modules.dashboard_module._env_vars', return_value={"FALLBACK_TUNNEL_URL": "https://env-fallback.loca.lt"}), \
         patch('modules.dashboard_module.detect_resource_pressure', return_value={"status": "normal"}), \
         patch('modules.dashboard_module._fleet_status', return_value={"launched": 0}
...[truncated]
```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.
