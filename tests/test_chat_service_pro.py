"""Tests for chat provider routing with pro features (VM fallback)."""

import unittest
from unittest.mock import patch, MagicMock
from modules import chat_service

class FakeRequests:
    def __init__(self, responses=None):
        self.responses = list(responses) if responses else []
        self.calls = []
        self._is_vm_test = True # For identification in chat_service.py

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise RuntimeError("Unexpected call to requests.post")
        return self.responses.pop(0)

def clock_from(values):
    iterator = iter(values)
    return lambda: next(iterator)

class TestChatProviderPro(unittest.TestCase):
    @patch("modules.vm_relay.get_vm_status")
    @patch("modules.vm_relay.send_task_to_vm")
    @patch("time.sleep") # Don't actually sleep in tests
    def test_vm_fallback_success(self, mock_sleep, mock_send, mock_status):
        client = FakeRequests([])

        mock_status.side_effect = [
            {"online": True}, # Initial check
            {"online": True, "recent": []}, # Polling check 1 (not done)
            {"online": True, "recent": [{"task": "chat-fallback-testmark", "status": "done", "result": "hello from vm"}]} # Polling check 2 (done)
        ]

        # In modules/chat_service.py: marker = f"chat-fallback-{uuid.uuid4().hex[:8]}"
        mock_uuid = MagicMock()
        mock_uuid.hex = "testmarkerhex"

        with patch("uuid.uuid4", return_value=mock_uuid):
            result = chat_service.chat(
                "hello",
                env={},
                requests_client=client,
                clock=clock_from([1.0, 1.5])
            )

        self.assertEqual(result["response"], "hello from vm")
        self.assertEqual(result["model_used"], "vm/jules-worker")
        mock_send.assert_called_once()
        self.assertIn("chat-fallback-testmark", mock_send.call_args[0][0])

    @patch("modules.vm_relay.get_vm_status")
    @patch("modules.vm_relay.send_task_to_vm")
    @patch("time.sleep")
    def test_vm_fallback_waits_for_late_worker_result(self, mock_sleep, mock_send, mock_status):
        client = FakeRequests([])
        late_recent = [{"task": "chat-fallback-latemark", "status": "done", "result": "late but valid"}]
        mock_status.side_effect = (
            [{"online": True}]
            + [{"online": True, "recent": []} for _ in range(6)]
            + [{"online": True, "recent": late_recent}]
        )

        mock_uuid = MagicMock()
        mock_uuid.hex = "latemarkerhex"

        with patch("uuid.uuid4", return_value=mock_uuid):
            result = chat_service.chat(
                "wait for the late worker",
                env={"VM_CHAT_TIMEOUT_S": "20", "VM_CHAT_POLL_INTERVAL_S": "1"},
                requests_client=client,
                clock=clock_from([1.0, 18.0])
            )

        self.assertEqual(result["response"], "late but valid")
        self.assertEqual(result["model_used"], "vm/jules-worker")
        self.assertGreaterEqual(mock_sleep.call_count, 7)
        mock_send.assert_called_once()

    @patch("modules.codebase_analyzer.analyze_codebase")
    @patch("modules.vm_relay.get_vm_status")
    @patch("modules.vm_relay.send_task_to_vm")
    @patch("time.sleep")
    def test_codebase_request_attaches_local_analysis_context(
        self,
        mock_sleep,
        mock_send,
        mock_status,
        mock_analyze,
    ):
        client = FakeRequests([])
        mock_analyze.return_value = {
            "ok": True,
            "status": "ready",
            "summary": {"route_count": 75, "module_count": 33, "test_count": 44},
            "routes": {"count": 75, "items": [{"path": "/codebase/analyze", "methods": ["POST"]}]},
            "modules": {"count": 33, "public_modules": ["codebase_analyzer"]},
            "tests": {"count": 44},
            "frontend": {"present": True, "package_name": "dashboard-ui"},
            "integrations": [{"id": "codebase_analyzer", "ready": True}],
            "findings": [{"tone": "success", "title": "Ready", "detail": "Bounded handoff present."}],
            "handoff": {"route": "POST /codebase/analyze"},
        }
        mock_status.side_effect = [
            {"online": True},
            {
                "online": True,
                "recent": [
                    {
                        "task": "chat-fallback-contextmark",
                        "status": "done",
                        "result": "analyzed local snapshot",
                    }
                ],
            },
        ]
        mock_uuid = MagicMock()
        mock_uuid.hex = "contextmarkerhex"

        with patch("uuid.uuid4", return_value=mock_uuid):
            result = chat_service.chat(
                "analyze your own codebase on my local system",
                env={"VM_CHAT_TIMEOUT_S": "2", "VM_CHAT_POLL_INTERVAL_S": "1"},
                requests_client=client,
                clock=clock_from([1.0, 2.0]),
            )

        self.assertEqual(result["response"], "analyzed local snapshot")
        sent_context = mock_send.call_args.kwargs["context"]
        self.assertIn("LOCAL_CODEBASE_ANALYSIS_JSON", sent_context)
        self.assertIn("/codebase/analyze", sent_context)
        self.assertIn("codebase_analyzer", sent_context)
        mock_analyze.assert_called_once_with(max_files=1200, include_files=False)

    @patch("modules.vm_relay.get_vm_status")
    def test_health_includes_vm(self, mock_status):
        client = FakeRequests([])

        mock_status.return_value = {"online": True}

        result = chat_service.test_chat_providers(
            env={},
            requests_client=client,
            clock=clock_from([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["vm"]["status"], "ok")

    @patch("modules.vm_relay.get_vm_status")
    def test_health_marks_vm_degraded_when_recent_chat_exhausted(self, mock_status):
        client = FakeRequests([])
        exhausted = (
            "No LLM available - GEMINI_API_KEY is rate-limited and all "
            "OpenRouter free models failed. Check ~/.jules_worker.env"
        )
        mock_status.return_value = {
            "online": True,
            "recent": [
                {
                    "task": "[chat-fallback-deadbeef] flash fast",
                    "status": "done",
                    "result": exhausted,
                }
            ],
        }

        result = chat_service.test_chat_providers(
            env={},
            requests_client=client,
            clock=clock_from([1.0, 1.1]),
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["vm"]["status"], "degraded")
        self.assertIn("No LLM available", result["providers"]["vm"]["detail"])

if __name__ == "__main__":
    unittest.main()
